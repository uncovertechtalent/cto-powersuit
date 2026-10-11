"""Every action and reusable workflow from outside the repository is referenced by a full commit SHA."""
import re

ID = "gate.actions-pinned"
DESCRIPTION = ("Workflows and composite actions reference every action and reusable workflow from outside the "
               "repository by a full 40-character commit SHA, and every Docker image by a sha256 digest. A tag "
               "or a branch can be moved to other code; a commit SHA cannot. Local actions (./...) are exempt.")
DEFAULTS = {
    "globs": [".github/workflows/*.yml", ".github/workflows/*.yaml",
              ".github/actions/**/action.yml", ".github/actions/**/action.yaml",
              "action.yml", "action.yaml"],
    "allow": [],  # reference prefixes exempt from the rule, e.g. "my-org/"; empty by default
}
USES = re.compile(r"""(?:^\s*(?:-\s+)?|[{,]\s*)uses\s*:\s*(['"]?)(?P<ref>[^'"\s#,}]+)\1""")
SHA = re.compile(r"^[0-9a-f]{40}$")
SHORT = re.compile(r"^[0-9a-f]{7,39}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
MESSAGE = {
    "tag-or-branch": "referenced by tag or branch; pin a full commit SHA",
    "short-sha": "short commit SHA; pin the full 40-character SHA",
    "no-ref": "no ref; pin a full commit SHA",
    "docker-tag": "image referenced by tag; pin a sha256 digest",
}


def classify(ref):
    """The hit rule for one reference, or None when it is local or pinned."""
    if ref.startswith(("./", "../")):
        return None
    if ref.startswith("docker://"):
        return None if DIGEST.search(ref) else "docker-tag"
    _, at, version = ref.rpartition("@")
    if not at:
        return "no-ref"
    if SHA.match(version):
        return None
    return "short-sha" if SHORT.match(version) else "tag-or-branch"


def check(ctx):
    files = ctx.files(ctx.options["globs"])
    if not files:
        return {"result": "n/a", "detail": "no workflow or action files"}
    allow = tuple(ctx.options["allow"])
    hits, refs = [], 0
    for p in files:
        rel = ctx.rel(p)
        for n, line in enumerate(ctx.read(p).splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in USES.finditer(line):
                ref = m.group("ref")
                if ref.startswith(("./", "../")) or (allow and ref.startswith(allow)):
                    continue
                refs += 1
                kind = classify(ref)
                if kind:
                    hits.append({"file": rel, "line": n, "snippet": f"{ref}: {MESSAGE[kind]}", "rule": kind})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(files)} workflow and action files, {refs} external references, {len(hits)} not pinned",
            "hits": hits}
