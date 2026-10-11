"""Interview rubrics have dimensions with a name, a signal and anchored levels numbered from 1."""
import json
import re

ID = "hiring.rubric-anchors"
DESCRIPTION = ("Every interview rubric has at least one dimension; every dimension has a name, a signal and levels "
               "keyed 1 to N with no gap, and every level has an anchor that is neither empty nor a placeholder in angle brackets.")
DEFAULTS = {"globs": ["hiring/rubrics/*.json"]}

PLACEHOLDER = re.compile(r"<[^<>\n]*>")


def state(value):
    """'ok', 'empty' or 'placeholder'. A value with no letter or digit left after removing <...> spans is a placeholder."""
    if not isinstance(value, str) or not value.strip():
        return "empty"
    return "ok" if re.search(r"[A-Za-z0-9]", PLACEHOLDER.sub("", value)) else "placeholder"


def find_line(lines, pattern, start=0):
    """1-based number of the first line from start that matches pattern, or None."""
    pat = re.compile(pattern)
    for n in range(start, len(lines)):
        if pat.search(lines[n]):
            return n + 1
    return None


def check(ctx):
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(p.startswith("_") for p in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}
    hits, bad, dims = [], set(), 0

    for f in files:
        rel, raw = ctx.rel(f), ctx.read(f)
        lines = raw.split("\n")

        def hit(line, snippet):
            hits.append({"file": rel, "line": line or 1, "snippet": snippet})
            bad.add(rel)

        try:
            rubric = json.loads(raw)
        except ValueError:
            hit(1, "not valid JSON")
            continue
        if not isinstance(rubric, dict):
            hit(1, "not a JSON object")
            continue
        dimensions = rubric.get("dimensions")
        if not isinstance(dimensions, list) or not dimensions:
            hit(find_line(lines, r'"dimensions"\s*:'), "no dimensions")
            continue
        for i, dim in enumerate(dimensions, 1):
            dims += 1
            if not isinstance(dim, dict):
                hit(find_line(lines, r'"dimensions"\s*:'), f"dimension {i}: not an object")
                continue
            name = dim.get("name")
            label = name.strip() if state(name) == "ok" else f"dimension {i}"
            at = find_line(lines, r'"name"\s*:\s*' + re.escape(json.dumps(name))) if isinstance(name, str) else None
            start = (at or 1) - 1
            for key in ("name", "signal"):
                s = state(dim.get(key))
                if s != "ok":
                    hit(find_line(lines, r'"' + key + r'"\s*:', start) if s == "placeholder" else at,
                        f"{label}: {'missing' if s == 'empty' else 'placeholder'} {key}")
            levels = dim.get("levels")
            levels_at = find_line(lines, r'"levels"\s*:', start) or at
            if levels is None or levels == {}:
                hit(levels_at, f"{label}: missing levels")
                continue
            if not isinstance(levels, dict):
                hit(levels_at, f"{label}: levels must be an object keyed 1 to N")
                continue
            keys = list(levels)
            if sorted(keys, key=lambda k: (len(k), k)) != [str(n) for n in range(1, len(keys) + 1)]:
                hit(levels_at, f"{label}: level keys not consecutive from 1 ({', '.join(sorted(keys, key=lambda k: (len(k), k)))})")
            for k, v in levels.items():
                anchor = v.get("anchor") if isinstance(v, dict) else v
                s = state(anchor)
                if s != "ok":
                    where = find_line(lines, r'"' + re.escape(k) + r'"\s*:', (levels_at or 1) - 1) or levels_at
                    hit(where, f"{label}: level {k}: {'empty' if s == 'empty' else 'placeholder'} anchor")
    return {"result": "fail" if hits else "pass",
            "detail": f"rubric files checked: {len(files)}, dimensions: {dims}, files with problems: {len(bad)}",
            "hits": hits}
