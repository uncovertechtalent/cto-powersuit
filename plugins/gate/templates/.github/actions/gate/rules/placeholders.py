"""Placeholder text in published files: TODO, TBD and fill-in markers."""
import re

ID = "gate.placeholders"
DESCRIPTION = "Published files carry no placeholder text such as TODO, TBD or [To be filled]."
DEFAULTS = {
    "globs": ["**/*.md", "**/*.html"],
    "exclude": [],
    "pattern": r"\bTODO\b|\bTBD\b|\bFIXME\b|\[To be filled[^\]]*\]|\bLINK PENDING\b",
}


def check(ctx):
    pat = re.compile(ctx.options["pattern"])
    files = ctx.files(ctx.options["globs"], ctx.options["exclude"])
    hits = []
    for f in files:
        in_code = False
        for n, line in enumerate(ctx.read(f).split("\n"), 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_code = not in_code
                continue
            if in_code:
                continue
            for m in pat.finditer(re.sub(r"`[^`]*`", " ", line)):
                hits.append({"file": ctx.rel(f), "line": n, "snippet": m.group(0)})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(hits)} placeholder hits in {len(files)} files (code spans and fenced code are skipped)",
            "hits": hits}
