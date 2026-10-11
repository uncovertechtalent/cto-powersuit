#!/usr/bin/env python3
"""Private terms stay out of public repositories: a gate check, a tree scan and a pre-push hook.

The term list is private and stays outside every repository: $POWERSUIT_OVERLAY/security/private-terms.txt,
or the file that the terms_file option or --terms names. Without the list the gate check returns n/a, so CI
on a public repository never needs it. A hit names the file, the line and the term's label, never the term.

  python3 private_terms.py scan [root] [--terms FILE] [--allow FILE] [--built DIR]...
  python3 private_terms.py history [root] [--terms FILE]             (counts per label in all commits; prints no line)
  python3 private_terms.py pre-push <remote> <url> [--terms FILE]    (as .git/hooks/pre-push; git sends the refs on stdin)
  python3 private_terms.py install-hook --into DIR --terms FILE      (writes DIR/pre-push, a two-line shim)

Exit codes: 0 clean, 1 hits, 2 no term list, a broken list or a hook that is already there.
Standard library only, Python 3.9+.
"""
import argparse
import bisect
import fnmatch
import html
import os
import re
import subprocess
import sys
from pathlib import Path

ID = "security.private-terms"
DESCRIPTION = ("Tracked files, file names and built pages carry no term from the private term list: names of "
               "prospective employers, internal shorthand, family references, private hosts and addresses. The list "
               "stays outside the repository, so the rule runs where the list is (pre-push hook, local dry run) and "
               "returns n/a elsewhere. Hits show the file, the line and the term's label, never the term.")
DEFAULTS = {
    "terms_file": "",                      # empty: $POWERSUIT_OVERLAY/security/private-terms.txt
    "allow_file": ".private-terms-allow",  # per repository, relative to root: "<path glob> <label or *> <reason>" per line
    "built": [],                           # folders under root to read even when git does not track them, such as a build output
    "tracked_only": True,                  # inside a git work tree, read the files git tracks under root (plus built)
    "require_list": False,                 # true: a missing or empty list fails instead of n/a
    "max_bytes": 2000000,                  # larger files are skipped and counted in the detail
}
LABEL = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s+=\s+(\S.*)$")
TAG = re.compile(r"<[^>]*>")
INVISIBLE = re.compile("[\u00ad\u200b-\u200d\u2060\ufeff]")  # soft hyphen and zero-width characters split no word for a reader
MARKUP = (".html", ".htm", ".xhtml", ".xml", ".svg")
MASK = "****"


class ListError(Exception):
    """A problem with the term list or the allow file. The message names a line number, never the line."""


def term_list_path(option=""):
    if option:
        return Path(os.path.expanduser(option))
    overlay = os.environ.get("POWERSUIT_OVERLAY")
    return Path(os.path.expanduser(overlay)) / "security" / "private-terms.txt" if overlay else None


def compile_term(body, n):
    """A literal term matches without case, on word boundaries, with any run of whitespace between its words.
    A term after "re:" is a regular expression; the word boundaries wrap it."""
    if body.startswith("re:"):
        core, head, tail = "(?:" + body[3:].strip() + ")", True, True
    else:
        words = body.split()
        core = r"\s+".join(re.escape(w) for w in words)
        head, tail = bool(re.match(r"\w", words[0])), bool(re.search(r"\w$", words[-1]))
    try:
        rx = re.compile(("(?<!\\w)" if head else "") + core + ("(?!\\w)" if tail else ""), re.IGNORECASE)
    except re.error:
        raise ListError(f"term list line {n}: invalid regular expression") from None
    if rx.search(""):
        raise ListError(f"term list line {n}: the expression matches an empty string")
    return rx


def load_terms(path):
    """[(label, regex)]. Each line is a term, "label = term", or "label = re:expression"; # starts a comment line.
    A term without a label gets the label line<N>."""
    terms, seen = [], set()
    for n, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LABEL.match(line)
        label, body = (m.group(1), m.group(2).strip()) if m else (f"line{n}", line)
        if label in seen:
            raise ListError(f"term list line {n}: label {label} is used twice")
        seen.add(label)
        terms.append((label, compile_term(body, n)))
    return terms


