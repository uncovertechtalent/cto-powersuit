"""Decision records (ADRs) carry a known status, an owner, a valid date and consistent supersede links."""
import datetime
import re

ID = "decisions.adr-fields"
DESCRIPTION = "Every ADR has a known status, an owner, an ISO date, a superseded_by that names an existing record when superseded, and a number no other record uses."
DEFAULTS = {
    "globs": ["docs/decisions/adr-[0-9]*.md"],
    "statuses": ["proposed", "accepted", "rejected", "deprecated", "superseded"],
    "date_fields": ["date", "created"],
}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILE_NUMBER = re.compile(r"^adr-(\d+)")


def valid_date(value):
    if not ISO_DATE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def record_number(meta, stem):
    """The adr field as an integer, or the number in the file name when the field is missing or not a number."""
    value = meta.get("adr", "").strip()
    if value.isdigit():
        return int(value)
    m = FILE_NUMBER.match(stem)
    return int(m.group(1)) if m else None


def check(ctx):
    statuses = list(ctx.options["statuses"])
    date_fields = list(ctx.options["date_fields"])
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"])}

    hits, numbers = [], {}
    for f in files:
        rel = ctx.rel(f)
        meta, _body, _line = ctx.front_matter(f)

        def hit(snippet):
            hits.append({"file": rel, "line": 1, "snippet": snippet})

        status = meta.get("status", "").strip()
        if not status:
            hit("missing status")
        elif status not in statuses:
            hit("unknown status: " + status)

        if not meta.get("owner", "").strip():
            hit("missing owner")

        field = next((k for k in date_fields if meta.get(k, "").strip()), None)
        if field is None:
            hit("missing date")
        elif not valid_date(meta[field].strip()):
            hit("malformed " + field)

        if status == "superseded":
            successors = [s.strip() for s in meta.get("superseded_by", "").split(",") if s.strip()]
            if not successors:
                hit("superseded without superseded_by")
            for slug in successors:
                name = slug[:-3] if slug.endswith(".md") else slug
                if not (f.parent / (name + ".md")).is_file():
                    hit("superseded_by names no record: " + slug)

        n = record_number(meta, f.stem)
        if n is not None:
            numbers.setdefault(n, []).append(rel)

    for n, rels in sorted(numbers.items()):
        if len(rels) > 1:
            for rel in rels:
                hits.append({"file": rel, "line": 1, "snippet": f"duplicate adr number {n:04d}"})

    hits.sort(key=lambda h: (h["file"], h["snippet"]))
    bad = len({h["file"] for h in hits})
    if hits:
        return {"result": "fail", "detail": f"problems: {len(hits)}, in {bad} of {len(files)} records", "hits": hits}
    return {"result": "pass", "detail": f"{len(files)} records checked: status, owner, date, supersede links and numbers are clean", "hits": []}
