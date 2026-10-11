"""Prometheus alert rules carry a route label that Alertmanager routes on and a runbook_url that resolves."""
import re

ID = "observability.alert-routes"
DESCRIPTION = ("Every Prometheus alert rule has a route label that matches a route or receiver in the Alertmanager "
               "config, and a runbook_url annotation that is an http(s) URL or a path to a file in the repository.")
DEFAULTS = {
    "globs": ["observability/prometheus/rules/*.yml", "observability/prometheus/rules/*.yaml"],
    "route_label": "route",
    "alertmanager": "observability/alertmanager/alertmanager.yml",
}


# A small YAML subset parser: block mappings and sequences, flow collections on one or more lines,
# quoted and plain scalars, block scalars and comments. Scalars stay strings. Every mapping records the
# line it starts on under "__line__". Enough for Prometheus rule files and Alertmanager configs.

KEY = re.compile(r"""^(?P<key>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s#'"{}\[\],&*!|>%@`-][^:]*?|-[^\s:][^:]*?)\s*:(?:\s+(?P<val>.*))?$""")
BLOCK_SCALAR = re.compile(r"^[|>][-+0-9]*$")


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _strip_comment(s):
    quote = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or s[i - 1] in " \t[{,:"):
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return re.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s[1:-1])
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    return s


def _balance(s):
    depth, quote = 0, None
    for ch in s:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
    return depth


def _flow(s, i=0):
    """Parse a flow value starting at s[i]; return (value, next index)."""
    while i < len(s) and s[i] in " \t":
        i += 1
    if i >= len(s):
        return "", i
    ch = s[i]
    if ch in "[{":
        close, items, mapping = ("]", [], None) if ch == "[" else ("}", None, {})
        i += 1
        while True:
            while i < len(s) and s[i] in " \t,":
                i += 1
            if i >= len(s) or s[i] == close:
                return (items if mapping is None else mapping), i + 1
            if mapping is None:
                value, i = _flow(s, i)
                items.append(value)
            else:
                key, i = _flow_scalar(s, i, ":,}")
                if i < len(s) and s[i] == ":":
                    value, i = _flow(s, i + 1)
                else:
                    value = ""
                mapping[key] = value
    return _flow_scalar(s, i, ",]}")


def _flow_scalar(s, i, stops):
    if i < len(s) and s[i] in "\"'":
        q, j = s[i], i + 1
        while j < len(s):
            if s[j] == "\\" and q == '"':
                j += 2
                continue
            if s[j] == q:
                if q == "'" and j + 1 < len(s) and s[j + 1] == "'":
                    j += 2
                    continue
                break
            j += 1
        return _unquote(s[i:j + 1]), j + 1
    j = i
    while j < len(s) and s[j] not in stops:
        if s[j] == ":" and ":" in stops and (j + 1 >= len(s) or s[j + 1] in " ,}]"):
            break
        j += 1
    return s[i:j].strip(), j


