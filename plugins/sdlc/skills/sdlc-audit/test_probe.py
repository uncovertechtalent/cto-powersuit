#!/usr/bin/env python3
"""Run probe.classify on every recorded case in cases/ and compare the expected fields.

A case is cases/<id>/case.json: {"title", "purpose", "observations", "expect"}. An expectation maps a
dotted path (list items as name[0]) to a value, or to {"startswith": text}. Exit 0 when every case
matches. Standard library only.
"""
import importlib.util, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe", HERE / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def get(d, path):
    for part in path.split("."):
        m = re.match(r"^([\w-]+)(?:\[(\d+)\])?$", part)
        d = d[m.group(1)]
        if m.group(2) is not None:
            d = d[int(m.group(2))]
    return d


failures = 0
for f in sorted(HERE.glob("cases/*/case.json")):
    case = json.loads(f.read_text())
    out = probe.classify(case["observations"], case.get("purpose", "users"))
    bad = []
    for path, want in case["expect"].items():
        try:
            got = get(out, path)
        except (KeyError, IndexError, TypeError):
            got = "<missing>"
        ok = got.startswith(want["startswith"]) if isinstance(want, dict) and isinstance(got, str) else got == want
        if not ok:
            bad.append(f"{path}: got {got!r}, want {want!r}")
    print(f"{'ok  ' if not bad else 'FAIL'} {f.parent.name}: {case['title']}")
    for b in bad:
        print("     " + b)
    failures += bool(bad)
print(f"{len(list(HERE.glob('cases/*/case.json')))} cases, {failures} failures")
sys.exit(1 if failures else 0)
