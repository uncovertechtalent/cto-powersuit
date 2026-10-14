#!/usr/bin/env python3
"""File the findings of a CTO review as GitHub Issues, and write one scorecard per area.

The findings file is JSON (see templates/review/findings.json):
  {"review": "...", "repo": "<owner>/<repo>", "date": "YYYY-MM-DD",
   "checks":   [{"area": "security", "skill": "/security:secrets", "status": "ran" | "not run", "note": "..."}],
   "verdicts": {"security": "one line"},
   "findings": [{"id": "SEC-1", "area": "security", "kind": "finding", "severity": "high",
                 "title": "...", "evidence": "...", "fix": "...", "check": "/security:secrets",
                 "private": false}]}

Labels follow the cockpit taxonomy (machinebehavior.io/inside/cockpit/): area:<key> for the eight areas and
kind:<kind>, with no space after the colon, plus severity:<level> with the fix-by windows of
/security:vuln-intake. A review files findings, decisions and actions, never leads.

Commands:
  check     <file>                         validate the file; exit 1 on any problem
  issues    <file> [--repo R] [--create] [--force]
                                           print every issue it would file (the default dry run); with --create,
                                           create the missing labels, skip items this review already filed (marked
                                           <date>/<id> in the body), hold items whose title an issue already has
                                           (--force files them), and create the rest
  scorecard <file> [--out F]               write the scorecards: per area, the checks run, findings by severity,
                                           and the one-line verdict

Guards: a string anywhere in the file that matches a secret pattern stops the run; on a repository that is not private
(public or internal), every security item and every item marked "private" stops the run, because an issue there
discloses it before the fix; an @mention or an owner/repo#n reference stops it too;
--create stops before any write without triage or write access. Needs gh for --create. Standard library only.
"""
import argparse, json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
AREAS = [  # key, title, label colour, label description: the cockpit's labels
    ("direction", "Direction", "7353D6", "CTO area: where the company stands, and the big technical decisions"),
    ("delivery", "Delivery", "C77D00", "CTO area: how code gets from an idea to production"),
    ("operations", "Operations", "12925F", "CTO area: keeping it running, and seeing what it does"),
    ("money", "Money", "D9533F", "CTO area: what the platform costs, and where the money goes"),
    ("security", "Security and risk", "D93445", "CTO area: protecting systems and data, staying compliant, testing for failure"),
    ("ai", "AI", "2F6FD6", "CTO area: running AI in the company, and being found by AI"),
    ("people", "People", "C63E92", "CTO area: hiring the team, and handing the work over"),
    ("knowledge", "Knowledge", "138C80", "CTO area: the layer under every module, what agents know and how they answer"),
]
KINDS = [
    ("finding", "8E7A55", "Kind: a gap that an audit or a review found"),
    ("decision", "6C7680", "Kind: a choice still to make"),
    ("action", "56605B", "Kind: work to do"),
    ("lead", "9A8C00", "Kind: a sales lead or an application"),
]
SEVERITIES = [  # the fix-by windows of /security:vuln-intake
    ("critical", "B60205", "Severity: fix within 7 days"),
    ("high", "D93F0B", "Severity: fix within 30 days"),
    ("medium", "FBCA04", "Severity: fix within 90 days"),
    ("low", "0E8A16", "Severity: fix within 180 days"),
]
AREA_KEYS = [a[0] for a in AREAS]
TITLES = {a[0]: a[1] for a in AREAS}
FILED_KINDS = ("finding", "decision", "action")
SEV_KEYS = [s[0] for s in SEVERITIES]
LABELS = ([(f"area:{k}", c, d) for k, _, c, d in AREAS] + [(f"kind:{k}", c, d) for k, c, d in KINDS]
          + [(f"severity:{k}", c, d) for k, c, d in SEVERITIES])
