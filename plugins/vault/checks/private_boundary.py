"""Nothing marked private in a vault reaches the published docs tree."""
import re

ID = "vault.private-boundary"
DESCRIPTION = ("No published page carries a private tag (private, status/private, status/sensitive) in its "
               "front matter or as an inline tag; the vault's private boundary holds when notes are published.")
DEFAULTS = {"globs": ["docs/**/*.md"], "private_tags": ["private", "status/private", "status/sensitive"], "exclude": []}


def check(ctx):
    tags = [t.lower() for t in ctx.options["private_tags"]]
    inline = re.compile(r"(?:^|\s)#(" + "|".join(re.escape(t) for t in tags) + r")(?![\w/-])", re.I)
    files = [f for f in ctx.files(ctx.options["globs"], ctx.options["exclude"])
             if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"])}
    hits = []
    for f in files:
        meta, body, body_line = ctx.front_matter(f)
        fm_tags = {t.strip().lstrip("#").lower() for t in re.split(r"[,\s]+", meta.get("tags", "")) if t.strip()}
        for t in sorted(fm_tags & set(tags)):
            hits.append({"file": ctx.rel(f), "line": 1, "snippet": f"front matter tag {t}"})
        in_code = False
        for n, line in enumerate(body.split("\n"), body_line):
            if line.lstrip().startswith(("```", "~~~")):
                in_code = not in_code
                continue
            if in_code:
                continue
            for m in inline.finditer(re.sub(r"`[^`]*`", " ", line)):
                hits.append({"file": ctx.rel(f), "line": n, "snippet": f"inline tag #{m.group(1).lower()}"})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(files)} published pages checked, {len(hits)} private tags found",
            "hits": hits}
