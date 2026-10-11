"""Every installed module has a row with a named owner in the owners table of docs/handover.md."""
import re

ID = "handover.module-owners"
DESCRIPTION = ("Every module installed in the repository, found by its signal, has a row in the owners table "
               "of docs/handover.md with a named owner; an angle-bracket placeholder counts as missing.")
DEFAULTS = {
    "page": "docs/handover.md",
    "signals": {},   # {"module": ["glob", ...]}; when set, used in place of the signal table on the page
}

MISSING = {"", "-", "none", "n/a", "?"}


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


def column(head, word):
    return head.index(next(h for h in head if word in h))


def plain(cell):
    return cell.replace("`", "").strip().lower()


def placeholder(cell):
    return plain(cell) in MISSING or bool(re.search(r"<[^<>]+>", cell))


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

    signals = {plain(k): list(v) for k, v in (ctx.options.get("signals") or {}).items()}
    if not signals:
        st, head = find_table(all_tables, "module", "signal")
        if st:
            mi, si = column(head, "module"), column(head, "signal")
            for _n, cells in st[1:]:
                if len(cells) > max(mi, si) and not placeholder(cells[mi]):
                    signals[plain(cells[mi])] = signal_globs(cells[si])
    if not signals:
        return {"result": "fail", "detail": f"{page} has no module signal table",
                "hits": [{"file": page, "line": 1, "snippet": "no module signal table"}]}

    installed = [m for m, globs in signals.items() if present(ctx, globs)]
    if not installed:
        return {"result": "n/a", "detail": "no installed module found by signal", "hits": []}

    ot, head = find_table(all_tables, "module", "owner", "backup")
    if not ot:
        return {"result": "fail", "detail": f"{page} has no owners table",
                "hits": [{"file": page, "line": 1, "snippet": "no owners table"}]}
    mi, oi = column(head, "module"), column(head, "owner")
    rows = {}
    for n, cells in ot[1:]:
        if len(cells) > max(mi, oi) and not placeholder(cells[mi]):
            rows[plain(cells[mi])] = (n, cells[oi])

    hits, ok = [], []
    for module in installed:
        if module not in rows:
            hits.append({"file": page, "line": ot[0][0], "snippet": f"{module}: no row in the owners table"})
        elif placeholder(rows[module][1]):
            hits.append({"file": page, "line": rows[module][0], "snippet": f"{module}: no named owner"})
        else:
            ok.append(f"ok: {module} owned by {rows[module][1]}")
    detail = f"{len(installed)} installed modules, {len(ok)} with a named owner; {len(hits)} problems"
    return {"result": "fail" if hits else "pass", "detail": detail,
            "evidence": ok + [h["snippet"] for h in hits], "hits": hits}
