#!/usr/bin/env python3
"""Secret values stay out of git: a gate check over tracked files, a pre-push hook over what a push adds, and an
optional pre-commit hook over what a commit adds.

  python3 secrets.py pre-push <remote> [<url>] [--tier warn|block]    (as .git/hooks/pre-push; git sends the refs on stdin)
  python3 secrets.py pre-commit [--tier warn|block]                   (as .git/hooks/pre-commit; reads the staged changes)
  python3 secrets.py check [remote] [--tier warn|block]               (what a push of the current branch would send; pushes nothing)
  python3 secrets.py history [root]                                   (secret hits in the added lines of every commit; counts and masked hits)
  python3 secrets.py install-hook --into DIR [--tier warn|block] [--pre-commit]

A hit shows the kind, the fixed prefix and the first 12 hex digits of the value's sha256, never the value.
Known false positives go into .secrets-allow at the repository root: "<path glob> <kind or *> <sha256 prefix or *> <reason>".
Exit codes: 0 clean (or tier warn), 1 hits, 2 a scan that could not run, a broken config or a hook that is already there.
Standard library only, Python 3.9+.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ID = "security.secrets"
DESCRIPTION = ("Files tracked in git carry no value that matches a secret pattern (API keys, access keys, tokens, "
               "private key blocks) and no .env file. Hits show the pattern, the fixed prefix and a short sha256 of "
               "the value, never the value. Outside a git work tree the rule reads every file under root. Known false "
               "positives go into .secrets-allow with a reason; the same file serves the pre-push and pre-commit hooks.")
DEFAULTS = {
    # kind: [pattern, what the hit shows instead of the value]. The patterns use word boundaries, so ids such as "risk-..." do not match.
    "patterns": {
        "anthropic-key": [r"\bsk-ant-[A-Za-z0-9_-]{20,}", "sk-ant-****"],
        "sk-key": [r"\bsk-[A-Za-z0-9]{32,}", "sk-****"],
        "aws-access-key-id": [r"\bAKIA[0-9A-Z]{16}\b", "AKIA****"],
        "github-token": [r"\bgh[pousr]_[A-Za-z0-9]{30,}", "gh?_****"],
        "github-fine-grained-token": [r"\bgithub_pat_[A-Za-z0-9_]{40,}", "github_pat_****"],
        "slack-token": [r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "xox?-****"],
        "private-key": [r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "BEGIN PRIVATE KEY header"],
    },
    "env_files": True,          # a tracked .env file is a hit; .env.example, .env.sample and .env.template are not
    "tracked_only": True,       # inside a git work tree, read only the files git tracks under root
    "allow": [],                # path globs exempt from the rule, e.g. "docs/examples/*"; empty by default
    "allow_hashes": [],         # sha256 prefixes (8 or more hex digits) of known example values, as the hits print them
    "allow_file": ".secrets-allow",  # per repository, relative to root: "<path glob> <kind or *> <sha256 prefix or *> <reason>" per line
    "max_bytes": 400000,        # larger files are skipped and counted in the detail
}
DEFAULT_EXCLUDE = [".git/", "node_modules/", "/gate/"]  # the gate runner's default; the hooks read "exclude" from gate/gate.json too
ENV_FILE = re.compile(r"(^|/)\.env(\.[^/]+)?$")
ENV_TEMPLATE = re.compile(r"\.(example|sample|template|dist)$")
ALLOW_HASH = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{8,64})$")
CATCH_ALL = re.compile(r"^[*/]*$")
PROBLEMS = {
    "no-reason": "allow entry without a reason; every entry needs a path glob, a kind, a sha256 prefix or *, and a reason",
    "bad-hash": "allow entry whose hash is not * or 8 or more hex digits",
    "too-broad": "allow entry that allows every secret in every path; name a path or a hash",
}
TIERS = ("warn", "block")
DEFAULT_TIER = "block"
HOOK_MARK = "secrets {} hook"
DISPATCH_MARK = "powersuit hook dispatcher"
PRIVATE_TERMS_MARK = "private-terms pre-push hook"
MAX_SHOWN = 50


class ConfigError(Exception):
    """A problem with gate/gate.json or .secrets-allow. The message names the file and the option, never a value."""


# ---------- patterns, allow file, masking ----------
def compile_patterns(patterns):
    kinds = []
    for kind, spec in patterns.items():
        try:
            kinds.append((kind, re.compile(spec[0]), spec[1]))
        except (re.error, TypeError, IndexError):
            raise ConfigError(f"gate/gate.json: pattern {kind} is not a [regular expression, shown prefix] pair") from None
    return kinds


def digest_of(value):
    return hashlib.sha256(value.encode()).hexdigest()


def scan_line(line, kinds):
    """[(kind, shown, sha256 hex)] for every match in one line."""
    return [(kind, shown, digest_of(m.group(0))) for kind, rx, shown in kinds for m in rx.finditer(line)]


def mask(text, kinds):
    """text with every match of every pattern replaced by what a hit shows: paths and ref names can hold a value too."""
    for _, rx, shown in kinds:
        text = rx.sub(lambda m, s=shown: s, text)
    return text


def load_allow(text):
    """(entries, problems). An entry is "<path glob> <kind or *> <sha256 prefix or *> <reason>"; # starts a comment line.
    problems are (line number, code) for entries that count for nothing: no reason, a bad hash, or one that allows everything."""
    entries, problems = [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            problems.append((n, "no-reason"))
            continue
        glob, kind, digest = parts[0], parts[1], parts[2]
        if digest == "*":
            digest = None
            if CATCH_ALL.match(glob):
                problems.append((n, "too-broad"))
                continue
        else:
            m = ALLOW_HASH.match(digest)
            if not m:
                problems.append((n, "bad-hash"))
                continue
            digest = m.group(1).lower()
        entries.append({"glob": glob, "kind": kind, "digest": digest, "line": n, "used": 0})
    return entries, problems


def allowed(entries, where, kind, digest):
    for e in entries:
        if e["kind"] in ("*", kind) and fnmatch.fnmatchcase(where, e["glob"]) and (e["digest"] is None or (digest or "").startswith(e["digest"])):
            e["used"] += 1
            return True
    return False


def excluded(patterns, rel):
    """The gate runner's rule: a pattern ending in '/' is a folder, any other a file; a leading '/' anchors it at the root."""
    for x in patterns:
        anchored, pat = x.startswith("/"), x.lstrip("/")
        if pat.endswith("/"):
            if rel.startswith(pat) or (not anchored and ("/" + pat) in ("/" + rel)):
                return True
        elif rel == pat or (not anchored and rel.endswith("/" + pat)):
            return True
    return False


