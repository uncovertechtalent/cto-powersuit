"""Every change on the main line names a ticket or a decision; source changes come with test changes."""
import fnmatch
import json
import re

ID = "sdlc.traceability"
DESCRIPTION = ("Every pull request or merge commit on the main line references a ticket or decision id; "
               "a change to source files with no change to a test file is a warning.")
DEFAULTS = {
    "range": "",                 # git revision range, for example "v1.4.0..HEAD"; empty = the last max_commits on HEAD
    "max_commits": 50,
    "since": "",                 # ISO date; commits before it are not checked (set it to the adoption date)
    "first_parent": True,        # check the main line only: merge commits and squashed pull requests
    "id_patterns": [r"#\d+", r"\b[A-Z][A-Z0-9]+-\d+\b", r"\b(?:ADR|RFC|adr|rfc)-\d{1,4}\b"],
    "skip_authors": ["gate-bot", "github-actions[bot]", "dependabot[bot]", "renovate[bot]"],
    "skip_subject": r"\[skip ci\]|^Revert \"",
    "source_globs": ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.rs", "*.java", "*.kt", "*.rb",
                     "*.php", "*.cs", "*.swift", "*.c", "*.cc", "*.cpp", "*.h"],
    "test_dirs": ["test", "tests", "__tests__", "spec", "e2e"],
    "test_globs": ["test_*", "*_test.*", "*.test.*", "*.spec.*", "*Test.java", "*Tests.cs"],
    "commits_file": ".sdlc-commits.json",  # read in place of git when present at the root (fixtures, offline audits)
}


def from_file(ctx, path):
    """A JSON list of {"sha", "author", "date", "subject", "body", "files"} records, newest first."""
    return json.loads(path.read_text(encoding="utf-8"))


def from_git(ctx, o):
    args = ["log", "--format=%x1e%H%x1f%an%x1f%cs%x1f%s%x1f%b%x1d", "--name-only", "--diff-merges=first-parent"]
    if o["first_parent"]:
        args.append("--first-parent")
    if o["since"]:
        args.append(f"--since={o['since']}")
    if o["range"]:
        args.append(o["range"])
    else:
        args += ["-n", str(int(o["max_commits"])), "HEAD"]
    out = ctx.git(*args)
    if not out:
        return None
    commits = []
    for rec in (r for r in out.split("\x1e") if r.strip()):  # str.strip() counts \x1e as whitespace, so the first separator may be gone
        head, _, files = rec.partition("\x1d")
        sha, author, date, subject, body = (head.split("\x1f") + ["", "", "", "", ""])[:5]
        commits.append({"sha": sha, "author": author, "date": date, "subject": subject, "body": body,
                        "files": [f for f in files.split("\n") if f.strip()]})
    return commits


def is_test(path, o):
    parts = path.split("/")
    if any(p in o["test_dirs"] for p in parts[:-1]):
        return True
    return any(fnmatch.fnmatch(parts[-1], g) for g in o["test_globs"])


def is_source(path, o):
    return any(fnmatch.fnmatch(path.split("/")[-1], g) for g in o["source_globs"]) and not is_test(path, o)


def check(ctx):
    o = ctx.options
    cfile = ctx.root / o["commits_file"]
    commits = from_file(ctx, cfile) if cfile.is_file() else from_git(ctx, o)
    if commits is None:
        return {"result": "n/a", "detail": "no git history and no commits file at the root"}
    if o["since"]:
        commits = [c for c in commits if c.get("date", "") >= o["since"]]
    ids = [re.compile(p) for p in o["id_patterns"]]
    skip = re.compile(o["skip_subject"]) if o["skip_subject"] else None
    checked, untraced, untested = 0, [], []
    for c in commits:
        if c.get("author") in o["skip_authors"] or (skip and skip.search(c.get("subject", ""))):
            continue
        checked += 1
        text = c.get("subject", "") + "\n" + c.get("body", "")
        short = c["sha"][:12]
        if not any(p.search(text) for p in ids):
            untraced.append({"file": f"commit {short}", "snippet": f"{short}: no ticket or decision id"})
        files = c.get("files") or []
        if any(is_source(f, o) for f in files) and not any(is_test(f, o) for f in files):
            untested.append(f"{short}: source files changed, no test file changed ({c.get('subject', '')[:60]})")
    if not checked:
        return {"result": "n/a", "detail": "no commit in the checked range after the skips"}
    detail = (f"{checked} commits checked: {len(untraced)} without a ticket or decision id, "
              f"{len(untested)} with source changes and no test changes")
    if untraced:
        return {"result": "fail", "detail": detail, "evidence": [h["snippet"] for h in untraced] + untested[:20], "hits": untraced}
    if untested:
        return {"result": "warn", "detail": detail, "evidence": untested[:20], "hits": []}
    return {"result": "pass", "detail": detail}