def load_allow(text):
    """Entries "<path glob> <label or *> <reason>" and the line numbers of entries without a reason."""
    entries, no_reason = [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            no_reason.append(n)
            continue
        entries.append({"glob": parts[0], "label": parts[1], "line": n, "used": 0})
    return entries, no_reason


def allowed(entries, rel, label):
    for e in entries:
        if e["label"] in ("*", label) and fnmatch.fnmatchcase(rel, e["glob"]):
            e["used"] += 1
            return True
    return False


def visible(text):
    """Markup as a reader sees it: tags removed (a tag keeps its line breaks) and entities decoded, line by line."""
    bare = TAG.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return "\n".join(html.unescape(line).replace("\n", " ") for line in bare.split("\n"))


def find(text, terms, first_line=1):
    """{(line, label)} for every match in text, read without invisible characters."""
    text = INVISIBLE.sub("", text)
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    out = set()
    for label, rx in terms:
        for m in rx.finditer(text):
            if m.end() > m.start():
                out.add((first_line - 1 + bisect.bisect_right(starts, m.start()), label))
    return out


def scan_text(text, terms, markup=False, first_line=1):
    """Sorted (line, label) pairs. Markup is read twice: as written (attributes, URLs) and as a reader sees it
    (a term split by a tag or written with entities)."""
    hits = find(text, terms, first_line)
    if markup and ("<" in text or "&" in text):
        hits |= find(visible(text), terms, first_line)
    return sorted(hits)


def mask(text, terms):
    """text with every match of every term replaced by the mask: file names can hold a term too."""
    for _, rx in terms:
        text = rx.sub(MASK, text)
    return text


def hit(file, line, label, rule="private-term"):
    where = "file name" if rule == "private-term-in-path" else "text"
    return {"file": file, "line": line, "rule": rule, "snippet": f"private term {label} {MASK} in the {where}"}


def git_out(args, cwd):
    p = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True)
    if p.returncode:
        raise RuntimeError("git " + args[0] + " failed: " + p.stderr.decode("utf-8", "replace").strip()[:200])
    return p.stdout


