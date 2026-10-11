"""Each site root has a security.txt with a contact and an expiry date in the future (RFC 9116)."""
import datetime
import re

ID = "compliance.security-txt"
DESCRIPTION = ("Each site root has .well-known/security.txt with a Contact field and an Expires field that is an "
               "ISO 8601 date-time with time zone, later than the time of the run (RFC 9116).")
DEFAULTS = {"roots": ["."]}

FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)$")
CONTACT = re.compile(r"^(mailto:|tel:|https://)[^\s<>]+$", re.I)
DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}")


def signed_body(lines):
    """The signed lines of an OpenPGP cleartext-signed file, or all lines when the file is not signed."""
    if not lines or not lines[0].startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
        return list(enumerate(lines, 1))
    out, started = [], False
    for n, line in enumerate(lines, 1):
        if not started:
            started = n > 1 and not line.strip()
            continue
        if line.startswith("-----BEGIN PGP SIGNATURE-----"):
            break
        out.append((n, line[2:] if line.startswith("- ") else line))
    return out


def parse_expires(value):
    """An aware datetime, or None when the value is not an ISO 8601 date-time with a time zone."""
    v = value.strip()
    if not DATE_TIME.match(v):
        return None
    if v[-1] in "Zz":
        v = v[:-1] + "+00:00"
    v = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], v)  # Python 3.9 wants 3 or 6 digits
    try:
        dt = datetime.datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


def check(ctx):
    roots = list(ctx.options["roots"])
    if not roots:
        return {"result": "n/a", "detail": "no site roots configured", "hits": []}

    hits, clean = [], []
    for root in roots:
        base = (ctx.root / root).resolve()
        try:
            base.relative_to(ctx.root)
        except ValueError:
            hits.append({"file": root, "line": 1, "snippet": "site root outside the repository"})
            continue
        if not base.is_dir():
            hits.append({"file": root, "line": 1, "snippet": "site root not found"})
            continue
        path = base / ".well-known" / "security.txt"
        rel = path.relative_to(ctx.root).as_posix()
        if not path.is_file():
            hits.append({"file": rel, "line": 1, "snippet": "missing .well-known/security.txt"})
            continue

        def hit(line, snippet):
            hits.append({"file": rel, "line": line, "snippet": snippet})

        before = len(hits)
        fields = []
        for n, line in signed_body(ctx.read(path).splitlines()):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            m = FIELD.match(s)
            if m:
                fields.append((m.group(1).lower(), m.group(2).strip(), n))
        contacts = [(v, n) for k, v, n in fields if k == "contact"]
        expires = [(v, n) for k, v, n in fields if k == "expires"]

        if not contacts:
            hit(1, "missing Contact")
        for value, n in contacts:
            if not CONTACT.match(value):
                hit(n, "Contact is not a mailto:, tel: or https: URI")
        if not expires:
            hit(1, "missing Expires")
        elif len(expires) > 1:
            hit(expires[1][1], "Expires appears more than once")
        else:
            value, n = expires[0]
            dt = parse_expires(value)
            if dt is None:
                hit(n, "malformed Expires: want an ISO 8601 date-time with time zone")
            elif dt <= ctx.now:
                hit(n, "Expires is in the past")
        if len(hits) == before:
            clean.append(f"{rel}: Expires {expires[0][0]}")

    if hits:
        return {"result": "fail", "detail": f"{len(roots)} site roots: {len(roots) - len(clean)} without a valid security.txt", "hits": hits}
    return {"result": "pass", "detail": f"{len(roots)} site roots: security.txt has Contact and a future Expires",
            "evidence": clean, "hits": []}
