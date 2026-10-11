#!/usr/bin/env python3
"""Print a changelog draft for the next release from the commits on the main line.

Reads the first-parent history since the last tag (or --since <ref>), drops bot commits and
'[skip ci]' commits, and sorts each commit subject into Added, Changed, Fixed, Removed or Security:
- a Conventional Commits prefix decides first (feat -> Added, fix -> Fixed, revert -> Removed,
  security -> Security; others -> Changed);
- otherwise the words decide: fix, repair, correct, restore -> Fixed; add, new, introduce -> Added;
  remove, delete, drop -> Removed; security, CVE, vulnerability -> Security; anything else -> Changed.
The rule reads words, so some entries land in the wrong group: edit the draft before it goes into
CHANGELOG.md. Writes nothing. Standard library only.

Usage: python3 scripts/changelog_draft.py [--since <ref>] [--version 1.4.0] [--date YYYY-MM-DD]
"""
import argparse, datetime, re, subprocess, sys

BOTS = {"gate-bot", "github-actions[bot]", "dependabot[bot]", "renovate[bot]"}
PREFIX = re.compile(r"^(\w+)(\([^)]*\))?!?:\s*")
GROUPS = ["Added", "Changed", "Fixed", "Removed", "Security"]
BY_PREFIX = {"feat": "Added", "fix": "Fixed", "revert": "Removed", "security": "Security"}
WORDS = [
    ("Security", re.compile(r"\b(security|cve-\d+|vulnerab\w*)\b", re.I)),
    ("Fixed", re.compile(r"\b(fix|fixes|fixed|repair\w*|correct\w*|restor\w*)\b", re.I)),
    ("Removed", re.compile(r"\b(remove\w*|delete\w*|drop\w*)\b", re.I)),
    ("Added", re.compile(r"\b(add|adds|added|new|introduce\w*)\b", re.I)),
]


def git(*args):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def group(subject):
    m = PREFIX.match(subject)
    if m:
        return BY_PREFIX.get(m.group(1).lower(), "Changed"), subject[m.end():]
    for name, rx in WORDS:
        if rx.search(subject):
            return name, subject
    return "Changed", subject


def main():
    ap = argparse.ArgumentParser(description="Print a changelog draft from the main line")
    ap.add_argument("--since", default=None, help="ref to start after; default: the last tag, or the whole history")
    ap.add_argument("--version", default="Unreleased")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    since = args.since or git("describe", "--tags", "--abbrev=0")
    rng = f"{since}..HEAD" if since else "HEAD"
    log = git("log", "--first-parent", "--format=%h%x1f%an%x1f%s%x1f%b%x1d", rng)
    if not log and not git("rev-parse", "HEAD"):
        sys.exit("changelog_draft: not a git repository, or no commits")
    entries = {g: [] for g in GROUPS}
    for rec in (r.strip("\n") for r in log.split("\x1d") if r.strip()):
        sha, author, subject, body = (rec.split("\x1f") + ["", "", ""])[:4]
        if author in BOTS or "[skip ci]" in subject:
            continue
        pr = re.match(r"Merge pull request (#\d+)", subject)
        if pr and body.strip():  # GitHub puts the pull request title on the first body line
            subject = f"{body.strip().splitlines()[0]} ({pr.group(1)})"
        g, text = group(subject)
        entries[g].append(f"- {text[:1].upper() + text[1:]} ({sha})")
    head = "## Unreleased" if args.version == "Unreleased" else f"## [{args.version}] - {args.date}"
    out = [head, ""]
    for g in GROUPS:
        if entries[g]:
            out += [f"### {g}", ""] + entries[g] + [""]
    if len(out) == 2:
        out.append(f"No commits since {since or 'the start'}.")
    print("\n".join(out).rstrip())
    print(f"\n<!-- draft from {rng}; edit before it goes into CHANGELOG.md -->", file=sys.stderr)


if __name__ == "__main__":
    main()