def inside(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def tree_files(root, options, excluded=lambda rel: False):
    """('tracked', paths) inside a git work tree with tracked files under root, else ('all', paths); plus built folders."""
    files, mode = [], "all"
    if options["tracked_only"]:
        try:
            names = [n for n in git_out(["-C", str(root), "ls-files", "-z"], root).decode("utf-8", "replace").split("\0") if n]
        except (RuntimeError, OSError):
            names = []
        if names:
            mode, files = "tracked", [root / n for n in names if not excluded(n)]
    if mode == "all":
        files = [p for p in root.rglob("*") if ".git" not in p.relative_to(root).parts and not excluded(p.relative_to(root).as_posix())]
    for d in options["built"]:
        files += [p for p in (root / d).rglob("*")] if (root / d).is_dir() else []
    seen, out = set(), []
    for p in files:
        if p.is_file() and p not in seen:
            seen.add(p)
            out.append(p)
    return mode, sorted(out)


def scan_tree(root, terms, options, allow_text="", excluded=lambda rel: False):
    """(hits, stats) for every file under root, with the allow file applied."""
    entries, no_reason = load_allow(allow_text)
    allow_file = options["allow_file"]
    hits = [{"file": allow_file, "line": n, "rule": "allow-without-reason",
             "snippet": "allow entry without a reason; every entry needs a path glob, a label and a reason"} for n in no_reason]
    mode, files = tree_files(root, options, excluded)
    stats = {"mode": mode, "read": 0, "skipped": 0, "allowed": 0}
    for p in files:
        rel = p.relative_to(root).as_posix()
        if rel == allow_file:
            continue
        found = [(None, label, "private-term-in-path") for _, label in scan_text(rel, terms)]
        if p.stat().st_size > options["max_bytes"]:
            stats["skipped"] += 1
        else:
            data = p.read_bytes()
            if b"\0" not in data[:8000]:
                stats["read"] += 1
                text = data.decode("utf-8", errors="replace")
                found += [(n, label, "private-term") for n, label in scan_text(text, terms, p.suffix.lower() in MARKUP)]
        for n, label, rule in found:
            if allowed(entries, rel, label):
                stats["allowed"] += 1
            else:
                hits.append(hit(mask(rel, terms), n, label, rule))
    labels = {label for label, _ in terms}
    stats["unused"] = [e["line"] for e in entries if not e["used"]]
    stats["unknown"] = [e["line"] for e in entries if e["label"] != "*" and e["label"] not in labels]
    return hits, stats


def load_list(option, root):
    """(terms, None) or (None, reason). Refuses a list inside the scanned tree: it would be committed with it."""
    path = term_list_path(option)
    if path is None:
        return None, "no term list: POWERSUIT_OVERLAY is unset and no terms_file is given"
    if not path.is_file():
        return None, f"no term list at {path}"
    if inside(path, root):
        raise ListError(f"the term list {path} is inside the scanned tree; move it out of the repository")
    return load_terms(path), None


def check(ctx):
    o = ctx.options
    terms, missing = load_list(o["terms_file"], ctx.root)
    if missing or not terms:
        reason = missing or "the term list has no terms yet"
        return {"result": "fail" if o["require_list"] else "n/a",
                "detail": f"{reason}. The list stays outside the repository, so this rule runs where the list is: the pre-push hook and local dry runs", "hits": []}
    allow = ctx.root / o["allow_file"]
    allow_text = allow.read_text(encoding="utf-8", errors="replace") if allow.is_file() else ""
    hits, s = scan_tree(ctx.root, terms, o, allow_text, getattr(ctx, "excluded", lambda rel: False))
    detail = (f"{len(terms)} terms, {s['read']} {'tracked ' if s['mode'] == 'tracked' else ''}text files read"
              f"{' (plus ' + ', '.join(o['built']) + ')' if o['built'] else ''}, {len(hits)} hits, {s['allowed']} allowed by {o['allow_file']}")
    if s["skipped"]:
        detail += f", {s['skipped']} files over {o['max_bytes']} bytes skipped"
    if s["unused"]:
        detail += f"; allow entries that matched nothing: lines {', '.join(map(str, s['unused']))}"
    if s["unknown"]:
        detail += f"; allow entries with a label not in the list: lines {', '.join(map(str, s['unknown']))}"
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}


# ---------- pre-push ----------
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
ZERO = re.compile(r"^0+$")


def added_blocks(diff):
    """{path: [(first new line, text)]}: each run of added lines in a -U0 diff, joined, so a term split
    across two added lines still matches."""
    blocks, path, header, nxt, cur = {}, None, False, 0, None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            header, path, cur = True, None, None
        elif header and line.startswith("+++ "):
            p = line[4:].rstrip("\t")
            path = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
        elif line.startswith("@@"):
            header, cur = False, None
            m = HUNK.match(line)
            nxt = int(m.group(1)) if m else 0
        elif header or path is None or line.startswith("\\"):
            continue
        elif line.startswith("+"):
            if cur is None:
                cur = [nxt, []]
                blocks.setdefault(path, []).append(cur)
            cur[1].append(line[1:])
            nxt += 1
        else:
            cur = None
            if not line.startswith("-"):
                nxt += 1
    return {p: [(first, "\n".join(lines)) for first, lines in runs] for p, runs in blocks.items()}


def new_paths(name_status):
    """Paths a commit adds, copies or renames to, from git diff --name-status -z output."""
    parts, out, i = name_status.split("\0"), [], 0
    while i < len(parts) and parts[i]:
        status = parts[i]
        if status[0] in "RC":
            out.append(parts[i + 2])
            i += 3
        else:
            if status[0] == "A":
                out.append(parts[i + 1])
            i += 2
    return out


def pushed_commits(remote, local_sha, remote_sha, cwd):
    """Commits the push sends: reachable from local_sha and from no ref of the remote."""
    args = ["rev-list", local_sha, "--not", f"--remotes={remote}"]
    if not ZERO.match(remote_sha):
        try:
            git_out(["cat-file", "-e", remote_sha + "^{commit}"], cwd)
            args.append(remote_sha)
        except RuntimeError:
            pass
    return git_out(args, cwd).decode().split()