FILED_LABELS = [l for l in LABELS if l[0] != "kind:lead"]  # what --create adds: a review files no lead
MENTION = re.compile(r"(?:^|[\s(\[])(?:@[A-Za-z0-9][A-Za-z0-9-]*|[\w.-]+/[\w.-]+#\d+)")  # pings a person or cross-links an issue
MULTILINE = re.compile(r"\.(evidence|fix)$")  # the only fields that may span lines
SECRET = re.compile(r"(\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-[A-Za-z0-9]{32,}|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}"
                    r"|\bgithub_pat_[A-Za-z0-9_]{40,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
ID_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
REPO_RX = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
MARKER = "<!-- powersuit-finding: {} -->"  # <review date>/<id>
DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WRITERS = ("TRIAGE", "WRITE", "MAINTAIN", "ADMIN")
MAX_TITLE = 300
VERDICT_TODO = "<one line: where this area stands and the first thing to do>"


def bad_chars(text):
    """Control and format characters (bidi marks, zero widths, soft hyphens) and line or paragraph separators."""
    return [c for c in text if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") and c not in "\n\t"]


def validate(doc):
    problems = []
    if not isinstance(doc, dict) or not isinstance(doc.get("findings"), list):
        return ["the file needs a findings list"]
    seen = set()
    for i, f in enumerate(doc["findings"]):
        at = f"findings[{i}]" + (f" {f.get('id')}" if isinstance(f, dict) and f.get("id") else "")
        if not isinstance(f, dict):
            problems.append(f"{at}: not an object")
            continue
        fid = str(f.get("id", ""))
        if not ID_RX.match(fid):
            problems.append(f"{at}: id {fid!r}, want letters, digits, dot, dash or underscore, up to 40")
        elif fid in seen:
            problems.append(f"{at}: id {fid} appears twice")
        seen.add(fid)
        if f.get("area") not in AREA_KEYS:
            problems.append(f"{at}: area {f.get('area')!r}, want one of {', '.join(AREA_KEYS)}")
        if f.get("kind") not in FILED_KINDS:
            problems.append(f"{at}: kind {f.get('kind')!r}, want one of {', '.join(FILED_KINDS)} (a review files no leads)")
        sev = f.get("severity")
        if f.get("kind") == "finding" and sev not in SEV_KEYS:
            problems.append(f"{at}: a finding needs a severity, one of {', '.join(SEV_KEYS)}")
        elif sev is not None and sev not in SEV_KEYS:
            problems.append(f"{at}: severity {sev!r}, want one of {', '.join(SEV_KEYS)}")
        title = f.get("title")
        if not isinstance(title, str) or not title.strip():
            problems.append(f"{at}: no title")
        else:
            if len(title) > MAX_TITLE:
                problems.append(f"{at}: title has {len(title)} characters, at most {MAX_TITLE}")
            if "\n" in title or "\t" in title:
                problems.append(f"{at}: title holds a line break or a tab")
        for key in ("evidence", "fix"):
            if not isinstance(f.get(key), str) or not f[key].strip():
                problems.append(f"{at}: no {key}")
        for key in ("title", "evidence", "fix"):
            if isinstance(f.get(key), str) and MENTION.search(f[key]):
                problems.append(f"{at}: {key} has an @mention or an owner/repo#n reference, which notifies people or "
                                "cross-links issues; write the handle or the reference in a code span")
        if f.get("private") not in (None, True, False):
            problems.append(f"{at}: private must be true or false")
    for key, kind in (("checks", list), ("verdicts", dict)):
        if not isinstance(doc.get(key) or kind(), kind):
            problems.append(f"{key}: want {'a list of checks' if kind is list else 'an object of area to one line'}")
            return problems
    for i, c in enumerate(doc.get("checks") or []):
        if not isinstance(c, dict) or c.get("area") not in AREA_KEYS or not c.get("skill") or c.get("status") not in ("ran", "not run"):
            problems.append(f"checks[{i}]: want area (one of the eight), skill, and status 'ran' or 'not run'")
    for k, v in (doc.get("verdicts") or {}).items():
        if k not in AREA_KEYS or not isinstance(v, str) or "\n" in v:
            problems.append(f"verdicts.{k}: want an area key and one line")
    problems += scan(doc, "")
    return problems


def scan(value, path):
    """Every string in the file, at any depth: no secret pattern, no control or format character."""
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in scan(v, f"{path}.{k}" if path else str(k))]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in scan(v, f"{path}[{i}]")]
    if not isinstance(value, str):
        return []
    out = []
    if SECRET.search(value):
        out.append(f"{path}: matches a secret pattern; mask the value (kind, prefix, hash prefix)")
    if bad_chars(value):
        out.append(f"{path}: holds a control or format character")
    if ("\n" in value or "\r" in value) and not MULTILINE.search(path):
        out.append(f"{path}: holds a line break; only evidence and fix may span lines")
    return out


