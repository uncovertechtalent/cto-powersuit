"""Pressure-test run records name the expected and the observed decision, and a verdict agrees with them."""
import json
import re

ID = "red-team.run-records"
DESCRIPTION = ("Every red-team run record names a non-empty expected_decision and observed_decision; "
               "a verdict, if present, is pass when the two match and fail when they differ.")
DEFAULTS = {"globs": ["red-team/runs/*.json"]}


def text(value):
    return value.strip() if isinstance(value, str) else ""


def key_line(raw, key):
    """Line of the first "key": in the file, or 1 when the key is missing."""
    pat = re.compile(r'"' + re.escape(key) + r'"\s*:')
    for n, line in enumerate(raw.split("\n"), 1):
        if pat.search(line):
            return n
    return 1


def check(ctx):
    files = [f for f in ctx.files(ctx.options["globs"]) if not any(p.startswith("_") for p in ctx.rel(f).split("/"))]
    if not files:
        return {"result": "n/a", "detail": "no file matches " + ", ".join(ctx.options["globs"]), "hits": []}
    hits, bad = [], set()

    def hit(rel, raw, key, snippet):
        hits.append({"file": rel, "line": key_line(raw, key) if key else 1, "snippet": snippet})
        bad.add(rel)

    for f in files:
        rel, raw = ctx.rel(f), ctx.read(f)
        try:
            rec = json.loads(raw)
        except ValueError:
            hit(rel, raw, None, "not valid JSON")
            continue
        if not isinstance(rec, dict):
            hit(rel, raw, None, "not a JSON object")
            continue
        expected, observed = text(rec.get("expected_decision")), text(rec.get("observed_decision"))
        if not expected:
            hit(rel, raw, "expected_decision", "missing expected_decision")
        if not observed:
            hit(rel, raw, "observed_decision", "missing observed_decision")
        verdict = rec.get("verdict")
        if verdict is None or not (expected and observed):
            continue
        want = "pass" if expected == observed else "fail"
        if verdict not in ("pass", "fail"):
            hit(rel, raw, "verdict", f"unknown verdict: {str(verdict)[:40]}")
        elif verdict != want:
            hit(rel, raw, "verdict", f"verdict {verdict} but the decisions {'match' if want == 'pass' else 'differ'}")
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(files)} run records checked, {len(bad)} with problems",
            "hits": hits}
