"""Every direction review memo names its date and period, carries the four sections, and gives every decision a status."""
import datetime
import re

ID = "direction.review-memo"
DESCRIPTION = ("Every direction review memo has an ISO date and a period in the front matter, the sections What moved, "
               "Blocked, Proposed allocation, and Decisions needed, and a status (open, recorded: <id>, or "
               "dropped: <reason>) at the end of every decision line.")
DEFAULTS = {
    "globs": ["docs/direction/**/review-*.md"],
    "sections": ["What moved", "Blocked", "Proposed allocation", "Decisions needed"],
    "decisions": "Decisions needed",   # the section whose list items are decisions; one of "sections"
}

DAY = r"\d{4}-\d{2}-\d{2}"
DATE = re.compile(rf"^{DAY}$")
PERIOD = re.compile(rf"^({DAY})/({DAY})$")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.*)$")   # top-level items only; an indented sub-item is part of its decision
STATUS = re.compile(r"\((?:open|recorded:\s*[A-Za-z0-9_.-]+(?:\s*,\s*[A-Za-z0-9_.-]+)*|dropped:\s*\S[^()]*(?:\([^()]*\)[^()]*)?)\)\s*$")
NONE = re.compile(r"^\s*None\.?\s*$")


def iso_date(value):
    """True for YYYY-MM-DD with a real date; fromisoformat alone also takes 20261009 and week dates on Python 3.11+."""
    if not DATE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def valid_period(value):
    m = PERIOD.match(value.strip())
    if not m or not iso_date(m.group(1)) or not iso_date(m.group(2)):
        return False
    return m.group(1) <= m.group(2)


def field_line(text, key, body_line):
    """Line number of the key in the front matter, or 1 when the key is missing."""
    pat = re.compile(r"^" + re.escape(key) + r"\s*:")
    for n, line in enumerate(text.split("\n")[: max(body_line - 1, 0)], 1):
        if pat.match(line):
            return n
    return 1


def sections_of(text, body_line):
    """(heading text, line number, body lines) per heading in the body, outside fenced code."""
    out, current, in_code = [], None, False
    for n, line in enumerate(text.split("\n"), 1):
        if n < body_line:
            continue
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING.match(line)
        if m:
            current = (m.group(1).strip(), n, [])
            out.append(current)
        elif current:
            current[2].append((n, line))
    return out


def check(ctx):
    sections = list(ctx.options["sections"])
    decisions_name = str(ctx.options["decisions"]).strip().lower()
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    hits = []
    decisions = 0
    if decisions_name not in [s.strip().lower() for s in sections]:
        hits.append({"file": "gate/gate.json", "line": 1, "snippet": "decisions section not in sections: " + str(ctx.options["decisions"])[:40]})
    for f in files:
        rel = ctx.rel(f)
        text = ctx.read(f)
        meta, _body, body_line = ctx.front_matter(f)

        date = meta.get("date", "").strip()
        if not date:
            hits.append({"file": rel, "line": 1, "snippet": "missing date"})
        elif not iso_date(date):
            hits.append({"file": rel, "line": field_line(text, "date", body_line), "snippet": "malformed date: " + date[:40]})

        period = meta.get("period", "").strip()
        if not period:
            hits.append({"file": rel, "line": 1, "snippet": "missing period"})
        elif not valid_period(period):
            hits.append({"file": rel, "line": field_line(text, "period", body_line), "snippet": "malformed period: " + period[:40]})

        found = sections_of(text, body_line)
        by_name = {name.lower(): (line, body) for name, line, body in found}
        for name in sections:
            if name.strip().lower() not in by_name:
                hits.append({"file": rel, "line": 1, "snippet": "missing section: " + name})

        if decisions_name in by_name:
            heading_line, body = by_name[decisions_name]
            found_any = False
            for n, line in body:
                if NONE.match(line):
                    found_any = True
                    continue
                m = LIST_ITEM.match(line)
                if not m:
                    continue
                found_any = True
                decisions += 1
                if not STATUS.search(m.group(1)):
                    hits.append({"file": rel, "line": n, "snippet": "decision without status: " + m.group(1).strip()[:40]})
            if not found_any:
                hits.append({"file": rel, "line": heading_line, "snippet": "no decision line and no None. under " + str(ctx.options["decisions"])[:40]})

    hits.sort(key=lambda h: (h["file"], h["line"], h["snippet"]))
    detail = f"{len(files)} memos, {decisions} decision lines, {len(hits)} hits"
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}
