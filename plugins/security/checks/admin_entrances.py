"""Every admin entrance has an owner and enforced multi-factor authentication, or a named, dated exception."""
import datetime
import re
import sys
from pathlib import Path

ID = "security.admin-entrances"
DESCRIPTION = ("The admin entrance inventory (docs/security/admin-entrances.md) has a row for every required kind of "
               "entrance, each row names an owner, where to see the setting and when it was last checked, and each "
               "entrance enforces multi-factor authentication with a method that resists phishing or interception. "
               "An entrance below that bar needs an exception with a reason, a person who accepted it and an expiry "
               "date, and an exception past its expiry is a hit. Hits name the entrance and the field, never a cell value.")
DEFAULTS = {
    "page": "docs/security/admin-entrances.md",
    # Kinds that need at least one row. A kind the organisation does not have gets a row with MFA enforced "n/a" and a reason.
    "required_kinds": ["cloud", "identity", "directory", "remote-access", "source-ci", "dns-registrar",
                       "password-manager", "saas", "on-prem"],
    # false: only sms, voice and email codes are below the bar. true: every method that can be phished is (totp, push).
    "phishing_resistant_only": False,
}

KINDS = ("cloud", "identity", "directory", "remote-access", "source-ci", "dns-registrar", "password-manager", "saas",
         "on-prem", "endpoint", "backup-monitoring", "vendor", "other")
ENFORCED = ("yes", "partial", "no", "n/a")
# Methods by how weak the weakest one an admin can still sign in with is: 1 resists phishing, 4 is no second factor.
WEAKNESS = {"passkey": 1, "security-key": 1, "certificate": 1, "push": 2, "totp": 2, "sms": 3, "voice": 3, "email": 3, "none": 4}
INTERCEPTABLE = ("sms", "voice", "email")
COLUMNS = ("entrance", "kind", "admin holders", "owner", "mfa enforced", "method", "reason", "accepted by", "expires",
           "last checked", "evidence")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def tables(text):
    """Markdown tables outside fenced code as lists of (line number, cells); the first row is the header."""
    out, cur, in_code = [], [], False
    for n, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if s.startswith(("```", "~~~")):
            in_code = not in_code
        if not in_code and s.startswith("|"):
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


def plain(cell):
    return cell.replace("`", "").strip()


def missing(cell):
    """Empty, a dash, or an angle-bracket placeholder."""
    v = plain(cell)
    return v in ("", "-", "none", "?") or bool(re.search(r"<[^<>]*>", v))


