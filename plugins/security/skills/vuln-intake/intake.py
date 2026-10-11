#!/usr/bin/env python3
"""Turn vulnerability alerts into ticket drafts with a fix-by date per severity.

Inputs, any mix:
  --dependabot FILE   output of: gh api --paginate --slurp "repos/<o>/<r>/dependabot/alerts?state=open&per_page=100"
  --osv FILE          output of: osv_query.py <sbom> --json   (from the supply-chain skill)
  --existing FILE     output of: gh issue list --label security --state all --limit 500 --json number,title,state
  --policy FILE       docs/security/vuln-policy.md; its fix-by table overrides the default windows

One draft per advisory and package. The window starts on the day the alert was created (Dependabot) or
on --today (an OSV lookup has no alert date). A draft whose key already appears in an issue title is
reported as tracked and gets no new draft. Prints the drafts; creates nothing.

Usage:
  intake.py [--dependabot FILE] [--osv FILE] [--existing FILE] [--policy FILE] [--today YYYY-MM-DD] [--json]

Standard library only, Python 3.9+.
"""
import argparse, datetime, json, re, sys

WINDOWS = {"critical": (7, "P0"), "high": (30, "P1"), "medium": (90, "P2"), "low": (180, "P3"), "unknown": (30, "P1")}
POLICY_ROW = re.compile(r"^\|\s*(critical|high|medium|low|unknown)\s*\|[^|]*?(\d+)\s*days?[^|]*\|\s*`?(P\d)`?\s*\|", re.I | re.M)


def windows(policy_text=None):
    w, parsed = dict(WINDOWS), set()
    for level, n, prio in POLICY_ROW.findall(policy_text or ""):
        w[level.lower()] = (int(n), prio.upper())
        parsed.add(level.lower())
    if "unknown" not in parsed:
        w["unknown"] = w["high"]  # an unrated finding takes the high window until the owner sets a level
    return w


def level(raw):
    raw = (raw or "unknown").lower()
    return {"moderate": "medium"}.get(raw, raw if raw in WINDOWS else "unknown")


def from_dependabot(alerts):
    for a in alerts:
        adv, dep = a.get("security_advisory") or {}, a.get("dependency") or {}
        pkg = dep.get("package") or {}
        fixed = ((a.get("security_vulnerability") or {}).get("first_patched_version") or {}).get("identifier")
        yield {"id": adv.get("ghsa_id") or f"alert-{a.get('number')}", "aliases": [x for x in [adv.get("cve_id")] if x],
               "package": f"{pkg.get('ecosystem', '?')}/{pkg.get('name', '?')}", "where": dep.get("manifest_path", ""),
               "severity": level(adv.get("severity")), "fixed": [fixed] if fixed else [], "summary": adv.get("summary", ""),
               "since": (a.get("created_at") or "")[:10] or None, "link": a.get("html_url", "")}


def from_osv(report):
    for v in report.get("vulns", []):
        yield {"id": v["id"], "aliases": v.get("aliases", []), "package": v["purl"].split("@", 1)[0], "where": v["purl"],
               "severity": level(v.get("severity")), "fixed": v.get("fixed", []), "summary": v.get("summary", ""),
               "since": None, "link": f"https://osv.dev/vulnerability/{v['id']}"}


def drafts(findings, today, w, existing_titles=()):
    out, tracked, seen = [], [], set()
    for f in findings:
        key = f"{f['id']} {f['package']}"
        ids = [f["id"]] + f["aliases"]
        if key in seen or any(f"{i} " in t and f["package"] in t for t in existing_titles for i in ids):
            if key not in seen:
                tracked.append(key)
            seen.add(key)
            continue
        seen.add(key)
        days, prio = w[f["severity"]]
        since = datetime.date.fromisoformat(f["since"]) if f["since"] else today
        fix_by = since + datetime.timedelta(days=days)
        title = f"[security] {f['id']} {f['package']}: fix by {fix_by.isoformat()}"
        body = "\n".join([
            "## Problem", "",
            f"{f['package']} ({f['where']}) has the known vulnerability {f['id']}"
            + (f" ({', '.join(f['aliases'])})" if f["aliases"] else "") + f", severity {f['severity']}. {f['summary']}".rstrip(),
            "", f"Advisory: {f['link']}", f"Reached the team: {since.isoformat()}. Fix-by window for {f['severity']}: {days} days.", "",
            "## Acceptance criteria", "",
            f"- The dependency is at {' or '.join(f['fixed']) + ' or later' if f['fixed'] else 'a version without the vulnerability, or removed (no fix is listed yet)'}.",
            "- The alert is closed, or the scan of the default branch no longer lists the vulnerability.",
            "- The deploy that carries the fix is live.", "",
            "## Risk", "",
            "<Is the vulnerable code reachable from the internet or does it handle credentials? Raise the severity if so. "
            "Lower it only with the search that shows the vulnerable function is never called.>",
        ])
        out.append({"key": key, "title": title, "severity": f["severity"], "fix_by": fix_by.isoformat(), "overdue": fix_by < today,
                    "labels": ["type: bug", "security", prio], "body": body})
    out.sort(key=lambda d: (d["fix_by"], d["key"]))
    return out, tracked


def main():
    ap = argparse.ArgumentParser(description="Vulnerability alerts to ticket drafts with fix-by dates")
    ap.add_argument("--dependabot")
    ap.add_argument("--osv")
    ap.add_argument("--existing")
    ap.add_argument("--policy")
    ap.add_argument("--today")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    read = lambda p: json.load(open(p, encoding="utf-8"))
    findings = []
    if a.dependabot:
        data = read(a.dependabot)
        if data and all(isinstance(x, list) for x in data):
            data = [x for page in data for x in page]  # gh api --slurp wraps the pages
        findings += from_dependabot(data)
    if a.osv:
        findings += from_osv(read(a.osv))
    titles = [i["title"] for i in read(a.existing)] if a.existing else []
    w = windows(open(a.policy, encoding="utf-8").read() if a.policy else None)
    out, tracked = drafts(findings, today, w, titles)
    if a.json:
        print(json.dumps({"drafts": out, "tracked": tracked}, indent=1))
    else:
        print(f"{len(findings)} findings, {len(out)} new drafts, {len(tracked)} already tracked, "
              f"{sum(d['overdue'] for d in out)} past their fix-by date")
        for d in out:
            print(f"  {d['fix_by']}{' OVERDUE' if d['overdue'] else ''}  {d['severity']:8} {' '.join(d['labels'][2:])}  {d['title']}")
        for t in tracked:
            print(f"  tracked: {t}")


if __name__ == "__main__":
    main()