def scan_commit(sha, terms, entries, cwd):
    """[(file, line, label, rule)] for the commit's message, author and committer, new file names and added lines."""
    text = lambda args: git_out(args, cwd).decode("utf-8", "replace")
    short, out = sha[:12], []
    out += [(f"commit {short} message", n, label, "private-term") for n, label in scan_text(text(["log", "-1", "--format=%B", sha]), terms)]
    out += [(f"commit {short} author or committer", None, label, "private-term") for _, label in scan_text(text(["log", "-1", "--format=%an <%ae> %cn <%ce>", sha]), terms)]
    parents = text(["rev-list", "--parents", "-n", "1", sha]).split()[1:]
    base = [parents[0], sha] if parents else [git_empty_tree(cwd), sha]
    for p in new_paths(text(["diff", "--name-status", "-z", "-M", *base])):
        out += [(p, None, label, "private-term-in-path") for _, label in scan_text(p, terms)]
    diff = text(["diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", *base])
    for p, runs in added_blocks(diff).items():
        markup = Path(p).suffix.lower() in MARKUP
        for first, block in runs:
            out += [(p, n, label, "private-term") for n, label in scan_text(block, terms, markup, first)]
    return [(f if f.startswith("commit ") else mask(f, terms), n, label, rule) for f, n, label, rule in out
            if f.startswith("commit ") or not allowed(entries, f, label)]


def git_empty_tree(cwd):
    return git_out(["hash-object", "-t", "tree", os.devnull], cwd).decode().strip()


def pre_push(remote, terms_option, refs, cwd):
    """Exit code and report lines for the refs git sends on the hook's stdin."""
    top = Path(git_out(["rev-parse", "--show-toplevel"], cwd).decode().strip() or cwd)
    terms, missing = load_list(terms_option, top)
    if missing:
        return 2, [f"private-terms: {missing}; push stopped. Fix the path in .git/hooks/pre-push, or push with --no-verify after you checked the commits yourself."]
    if not terms:
        return 0, ["private-terms: the term list has no terms yet; nothing checked."]
    found, commits = [], 0
    for line in refs:
        parts = line.split()
        if len(parts) != 4 or ZERO.match(parts[1]):
            continue  # a deletion sends no content
        local_ref, local_sha, remote_ref, remote_sha = parts
        found += [(f"ref {mask(remote_ref, terms)}", None, label, "private-term-in-path") for _, label in scan_text(remote_ref, terms)]
        if local_ref.startswith("refs/tags/") and git_out(["cat-file", "-t", local_sha], cwd).decode().strip() == "tag":
            tag = git_out(["cat-file", "-p", local_sha], cwd).decode("utf-8", "replace")
            found += [(f"tag {mask(local_ref[10:], terms)}", n, label, "private-term") for n, label in scan_text(tag, terms)]
        try:
            allow_text = git_out(["show", f"{local_sha}:.private-terms-allow"], cwd).decode("utf-8", "replace")
        except RuntimeError:
            allow_text = ""
        entries, no_reason = load_allow(allow_text)
        found += [(".private-terms-allow", n, "-", "allow-without-reason") for n in no_reason]
        for sha in pushed_commits(remote, local_sha, remote_sha, cwd):
            commits += 1
            found += scan_commit(sha, terms, entries, cwd)
    found = sorted(set(found), key=lambda x: (x[0], x[1] or 0, x[2]))
    if not found:
        return 0, []
    lines = [f"private-terms: push to {remote} stopped, {len(found)} hits in {commits} commits:"]
    for f, n, label, rule in found:
        where = f"{f}:{n}" if n else f
        lines.append(f"  {where} " + ("allow entry without a reason" if rule == "allow-without-reason" else f"private term {label} {MASK}"))
    lines.append("Fix the commits (git commit --amend for the last one), or add a line \"<path glob> <label> <reason>\" to .private-terms-allow for an intended mention.")
    return 1, lines


