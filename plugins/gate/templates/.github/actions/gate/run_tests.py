#!/usr/bin/env python3
"""Test step of the deploy gate. Standard library only, Python 3.9+.

Runs the repository's own test command, named under "tests" in the gate config, and turns the
outcome into an exit code by tier. It guesses nothing: no command in the config means no test run,
and that is said in the output and in a workflow annotation, never skipped quietly.

Config (gate/gate.json):
  "tests": {"tier": "warn", "command": "make check"}
  tier     block  a failing test run, or an empty command, fails this step; the deploy job does not run
           warn   a failing test run is reported and the step passes; the deploy runs (default)
           off    the command does not run; said in the output
  command  one shell command, run from the repository root with `bash -e -o pipefail` (a multi-line
           command stops at its first failing line). Without bash on PATH the step exits 2 and runs nothing:
           sh would run the same command without -e and pipefail and could report a failed test run as a pass.
  false_positive_test  required on block: "date", "hits", and "legitimate" (also record "corpus" and
           "decision"); "legitimate" must be 0 (the failed runs on warn that were not real regressions)
No "tests" key counts as warn with no command.

Usage: run_tests.py [--config gate/gate.json] [--root .]

Exit codes: 0 pass, warn, off, or a missing command on warn; 1 the tests failed on block, or no
command on block; 2 config error (nothing ran).
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode = True

TIERS = ("block", "warn", "off")
CMD_KEY = "tests.command in gate/gate.json"
TIER_KEY = "tests.tier in gate/gate.json"


class ConfigError(Exception):
    pass


def esc(text):
    """Escape a message for a GitHub workflow command."""
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def annotate(level, message):
    print(f"::{level} title=Gate tests::{esc(message)}")


def label(command):
    lines = command.splitlines()
    return lines[0] + (" ..." if len(lines) > 1 else "")


def count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load(cfg_path):
    if not cfg_path.exists():
        raise ConfigError(f"gate config not found: {cfg_path}")
    tests = json.loads(cfg_path.read_text()).get("tests", {})
    if not isinstance(tests, dict):
        raise ConfigError('"tests" in the gate config must be an object')
    tier = tests.get("tier", "warn")
    if tier not in TIERS:
        raise ConfigError(f'tests.tier is {tier!r}, want one of {", ".join(TIERS)}')
    command = tests.get("command", "")
    if not isinstance(command, str):
        raise ConfigError("tests.command must be a string")
    if tier == "block":
        rec = tests.get("false_positive_test")
        rec = rec if isinstance(rec, dict) else {}
        if not (rec.get("date") and count(rec.get("hits")) and count(rec.get("legitimate"))):
            raise ConfigError("tests.tier is block without a recorded false-positive test "
                              "(false_positive_test with date, hits, and legitimate); keep the tier on warn until it is recorded")
        if rec["legitimate"] != 0:
            raise ConfigError(f"tests.tier is block and the false-positive test records {rec['legitimate']} legitimate failures; "
                              "fix or quarantine the flaky tests, run again on warn, and record a new test")
    return tier, command.strip()


def run_command(command, root):
    bash = shutil.which("bash")
    if not bash:
        raise ConfigError("bash is not on PATH; the test command runs with bash -e -o pipefail, and sh would hide a failing line")
    sys.stdout.flush()
    return subprocess.run([bash, "-e", "-o", "pipefail", "-c", command], cwd=str(root), stdin=subprocess.DEVNULL).returncode


def write_summary(rows):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a") as f:
        f.write("### Gate tests\n\n| | |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in rows) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Run the repository's test command for the deploy gate")
    ap.add_argument("--config", default="gate/gate.json")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    cfg_path = Path(args.config) if Path(args.config).is_absolute() else root / args.config
    tier, command = load(cfg_path)
    rows = [("Tier", f"`{tier}`")]

    if tier == "off":
        annotate("warning", f"Tests are off ({TIER_KEY}); the deploy does not wait for tests")
        print("tests: tier=off result=off")
        write_summary(rows + [("Result", "off: the deploy does not wait for tests")])
        return 0
    if not command:
        msg = f"No test command is set ({CMD_KEY}); the deploy does not wait for tests until one is named"
        if tier == "block":
            annotate("error", msg + ". Name the command or set the tier to warn or off")
            print("tests: tier=block result=fail reason=no-command")
            write_summary(rows + [("Result", "fail: no test command")])
            return 1
        annotate("warning", msg)
        print("tests: tier=warn result=unset")
        write_summary(rows + [("Result", "no test command set")])
        return 0

    print(f"tests: running ({tier}): {label(command)}")
    started = time.monotonic()
    code = run_command(command, root)
    seconds = round(time.monotonic() - started, 1)
    rows += [("Command", f"`{label(command)}`"), ("Exit code", code), ("Seconds", seconds)]
    if code == 0:
        print(f"tests: tier={tier} result=pass exit=0 seconds={seconds}")
        write_summary(rows + [("Result", "pass")])
        return 0
    if tier == "block":
        annotate("error", f"Tests failed (exit {code}); deploy blocked, the previous build stays live")
        print(f"tests: tier=block result=fail exit={code} seconds={seconds}")
        write_summary(rows + [("Result", "fail: deploy blocked")])
        return 1
    annotate("warning", f"Tests failed (exit {code}) on the warn tier; the deploy runs anyway. Fix the tests, or check that the failure is real before moving the tier to block")
    print(f"tests: tier=warn result=warn exit={code} seconds={seconds}")
    write_summary(rows + [("Result", "failed on warn: the deploy is not waiting for this result")])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ConfigError, json.JSONDecodeError) as e:
        annotate("error", f"Gate tests config error: {e}")
        print(f"run_tests.py: config error: {e}", file=sys.stderr)
        sys.exit(2)
