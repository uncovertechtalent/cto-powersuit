"""Published text carries none of the blocking-tier vestige patterns."""
import json
import re

ID = "vestige.catalog-scan"
DESCRIPTION = ("Published Markdown carries no blocking-tier vestige pattern (praise openers, service closers, "
               "filler idioms, stage hooks). Code, quoted lines and quoted spans are exempt.")
# The starter blocking tier of hooks/vestige-patterns.js, ported to Python. A calibrated catalog
# replaces it through the option patterns_file: a JSON list of {"name", "pattern", "flags"}.
STARTER = [
    {"name": "praise-opener", "pattern": r"\b(great|good|excellent|fair|interesting) (question|point|catch|idea|observation)\b", "flags": "i"},
    {"name": "service-closer", "pattern": r"\b(let me know if|feel free to|happy to help|hope (this|that) helps|don't hesitate to)\b", "flags": "i"},
    {"name": "filler-idiom", "pattern": r"\b(at the end of the day|the bottom line is|needless to say)\b", "flags": "i"},
    {"name": "hook-opener", "pattern": r"(?:^|[.!?]\s+)[ \t]*(?:[-*+]\s+|\d+\.\s+|#+\s+)?(?:\*\*|_)?(?:here'?s the (?:thing|kicker|catch|twist)|let'?s (?:dive|jump) in|let'?s break (?:it|this) down|picture this|imagine this:|buckle up|spoiler(?: alert)?:|but wait)", "flags": "im"},
]
DEFAULTS = {"globs": ["docs/**/*.md", "README.md"], "patterns_file": "", "exclude": []}


def compile_rules(rules):
    out = []
    for r in rules:
        flags = (re.I if "i" in r.get("flags", "") else 0) | (re.M if "m" in r.get("flags", "") else 0)
        out.append((r["name"], re.compile(r["pattern"], flags)))
    return out


def strip_exempt(text):
    """Blank out what is a mention and not a use: fenced code, inline code, quoted lines,
    front matter and double-quoted spans up to 240 characters. Line numbers stay intact."""
    keep = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"\A---\n.*?\n---\n", keep, text, flags=re.S)
    text = re.sub(r"```.*?```|~~~.*?~~~", keep, text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", keep, text)
    text = re.sub(r"^\s*>.*$", keep, text, flags=re.M)
    return re.sub(r"[\"“][^\"“”\n]{1,240}[\"”]", keep, text)


def check(ctx):
    pf = ctx.options["patterns_file"]
    rules = STARTER
    if pf:
        path = ctx.root / pf
        if not path.is_file():
            return {"result": "fail", "detail": f"patterns_file {pf} not found", "hits": [{"file": pf, "snippet": "patterns file missing"}]}
        rules = json.loads(path.read_text(encoding="utf-8"))
    compiled = compile_rules(rules)
    files = [f for f in ctx.files(ctx.options["globs"], ctx.options["exclude"])
             if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"])}
    hits = []
    for f in files:
        text = strip_exempt(ctx.read(f))
        for name, rx in compiled:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                if m.group(0).startswith("\n"):
                    line += 1
                found = m.group(0).strip().lstrip(".!? \t")[:60]
                hits.append({"file": ctx.rel(f), "line": line, "snippet": f"{name}: {found}"})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(hits)} blocking-tier hits in {len(files)} files, {len(compiled)} rules",
            "hits": hits}
