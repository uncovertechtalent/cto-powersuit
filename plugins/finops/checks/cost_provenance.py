"""Cost figures on docs pages name the period they cover and the source they come from."""
import datetime
import re

ID = "finops.cost-provenance"
DESCRIPTION = ("Every cost figure on a docs page has a date range and a source: cost_period and cost_source in the "
               "front matter, or a (period <range>, source: <source>) marker on the line of the figure.")
DEFAULTS = {
    "globs": ["docs/**/*.md"],
    "symbols": ["€", "$", "£"],
    "codes": ["EUR", "USD", "GBP"],
}

DAY = r"\d{4}-\d{2}-\d{2}"
MONTH = r"\d{4}-\d{2}"
RANGE = re.compile(rf"^(?:({DAY})/({DAY})|({MONTH})/({MONTH}))$")
INLINE = re.compile(r"\(period\s+([^,()\s]+)\s*,\s*source:\s*([^()]*)\)")
CODE_SPAN = re.compile(r"`[^`]*`")
SCANNED_FIELDS = re.compile(r"^(title|summary)\s*:")


def parse_month(value):
    year, month = value.split("-")
    return datetime.date(int(year), int(month), 1)


def valid_range(value):
    """True for YYYY-MM-DD/YYYY-MM-DD or YYYY-MM/YYYY-MM with real dates and the start not after the end."""
    m = RANGE.match(value.strip())
    if not m:
        return False
    try:
        if m.group(1):
            start, end = datetime.date.fromisoformat(m.group(1)), datetime.date.fromisoformat(m.group(2))
        else:
            start, end = parse_month(m.group(3)), parse_month(m.group(4))
    except ValueError:
        return False
    return start <= end


def amount_pattern(symbols, codes):
    """A number with a currency symbol or code directly before or after it, with at most one space between."""
    num = r"\d(?:[\d.,]*\d)?"
    parts = []
    if symbols:
        sym = "|".join(re.escape(s) for s in symbols)
        parts += [rf"(?:{sym})\s?-?{num}", rf"(?<![\w.,]){num}\s?(?:{sym})"]
    if codes:
        code = "|".join(re.escape(c) for c in codes)
        parts += [rf"(?<![A-Za-z])(?:{code})\s?-?{num}", rf"(?<![\w.,]){num}\s?(?:{code})(?![A-Za-z])"]
    return re.compile("|".join(parts))


def field_line(text, key, body_line):
    """Line number of the key in the front matter, or 1 when the key is missing."""
    pat = re.compile(r"^" + re.escape(key) + r"\s*:")
    for n, line in enumerate(text.split("\n")[: max(body_line - 1, 0)], 1):
        if pat.match(line):
            return n
    return 1


def scanned_lines(text, body_line):
    """(line number, text) for the title and summary lines of the front matter and every body line outside
    fenced code. Inline code spans are blanked."""
    lines = text.split("\n")
    in_code = False
    for n, line in enumerate(lines, 1):
        if n < body_line:
            if SCANNED_FIELDS.match(line):
                yield n, CODE_SPAN.sub(" ", line)
            continue
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if not in_code:
            yield n, CODE_SPAN.sub(" ", line)


def check(ctx):
    pat = amount_pattern(list(ctx.options["symbols"]), list(ctx.options["codes"]))
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    hits = []
    figures = covered_by_page = 0
    for f in files:
        rel = ctx.rel(f)
        text = ctx.read(f)
        meta, _body, body_line = ctx.front_matter(f)

        period = meta.get("cost_period", "").strip()
        source = meta.get("cost_source", "").strip()
        period_ok = bool(period) and valid_range(period)
        if period and not period_ok:
            hits.append({"file": rel, "line": field_line(text, "cost_period", body_line), "snippet": "malformed cost_period"})
        page_ok = period_ok and bool(source)

        for n, line in scanned_lines(text, body_line):
            found = pat.search(line)
            if not found:
                continue
            figures += 1
            if page_ok:
                covered_by_page += 1
                continue
            marker = INLINE.search(line)
            if marker and valid_range(marker.group(1)) and marker.group(2).strip():
                continue
            if marker and not valid_range(marker.group(1)):
                snippet = "malformed inline period: " + marker.group(1)[:40]
            else:
                snippet = "cost figure without period and source: " + found.group(0).strip()[:40]
            hits.append({"file": rel, "line": n, "snippet": snippet})

    hits.sort(key=lambda h: (h["file"], h["line"], h["snippet"]))
    detail = (f"{len(files)} pages, {figures} lines with cost figures: {covered_by_page} covered by front matter, "
              f"{len(hits)} hits")
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}
