"""Tracked files carry no secret values and no .env files."""
import fnmatch
import hashlib
import re

ID = "security.secrets"
DESCRIPTION = ("Files tracked in git carry no value that matches a secret pattern (API keys, access keys, tokens, "
               "private key blocks) and no .env file. Hits show the pattern, the fixed prefix and a short sha256 of "
               "the value, never the value. Outside a git work tree the rule reads every file under root.")
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
    "max_bytes": 400000,        # larger files are skipped and counted in the detail
}
ENV_FILE = re.compile(r"(^|/)\.env(\.[^/]+)?$")
ENV_TEMPLATE = re.compile(r"\.(example|sample|template|dist)$")


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
    kinds = [(k, re.compile(p), shown) for k, (p, shown) in o["patterns"].items()]
    allow = list(o["allow"])
    allow_hashes = tuple(h.lower() for h in o["allow_hashes"] if len(h) >= 8)
    mode, files = candidates(ctx)
    hits, scanned, skipped = [], 0, 0
    for p in files:
        rel = ctx.rel(p)
        if not p.is_file() or any(fnmatch.fnmatch(rel, g) for g in allow):
            continue
        if o["env_files"] and ENV_FILE.search(rel) and not ENV_TEMPLATE.search(rel):
            hits.append({"file": rel, "snippet": ".env file in the repository; keep it out of git", "rule": "env-file"})
        if p.stat().st_size > o["max_bytes"]:
            skipped += 1
            continue
        data = p.read_bytes()
        if b"\0" in data[:8000]:
            continue  # binary, as git grep -I
        scanned += 1
        for n, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            for kind, rx, shown in kinds:
                for m in rx.finditer(line):
                    digest = hashlib.sha256(m.group(0).encode()).hexdigest()
                    if allow_hashes and digest.startswith(allow_hashes):
                        continue
                    hits.append({"file": rel, "line": n, "rule": kind,
                                 "snippet": f"{kind} {shown} sha256:{digest[:12]}"})
    detail = f"{scanned} {'tracked ' if mode == 'tracked' else ''}text files read, {len(hits)} secret hits"
    if skipped:
        detail += f", {skipped} files over {o['max_bytes']} bytes skipped"
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}