def marker_of(f, doc):
    return MARKER.format(f"{doc.get('date') or 'undated'}/{f['id']}")


def cell(text):
    return str(text).replace("|", "\\|")


def labels_of(f):
    out = [f"area:{f['area']}", f"kind:{f['kind']}"]
    if f.get("severity"):
        out.append(f"severity:{f['severity']}")
    return out


def body_of(f, doc):
    lines = []
    if f.get("severity"):
        lines += [f"Severity: {f['severity']}. Area: {TITLES[f['area']]}. Kind: {f['kind']}.", ""]
    else:
        lines += [f"Area: {TITLES[f['area']]}. Kind: {f['kind']}.", ""]
    lines += ["## Evidence", "", f["evidence"].strip(), "", "## Fix", "", f["fix"].strip(), ""]
    if f.get("check"):
        lines += [f"Found by `{f['check']}`" + (f" in {doc['review']}." if doc.get("review") else "."), ""]
    lines += [f"<sub>Filed by /fit:file-findings from the CTO Powersuit review. Item {f['id']} of the review of {doc.get('date') or 'an undated day'}.</sub>",
              marker_of(f, doc)]
    return "\n".join(lines) + "\n"


def gh(*args, input_text=None):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, input=input_text)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout


def cmd_check(doc):
    problems = validate(doc)
    for p in problems:
        print("FAIL " + p)
    n = len(doc.get("findings") or []) if isinstance(doc, dict) else 0
    print(f"{n} items, {len(problems)} problems")
    return 1 if problems else 0


def existing_issues(repo):
    """Every issue and pull request of the repository, open and closed, read page by page."""
    out = gh("api", "--paginate", f"repos/{repo}/issues?state=all&per_page=100",
             "--jq", ".[] | {number, title, body, url: .html_url, state}")
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def cmd_issues(doc, repo, create, force=False):
    problems = validate(doc)
    if problems:
        for p in problems:
            print("FAIL " + p)
        print(f"{len(problems)} problems: nothing filed")
        return 1
    repo = repo or doc.get("repo")
    findings = doc["findings"]
    if create:
        if not (repo and REPO_RX.match(repo)):
            print("FAIL --create needs --repo <owner>/<repo> or a repo in the file")
            return 1
        if not DATE_RX.match(str(doc.get("date") or "")):
            print("FAIL --create needs the review date (YYYY-MM-DD) in the file: it marks each issue as this review's")
            return 1
        try:
            info = json.loads(gh("repo", "view", repo, "--json", "visibility,viewerPermission"))
            if info.get("viewerPermission") not in WRITERS:
                print(f"FAIL {repo}: permission {info.get('viewerPermission')}; filing needs triage or write access. "
                      "Give the team this file and the dry-run output, and the team runs --create.")
                return 1
            closed_door = [f["id"] for f in findings if f["area"] == "security" or f.get("private")]
            if info.get("visibility") != "PRIVATE" and closed_door:
                print(f"FAIL {repo} is {str(info.get('visibility')).lower()}: an issue there discloses a security item before the fix. File these "
                      f"privately (a security advisory, or a private tracker), then run again without them: {', '.join(closed_door)}")
                return 1
            have = {l["name"].lower() for l in json.loads(gh("label", "list", "--repo", repo, "--limit", "1000", "--json", "name"))}
            existing = existing_issues(repo)
            made = []
            for name, color, desc in FILED_LABELS:
                if name not in have:  # GitHub label names ignore case
                    gh("label", "create", name, "--repo", repo, "--color", color, "--description", desc)
                    made.append(name)
        except (RuntimeError, ValueError) as e:
            print(f"FAIL {e}")
            return 1
        print(f"labels: {len(made)} created" + (f" ({', '.join(made)})" if made else "") + f", {len(FILED_LABELS) - len(made)} present")
    else:
        existing = []
        print(f"dry run: nothing is created. {len(findings)} issues for {repo or '<repo>'}:\n")
    filed, skipped, held = 0, 0, 0
    for f in findings:
        labels = labels_of(f)
        body = body_of(f, doc)
        mine = next((i for i in existing if marker_of(f, doc) in (i.get("body") or "")), None)
        if mine:
            print(f"{f['id']}: already filed by this review as {mine['url']} ({mine.get('state', '').lower()})")
            skipped += 1
            continue
        same = next((i for i in existing if i.get("title") == f["title"]), None)
        if same and not force:
            print(f"HOLD {f['id']}: {same['url']} ({same.get('state', '').lower()}) has the same title. "
                  "Check it; run again with --force to file this item anyway.")
            held += 1
            continue
        if not create:
            print(f"--- {f['id']}: {f['title']}\nlabels: {', '.join(labels)}\n\n{body}")
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as t:
            t.write(body)
        args = ["issue", "create", "--repo", repo, "--title", f["title"], "--body-file", t.name]
        for l in labels:
            args += ["--label", l]
        try:
            url = gh(*args).strip().splitlines()[-1]
        except RuntimeError as e:
            print(f"FAIL {f['id']}: {e}")
            return 1
        finally:
            Path(t.name).unlink(missing_ok=True)
        print(f"{f['id']}: {url}")
        filed += 1
    if create:
        print(f"{filed} filed, {skipped} already filed, {held} held")
    return 0