class _Parser:
    def __init__(self, text):
        self.lines = text.replace("\t", "  ").split("\n")
        self.i = 0

    def skip(self):
        while self.i < len(self.lines):
            s = self.lines[self.i].strip()
            if s and not s.startswith("#") and s not in ("---", "..."):
                return
            self.i += 1

    def done(self):
        self.skip()
        return self.i >= len(self.lines)

    def node(self, indent):
        content = self.lines[self.i].strip()
        if content == "-" or content.startswith("- "):
            return self.seq(indent)
        if KEY.match(_strip_comment(content)):
            return self.mapping(indent)
        return self.scalar(content, indent)

    def seq(self, indent):
        out = []
        while not self.done():
            line = self.lines[self.i]
            content = line.strip()
            if _indent(line) != indent or not (content == "-" or content.startswith("- ")):
                break
            rest = content[1:].lstrip()
            col = indent + (len(content) - len(rest))
            if not _strip_comment(rest):
                self.i += 1
                if not self.done() and _indent(self.lines[self.i]) > indent:
                    out.append(self.node(_indent(self.lines[self.i])))
                else:
                    out.append(None)
            elif rest == "-" or rest.startswith("- "):
                self.lines[self.i] = " " * col + rest
                out.append(self.seq(col))
            elif KEY.match(_strip_comment(rest)) and rest[0] not in "[{\"'":
                self.lines[self.i] = " " * col + rest
                out.append(self.mapping(col))
            else:
                out.append(self.scalar(rest, indent))
        return out

    def mapping(self, indent):
        out = {"__line__": self.i + 1}
        while not self.done():
            line = self.lines[self.i]
            ind = _indent(line)
            if ind < indent:
                break
            if ind > indent:
                self.i += 1  # stray deeper line; skip it
                continue
            content = _strip_comment(line.strip())
            if content == "-" or content.startswith("- "):
                break
            m = KEY.match(content)
            if not m:
                self.i += 1
                continue
            key, val = _unquote(m.group("key")), (m.group("val") or "").strip()
            if not val:
                self.i += 1
                if self.done():
                    out[key] = None
                    break
                nxt = self.lines[self.i]
                nc = nxt.strip()
                if _indent(nxt) > indent:
                    out[key] = self.node(_indent(nxt))
                elif _indent(nxt) == indent and (nc == "-" or nc.startswith("- ")):
                    out[key] = self.seq(indent)
                else:
                    out[key] = None
            elif BLOCK_SCALAR.match(val):
                out[key] = self.block_scalar(indent, val[0])
            else:
                out[key] = self.scalar(val, indent)
        return out

    def block_scalar(self, indent, style):
        self.i += 1
        parts = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() and _indent(line) <= indent:
                break
            parts.append(line.strip())
            self.i += 1
        return ("\n" if style == "|" else " ").join(parts).strip()

    def scalar(self, text, indent):
        """A scalar or flow value that starts on the current line; may continue on deeper lines."""
        self.i += 1
        text = text.strip()
        if text[:1] in "[{":
            while _balance(text) > 0 and self.i < len(self.lines):
                text += " " + self.lines[self.i].strip()
                self.i += 1
            return _flow(text)[0]
        if text[:1] in "\"'":
            q = text[0]
            while not re.search(r"(?<!\\)" + re.escape(q) + r"\s*(#.*)?$", text[1:]) and self.i < len(self.lines):
                text += " " + self.lines[self.i].strip()
                self.i += 1
            return _flow_scalar(text, 0, "")[0]
        text = _strip_comment(text)
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip() or _indent(line) <= indent or line.strip().startswith("#"):
                break
            text += " " + _strip_comment(line.strip())
            self.i += 1
        return text


def parse_yaml(text):
    p = _Parser(text)
    if p.done():
        return None
    return p.node(_indent(p.lines[p.i]))


# The rule.

MATCHER = re.compile(r"""(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>=~|!~|!=|=)\s*(?P<val>"(?:[^"\\]|\\.)*"|'[^']*'|[^,}\s]+)""")
SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def routing(config, label):
    """Values of the label that the routing tree matches: (exact values, regexes, receiver names)."""
    exact, regexes, receivers = set(), [], set()
    if not isinstance(config, dict) or not isinstance(config.get("route"), dict):
        return None

    def walk(node):
        if not isinstance(node, dict):
            return
        if node.get("receiver"):
            receivers.add(str(node["receiver"]))
        for matcher in as_list(node.get("matchers")):
            for m in MATCHER.finditer(str(matcher)):
                if m.group("name") == label and m.group("op") in ("=", "=~"):
                    value = _unquote(m.group("val"))
                    if m.group("op") == "=":
                        exact.add(value)
                    else:
                        regexes.append(value)
        for key, target in (("match", exact), ("match_re", None)):
            block = node.get(key)
            if isinstance(block, dict) and block.get(label):
                if target is None:
                    regexes.append(str(block[label]))
                else:
                    target.add(str(block[label]))
        for child in as_list(node.get("routes")):
            walk(child)

    walk(config["route"])
    for r in as_list(config.get("receivers")):
        if isinstance(r, dict) and r.get("name"):
            receivers.add(str(r["name"]))
    return exact, regexes, receivers


