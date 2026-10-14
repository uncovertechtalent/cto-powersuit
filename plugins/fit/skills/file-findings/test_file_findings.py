#!/usr/bin/env python3
"""Tests for file_findings.py. A fake gh on PATH answers from a state file and logs every call, so the tests see
exactly what the script would do on GitHub. Standard library only, Python 3.9+.

Usage: python3 plugins/fit/skills/file-findings/test_file_findings.py [-v]
"""
import importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "file_findings.py"
TEMPLATE = HERE.parent.parent / "templates" / "review" / "findings.json"
VERBOSE = "-v" in sys.argv
spec = importlib.util.spec_from_file_location("file_findings", SCRIPT)
ff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ff)

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
state_path, log_path = os.environ["FAKE_GH_STATE"], os.environ["FAKE_GH_LOG"]
state = json.load(open(state_path))
a = sys.argv[1:]
with open(log_path, "a") as f:
    f.write(json.dumps(a) + "\n")
def opt(name):
    return a[a.index(name) + 1] if name in a else None
if a[:2] == ["repo", "view"]:
    if state.get("fail_view"):
        sys.stderr.write("GraphQL: Could not resolve to a Repository\n"); sys.exit(1)
    print(json.dumps({"visibility": state["visibility"], "viewerPermission": state.get("permission", "WRITE")}))
elif a[:2] == ["label", "list"]:
    print(json.dumps([{"name": n} for n in state["labels"]]))
elif a[:2] == ["label", "create"]:
    if state.get("fail_label"):
        sys.stderr.write("HTTP 403: Resource not accessible by integration\n"); sys.exit(1)
    state["labels"].append(a[2])
elif a[0] == "api" and "--paginate" in a and "/issues?state=all" in a[2]:
    for i in state["issues"]:
        print(json.dumps({"number": i["number"], "title": i["title"], "body": i.get("body", ""), "url": i["url"],
                          "state": i.get("state", "OPEN")}))
elif a[:2] == ["issue", "create"]:
    if state.get("fail_create"):
        sys.stderr.write("could not add label: 'area:delivery' not found\n"); sys.exit(1)
    n = 100 + len(state["issues"])
    labels = [a[i + 1] for i, x in enumerate(a) if x == "--label"]
    body = open(opt("--body-file")).read()
    url = f"https://github.com/{opt('--repo')}/issues/{n}"
    state["issues"].append({"number": n, "title": opt("--title"), "body": body, "url": url, "labels": labels})
    print(url)
else:
    sys.stderr.write("fake gh: unexpected call\n"); sys.exit(2)
