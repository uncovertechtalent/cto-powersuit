"""The backup inventory records, per data store, a copy outside production admin reach and a restore test that is recent, passed and within its time target."""
import datetime
import re

ID = "reliability.backup-inventory"
DESCRIPTION = ("Every data store in docs/sre/backups.md has a copy outside production admin reach that no production "
               "administrator can delete, and a restore test with a date, a pass result and a measured restore time "
               "within the target; a restore test older than max_age_days is a warning.")
DEFAULTS = {
    "globs": ["docs/sre/backups.md"],
    "max_age_days": 90,
    "stale_fails": False,
}

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$")
DIVIDER = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
PLACEHOLDER = re.compile(r"<[^<>]*>")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)?$", re.I)
UNITS = {"h": 60, "hr": 60, "hrs": 60, "hour": 60, "hours": 60, "d": 1440, "day": 1440, "days": 1440}
REACH = ("separate-account", "immutable", "offline")
NOBODY = ("none", "nobody", "no one", "-")

COPY, DELETERS, TESTED, RESULT, MEASURED, TARGET = (
    "out-of-reach copy", "out-of-reach deletable by", "last restore test", "restore result",
    "restore time measured", "restore time target")
ADMINS = "production administrators"


def norm(key):
    return re.sub(r"\s+", " ", key.strip().strip("*`").lower())


def filled(value):
    return bool(value) and not PLACEHOLDER.search(value)


def parse(text, body_line):
    """Return (page, stores). page and each store's 'fields' map a normalised field name to (value, line number);
    a store also has 'name' and 'line'. A level 3 heading opens a store; a level 1 or 2 heading closes it.
    Fields are the rows of a 'Field | Value' table. Fenced code is skipped."""
    page, stores, current, in_code = {}, [], None, False
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
            if len(m.group(1)) == 3:
                current = {"name": m.group(2).strip(), "line": n, "fields": {}}
                stores.append(current)
            elif len(m.group(1)) <= 2:
                current = None
            continue
        m = ROW.match(line)
        if m and not DIVIDER.match(line) and norm(m.group(1)) != "field":
            (current["fields"] if current else page).setdefault(norm(m.group(1)), (m.group(2).strip(), n))
    return page, stores


def identities(value):
    """Lower-cased identities of a comma or semicolon list, without parenthetical notes."""
    out = set()
    for part in re.split(r"[,;]", value):
        part = re.sub(r"\([^)]*\)", "", part)
        part = re.sub(r"\s+", " ", part).strip().strip("`").lower()
        if part and part not in NOBODY:
            out.add(part)
    return out


def minutes(value):
    m = DURATION.match(value.strip())
    if not m:
        return None
    return float(m.group(1)) * UNITS.get((m.group(2) or "min").lower(), 1)


def shown(x):
    return f"{x:g}"


def iso_date(value):
    """The date of a YYYY-MM-DD string, or None; fromisoformat alone also takes other forms on Python 3.11+."""
    if not DATE.match(value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def check(ctx):
    max_age = ctx.options["max_age_days"]
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    problems, stale = [], []
    stores_seen = flagged = 0
    for f in files:
        rel = ctx.rel(f)
        _meta, _body, body_line = ctx.front_matter(f)
        page, stores = parse(ctx.read(f), body_line)
        admins = identities(page[ADMINS][0]) if ADMINS in page and filled(page[ADMINS][0]) else set()
        relies_on_admins = False

        def hit(bucket, line, snippet):
            bucket.append({"file": rel, "line": line, "snippet": snippet})

        if not stores:
            hit(problems, 1, "no data store listed")
        for s in stores:
            stores_seen += 1
            before = len(problems)
            name, fields = s["name"], s["fields"]

            def value(key):
                v, line = fields.get(key, ("", s["line"]))
                return (v if filled(v) else ""), line

            def say(key, snippet, bucket=problems):
                hit(bucket, value(key)[1], f"{name}: {snippet}")

            # 1. a copy outside production admin reach
            kinds, line = value(COPY)
            tokens = [t.strip().lower() for t in re.split(r"[,;]", kinds) if t.strip()]
            if not tokens:
                say(COPY, "no copy outside production admin reach recorded")
            elif tokens == ["none"]:
                say(COPY, "no copy outside production admin reach")
            elif any(t not in REACH for t in tokens):
                say(COPY, "copy outside production admin reach has an unknown value: " + kinds[:60])
            else:
                deleters, _ = value(DELETERS)
                if not deleters:
                    say(DELETERS, "identities that can delete or overwrite the out-of-reach copy not recorded")
                elif identities(deleters) & admins:
                    who = sorted(identities(deleters) & admins)[0]
                    say(DELETERS, f"out-of-reach copy can be deleted by production administrator {who}")
                relies_on_admins = True

            # 2. a restore test
            tested, _ = value(TESTED)
            if not tested or tested.lower() == "never":
                say(TESTED, "no restore test")
            elif not iso_date(tested):
                say(TESTED, "restore test date is not a YYYY-MM-DD date: " + tested[:40])
            else:
                day = iso_date(tested)
                if day > ctx.today:
                    say(TESTED, "restore test date is in the future: " + tested)
                elif (ctx.today - day).days > max_age:
                    say(TESTED, f"restore test older than {max_age} days", stale)
                result = value(RESULT)[0].lower()
                if not result:
                    say(RESULT, "restore test has no result")
                elif result == "fail":
                    say(RESULT, "last restore test failed")
                elif result != "pass":
                    say(RESULT, "restore result is not pass or fail: " + result[:40])
                else:
                    got, want = value(MEASURED)[0], value(TARGET)[0]
                    m, t = minutes(got) if got else None, minutes(want) if want else None
                    if not got:
                        say(MEASURED, "no measured restore time")
                    elif m is None:
                        say(MEASURED, "measured restore time is not a duration: " + got[:40])
                    if not want:
                        say(TARGET, "no restore time target")
                    elif t is None:
                        say(TARGET, "restore time target is not a duration: " + want[:40])
                    if m is not None and t is not None and m > t:
                        say(MEASURED, f"measured restore time {shown(m)} min is above the target {shown(t)} min")
            flagged += len(problems) > before
        if stores and not admins and relies_on_admins:
            hit(problems, page.get(ADMINS, ("", 1))[1], "no production administrators listed")

    detail = (f"{stores_seen} data stores: {flagged} with problems, {len(stale)} with a restore test older than "
              f"{max_age} days")
    order = lambda h: (h["file"], h["line"], h["snippet"])
    if problems:
        hits = problems + (stale if ctx.options["stale_fails"] else [])
        return {"result": "fail", "detail": detail, "hits": sorted(hits, key=order)}
    if stale:
        return {"result": "fail" if ctx.options["stale_fails"] else "warn", "detail": detail, "hits": sorted(stale, key=order)}
    return {"result": "pass", "detail": detail, "hits": []}

