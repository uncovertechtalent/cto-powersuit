"""Agent settings checked into the repository carry no secrets and no wildcard permissions."""
import json
import re

ID = "ai-ops.agent-settings"
DESCRIPTION = ("Shared agent settings (.claude/settings.json, .mcp.json) carry no secrets and grant no wildcard "
               "permissions: no allow rule for every shell command or every fetch, no bypass mode, no literal "
               "value in a secret-named key.")
DEFAULTS = {
    "files": [".claude/settings.json", ".mcp.json"],
    "wildcards": ["*", "Bash", "Bash(*)", "Bash(:*)", "Bash(*:*)", "WebFetch", "WebFetch(*)", "mcp__*"],
    "secret_keys": r"(?i)(token|secret|password|passwd|api[_-]?key|access[_-]?key|private[_-]?key|credential)",
    "secret_patterns": [
        r"sk-ant-[A-Za-z0-9_-]{20,}", r"\bsk-[A-Za-z0-9]{32,}", r"\bgh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{40,}",
        r"\bAKIA[0-9A-Z]{16}\b", r"\bxox[abprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    ],
}
REFERENCE = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*(:-[^}]*)?\}$|^<[^>]*>$|^$")


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, node


def check(ctx):
    o = ctx.options
    present = [f for f in o["files"] if (ctx.root / f).is_file()]
    if not present:
        return {"result": "n/a", "detail": "no shared agent settings: " + ", ".join(o["files"])}
    key_rx = re.compile(o["secret_keys"])
    value_rx = [re.compile(p) for p in o["secret_patterns"]]
    hits = []
    for rel in present:
        raw = (ctx.root / rel).read_text(encoding="utf-8")
        for rx in value_rx:
            for m in rx.finditer(raw):
                line = raw.count("\n", 0, m.start()) + 1
                hits.append({"file": rel, "line": line, "snippet": f"secret pattern {rx.pattern[:24]}"})
        try:
            data = json.loads(raw)
        except ValueError as e:
            hits.append({"file": rel, "snippet": f"not valid JSON: {type(e).__name__}"})
            continue
        for path, value in walk(data):
            leaf = path.rsplit(".", 1)[-1]
            if isinstance(value, str) and key_rx.search(leaf) and not REFERENCE.match(value.strip()):
                hits.append({"file": rel, "snippet": f"{path} holds a literal value; use an environment variable reference"})
        perms = data.get("permissions") or {}
        for rule in perms.get("allow") or []:
            if str(rule).strip() in o["wildcards"]:
                hits.append({"file": rel, "snippet": f"permissions.allow grants a wildcard: {rule}"})
        if perms.get("defaultMode") == "bypassPermissions":
            hits.append({"file": rel, "snippet": "permissions.defaultMode is bypassPermissions"})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(present)} shared settings files checked, {len(hits)} problems",
            "hits": hits}