def history_counts(root, terms):
    """{label: lines} over every commit on every ref: messages, authors and patches. Counts only."""
    log = git_out(["log", "--all", "-p", "--no-color", "--no-ext-diff", "--no-textconv", "--format=%an <%ae> %cn <%ce>%n%B"], root)
    counts = {}
    for _, label in find(log.decode("utf-8", "replace"), terms):
        counts[label] = counts.get(label, 0) + 1
    return counts


def install_hook(into, terms):
    """Write <into>/pre-push: a shim that runs this file with the term list. Refuses to replace another hook."""
    into = Path(os.path.expanduser(into))
    target = into / "pre-push"
    me = Path(__file__).resolve()
    shim = f'#!/bin/sh\n# private-terms pre-push hook (CTO powersuit, security module)\nexec python3 "{me}" pre-push "$@" --terms "{Path(os.path.expanduser(terms)).resolve()}"\n'
    if target.exists() and "private-terms pre-push hook" not in target.read_text(errors="replace"):
        return 2, [f"{target} exists and is another hook; chain it by hand"]
    into.mkdir(parents=True, exist_ok=True)
    target.write_text(shim)
    target.chmod(0o755)
    return 0, [f"wrote {target}"]


def main(argv):
    ap = argparse.ArgumentParser(description="Private terms stay out of public repositories.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a tree")
    s.add_argument("root", nargs="?", default=".")
    s.add_argument("--terms", default="")
    s.add_argument("--allow", default=None, help="allow file; default <root>/.private-terms-allow")
    s.add_argument("--built", action="append", default=[], help="a folder under root to read even when untracked; repeatable")
    s.add_argument("--all-files", action="store_true", help="read untracked files too")
    y = sub.add_parser("history", help="count matches per label in every commit of every ref")
    y.add_argument("root", nargs="?", default=".")
    y.add_argument("--terms", default="")
    h = sub.add_parser("pre-push", help="run as the pre-push hook")
    h.add_argument("remote")
    h.add_argument("url", nargs="?", default="")
    h.add_argument("--terms", default="")
    i = sub.add_parser("install-hook", help="write a pre-push shim into a hooks folder")
    i.add_argument("--into", required=True, help=".git/hooks of one repository, or the hooks folder of a git template")
    i.add_argument("--terms", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "install-hook":
            code, lines = install_hook(a.into, a.terms)
        elif a.cmd == "history":
            root = Path(a.root).resolve()
            terms, missing = load_list(a.terms, root)
            if missing or not terms:
                code, lines = 2, [f"private-terms: {missing or 'the term list has no terms yet'}"]
            else:
                counts = history_counts(root, terms)
                lines = [f"{label}: {n} lines" for label, n in sorted(counts.items())]
                lines.append(f"private-terms: {len(terms)} terms, {len(counts)} found in the history, {sum(counts.values())} lines")
                code = 1 if counts else 0
        elif a.cmd == "pre-push":
            code, lines = pre_push(a.remote, a.terms, sys.stdin.read().splitlines(), os.getcwd())
        else:
            root = Path(a.root).resolve()
            terms, missing = load_list(a.terms, root)
            if missing or not terms:
                code, lines = 2, [f"private-terms: {missing or 'the term list has no terms yet'}"]
            else:
                opts = dict(DEFAULTS, built=a.built, tracked_only=not a.all_files)
                allow = Path(a.allow) if a.allow else root / opts["allow_file"]
                hits, st = scan_tree(root, terms, opts, allow.read_text(encoding="utf-8") if allow.is_file() else "")
                lines = [f"{x['file']}{':' + str(x['line']) if x['line'] else ''} {x['snippet']}" for x in hits]
                lines.append(f"private-terms: {len(terms)} terms, {st['read']} files read, {len(hits)} hits, {st['allowed']} allowed")
                code = 1 if hits else 0
    except ListError as e:
        code, lines = 2, [f"private-terms: {e}"]
    for line in lines:
        print(line, file=sys.stderr if a.cmd == "pre-push" else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