# ---------- gate check ----------
def candidates(ctx):
    """('tracked', paths) inside a git work tree with tracked files under root, else ('all', paths)."""
    if ctx.options["tracked_only"]:
        names = [n for n in ctx.git("-C", str(ctx.root), "ls-files", "-z").split("\0") if n]
        if names:
            skip = getattr(ctx, "excluded", lambda rel: False)
            return "tracked", sorted(ctx.root / n for n in names if not skip(n))
    return "all", ctx.files(["**/*"])


def check(ctx):
    o = ctx.options
    kinds = compile_patterns(o["patterns"])
    allow = list(o["allow"])
    allow_hashes = tuple(h.lower() for h in o["allow_hashes"] if len(h) >= 8)
    allow_path = ctx.root / o["allow_file"]
    entries, problems = load_allow(allow_path.read_text(encoding="utf-8", errors="replace") if allow_path.is_file() else "")
    mode, files = candidates(ctx)
    hits = [{"file": o["allow_file"], "line": n, "rule": "allow-entry", "snippet": PROBLEMS[code]} for n, code in problems]
    scanned, skipped, by_file = 0, 0, 0
    for p in files:
        rel = ctx.rel(p)
        if not p.is_file() or any(fnmatch.fnmatch(rel, g) for g in allow):
            continue
        if o["env_files"] and ENV_FILE.search(rel) and not ENV_TEMPLATE.search(rel):
            if allowed(entries, rel, "env-file", None):
                by_file += 1
            else:
                hits.append({"file": rel, "snippet": ".env file in the repository; keep it out of git", "rule": "env-file"})
        if p.stat().st_size > o["max_bytes"]:
            skipped += 1
            continue
        data = p.read_bytes()
        if b"\0" in data[:8000]:
            continue  # binary, as git grep -I
        scanned += 1
        for n, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            for kind, shown, digest in scan_line(line, kinds):
                if allow_hashes and digest.startswith(allow_hashes):
                    continue
                if allowed(entries, rel, kind, digest):
                    by_file += 1
                    continue
                hits.append({"file": rel, "line": n, "rule": kind, "snippet": f"{kind} {shown} sha256:{digest[:12]}"})
    detail = f"{scanned} {'tracked ' if mode == 'tracked' else ''}text files read, {len(hits)} secret hits"
    if by_file:
        detail += f", {by_file} allowed by {o['allow_file']}"
    if skipped:
        detail += f", {skipped} files over {o['max_bytes']} bytes skipped"
    unused = [e["line"] for e in entries if not e["used"]]
    if unused:
        detail += f"; allow entries that matched nothing: lines {', '.join(map(str, unused))}"
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}