json.dump(state, open(state_path, "w"))
'''


def finding(**kw):
    f = {"id": "SEC-1", "area": "security", "kind": "finding", "severity": "high", "title": "Actions are pinned by tag",
         "evidence": "`.github/workflows/ci.yml:7` uses `actions/checkout@v4`.", "fix": "Pin to the commit SHA.",
         "check": "/security:supply-chain"}
    f.update(kw)
    return f


def doc(*findings, **kw):
    d = {"review": "Pilot review", "repo": "acme/platform", "date": "2026-10-14", "findings": list(findings),
         "checks": [{"area": "security", "skill": "/security:supply-chain", "status": "ran"},
                    {"area": "security", "skill": "/security:threat-model", "status": "not run", "note": "no notes"},
                    {"area": "delivery", "skill": "/sdlc:sdlc-audit", "status": "ran"}],
         "verdicts": {"security": "Pins and secrets need a week of work."}}
    d.update(kw)
    return d


class Env:
    def __init__(self, tmp, visibility="PRIVATE", labels=(), issues=(), **flags):
        self.tmp = Path(tmp)
        (self.tmp / "bin").mkdir()
        gh = self.tmp / "bin" / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.state, self.log = self.tmp / "state.json", self.tmp / "log.jsonl"
        self.state.write_text(json.dumps(dict({"visibility": visibility, "labels": list(labels), "issues": list(issues)}, **flags)))
        self.log.write_text("")

    def run(self, cmd, d, *extra):
        f = self.tmp / "findings.json"
        f.write_text(json.dumps(d))
        env = dict(os.environ, PATH=f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}",
                   FAKE_GH_STATE=str(self.state), FAKE_GH_LOG=str(self.log))
        p = subprocess.run([sys.executable, str(SCRIPT), cmd, str(f), *extra], capture_output=True, text=True, env=env)
        if VERBOSE:
            print(p.stdout + p.stderr)
        return p

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]

    def data(self):
        return json.loads(self.state.read_text())


def problems_for(f):
    return ff.validate(doc(f))


def case_template_valid():
    d = json.loads(TEMPLATE.read_text())
    p = ff.validate(d)
    return [] if not p else [f"template: {p}"]


def case_validation():
    out = []
    bad = {
        "area": finding(area="infra"), "lead": finding(kind="lead"), "no severity": finding(severity=None),
        "bad severity": finding(kind="action", severity="urgent"), "long title": finding(title="x" * 301),
        "newline in title": finding(title="a\nb"), "bidi in title": finding(title="safe‮txt.exe"),
        "zero width": finding(evidence="see​this"), "no evidence": finding(evidence=" "), "no fix": finding(fix=None),
        "bad id": finding(id="SEC 1"), "secret": finding(evidence="key AKIA" + "Q7RZ4T2XK9W3B6MN in .env"),
        "secret in title": finding(title="Token ghp_" + "a" * 36 + " leaked"),
    }
    for name, f in bad.items():
        if not problems_for(f):
            out.append(f"{name}: accepted")
    if not ff.validate(doc(finding(), finding())):
        out.append("duplicate ids: accepted")
    if not ff.validate(doc(finding(), checks=[{"area": "security", "skill": "/x", "status": "maybe"}])):
        out.append("bad check status: accepted")
    if not ff.validate(doc(finding(), verdicts={"infra": "x"})):
        out.append("verdict for an unknown area: accepted")
    key = "AKIA" + "Q7RZ4T2XK9W3B6MN"
    for name, d in (("secret in review", doc(finding(), review=f"Review {key}")),
                    ("secret in verdict", doc(finding(), verdicts={"security": f"rotate {key}"})),
                    ("secret in check note", doc(finding(), checks=[{"area": "security", "skill": "/x", "status": "ran", "note": key}])),
                    ("bidi in review", doc(finding(), review="Review \u202e")),
                    ("private not a boolean", doc(finding(private="yes"))),
                    ("line break in a check note", doc(finding(), checks=[{"area": "security", "skill": "/x", "status": "ran", "note": "a\nb"}])),
                    ("line break in review", doc(finding(), review="Pilot\nreview")),
                    ("line break in check", doc(finding(check="/x\n/y"))),
                    ("mention in evidence", doc(finding(evidence="Ask @alice about it"))),
                    ("mention at start", doc(finding(fix="@team-sec rotates it"))),
                    ("cross-repo reference", doc(finding(evidence="Same as acme/infra#12"))),
                    ("verdicts as a list", doc(finding(), verdicts=["x"])),
                    ("checks as an object", doc(finding(), checks={"a": 1}))):
        if not ff.validate(d):
            out.append(f"{name}: accepted")
    ok = [finding(), finding(id="DEL-2", area="delivery", kind="decision", severity=None),
          finding(id="OPS-3", area="operations", kind="action", severity="low"), finding(id="X-4", evidence="multi\nline\tok"),
          finding(id="X-5", evidence="uses `actions/checkout@v4` and issue #12; mail ops@example.com"),
          finding(id="X-6", fix="ask `@alice`, see `acme/infra#12`")]
    for f in ok:
        if problems_for(f):
            out.append(f"valid {f['id']} rejected: {problems_for(f)}")
    return out


def case_labels():
    names = [n for n, _, _ in ff.LABELS]
    out = []
    want = [f"area:{k}" for k in ("direction", "delivery", "operations", "money", "security", "ai", "people", "knowledge")]
    want += [f"kind:{k}" for k in ("finding", "decision", "action", "lead")] + [f"severity:{k}" for k in ("critical", "high", "medium", "low")]
    if names != want:
        out.append(f"labels {names}")
    if any(" " in n for n in names):
        out.append("a label has a space")
    if [n for n, _, _ in ff.FILED_LABELS] != [n for n in want if n != "kind:lead"]:
        out.append(f"filed labels {[n for n, _, _ in ff.FILED_LABELS]}")
    if ff.labels_of(finding(kind="decision", severity=None)) != ["area:security", "kind:decision"]:
        out.append("a decision without severity gets a severity label")
    return out


def case_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp)
        p = e.run("issues", doc(finding(), finding(id="DEL-2", area="delivery", kind="decision", severity=None, title="Decide the branch rule")))
        out = []
        if p.returncode != 0:
            out.append(f"exit {p.returncode}")
        if e.calls():
            out.append(f"dry run called gh: {e.calls()}")
        for want in ("dry run: nothing is created. 2 issues for acme/platform", "--- SEC-1: Actions are pinned by tag",
                     "labels: area:security, kind:finding, severity:high", "labels: area:delivery, kind:decision\n",
                     "## Evidence", "## Fix", "Found by `/security:supply-chain` in Pilot review.", "<!-- powersuit-finding: 2026-10-14/SEC-1 -->"):
            if want not in p.stdout:
                out.append(f"missing {want!r}")
        return out


def case_create():
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, labels=["bug", "area:security", "kind:finding"])
        d = doc(finding(), finding(id="DEL-2", area="delivery", kind="decision", severity=None, title="Decide the branch rule"))
        p = e.run("issues", d, "--create")
        out = []
        if p.returncode != 0:
            out.append(f"exit {p.returncode}: {p.stdout}")
        made = [c[2] for c in e.calls() if c[:2] == ["label", "create"]]
        if "area:security" in made or "kind:finding" in made or "kind:lead" in made or len(made) != 13:
            out.append(f"created labels {made}")
        lc = next((c for c in e.calls() if c[:3] == ["label", "create", "area:delivery"]), [])
        if not lc or lc[lc.index("--color") + 1] != "C77D00":
            out.append(f"area:delivery colour: {lc}")
        issues = e.data()["issues"]
        if [i["title"] for i in issues] != ["Actions are pinned by tag", "Decide the branch rule"]:
            out.append(f"issues {issues}")
        elif issues[0]["labels"] != ["area:security", "kind:finding", "severity:high"] or issues[1]["labels"] != ["area:delivery", "kind:decision"]:
            out.append(f"issue labels {[i['labels'] for i in issues]}")
        if "2 filed, 0 already filed" not in p.stdout or "labels: 13 created" not in p.stdout:
            out.append(f"summary: {p.stdout}")
        p2 = e.run("issues", d, "--create")
        if "0 filed, 2 already filed" not in p2.stdout or len(e.data()["issues"]) != 2:
            out.append(f"second run filed again: {p2.stdout}")
        if any(c[:2] == ["label", "create"] for c in e.calls()[len(made) + 5:]):
            out.append("second run created labels again")
        return out


def case_dedupe_by_marker_and_title():
    out = []
    old = [{"number": 7, "title": "Renamed by the team", "body": "x\n<!-- powersuit-finding: 2026-10-14/SEC-1 -->", "url": "u7", "state": "CLOSED"},
           {"number": 8, "title": "Decide the branch rule", "body": "", "url": "u8"},
           {"number": 9, "title": "Old review", "body": "<!-- powersuit-finding: 2026-09-01/OPS-1 -->", "url": "u9"}]
    d = doc(finding(), finding(id="DEL-2", area="delivery", kind="decision", severity=None, title="Decide the branch rule"),
            finding(id="OPS-1", area="operations", kind="action", severity=None, title="Write the first runbook"))
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, labels=[n for n, _, _ in ff.LABELS], issues=old)
        p = e.run("issues", d, "--create")
        if "SEC-1: already filed by this review as u7 (closed)" not in p.stdout:
            out.append(f"marker match: {p.stdout}")
        if "HOLD DEL-2: u8" not in p.stdout:
            out.append(f"title-only match not held: {p.stdout}")
        titles = [i["title"] for i in e.data()["issues"][3:]]
        if titles != ["Write the first runbook"]:
            out.append(f"filed {titles}; want only OPS-1 (an older review's marker is not this review's)")
        if "1 filed, 1 already filed, 1 held" not in p.stdout:
            out.append(f"summary: {p.stdout}")
        p = e.run("issues", d, "--create", "--force")
        if [i["title"] for i in e.data()["issues"][4:]] != ["Decide the branch rule"]:
            out.append(f"--force did not file the held item: {p.stdout}")
    return out


def case_public_repo_guard():
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, visibility="PUBLIC")
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "is public" not in p.stdout or "SEC-1" not in p.stdout:
            out.append(f"public + security finding: exit {p.returncode} {p.stdout}")
        if any(c[:2] in (["issue", "create"], ["label", "create"]) for c in e.calls()):
            out.append("public guard created something")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, visibility="PUBLIC")
        p = e.run("issues", doc(finding(kind="action", severity=None, title="Rotate the keys")), "--create")
        if p.returncode != 1 or "SEC-1" not in p.stdout:
            out.append(f"public + security action: exit {p.returncode} {p.stdout}")
        p = e.run("issues", doc(finding(id="AI-1", area="ai", private=True)), "--create")
        if p.returncode != 1 or "AI-1" not in p.stdout:
            out.append(f"public + private item: exit {p.returncode} {p.stdout}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, visibility="INTERNAL")
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "is internal" not in p.stdout or e.data()["issues"]:
            out.append(f"internal + security finding: exit {p.returncode} {p.stdout}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, visibility="PUBLIC")
        p = e.run("issues", doc(finding(id="AI-1", area="ai", private=True)), "--create")
        if p.returncode != 1 or "AI-1" not in p.stdout:
            out.append(f"public + private item: exit {p.returncode} {p.stdout}")
        p = e.run("issues", doc(finding(id="DEL-1", area="delivery"), finding(id="AI-2", area="ai", private=False, title="Agents share one token")), "--create")
        if p.returncode != 0 or len(e.data()["issues"]) != 2:
            out.append(f"public + delivery finding and a non-private ai item: exit {p.returncode} {p.stdout}")
    return out


def case_refusals():
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp)
        p = e.run("issues", doc(finding(area="infra")), "--create")
        if p.returncode != 1 or e.calls():
            out.append("an invalid file reached gh")
        p = e.run("issues", doc(finding(), repo=None), "--create")
        if p.returncode != 1 or "--create needs --repo" not in p.stdout:
            out.append("--create without a repo")
        p = e.run("issues", doc(finding(), repo=None), "--create", "--repo", "other/repo")
        if p.returncode != 0 or e.data()["issues"][0]["url"] != "https://github.com/other/repo/issues/100":
            out.append(f"--repo flag: {p.stdout}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, fail_view=True)
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "Could not resolve" not in p.stdout:
            out.append(f"repo not found: exit {p.returncode}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, permission="READ")
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "needs triage or write access" not in p.stdout or any(c[0] != "repo" for c in e.calls()):
            out.append(f"read-only access: exit {p.returncode}, calls {e.calls()}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp)
        p = e.run("issues", doc(finding(), date=None), "--create")
        if p.returncode != 1 or "needs the review date" not in p.stdout or e.calls():
            out.append(f"no date: exit {p.returncode}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, fail_label=True)
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "FAIL gh label create: HTTP 403" not in p.stdout or "Traceback" in p.stderr:
            out.append(f"label create failure: exit {p.returncode} {p.stdout} {p.stderr[-200:]}")
        if e.data()["issues"]:
            out.append("filed an issue after a label failure")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, labels=[n.upper() for n, _, _ in ff.LABELS])
        p = e.run("issues", doc(finding()), "--create")
        if any(c[:2] == ["label", "create"] for c in e.calls()) or "labels: 0 created" not in p.stdout:
            out.append(f"labels that differ in case were created again: {p.stdout}")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp, fail_create=True)
        p = e.run("issues", doc(finding()), "--create")
        if p.returncode != 1 or "FAIL SEC-1" not in p.stdout:
            out.append(f"failed create: exit {p.returncode}")
    return out


def case_check_command():
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp)
        out = []
        p = e.run("check", doc(finding()))
        if p.returncode != 0 or "1 items, 0 problems" not in p.stdout:
            out.append(f"valid: {p.stdout}")
        p = e.run("check", doc(finding(kind="lead")))
        if p.returncode != 1 or "a review files no leads" not in p.stdout:
            out.append(f"invalid: {p.stdout}")
        return out


def case_scorecard():
    d = doc(finding(), finding(id="SEC-2", severity="critical", title="Key in history"),
            finding(id="SEC-3", kind="action", severity=None, title="Rotate keys"),
            finding(id="SEC-4", kind="action", severity="high", title="Pin the actions"),
            finding(id="DEL-1", area="delivery", severity="medium", title="No tests before deploy"))
    text = ff.scorecard(d)
    out = []
    for want in ("# Scorecard: Pilot review", "2026-10-14, repository acme/platform.",
                 "| Delivery | 1 | 0 | 0 | 1 | 0 | " + ff.VERDICT_TODO + " |",
                 "| Security and risk | 1 | 1 | 1 | 0 | 0 | Pins and secrets need a week of work. |",
                 "| `/security:threat-model` | not run: no notes |", "Decisions open: 0. Actions: 2. Items: SEC-1, SEC-2, SEC-3, SEC-4.",
                 "Verdict: Pins and secrets need a week of work."):
        if want not in text:
            out.append(f"missing {want!r}")
    if "## Money" in text:
        out.append("an area with no checks and no findings got a section")
    if text.index("| Delivery |") > text.index("| Security and risk |"):
        out.append("areas are not in cockpit order")
    piped = ff.scorecard(doc(finding(), verdicts={"security": "Fix a|b first"},
                             checks=[{"area": "security", "skill": "/x", "status": "not run", "note": "no a|b access"}]))
    if "Fix a\\|b first |" not in piped or "no a\\|b access |" not in piped:
        out.append("a | in a verdict or a note is not escaped")
    with tempfile.TemporaryDirectory() as tmp:
        e = Env(tmp)
        target = Path(tmp) / "scorecard.md"
        p = e.run("scorecard", d, "--out", str(target))
        if p.returncode != 0 or target.read_text() != text:
            out.append("--out does not write the same text")
        p = e.run("scorecard", doc(finding(area="x")))
        if p.returncode != 1:
            out.append("scorecard of an invalid file")
    return out


CASES = [case_template_valid, case_validation, case_labels, case_dry_run, case_create, case_dedupe_by_marker_and_title,
         case_public_repo_guard, case_refusals, case_check_command, case_scorecard]


def main():
    failures = 0
    for case in CASES:
        problems = case()
        failures += bool(problems)
        print(f"{'ok  ' if not problems else 'FAIL'} {case.__name__}")
        for p in problems:
            print("     " + p)
    print(f"{len(CASES)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