def valid_date(value):
    if not DAY.match(value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def join(items):
    """a, b, and c"""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + (", and " if len(items) > 2 else " and ") + items[-1]


def weakest(cell):
    """The weakest method named in the cell (several are separated by , + or /), or None for an unknown word."""
    words = [w.strip().lower() for w in re.split(r"[,+/]", plain(cell)) if w.strip()]
    if not words or any(w not in WEAKNESS for w in words):
        return None
    return max(words, key=WEAKNESS.get)


def check(ctx):
    o = ctx.options
    page = o["page"]
    path = ctx.root / page
    if not path.is_file():
        return {"result": "n/a", "detail": f"no {page}", "hits": []}
    required = [k.lower() for k in o["required_kinds"]]
    all_tables = tables(ctx.read(path))
    found = None
    for t in all_tables:
        head = [plain(c).lower() for c in t[0][1]]
        if "entrance" in head and "mfa enforced" in head:
            found = (t, head)
            break
    if not found:
        return {"result": "fail", "detail": f"{page} has no inventory table with the columns Entrance and MFA enforced",
                "hits": [{"file": page, "line": 1, "rule": "no-table", "snippet": "no inventory table"}]}
    table, head = found
    lacking = [c for c in COLUMNS if c not in head]
    if lacking:
        return {"result": "fail", "detail": f"{page} lacks the columns {', '.join(lacking)}",
                "hits": [{"file": page, "line": table[0][0], "rule": "no-table", "snippet": "inventory table lacks the column " + c}
                         for c in lacking]}
    col = {c: head.index(c) for c in COLUMNS}
    today = ctx.today
    hits, seen_kinds, rows, excepted, ok = [], set(), 0, 0, 0

    for n, cells in table[1:]:
        cells = cells + [""] * (len(head) - len(cells))

        def get(name):
            return cells[col[name]]

        def hit(rule, snippet):
            hits.append({"file": page, "line": n, "rule": rule, "snippet": snippet})

        name = plain(get("entrance"))
        if missing(get("entrance")):
            # A row of placeholders, or only a kind hint, is an unfilled template row; anything more is a half-filled row.
            if not all(missing(c) for i, c in enumerate(cells) if i != col["kind"]):
                hit("row-incomplete", "row has no entrance name")
            continue
        rows += 1
        kind = plain(get("kind")).lower()
        enforced = plain(get("mfa enforced")).lower()
        if kind not in KINDS:
            hit("row-incomplete", f"{name}: kind is not one of {', '.join(KINDS)}")
        else:
            seen_kinds.add(kind)
        if enforced not in ENFORCED:
            hit("row-incomplete", f"{name}: MFA enforced is not yes, partial, no or n/a")
            continue
        if missing(get("owner")):
            hit("row-incomplete", f"{name}: no owner")
        if enforced == "n/a":
            if missing(get("reason")):
                hit("row-incomplete", f"{name}: n/a needs a reason")
            continue
        for field in ("admin holders", "evidence"):
            if missing(get(field)):
                hit("row-incomplete", f"{name}: no {field}")
        checked = plain(get("last checked"))
        when = valid_date(checked)
        if missing(get("last checked")):
            hit("row-incomplete", f"{name}: no last checked date")
        elif when is None:
            hit("row-incomplete", f"{name}: last checked is not a YYYY-MM-DD date")
        elif when > today:
            hit("row-incomplete", f"{name}: last checked is in the future")

        method = weakest(get("method"))
        below_bar = INTERCEPTABLE + (("push", "totp") if o["phishing_resistant_only"] else ())
        gap = None   # (rule, text) for a row below the bar
        if enforced in ("no", "partial"):
            gap = ("mfa-not-enforced", f"MFA enforced is {enforced}" + ("" if enforced == "no" else " for some admin accounts only"))
        elif method is None:
            hit("row-incomplete", f"{name}: method is not one of {', '.join(WEAKNESS)}")
            continue
        elif method == "none":
            hit("row-incomplete", f"{name}: MFA enforced is yes and the method is none")
            continue
        elif method in below_bar:
            gap = ("weak-method", f"the weakest method an admin can use is {method}")
        if gap is None:
            ok += 1
            continue

        rule, text = gap
        reason, who, expires = get("reason"), get("accepted by"), plain(get("expires"))
        absent = [label for label, cell in (("a reason", reason), ("a person who accepted it", who)) if missing(cell)]
        end = valid_date(expires)
        if missing(get("expires")):
            absent.append("an expiry date")
        elif end is None:
            absent.append("an expiry date as YYYY-MM-DD")
        if absent:
            hit(rule, f"{name}: {text}, and the exception lacks {join(absent)}")
        elif end < today:
            hit("exception-expired", f"{name}: the exception expired on {end.isoformat()}; {text}")
        else:
            excepted += 1

    for kind in required:
        if kind not in seen_kinds:
            hits.append({"file": page, "line": table[0][0], "rule": "kind-missing",
                         "snippet": f"no row of kind {kind}; add one, or a row with MFA enforced n/a and a reason"})
    detail = (f"{rows} entrances: {ok} enforce MFA with a method above the bar, {excepted} on a dated exception; "
              f"{len(hits)} problems")
    if not rows and not hits:
        return {"result": "n/a", "detail": f"{page} has no entrance rows yet", "hits": []}
    return {"result": "fail" if hits else "pass", "detail": detail, "hits": hits}


if __name__ == "__main__":
    # Without the gate: python3 admin_entrances.py [repository root]. Prints the hits; exit 1 when there are any.
    class _Ctx:
        def __init__(self, root):
            self.root = Path(root).resolve()
            self.options = dict(DEFAULTS)
            self.today = datetime.date.today()

        def read(self, p):
            return Path(p).read_text(encoding="utf-8", errors="replace")

    res = check(_Ctx(sys.argv[1] if len(sys.argv) > 1 else "."))
    print(f"{ID}: {res['result']}: {res['detail']}")
    for h in res["hits"]:
        print(f"  {h['file']}:{h['line']} {h['rule']}: {h['snippet']}")
    sys.exit(1 if res["result"] == "fail" else 0)
