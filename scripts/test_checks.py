#!/usr/bin/env python3
"""Run every module's gate check against its fixtures with the gate runner.

For each plugins/<module>/checks/<rule>.py, run the gate runner in dry-run mode against
checks/fixtures/<rule id>/pass (expect exit 0) and fail (expect exit 1).
Standard library only. Exit 0 when every check behaves, 1 otherwise.

Usage: python3 scripts/test_checks.py [-v]
"""
import importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # loading rule files must not leave __pycache__ in the repository

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "plugins/gate/templates/.github/actions/gate/run.py"
VERBOSE = "-v" in sys.argv


def rule_id(path):
    spec = importlib.util.spec_from_file_location("check_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ID


def main():
    failures, runs = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for checks in sorted(REPO.glob("plugins/*/checks")):
            for rule in sorted(checks.glob("*.py")):
                if rule.name.startswith("_"):
                    continue
                rid = rule_id(rule)
                cfg = Path(tmp) / f"{rid}.json"
                cfg.write_text(json.dumps({"name": "fixture-test", "rules_dir": str(checks), "rules": {rid: {"tier": "block"}}}))
                for kind, want in (("pass", 0), ("fail", 1)):
                    root = checks / "fixtures" / rid / kind
                    runs += 1
                    if not root.is_dir():
                        failures.append(f"{rid}: no {kind} fixture at {root.relative_to(REPO)}")
                        continue
                    p = subprocess.run([sys.executable, str(RUNNER), "--config", str(cfg), "--root", str(root), "--dry-run", "--exit-code", "--sha", "fixture"],
                                       capture_output=True, text=True)
                    ok = p.returncode == want
                    print(f"{'ok  ' if ok else 'FAIL'} {rid} {kind}: exit {p.returncode} (want {want})")
                    if VERBOSE or not ok:
                        for line in (p.stdout + p.stderr).strip().splitlines():
                            print("     " + line)
                    if not ok:
                        failures.append(f"{rid} {kind}: exit {p.returncode}, want {want}")
    print(f"{runs} fixture runs, {len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
