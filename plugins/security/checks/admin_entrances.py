"""Every admin entrance has an owner and enforced multi-factor authentication, or a named, dated exception."""
import datetime
import re
import sys
from pathlib import Path

ID = "security.admin-entrances"
DESCRIPTION = ("The admin entrance inventory (docs/security/admin-entrances.md) has a row for every required kind of "
               "entrance, each row names an owner, where to see the setting and when it was last checked, and each "
               "entrance enforces multi-factor authentication with a method above the bar (sms, voice, email, and push "
               "without number matching are below it). An entrance below the bar needs an exception with a reason, a "
               "person who accepted it and an end date within the allowed span, and an exception past its end date is a "
               "hit. A hit names the entrance and the field; it never prints a reason, owner, holder, or evidence.")
DEFAULTS = {
    "page": "docs/security/admin-entrances.md",
    # Kinds that need at least one row. A kind the organisation does not have gets a row with MFA enforced "n/a", no admin holders and a reason.
    "required_kinds": ["cloud", "identity", "directory", "remote-access", "source-ci", "dns-registrar", "password-manager",
                       "saas", "on-prem", "endpoint", "backup-monitoring", "vendor"],
    # false: sms, voice, email and push without number matching are below the bar. true: every method that can be phished is (totp, push).
    "phishing_resistant_only": False,
    # An exception ends at most this many days after the row's Last checked date. 0 turns the span off.
    "max_exception_days": 180,
    # A row's Last checked date lies at most this many days before the page's `reviewed` date. 0 turns it off.
    "max_check_age_days": 120,
}

KINDS = ("cloud", "identity", "directory", "remote-access", "source-ci", "dns-registrar", "password-manager", "saas",
         "on-prem", "endpoint", "backup-monitoring", "vendor", "other")
ENFORCED = ("yes", "partial", "no", "n/a")
# Methods by how weak the weakest one an admin can still sign in or recover with is: 1 resists phishing, 4 is no second factor.
WEAKNESS = {"passkey": 1, "security-key": 1, "certificate": 1, "push": 2, "totp": 2,
            "push-no-match": 3, "sms": 3, "voice": 3, "email": 3, "none": 4}
BELOW_BAR = ("push-no-match", "sms", "voice", "email")
ALIASES = {"smart-card": "certificate", "smartcard": "certificate", "fido2": "security-key", "webauthn": "security-key",
           "yubikey": "security-key", "hardware-key": "security-key", "authenticator": "totp", "authenticator-app": "totp",
           "otp": "totp", "push-notification": "push", "text-message": "sms"}
NO_HOLDERS = ("0", "no", "none", "no accounts")
COLUMNS = ("entrance", "kind", "admin holders", "owner", "mfa enforced", "method", "reason", "accepted by", "expires",
           "last checked", "evidence")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def cells_of(line):
    """Cells of one table line: the outer pipes are optional and `\\|` is a pipe inside a cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", s)]


def tables(text):
    """Markdown tables outside fenced code as lists of (line number, cells); the first row is the header.
    A table is a line with a pipe followed by a separator line; every later line with a pipe is a row,
    with or without outer pipes, as GitHub shows it."""
    lines = text.split("\n")
    out, i, in_code = [], 0, False
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith(("```", "~~~")):
            in_code = not in_code
        elif not in_code and "|" in s and i + 1 < len(lines) and "|" in lines[i + 1] and SEPARATOR.match(lines[i + 1].strip()):
            rows = [(i + 1, cells_of(s))]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append((i + 1, cells_of(lines[i])))
                i += 1
            out.append(rows)
            continue
        i += 1
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


def reviewed_date(text):
    """The `reviewed` date of the page's front matter, or None."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^reviewed\s*:\s*(\S+)\s*$", line)
        if m:
            return valid_date(m.group(1).strip("\"'"))
    return None


def join(items):
    """a, b, and c"""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + (", and " if len(items) > 2 else " and ") + items[-1]


def weakest(cell):
    """The weakest method named in the cell (several are separated by , + or /), or None for an unknown word."""
    words = []
    for w in re.split(r"[,+/]", plain(cell)):
        w = re.sub(r"[\s_]+", "-", w.strip().lower())
        if w:
            words.append(ALIASES.get(w, w))
    if not words or any(w not in WEAKNESS for w in words):
        return None
    return max(words, key=WEAKNESS.get)


