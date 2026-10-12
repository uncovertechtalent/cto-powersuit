"""Every action and reusable workflow from outside the repository comes from an owner on the allowlist."""
import re
import sys
from pathlib import Path

ID = "security.action-owners"
DESCRIPTION = ("Workflows and composite actions use actions and reusable workflows only from owners on the "
               "allowlist, and Docker images only from listed prefixes. A new owner in a workflow is a new party "
               "that runs code with the workflow's token. Pinning is the job of gate.actions-pinned; this rule "
               "reads the owner only. Local actions (./..., ../... and the self-repository form $/...) are "
               "exempt.")
DEFAULTS = {
    "globs": [".github/workflows/*.yml", ".github/workflows/*.yaml",
              ".github/actions/**/action.yml", ".github/actions/**/action.yaml",
              "action.yml", "action.yaml"],
    # The owners this repository's own workflows use. Build your list with:
    #   python3 .github/actions/gate/rules/action_owners.py .
    "owners": ["actions"],
    "images": [],  # docker:// prefixes, e.g. "docker://ghcr.io/my-org/"; empty: every image is a hit
}
# The same reference pattern and local prefixes as gate.actions-pinned. $/ is GitHub's self-repository form.
LOCAL = ("./", "../", "$/")
USES = re.compile(r"""(?:^\s*(?:-\s+)?|[{,]\s*)uses\s*:\s*(['"]?)(?P<ref>[^'"\s#,}]+)\1""")


def references(text):
    """(line number, reference) for every external uses: reference in a workflow or action file."""
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for m in USES.finditer(line):
            ref = m.group("ref")
            if not ref.startswith(LOCAL):
                yield n, ref


def owner(ref):
    return ref.split("/", 1)[0].lower()


def check(ctx):
    files = ctx.files(ctx.options["globs"])
    if not files:
        return {"result": "n/a", "detail": "no workflow or action files"}
    owners = {o.lower().rstrip("/") for o in ctx.options["owners"]}
    images = tuple(ctx.options["images"])
    hits, refs = [], 0
    for p in files:
        rel = ctx.rel(p)
        for n, ref in references(ctx.read(p)):
            refs += 1
            if ref.startswith("docker://"):
                if not (images and ref.startswith(images)):
                    hits.append({"file": rel, "line": n, "rule": "image-not-allowed",
                                 "snippet": f"{ref.split('@')[0]}: image prefix not on the allowlist"})
            elif owner(ref) not in owners:
                hits.append({"file": rel, "line": n, "rule": "owner-not-allowed",
                             "snippet": f"{ref.split('@')[0]}: owner {owner(ref)} not on the allowlist"})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(files)} workflow and action files, {refs} external references, {len(hits)} from owners not on the list",
            "hits": hits}


if __name__ == "__main__":
    # List the owners and images a repository uses today, as a starting allowlist for review.
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = {}
    for g in DEFAULTS["globs"]:
        for p in sorted(root.glob(g)):
            for _, ref in references(p.read_text(encoding="utf-8", errors="replace")):
                key = ref.split("@")[0] if ref.startswith("docker://") else owner(ref)
                found.setdefault(key, set()).add(p.relative_to(root).as_posix())
    for key in sorted(found):
        print(f"{key}\t{len(found[key])} files\t{', '.join(sorted(found[key]))}")
