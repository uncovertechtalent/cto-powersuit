"""HTML pages load nothing from third-party hosts when they open."""
import re
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urlsplit

ID = "compliance.no-third-party"
DESCRIPTION = ("HTML files under the site roots load no script, stylesheet, font, icon, image, frame or media from a "
               "host outside allowed_hosts. Links (<a href>) and code in <pre> and <code> do not count.")
DEFAULTS = {"roots": ["."], "globs": ["**/*.html", "**/*.htm"], "allowed_hosts": []}

# <link rel> values that make the browser fetch or connect when the page opens.
LINK_RELS = ("stylesheet", "preload", "modulepreload", "prefetch", "preconnect", "icon", "apple-touch-icon",
             "mask-icon", "manifest")
# Attributes that load a resource, per tag.
SOURCES = {"script": ("src",), "img": ("src", "srcset"), "iframe": ("src",), "source": ("src", "srcset"),
           "video": ("src", "poster"), "audio": ("src",)}
CSS_REF = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s]*))\s*\)|@import\s+(?:"([^"]*)"|'([^']*)')""", re.I)
SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")


def srcset_urls(value):
    return [part.strip().split()[0] for part in value.split(",") if part.strip()]


def css_refs(css):
    """(offset, kind, url) for every url() and quoted @import in a CSS text."""
    out = []
    for m in CSS_REF.finditer(css):
        url = next(g for g in m.groups() if g is not None)
        out.append((m.start(), "url()" if m.group(0).lower().startswith("url") else "@import", url))
    return out


class Scanner(HTMLParser):
    """Collects (line, what, url) for every resource the page loads, outside <pre> and <code>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.code_depth = 0
        self.in_style = False
        self.found = []

    def handle_starttag(self, tag, attrs):
        if tag in ("pre", "code"):
            self.code_depth += 1
            return
        if self.code_depth:
            return
        line = self.getpos()[0]
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "style":
            self.in_style = True
        if a.get("style"):
            for _off, kind, url in css_refs(a["style"]):
                self.found.append((line, f"style attribute {kind}", url))
        if tag == "link" and a.get("href"):
            rels = [r for r in a.get("rel", "").lower().split() if r in LINK_RELS]
            if rels:
                self.found.append((line, f"link rel={rels[0]} href", a["href"]))
        for attr in SOURCES.get(tag, ()):
            if a.get(attr):
                for url in srcset_urls(a[attr]) if attr == "srcset" else [a[attr]]:
                    self.found.append((line, f"{tag} {attr}", url))

    def handle_endtag(self, tag):
        if tag in ("pre", "code") and self.code_depth:
            self.code_depth -= 1
        elif tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style and not self.code_depth:
            line = self.getpos()[0]
            for off, kind, url in css_refs(data):
                self.found.append((line + data.count("\n", 0, off), f"style {kind}", url))


def third_party_host(url, allowed):
    """The host a URL loads from when it is outside the allowed hosts; None for relative and non-web URLs."""
    u = url.strip()
    if u.startswith("//"):
        host = urlsplit("https:" + u).hostname
    else:
        m = SCHEME.match(u)
        if not m or m.group(1).lower() not in ("http", "https"):
            return None  # relative, root-relative, data:, blob:, mailto: and the like
        host = urlsplit(u).hostname
    if not host:
        return None
    host = host.lower().rstrip(".")
    for a in allowed:
        a = a.lower().strip()
        if host == a or (a.startswith("*.") and host.endswith(a[1:])):
            return None
    return host


def check(ctx):
    roots, globs = list(ctx.options["roots"]), list(ctx.options["globs"])
    allowed = list(ctx.options["allowed_hosts"])
    hits, files, seen = [], [], set()
    for root in roots:
        base = (ctx.root / root).resolve()
        try:
            prefix = base.relative_to(ctx.root).as_posix()
        except ValueError:
            hits.append({"file": root, "line": 1, "snippet": "site root outside the repository"})
            continue
        if not base.is_dir():
            hits.append({"file": root, "line": 1, "snippet": "site root not found"})
            continue
        patterns = globs if prefix == "." else [f"{prefix}/{g}" for g in globs]
        for f in ctx.files(patterns):
            rel = ctx.rel(f)
            inside = PurePosixPath(rel).relative_to(prefix) if prefix != "." else PurePosixPath(rel)
            if rel in seen or any(part.startswith("_") for part in inside.parts):
                continue
            seen.add(rel)
            files.append(f)

    if not files and not hits:
        return {"result": "n/a", "detail": "no HTML file under " + ", ".join(roots), "hits": []}

    bad = set()
    for f in files:
        rel = ctx.rel(f)
        scanner = Scanner()
        scanner.feed(ctx.read(f))
        scanner.close()
        reported = set()
        for line, what, url in scanner.found:
            host = third_party_host(url, allowed)
            if host is None:
                continue
            snippet = f"{what} loads from third-party host: {host}"
            if snippet in reported:
                continue
            reported.add(snippet)
            bad.add(rel)
            hits.append({"file": rel, "line": line, "snippet": snippet})

    detail = f"{len(files)} HTML files under {', '.join(roots)}: {len(bad)} load from third-party hosts"
    if allowed:
        detail += " (allowed: " + ", ".join(allowed) + ")"
    if hits:
        return {"result": "fail", "detail": detail, "hits": sorted(hits, key=lambda h: (h["file"], h["line"], h["snippet"]))}
    return {"result": "pass", "detail": detail, "hits": []}