def inventories(text):
    """Every table with the columns Entrance and MFA enforced, as (rows, header cells in lower case)."""
    found = []
    for t in tables(text):
        head = [plain(c).lower() for c in t[0][1]]
        if "entrance" in head and "mfa enforced" in head:
            found.append((t, head))
    return found


def check(ctx):
    o = ctx.options
    page = o["page"]
    path = ctx.root / page
    if not path.is_file():
        return {"result": "n/a", "detail": f"no {page}", "hits": []}
    text = ctx.read(path)
    required = [k.lower() for k in o["required_kinds"]]
    found = inventories(text)
    if not found:
        return {"result": "fail", "detail": f"{page} has no inventory table with the columns Entrance and MFA enforced",
                "hits": [{"file": page, "line": 1, "rule": "no-table", "snippet": "no inventory table"}]}
    hits = []
    for table, head in found:
        for c in COLUMNS:
            if c not in head:
                hits.append({"file": page, "line": table[0][0], "rule": "no-table", "snippet": "inventory table lacks the column " + c})
    if hits:
        return {"result": "fail", "detail": f"{page}: an inventory table lacks columns", "hits": hits}

    today, reviewed = ctx.today, reviewed_date(text)
    below_bar = BELOW_BAR + (("push", "totp") if o["phishing_resistant_only"] else ())
    seen_kinds, rows, excepted, ok, absent_kinds = set(), 0, 0, 0, 0

    for table, head in found:
        col = {c: head.index(c) for c in COLUMNS}
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
                absent_kinds += 1
                if missing(get("reason")):
                    hit("row-incomplete", f"{name}: n/a needs a reason")
                if not missing(get("admin holders")) and plain(get("admin holders")).lower() not in NO_HOLDERS:
                    hit("row-incomplete", f"{name}: n/a, and admin holders lists accounts; a live entrance without MFA is a "
                                          "no or partial row with an exception")
                continue
            for field in ("admin holders", "evidence"):
                if missing(get(field)):
                    hit("row-incomplete", f"{name}: no {field}")
            when = valid_date(plain(get("last checked")))
            if missing(get("last checked")):
                hit("row-incomplete", f"{name}: no last checked date")
            elif when is None:
                hit("row-incomplete", f"{name}: last checked is not a YYYY-MM-DD date")
            elif when > today:
                hit("row-incomplete", f"{name}: last checked is in the future")
            elif reviewed and o["max_check_age_days"] and (reviewed - when).days > o["max_check_age_days"]:
                hit("row-stale", f"{name}: last checked {when.isoformat()}, {(reviewed - when).days} days before the page "
                                 f"was reviewed on {reviewed.isoformat()}; read the setting again")

            method = weakest(get("method"))
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

            rule, what = gap
            reason, who, expires = get("reason"), get("accepted by"), plain(get("expires"))
            absent = [label for label, cell in (("a reason", reason), ("a person who accepted it", who)) if missing(cell)]
            end = valid_date(expires)
            if missing(get("expires")):
                absent.append("an expiry date")
            elif end is None:
                absent.append("an expiry date as YYYY-MM-DD")
            if absent:
                hit(rule, f"{name}: {what}, and the exception lacks {join(absent)}")
            elif end < today:
                hit("exception-expired", f"{name}: the exception expired on {end.isoformat()}; {what}")
            elif o["max_exception_days"] and when and (end - when).days > o["max_exception_days"]:
                hit("exception-too-long", f"{name}: the exception ends {end.isoformat()}, {(end - when).days} days after the "
                                          f"last check; the span is {o['max_exception_days']} days")
            else:
                excepted += 1

    for kind in required:
        if kind not in seen_kinds:
            hits.append({"file": page, "line": found[0][0][0][0], "rule": "kind-missing",
                         "snippet": f"no row of kind {kind}; add one, or a row with MFA enforced n/a, no admin holders and a reason"})
    if not rows and not hits:
        return {"result": "n/a", "detail": f"{page} has no entrance rows yet", "hits": []}
    detail = (f"{rows} rows: {ok} enforce MFA with a method above the bar, {excepted} on a dated exception, "
              f"{absent_kinds} marked n/a; {len(hits)} problems")
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