def scorecard(doc):
    checks, findings, verdicts = doc.get("checks") or [], doc["findings"], doc.get("verdicts") or {}
    used = [k for k in AREA_KEYS if any(c["area"] == k for c in checks) or any(f["area"] == k for f in findings)]
    head = doc.get("review") or "CTO Powersuit review"
    meta = ", ".join(x for x in (doc.get("date"), f"repository {doc['repo']}" if doc.get("repo") else None) if x)
    out = [f"# Scorecard: {head}", ""]
    if meta:
        out += [meta[:1].upper() + meta[1:] + ".", ""]
    out += ["| Area | Checks run | Critical | High | Medium | Low | Verdict |", "|---|---:|---:|---:|---:|---:|---|"]
    def count(k, sev):
        return sum(1 for f in findings if f["area"] == k and f["kind"] == "finding" and f.get("severity") == sev)
    for k in used:
        ran = sum(1 for c in checks if c["area"] == k and c["status"] == "ran")
        out.append(f"| {TITLES[k]} | {ran} | " + " | ".join(str(count(k, s)) for s in SEV_KEYS)
                   + f" | {cell(verdicts.get(k, VERDICT_TODO))} |")
    for k in used:
        out += ["", f"## {TITLES[k]}", "", "| Check | Status |", "|---|---|"]
        mine = [c for c in checks if c["area"] == k]
        out += [f"| `{cell(c['skill'])}` | {c['status']}" + (f": {cell(c['note'])}" if c.get("note") else "") + " |" for c in mine] or ["| none recorded | |"]
        out += ["", "| Severity | Findings |", "|---|---:|"] + [f"| {s.capitalize()} | {count(k, s)} |" for s in SEV_KEYS]
        dec = sum(1 for f in findings if f["area"] == k and f["kind"] == "decision")
        act = sum(1 for f in findings if f["area"] == k and f["kind"] == "action")
        ids = [f["id"] for f in findings if f["area"] == k]
        out += ["", f"Decisions open: {dec}. Actions: {act}." + (f" Items: {', '.join(ids)}." if ids else ""),
                "", f"Verdict: {verdicts.get(k, VERDICT_TODO)}"]
    return "\n".join(out) + "\n"


def cmd_scorecard(doc, out):
    problems = validate(doc)
    if problems:
        for p in problems:
            print("FAIL " + p)
        return 1
    text = scorecard(doc)
    if out:
        Path(out).write_text(text)
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 0


def main():
    ap = argparse.ArgumentParser(description="File the findings of a CTO review as GitHub Issues, and write the scorecards")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "issues", "scorecard"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name == "issues":
            p.add_argument("--repo")
            p.add_argument("--create", action="store_true", help="create the labels and issues; without it, a dry run")
            p.add_argument("--force", action="store_true", help="file an item even when an issue has its title")
        if name == "scorecard":
            p.add_argument("--out")
    args = ap.parse_args()
    try:
        doc = json.loads(Path(args.file).read_text())
    except (OSError, ValueError) as e:
        print(f"FAIL {args.file}: {e}")
        sys.exit(1)
    if args.cmd == "check":
        sys.exit(cmd_check(doc))
    if args.cmd == "issues":
        sys.exit(cmd_issues(doc, args.repo, args.create, args.force))
    sys.exit(cmd_scorecard(doc, args.out))


if __name__ == "__main__":
    main()
