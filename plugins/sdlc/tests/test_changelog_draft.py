#!/usr/bin/env python3
"""Tests for the changelog draft template (templates/scripts/changelog_draft.py).

The grouping cases call group() directly. The history case builds a small repository with a tag,
a merge commit, a bot commit and a '[skip ci]' commit in a temporary folder and runs the script.
Standard library only, Python 3.9+.

Usage: python3 plugins/sdlc/tests/test_changelog_draft.py [-v]
"""
import importlib.util, os, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT = Path(__file__).resolve().parent.parent / "templates/scripts/changelog_draft.py"
VERBOSE = "-v" in sys.argv
spec = importlib.util.spec_from_file_location("changelog_draft", SCRIPT)
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)

GROUPING = [
    ("feat: add the release check", ("Added", "add the release check")),
    ("fix(api): retry on 503", ("Fixed", "retry on 503")),
    ("chore!: drop Python 3.8", ("Changed", "drop Python 3.8")),
    ("docs: explain the overlay", ("Changed", "explain the overlay")),
    ("Security: rotate the deploy key", ("Security", "rotate the deploy key")),
    ("revert: the cache change", ("Removed", "the cache change")),
    ("README: the canary mascot", ("Changed", "README: the canary mascot")),
    ("sdlc: pre-push skill runs the workflow check jobs", ("Changed", "sdlc: pre-push skill runs the workflow check jobs")),
    ("gate: fix the zsh finder", ("Fixed", "gate: fix the zsh finder")),
    ("Add the fit module", ("Added", "Add the fit module")),
    ("Repair the ai-ops README row", ("Fixed", "Repair the ai-ops README row")),
    ("Remove the old template", ("Removed", "Remove the old template")),
    ("Bump osv for CVE-2026-1234", ("Security", "Bump osv for CVE-2026-1234")),
    ("Rename the review skill", ("Changed", "Rename the review skill")),
]


def git(cwd, *args, author="Dev"):
    env = dict(os.environ, GIT_AUTHOR_NAME=author, GIT_AUTHOR_EMAIL="d@example.com",
               GIT_COMMITTER_NAME=author, GIT_COMMITTER_EMAIL="d@example.com")
    subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                   cwd=cwd, env=env, check=True, capture_output=True)


def history_case():
    with tempfile.TemporaryDirectory() as tmp:
        git(tmp, "init", "-q")
        git(tmp, "commit", "-q", "--allow-empty", "-m", "Add the first module")
        git(tmp, "tag", "v0.1.0")
        git(tmp, "commit", "-q", "--allow-empty", "-m", "README: the canary mascot")
        git(tmp, "commit", "-q", "--allow-empty", "-m", "Bump actions", author="dependabot[bot]")
        git(tmp, "commit", "-q", "--allow-empty", "-m", "Record the run [skip ci]")
        git(tmp, "checkout", "-q", "-b", "topic")
        git(tmp, "commit", "-q", "--allow-empty", "-m", "Add the pre-push skill")
        git(tmp, "checkout", "-q", "main")
        git(tmp, "merge", "-q", "--no-ff", "topic", "-m", "Merge pull request #3 from owner/topic\n\nsdlc: pre-push skill runs the check jobs")
        p = subprocess.run([sys.executable, str(SCRIPT), "--version", "0.2.0", "--date", "2026-10-12"],
                           cwd=tmp, capture_output=True, text=True)
        out = p.stdout
        if VERBOSE:
            print(out)
        problems = []
        if p.returncode != 0:
            problems.append(f"exit {p.returncode}: {p.stderr.strip()}")
        for want in ("## [0.2.0] - 2026-10-12", "- README: the canary mascot", "- Sdlc: pre-push skill runs the check jobs (#3)"):
            if want not in out:
                problems.append(f"missing {want!r}")
        for unwanted in ("Add the first module", "Bump actions", "skip ci", "Add the pre-push skill"):
            if unwanted in out:
                problems.append(f"unexpected {unwanted!r}")
        return problems


def main():
    failures = 0
    for subject, want in GROUPING:
        got = draft.group(subject)
        ok = got == want
        failures += not ok
        if VERBOSE or not ok:
            print(f"{'ok  ' if ok else 'FAIL'} {subject!r} -> {got}" + ("" if ok else f", want {want}"))
    problems = history_case()
    for p in problems:
        print(f"FAIL history: {p}")
    failures += len(problems)
    print(f"{len(GROUPING) + 1} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