def routed(value, routes):
    exact, regexes, receivers = routes
    if value in exact or value in receivers:
        return True
    for rx in regexes:
        try:
            if re.fullmatch(rx, value):
                return True
        except re.error:
            continue
    return False


def runbook_problem(ctx, rule_file, url):
    """None when the runbook_url resolves, else the problem as a stable snippet tail."""
    m = SCHEME.match(url)
    if m:
        scheme = m.group(1).lower()
        return None if scheme in ("http", "https") else "runbook_url scheme is not http or https: " + scheme
    path = re.split(r"[#?]", url, 1)[0]
    if not path or path.startswith("//"):
        return "runbook_url points to no file: " + url
    candidates = [ctx.root / path.lstrip("/")]
    if not path.startswith("/"):
        candidates.append(rule_file.parent / path)
    for c in candidates:
        try:
            resolved = c.resolve()
            resolved.relative_to(ctx.root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            return None
    return "runbook_url points to no file: " + path


def check(ctx):
    label = ctx.options["route_label"]
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(part.startswith("_") for part in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}

    hits, evidence = [], []
    routes = None
    am_rel = ctx.options.get("alertmanager") or ""
    am_path = ctx.root / am_rel if am_rel else None
    if am_path is not None and am_path.is_file():
        routes = routing(parse_yaml(ctx.read(am_path)), label)
        if routes is None:
            hits.append({"file": am_rel, "line": 1, "snippet": "alertmanager config has no route tree"})
        else:
            evidence.append(f"{am_rel}: {len(routes[0]) + len(routes[1])} {label} matchers, {len(routes[2])} receivers")
    else:
        evidence.append(f"no Alertmanager config at {am_rel}; route values are not checked against it")

    alerts = 0
    for f in files:
        rel = ctx.rel(f)
        doc = parse_yaml(ctx.read(f))
        groups = doc.get("groups") if isinstance(doc, dict) else None
        if not isinstance(groups, list):
            hits.append({"file": rel, "line": 1, "snippet": "not a rule file: no groups list"})
            continue
        for group in groups:
            for rule in as_list(group.get("rules")) if isinstance(group, dict) else []:
                if not isinstance(rule, dict) or not rule.get("alert"):
                    continue
                alerts += 1
                name, line = str(rule["alert"]), rule.get("__line__", 1)

                def hit(problem):
                    hits.append({"file": rel, "line": line, "snippet": f"{name}: {problem}"})

                labels = rule.get("labels") if isinstance(rule.get("labels"), dict) else {}
                annotations = rule.get("annotations") if isinstance(rule.get("annotations"), dict) else {}
                value = str(labels.get(label) or "").strip()
                if not value:
                    hit(f"missing {label} label")
                elif routes and not routed(value, routes):
                    hit(f"{label} {value} matches no Alertmanager route or receiver")
                url = str(annotations.get("runbook_url") or "").strip()
                if not url:
                    hit("missing runbook_url")
                else:
                    problem = runbook_problem(ctx, f, url)
                    if problem:
                        hit(problem)

    hits.sort(key=lambda h: (h["file"], h["line"], h["snippet"]))
    bad = len({(h["file"], h["snippet"].split(":")[0]) for h in hits})
    detail = f"{alerts} alert rules in {len(files)} files: {bad} with problems"
    if hits:
        return {"result": "fail", "detail": detail, "hits": hits}
    return {"result": "pass", "detail": f"{alerts} alert rules in {len(files)} files: route labels and runbooks resolve",
            "evidence": evidence, "hits": []}
