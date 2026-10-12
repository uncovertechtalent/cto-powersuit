#!/usr/bin/env python3
"""Check a repo clinic folder before anything in it goes public.

report.md: a "# Repo clinic: <owner>/<repo>" heading, under 300 words, three gap sections
"## 1." to "## 3." with an "Evidence:" and a "Fix:" line each, a "Checked: ... Not checked: ..."
line, and the footer line last.
pr-plan.md: a "State:" line.
Public files (report.md, pr-plan.md, fix.patch): no secret pattern, and no file-and-line
reference from private.md. report.md and pr-plan.md: no em or en dash, no praise word,
no "not ... but" sentence.
LOG.md next to the clinic folder: a row that names <owner>/<repo>.
It does not check for analogies or the Oxford comma; a person reads for those.
Standard library only. Exit 0 when all hold, 1 otherwise.

Usage: python3 lint_clinic.py <clinic folder>
"""
import re, sys
from pathlib import Path

FOOTER = "Audited with the CTO Powersuit (github.com/uncovertechtalent/cto-powersuit)."
WORD_LIMIT = 300  # the report stays under this
HEADING = re.compile(r"^# Repo clinic: ([\w.-]+/[\w.-]+)\s*$", re.M)
GAP = re.compile(r"^## ([0-9]+)\. \S", re.M)
DASH = re.compile("[–—]")
PRAISE = re.compile(r"\b(great|awesome|amazing|impressive|excellent|fantastic|brilliant|beautiful|kudos|congrat\w*|"
                    r"love|loved|well done|nice work|nice job|good job)\b", re.I)
NOT_BUT = re.compile(r"(\bnot\b|n't\b)[^.!?\n]{0,80}?\bbut\b", re.I)
SECRET = re.compile(r"(^|[^A-Za-z0-9_])(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}(?![A-Za-z0-9_])|"
                    r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xox[abprs]-[A-Za-z0-9-]{10,})"
                    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----")
FILE_LINE = re.compile(r"[\w./-]+\.[A-Za-z0-9]+:\d+")


def words(text):
    return [w for w in text.split() if re.search(r"[A-Za-z0-9]", w)]


def copy_rules(name, text):
    problems = []
    for n, line in enumerate(text.splitlines(), 1):
        if DASH.search(line):
            problems.append(f"{name}:{n}: em or en dash; use a full stop, a comma, or a colon")
        m = PRAISE.search(line)
        if m:
            problems.append(f"{name}:{n}: praise word '{m.group(0)}'; cut it")
        m = NOT_BUT.search(line)
        if m:
            problems.append(f"{name}:{n}: 'not ... but' sentence; say what it is")
    return problems


def lint(folder):
    problems = []
    report_path, plan_path = folder / "report.md", folder / "pr-plan.md"
    report = report_path.read_text(encoding="utf-8") if report_path.is_file() else None
    plan = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else None
    slug = None
    if report is None:
        problems.append("report.md: missing")
    else:
        m = HEADING.search(report)
        slug = m.group(1) if m else None
        if not slug:
            problems.append("report.md: no '# Repo clinic: <owner>/<repo>' heading")
        n = len(words(report))
        if n >= WORD_LIMIT:
            problems.append(f"report.md: {n} words, want under {WORD_LIMIT}")
        gaps = [int(g) for g in GAP.findall(report)]
        if gaps != [1, 2, 3]:
            problems.append(f"report.md: gap sections {gaps}, want [1, 2, 3]")
        sections = re.split(r"^## [0-9]+\. ", report, flags=re.M)[1:]
        for i, sec in enumerate(sections, 1):
            for label in ("Evidence:", "Fix:"):
                if not re.search(rf"^{label}", sec, re.M):
                    problems.append(f"report.md: gap {i} has no '{label}' line")
        if not re.search(r"^Checked: .*Not checked: ", report, re.M):
            problems.append("report.md: no 'Checked: ... Not checked: ...' line")
        lines = [l.strip() for l in report.splitlines() if l.strip()]
        if not lines or lines[-1] != FOOTER:
            problems.append("report.md: the last line must be the footer: " + FOOTER)
        problems += copy_rules("report.md", report)
    if plan is None:
        problems.append("pr-plan.md: missing")
    else:
        if not re.search(r"^State: \S", plan, re.M):
            problems.append("pr-plan.md: no 'State:' line")
        problems += copy_rules("pr-plan.md", plan)
    public = {"report.md": report, "pr-plan.md": plan}
    patch = folder / "fix.patch"
    if patch.is_file():
        public["fix.patch"] = patch.read_text(encoding="utf-8", errors="replace")
    private = folder / "private.md"
    refs = set(FILE_LINE.findall(private.read_text(encoding="utf-8"))) if private.is_file() else set()
    for name, text in public.items():
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if SECRET.search(line):
                problems.append(f"{name}:{n}: secret pattern; it belongs in private.md, masked")
        for ref in sorted(refs):
            if re.search(rf"(?<![\w./-]){re.escape(ref)}(?!\d)", text):
                problems.append(f"{name}: names {ref} from private.md")
    log = folder.parent / "LOG.md"
    if slug:
        rows = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
        if not any(r.startswith("|") and slug in r for r in rows):
            problems.append(f"{log.name}: no row for {slug}")
    return problems


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    folder = Path(sys.argv[1])
    problems = lint(folder)
    for p in problems:
        print("FAIL " + p)
    print(f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
