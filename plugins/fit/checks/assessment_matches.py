"""Every module marked fitted in docs/fit.md is present in the repository by its signal."""
import re

ID = "fit.assessment-matches"
DESCRIPTION = ("Every module marked fitted in the module table of docs/fit.md has its signal in the repository; "
               "a module present by signal and missing from the table, or not marked fitted, is a warning.")
DEFAULTS = {
    "page": "docs/fit.md",
    "signals": {},   # {"module": ["glob", ...]}; when set, used in place of the signal table on the page
}

RECOMMENDATIONS = ("fit now", "fit later", "not needed", "fitted")


def tables(text):
    """Markdown tables as lists of (line number, cells); the first row is the header."""
    out, cur = [], []
    for n, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                continue
            cur.append((n, cells))
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def find_table(all_tables, *words):
    for t in all_tables:
        head = [c.lower() for c in t[0][1]]
        if all(any(w in h for h in head) for w in words):
            return t, head
    return None, None


def plain(cell):
    return cell.replace("`", "").strip().lower()


def placeholder(cell):
    return not cell.strip() or bool(re.search(r"<[^<>]+>", cell))


def signal_globs(cell):
    found = re.findall(r"`([^`]+)`", cell)
    return found or [p.strip() for p in re.split(r"\bor\b|,", cell) if p.strip()]


def present(ctx, globs):
    for g in globs:
        if any(ch in g for ch in "*?["):
            for p in ctx.root.glob(g):
                if p.is_file() and not any(s.startswith("_") for s in ctx.rel(p).split("/")):
                    return True
        elif (ctx.root / g).is_file():
            return True
    return False


def check(ctx):
    page = ctx.options["page"]
    path = ctx.root / page
    if not path.is_file():
        return {"result": "n/a", "detail": f"no {page}", "hits": []}
    all_tables = tables(ctx.read(path))
    hits, warns = [], []

    signals = {plain(k): list(v) for k, v in (ctx.options.get("signals") or {}).items()}
    if not signals:
        st, head = find_table(all_tables, "module", "signal")
        if st:
            mi = head.index(next(h for h in head if "module" in h))
            si = head.index(next(h for h in head if "signal" in h))
            for _n, cells in st[1:]:
                if len(cells) > max(mi, si) and not placeholder(cells[mi]):
                    signals[plain(cells[mi])] = signal_globs(cells[si])
    if not signals:
        hits.append({"file": page, "line": 1, "snippet": "no module signal table"})

    mt, head = find_table(all_tables, "module", "recommendation")
    rows = {}
    if mt:
        mi = head.index(next(h for h in head if "module" in h))
        ri = head.index(next(h for h in head if "recommendation" in h))
        for n, cells in mt[1:]:
            if len(cells) > max(mi, ri) and not placeholder(cells[mi]):
                rows[plain(cells[mi])] = (n, cells[ri])
    if not rows:
        hits.append({"file": page, "line": 1, "snippet": "no module table"})

    fitted = 0
    for module, (n, rec_cell) in rows.items():
        rec = plain(rec_cell)
        on_disk = module in signals and present(ctx, signals[module])
        if rec == "fitted":
            fitted += 1
            if module not in signals:
                hits.append({"file": page, "line": n, "snippet": f"{module}: marked fitted, no signal listed"})
            elif not on_disk:
                hits.append({"file": page, "line": n, "snippet": f"{module}: marked fitted, signal missing"})
        else:
            if not placeholder(rec_cell) and rec not in RECOMMENDATIONS:
                warns.append(f"{page}:{n} {module}: unknown recommendation '{rec}'")
            if on_disk:
                marked = "no recommendation" if placeholder(rec_cell) else f"marked '{rec}'"
                warns.append(f"{page}:{n} {module}: signal present, {marked}")
    for module, globs in signals.items():
        if module not in rows and present(ctx, globs):
            warns.append(f"{page} {module}: signal present, missing from the module table")

    detail = (f"{len(rows)} modules in the table, {fitted} marked fitted; "
              f"{len(hits)} problems, {len(warns)} warnings")
    evidence = [h["snippet"] for h in hits] + warns
    if hits:
        return {"result": "fail", "detail": detail, "evidence": evidence, "hits": hits}
    if warns:
        return {"result": "warn", "detail": detail, "evidence": evidence, "hits": []}
    return {"result": "pass", "detail": detail}
