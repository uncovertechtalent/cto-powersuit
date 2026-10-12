#!/usr/bin/env python3
"""Run lint_clinic.py on the recorded cases in cases/.

Each case folder holds a clinic folder acme-widget/, an optional LOG.md next to it, and
expect.json: the exit code, the number of problems, and lines the output must contain.
Standard library only. Exit 0 when every case behaves.

Usage: python3 test_lint.py
"""
import json, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def main():
    failures = 0
    for case in sorted(p for p in (HERE / "cases").iterdir() if p.is_dir()):
        want = json.loads((case / "expect.json").read_text())
        p = subprocess.run([sys.executable, "-B", str(HERE / "lint_clinic.py"), str(case / "acme-widget")],
                           capture_output=True, text=True)
        out = p.stdout + p.stderr
        missing = [e for e in want["expect"] if e not in out]
        ok = p.returncode == want["exit"] and f"\n{want['problems']} problems" in "\n" + out and not missing
        print(f"{'ok  ' if ok else 'FAIL'} {case.name}: exit {p.returncode} (want {want['exit']})")
        if not ok:
            failures += 1
            for m in missing:
                print(f"     missing: {m}")
            for line in out.strip().splitlines():
                print("     " + line)
    print(f"{failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
