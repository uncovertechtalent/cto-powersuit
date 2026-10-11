"""Service catalogue entries name an owner, an SLO with a numeric target and at least one runbook that resolves."""
import re

ID = "reliability.service-catalog"
DESCRIPTION = ("Every services/*.yml entry has a non-empty owner, an slo with a numeric target, and at least one "
               "runbook link that resolves to a file, a docs page or an http(s) URL.")
DEFAULTS = {
    "globs": ["services/*.yml", "services/*.yaml"],
    "docs_dir": "docs",
}

KEY = re.compile(r"^([A-Za-z_][\w-]*)\s*:(?:\s+(.*))?$")
URL = re.compile(r"^https?://\S+$")
DOC = re.compile(r"^doc:([A-Za-z0-9][\w.-]*)(?:/([A-Za-z0-9][\w.-]*))?$")


class YamlError(Exception):
    pass


def strip_comment(line):
    """Drop a comment: a line that starts with #, or ' #' outside quotes."""
    if line.lstrip().startswith("#"):
        return ""
    quote = None
    for i, ch in enumerate(line):
        if ch in "\"'":
            quote = None if quote == ch else (quote or ch)
        elif ch == "#" and quote is None and i > 0 and line[i - 1] in " \t":
            return line[:i].rstrip()
    return line.rstrip()


def scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return "" if v in ("~", "null") else v


def value(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    return scalar(v)


def parse(text):
    """A YAML subset: top-level 'key: value', flow lists [a, b], block lists, folded or literal blocks
    (> and |), and one nested mapping level. Returns (data, lines), lines mapping 'key' and 'key.sub' to line numbers."""
    rows = text.split("\n")
    data, lines, i = {}, {}, 0
    indented = lambda r: r[:1] in (" ", "\t")
    while i < len(rows):
        line = strip_comment(rows[i])
        if not line.strip() or line.strip() in ("---", "..."):
            i += 1
            continue
        if indented(line):
            raise YamlError(f"line {i + 1}: indented line without a parent key")
        m = KEY.match(line)
        if not m:
            raise YamlError(f"line {i + 1}: expected 'key: value'")
        key, val = m.group(1), (m.group(2) or "").strip()
        if key in data:
            raise YamlError(f"line {i + 1}: duplicate key {key}")
        lines[key] = i + 1
        i += 1
        if val in (">", "|", ">-", "|-"):
            block = []
            while i < len(rows) and (not rows[i].strip() or indented(rows[i])):
                block.append(rows[i].strip())
                i += 1
            data[key] = (" " if val[0] == ">" else "\n").join(block).strip()
        elif val:
            data[key] = value(val)
        else:
            items, sub = [], {}
            item = lambda r: r.strip() == "-" or r.startswith("- ")
            while i < len(rows) and (not strip_comment(rows[i]).strip() or indented(rows[i]) or item(rows[i])):
                s = strip_comment(rows[i]).strip()
                if s == "-" or s.startswith("- "):
                    items.append(scalar(s[1:]))
                elif s:
                    m2 = KEY.match(s)
                    if not m2:
                        raise YamlError(f"line {i + 1}: expected '- item' or 'key: value' under {key}")
                    sub[m2.group(1)] = value(m2.group(2) or "")
                    lines[f"{key}.{m2.group(1)}"] = i + 1
                i += 1
            if items and sub:
                raise YamlError(f"line {lines[key]}: {key} mixes list items and keys")
            data[key] = items or sub or ""
    return data, lines


def number(v):
    try:
        return float(str(v).strip().rstrip("%"))
    except ValueError:
        return None


def resolves(link, f, ctx, docs_dir):
    """A relative path to an existing file (from the entry's folder or the repository root), a doc:<space>/<slug>
    link with <docs_dir>/<space>/<slug>.md present, or an http(s) URL."""
    if URL.match(link):
        return True
    m = DOC.match(link)
    if m:
        return (ctx.root / docs_dir / m.group(1) / ((m.group(2) or "index") + ".md")).is_file()
    if ":" in link.split("/")[0]:
        return False
    path = link.split("#")[0]
    if not path:
        return False
    return (f.parent / path).is_file() or (ctx.root / path.lstrip("/")).is_file()


def check(ctx):
    docs_dir = ctx.options["docs_dir"]
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    hits = []
    for f in files:
        rel = ctx.rel(f)

        def hit(line, snippet):
            hits.append({"file": rel, "line": line, "snippet": snippet})

        try:
            data, lines = parse(ctx.read(f))
        except YamlError as e:
            m = re.match(r"^line (\d+): (.*)$", str(e))
            hit(int(m.group(1)) if m else 1, "unreadable entry: " + (m.group(2) if m else str(e)))
            continue

        owner = data.get("owner", "")
        if not isinstance(owner, str) or not owner.strip():
            hit(lines.get("owner", 1), "missing owner")

        slo = data.get("slo")
        if slo in (None, ""):
            hit(lines.get("slo", 1), "missing slo")
        elif not isinstance(slo, dict):
            hit(lines["slo"], "slo is not a mapping")
        elif slo.get("target", "") in ("", []):
            hit(lines["slo"], "slo without target")
        else:
            target = number(slo["target"]) if isinstance(slo["target"], str) else None
            where = lines.get("slo.target", lines["slo"])
            if target is None:
                hit(where, "slo target is not a number: " + str(slo["target"])[:40])
            elif not 0 < target < 100:
                hit(where, "slo target outside 0 to 100: " + str(slo["target"])[:40])

        links = data.get("runbooks", [])
        links = [links] if isinstance(links, str) and links else links if isinstance(links, list) else []
        if not links:
            hit(lines.get("runbooks", 1), "no runbook link")
        for link in links:
            if not resolves(link, f, ctx, docs_dir):
                hit(lines.get("runbooks", 1), "runbook link does not resolve: " + link[:80])

    hits.sort(key=lambda h: (h["file"], h["line"], h["snippet"]))
    bad = len({h["file"] for h in hits})
    detail = f"{len(files)} catalogue entries: {bad} with problems, {len(hits)} hits"
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}