# ---------- git ----------
def git_run(args, cwd):
    """The completed process. Replace objects are off, so the scan reads what a push sends. Standard input is closed."""
    return subprocess.run(["git", "--no-replace-objects", "-c", "core.quotepath=off", *args], cwd=cwd,
                          stdin=subprocess.DEVNULL, capture_output=True)


def git_out(args, cwd):
    p = git_run(args, cwd)
    if p.returncode:
        raise RuntimeError("git " + args[0] + " failed: " + p.stderr.decode("utf-8", "replace").strip()[:200])
    return p.stdout


def git_text(args, cwd):
    return git_out(args, cwd).decode("utf-8", "replace")


def git_blob(rev, path, cwd):
    """The text of path at rev (a commit, or "" for the index), or None when the path is not there."""
    p = git_run(["show", f"{rev}:{path}"], cwd)
    return None if p.returncode else p.stdout.decode("utf-8", "replace")


def empty_tree(cwd):
    return git_text(["hash-object", "-t", "tree", os.devnull], cwd).strip()


ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11, '"': 34, "\\": 92}


def unquote(s):
    """A path as git quotes it in a diff header (C-style, in double quotes), or s as it is."""
    if not (len(s) >= 2 and s[0] == '"' and s[-1] == '"'):
        return s
    body, out, i = s[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            if body[i + 1] in ESCAPES:
                out.append(ESCAPES[body[i + 1]])
                i += 2
                continue
            octal = re.match(r"[0-7]{3}", body[i + 1:i + 4])
            if octal:
                out.append(int(octal.group(0), 8))
                i += 4
                continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", "replace")


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
ZERO = re.compile(r"^0+$")


def added_lines(diff):
    """[(path, line number in the new file, text)] for every added line of a -U0 diff made with the prefixes a/ and b/."""
    out, path, header, nxt = [], None, False, 0
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            header, path = True, None
        elif header and line.startswith("+++ "):
            p = unquote(line[4:].rstrip("\t"))
            path = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
        elif line.startswith("@@"):
            header = False
            m = HUNK.match(line)
            nxt = int(m.group(1)) if m else 0
        elif header or path is None or line.startswith("\\"):
            continue
        elif line.startswith("+"):
            out.append((path, nxt, line[1:]))
            nxt += 1
        elif not line.startswith("-"):
            nxt += 1
    return out


def new_paths(name_status):
    """Paths a change adds, copies or renames to, from git diff --name-status -z output."""
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


class ScanError(Exception):
    """A ref or object the scanner cannot read. The message holds no content."""


class Scan:
    """One scan with one configuration: the patterns, excludes and allow entries as the pushed revision (or the index) has them."""

    def __init__(self, cwd, read):
        self.cwd = cwd
        cfg = self.load_config(read("gate/gate.json"))
        self.kinds = compile_patterns(cfg["patterns"])
        self.env_files, self.exclude = cfg["env_files"], cfg["exclude"]
        self.allow_file = cfg["allow_file"]
        self.entries, self.problems = load_allow(read(self.allow_file) or "")
        self.entries += [{"glob": g, "kind": "*", "digest": None, "line": 0, "used": 0} for g in cfg["allow"]]
        self.entries += [{"glob": "*", "kind": "*", "digest": h.lower(), "line": 0, "used": 0} for h in cfg["allow_hashes"] if len(h) >= 8]

    @staticmethod
    def load_config(text):
        """The options of security.secrets and the exclude list from gate/gate.json, as the gate reads them; defaults without the file."""
        cfg = {"patterns": DEFAULTS["patterns"], "env_files": True, "allow": [], "allow_hashes": [],
               "allow_file": DEFAULTS["allow_file"], "exclude": DEFAULT_EXCLUDE}
        if text is None:
            return cfg
        try:
            data = json.loads(text)
        except ValueError:
            raise ConfigError("gate/gate.json is not valid JSON") from None
        if not isinstance(data, dict):
            raise ConfigError("gate/gate.json is not a JSON object")
        rule = (data.get("rules") or {}).get(ID) if isinstance(data.get("rules"), dict) else None
        options = rule.get("options") if isinstance(rule, dict) else None
        found = dict(options) if isinstance(options, dict) else {}
        if "exclude" in data:
            found["exclude"] = data["exclude"]
        for key, want in (("patterns", dict), ("env_files", bool), ("allow", list), ("allow_hashes", list), ("allow_file", str), ("exclude", list)):
            if key in found:
                if not isinstance(found[key], want) or (want is list and not all(isinstance(x, str) for x in found[key])):
                    raise ConfigError(f"gate/gate.json: option {key} has the wrong type")
                cfg[key] = found[key]
        return cfg

    def mask(self, text):
        return mask(text, self.kinds)

    def text_findings(self, commit, where, text, first_line=1):
        out = []
        for n, line in enumerate(text.split("\n"), first_line):
            out += [(commit, where, n, kind, shown, digest) for kind, shown, digest in scan_line(line, self.kinds)
                    if not allowed(self.entries, where, kind, digest)]
        return out

    def problem_findings(self):
        return [("config", self.allow_file, n, "allow-entry", PROBLEMS[code], None) for n, code in self.problems]

    def change(self, label, bases, head):
        """Findings for what a change adds. head is a revision, or None for the index. With several bases (a merge) a line
        or path counts only when it is new against every base: what a merge takes from a parent was scanned with that parent."""
        keep, new = None, None
        for base in bases:
            rng = [base, head] if head else ["--cached", base]
            patch = git_text(["diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--text", "-M",
                              "--src-prefix=a/", "--dst-prefix=b/", *rng], self.cwd)
            added = added_lines(patch)
            names = set(new_paths(git_text(["diff", "--name-status", "-z", "-M", "--no-ext-diff", *rng], self.cwd)))
            if keep is None:
                keep, new = added, names
            else:
                seen = {(p, t) for p, _, t in added}
                keep = [x for x in keep if (x[0], x[2]) in seen]
                new &= names
        out = []
        for path in sorted(new or ()):
            if excluded(self.exclude, path):
                continue
            if self.env_files and ENV_FILE.search(path) and not ENV_TEMPLATE.search(path) and not allowed(self.entries, path, "env-file", None):
                out.append((label, path, None, "env-file", ".env file in the change; keep it out of git", None))
        for path, n, text in keep or ():
            if not excluded(self.exclude, path):
                out += self.text_findings(label, path, text, n)
        return out

    def commit(self, sha):
        short = sha[:12]
        parents = git_text(["rev-list", "--parents", "-n", "1", sha], self.cwd).split()[1:]
        out = self.text_findings(short, "commit-message", git_text(["log", "-1", "--format=%B", sha], self.cwd))
        return out + self.change(short, parents or [empty_tree(self.cwd)], sha)


def describe(scan, f):
    commit, where, line, kind, shown, digest = f
    place = scan.mask(where) + (f":{line}" if line else "")
    tail = f"{kind} {shown}" + (f" sha256:{digest[:12]}" if digest else "")
    return f"  {commit} {place} {tail}" if commit != "config" else f"  {place} {shown}"


def report(scan, found, what, tier):
    """Report lines for the findings, most useful first. Never a value, never a way to skip the hook."""
    found = sorted(set(found), key=lambda f: (f[0], f[1], f[2] or 0, f[3], f[5] or ""))
    head = (f"secrets: {what} stopped, {len(found)} hits:" if tier == "block"
            else f"secrets: tier warn, {what} goes on, {len(found)} hits:")
    lines = [head] + [describe(scan, f) for f in found[:MAX_SHOWN]]
    if len(found) > MAX_SHOWN:
        lines.append(f"  and {len(found) - MAX_SHOWN} more")
    live = ("A live value: unstage the file or the lines, keep the value in a secret store, and rotate it if it left this machine (/security:secrets)."
            if what == "commit" else
            "A live value: take it out of the commits that carry it (git commit --amend for the last one, git rebase for older ones), keep it in a secret store, and rotate it if it left this machine (/security:secrets).")
    lines += [live, "A documented example value: add one line to .secrets-allow at the repository root: <path glob> <kind> sha256:<digits from the hit> <reason>."]
    return lines


# ---------- pre-push ----------
def pushed_commits(remote, local_sha, remote_sha, cwd):
    """Commits the push sends: reachable from local_sha and from no ref of the remote."""
    args = ["rev-list", local_sha, "--not", f"--remotes={remote}"]
    if not ZERO.match(remote_sha) and git_run(["cat-file", "-e", remote_sha + "^{commit}"], cwd).returncode == 0:
        args.append(remote_sha)
    return git_text(args, cwd).split()


def object_type(sha, cwd):
    return git_text(["cat-file", "-t", sha], cwd).strip()


def pre_push(remote, refs, cwd, tier):
    """Exit code and report lines for the refs git sends on the hook's stdin."""
    found, commits, scans = [], 0, []
    for line in refs:
        parts = line.split()
        if len(parts) != 4 or ZERO.match(parts[1]):
            continue  # a deletion sends no content
        local_ref, local_sha, remote_ref, remote_sha = parts
        scan = Scan(cwd, lambda path, rev=local_sha: git_blob(rev, path, cwd))
        scans.append(scan)
        kind = object_type(local_sha, cwd)
        peeled = object_type(local_sha + "^{}", cwd) if kind == "tag" else kind
        if peeled != "commit":
            raise ScanError(f"ref {scan.mask(remote_ref)} points to a {peeled}, not a commit; the scanner reads commits only")
        found += scan.problem_findings()
        found += scan.text_findings("ref", "ref-name", remote_ref)
        if kind == "tag":
            body = git_text(["cat-file", "-p", local_sha], cwd).split("\n\n", 1)  # header, then the message
            found += scan.text_findings("tag", "tag-message", body[1] if len(body) > 1 else "")
        for sha in pushed_commits(remote, local_sha, remote_sha, cwd):
            commits += 1
            found += scan.commit(sha)
    if not found:
        return 0, []
    lines = report(scans[0], found, f"push to {remote} ({commits} commits)", tier)
    return (1 if tier == "block" else 0), lines


def current_ref(cwd):
    p = git_run(["symbolic-ref", "-q", "HEAD"], cwd)
    return p.stdout.decode().strip() if p.returncode == 0 else "HEAD"


# ---------- pre-commit ----------
def pre_commit(cwd, tier):
    """Exit code and report lines for the staged changes."""
    scan = Scan(cwd, lambda path: git_blob("", path, cwd))
    head = git_run(["rev-parse", "-q", "--verify", "HEAD"], cwd)
    bases = [head.stdout.decode().strip()] if head.returncode == 0 else [empty_tree(cwd)]
    merge = git_run(["rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd)
    if merge.returncode == 0:
        bases.append(merge.stdout.decode().strip())
    found = scan.problem_findings() + scan.change("staged", bases, None)
    if not found:
        return 0, []
    return (1 if tier == "block" else 0), report(scan, found, "commit", tier)


# ---------- history ----------
def history(root):
    """(hits, commits) over the added lines of every commit on every branch, tag and remote-tracking ref."""
    scan = Scan(root, lambda path: git_blob("HEAD", path, root))
    shas = git_text(["rev-list", "--branches", "--tags", "--remotes"], root).split()
    found = scan.problem_findings()
    for sha in shas:
        found += scan.commit(sha)
    return scan, sorted(set(found), key=lambda f: (f[0], f[1], f[2] or 0, f[3], f[5] or "")), len(shas)


# ---------- install ----------
def dispatcher_text(hook):
    return f"""#!/bin/sh
# {DISPATCH_MARK} (CTO powersuit, security module): runs every executable in {hook}.d in name order,
# each with this hook's arguments and standard input; the hook fails when one of them does.
dir="$(dirname "$0")/{hook}.d"
[ -d "$dir" ] || exit 0
input="$(mktemp "${{TMPDIR:-/tmp}}/powersuit-hook.XXXXXX")" || exit 1
trap 'rm -f "$input"' EXIT HUP INT TERM
cat > "$input"
status=0
for h in "$dir"/*; do
  [ -f "$h" ] && [ -x "$h" ] || continue
  "$h" "$@" < "$input" || status=1
done
exit "$status"
"""


def shim_text(hook, tier):
    call = 'pre-push "$@"' if hook == "pre-push" else "pre-commit"
    return f"#!/bin/sh\n# {HOOK_MARK.format(hook)} (CTO powersuit, security module)\nexec python3 {shlex.quote(str(Path(__file__).resolve()))} {call} --tier {tier}\n"


def put(path, text):
    """Write path through a temporary file in the same folder, so a hook is never half written."""
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(text)
    tmp.chmod(0o755)
    os.replace(tmp, path)


def install_hook(into, tier=DEFAULT_TIER, with_commit=False):
    """Write a dispatcher as <into>/pre-push (and pre-commit) and the secrets hook as <hook>.d/20-secrets. A private-terms
    shim already in pre-push moves to pre-push.d/10-private-terms, so both run. Any other hook is left as it is."""
    into = Path(os.path.expanduser(into))
    plans = []
    for hook in ["pre-push"] + (["pre-commit"] if with_commit else []):
        target, chain = into / hook, into / f"{hook}.d"
        mine, move = chain / "20-secrets", None
        if os.path.lexists(target):
            if target.is_symlink() or not target.is_file():
                return 2, [f"{target} is a link or not a file; chain it by hand"]
            text = target.read_text(errors="replace")
            if DISPATCH_MARK not in text:
                if hook == "pre-push" and PRIVATE_TERMS_MARK in text:
                    move = (chain / "10-private-terms", text)
                    if os.path.lexists(move[0]):
                        return 2, [f"{move[0]} exists; chain the hooks by hand"]
                else:
                    return 2, [f"{target} exists and is another hook; chain it by hand: call secrets.py {hook} from it (see /security:secrets)"]
        if os.path.lexists(mine) and (mine.is_symlink() or HOOK_MARK.format(hook) not in mine.read_text(errors="replace")):
            return 2, [f"{mine} exists and is another hook; chain it by hand"]
        plans.append((hook, target, chain, mine, move))
    lines = []
    for hook, target, chain, mine, move in plans:
        chain.mkdir(parents=True, exist_ok=True)
        if move:
            put(move[0], move[1])
            lines.append(f"moved the private-terms hook to {move[0]}")
        put(mine, shim_text(hook, tier))
        put(target, dispatcher_text(hook))
        lines.append(f"wrote {target} and {mine} (tier {tier})")
    return 0, lines


# ---------- command line ----------
def tier_arg(p):
    p.add_argument("--tier", choices=TIERS, default=DEFAULT_TIER,
                   help="block stops the push or the commit on a hit; warn reports it and goes on (default %(default)s)")


def main(argv):
    ap = argparse.ArgumentParser(description="Secret values stay out of git.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("pre-push", help="run as the pre-push hook")
    h.add_argument("remote")
    h.add_argument("url", nargs="?", default="")
    tier_arg(h)
    c = sub.add_parser("pre-commit", help="run as the pre-commit hook")
    tier_arg(c)
    k = sub.add_parser("check", help="scan what a push of the current branch would send")
    k.add_argument("remote", nargs="?", default="origin")
    tier_arg(k)
    y = sub.add_parser("history", help="list the secret hits in the added lines of every commit, masked")
    y.add_argument("root", nargs="?", default=".")
    i = sub.add_parser("install-hook", help="write the dispatcher and the hook into a hooks folder")
    i.add_argument("--into", required=True, help=".git/hooks of one repository, or the hooks folder of a git template")
    i.add_argument("--pre-commit", action="store_true", help="also install the pre-commit hook")
    tier_arg(i)
    a = ap.parse_args(argv)
    tier = getattr(a, "tier", DEFAULT_TIER)
    stream = sys.stderr if a.cmd in ("pre-push", "pre-commit", "check") else sys.stdout
    try:
        if a.cmd == "install-hook":
            code, lines = install_hook(a.into, a.tier, a.pre_commit)
        elif a.cmd == "history":
            root = Path(a.root).resolve()
            scan, found, n = history(root)
            lines = [describe(scan, f) for f in found[:MAX_SHOWN]]
            if len(found) > MAX_SHOWN:
                lines.append(f"  and {len(found) - MAX_SHOWN} more")
            lines.append(f"secrets: {n} commits read, {len(found)} hits")
            code = 1 if found else 0
        elif a.cmd == "pre-commit":
            code, lines = pre_commit(os.getcwd(), tier)
        elif a.cmd == "check":
            cwd = os.getcwd()
            ref = current_ref(cwd)
            sha = git_text(["rev-parse", "HEAD"], cwd).strip()
            code, lines = pre_push(a.remote, [f"{ref} {sha} {ref} {'0' * 40}"], cwd, tier)
            lines = lines or ["secrets: no hits in what a push of this branch would send"]
        else:
            code, lines = pre_push(a.remote, sys.stdin.read().splitlines(), os.getcwd(), tier)
    except (ConfigError, ScanError) as e:
        code, lines = 2, [f"secrets: {e}"]
    except (RuntimeError, OSError) as e:
        code, lines = 2, [f"secrets: the scan failed ({type(e).__name__}): {mask(str(e), compile_patterns(DEFAULTS['patterns']))}"]
    if code == 2 and tier == "warn" and a.cmd in ("pre-push", "pre-commit"):
        lines.append("secrets: tier warn, nothing was checked and the push goes on" if a.cmd == "pre-push" else "secrets: tier warn, nothing was checked and the commit goes on")
        code = 0
    elif code == 2 and a.cmd in ("pre-push", "pre-commit"):
        lines.append("secrets: nothing was checked, so the " + ("push" if a.cmd == "pre-push" else "commit") + " is stopped. Fix the cause above and run it again.")
    for line in lines:
        print(line, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
