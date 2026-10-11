"""Docs pages name an owner, a review date, a next review date and a Diátaxis type."""
import datetime
import re

ID = "docs.review"
DESCRIPTION = "Every docs page has an owner, reviewed as a date or no, a review_by date and a known type; a passed review_by or reviewed: no is a warning."
DEFAULTS = {
    "globs": ["docs/**/*.md"],
    "types": ["tutorial", "how-to", "reference", "explanation"],
    "overdue_fails": False,
}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valid_date(value):
    if not ISO_DATE.match(value or ""):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def field_line(text, key, body_line):
    """Line number of the key in the front matter, or 1 when the key is missing."""
    if key:
        pat = re.compile(r"^" + re.escape(key) + r"\s*:")
        for n, line in enumerate(text.split("\n")[: max(body_line - 1, 0)], 1):
            if pat.match(line):
                return n
    return 1


def check(ctx):
    types = list(ctx.options["types"])
    today = ctx.today.isoformat()
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    problems, late = [], []
    overdue = not_reviewed = 0
    for f in files:
        rel = ctx.rel(f)
        text = ctx.read(f)
        meta, _body, body_line = ctx.front_matter(f)

        def hit(bucket, key, snippet):
            bucket.append({"file": rel, "line": field_line(text, key, body_line), "snippet": snippet})

        if not meta:
            hit(problems, None, "missing front matter")
            continue

        if not meta.get("owner", "").strip():
            hit(problems, "owner", "missing owner")

        reviewed = meta.get("reviewed", "").strip()
        review_by = meta.get("review_by", "").strip()
        if not reviewed:
            hit(problems, "reviewed", "missing reviewed")
        elif reviewed != "no" and not valid_date(reviewed):
            hit(problems, "reviewed", "malformed reviewed date")
        if review_by and not valid_date(review_by):
            hit(problems, "review_by", "malformed review_by date")
        elif not review_by and valid_date(reviewed):
            hit(problems, "review_by", "missing review_by")

        page_type = meta.get("type", "").strip()
        if not page_type:
            hit(problems, "type", "missing type")
        elif page_type not in types:
            hit(problems, "type", "unknown type: " + page_type)

        if valid_date(review_by) and review_by < today:
            overdue += 1
            hit(late, "review_by", "review overdue")
        if reviewed == "no":
            not_reviewed += 1
            hit(late, "reviewed", "not reviewed")

    bad = len({h["file"] for h in problems})
    detail = (f"{len(files)} pages: {bad} with missing or malformed fields, {overdue} past review_by, "
              f"{not_reviewed} not reviewed")
    order = lambda h: (h["file"], h["line"], h["snippet"])
    if problems:
        hits = problems + (late if ctx.options["overdue_fails"] else [])
        return {"result": "fail", "detail": detail, "hits": sorted(hits, key=order)}
    if late:
        return {"result": "fail" if ctx.options["overdue_fails"] else "warn", "detail": detail, "hits": sorted(late, key=order)}
    return {"result": "pass", "detail": detail, "hits": []}
