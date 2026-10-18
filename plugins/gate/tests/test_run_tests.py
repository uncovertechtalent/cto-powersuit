#!/usr/bin/env python3
"""Tests for the gate's test step (templates/.github/actions/gate/run_tests.py) and its place in the workflow template.

The direct cases run the script against small repositories built in a temporary folder. The replay
cases install the gate the way /gate:gate-init does, read the job graph from the shipped gate.yml
(each job's `needs`), run the gate job's runner and the tests job's command, and apply the GitHub
rule that a job runs only when every job it needs succeeded. They show whether the deploy job runs.
Standard library only, Python 3.9+.

Usage: python3 plugins/gate/tests/test_run_tests.py [-v]
"""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

GATE = Path(__file__).resolve().parent.parent
TEMPLATES = GATE / "templates"
RUN_TESTS = TEMPLATES / ".github/actions/gate/run_tests.py"
RUNNER = TEMPLATES / ".github/actions/gate/run.py"
WORKFLOW = TEMPLATES / ".github/workflows/gate.yml"
VERBOSE = "-v" in sys.argv

FP = {"date": "2026-10-18", "corpus": "5 runs of the tests job on main", "hits": 0, "legitimate": 0, "decision": "block: no failed run"}
CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def repo(tmp, tests=None, raw=None):
    """A folder with only gate/gate.json. `raw` replaces the file's text."""
    root = Path(tmp)
    (root / "gate").mkdir(exist_ok=True)
    cfg = {"name": "t"}
    if tests is not None:
        cfg["tests"] = tests
    (root / "gate/gate.json").write_text(raw if raw is not None else json.dumps(cfg))
    return root


def step(root, env=None, config="gate/gate.json"):
    e = dict(os.environ)
    e.pop("GITHUB_STEP_SUMMARY", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, str(RUN_TESTS), "--root", str(root), "--config", config], capture_output=True, text=True, env=e)
    if VERBOSE:
        print("     " + (p.stdout + p.stderr).strip().replace("\n", "\n     "))
    return p


# ---- the script on its own ----

@case
def no_tests_key_is_warn_with_a_visible_notice(tmp):
    p = step(repo(tmp))
    assert p.returncode == 0, p.stderr
    assert "::warning" in p.stdout and "No test command is set" in p.stdout and "tier=warn result=unset" in p.stdout, p.stdout


@case
def empty_command_warns_on_warn_and_fails_on_block(tmp):
    p = step(repo(tmp, {"tier": "warn", "command": ""}))
    assert p.returncode == 0 and "::warning" in p.stdout, p.stdout
    p = step(repo(tmp, {"tier": "block", "command": "   ", "false_positive_test": FP}))
    assert p.returncode == 1 and "::error" in p.stdout and "reason=no-command" in p.stdout, p.stdout


@case
def passing_command_runs_from_the_root_on_every_tier(tmp):
    for tier in ("warn", "block"):
        root = repo(tmp, {"tier": tier, "command": "test -f ./sentinel && echo ran > ./marker", "false_positive_test": FP})
        (root / "sentinel").write_text("")
        (root / "marker").unlink(missing_ok=True)
        p = step(root)
        assert p.returncode == 0 and (root / "marker").read_text().strip() == "ran", (tier, p.stdout + p.stderr)
        assert f"tier={tier} result=pass exit=0" in p.stdout, p.stdout


@case
def failing_command_fails_on_block_and_is_reported_on_warn(tmp):
    root = repo(tmp, {"tier": "block", "command": "echo output-of-the-tests; exit 3", "false_positive_test": FP})
    p = step(root)
    assert p.returncode == 1, p.stdout
    assert "output-of-the-tests" in p.stdout, "the test output must reach the log"
    assert "::error" in p.stdout and "exit 3" in p.stdout and "deploy blocked" in p.stdout and "tier=block result=fail exit=3" in p.stdout, p.stdout
    root = repo(tmp, {"tier": "warn", "command": "exit 3"})
    p = step(root)
    assert p.returncode == 0, p.stdout
    assert "::warning" in p.stdout and "exit 3" in p.stdout and "tier=warn result=warn exit=3" in p.stdout, p.stdout


@case
def off_runs_nothing_and_says_so(tmp):
    root = repo(tmp, {"tier": "off", "command": "echo ran > ./marker; exit 1"})
    p = step(root)
    assert p.returncode == 0 and not (root / "marker").exists(), p.stdout
    assert "::warning" in p.stdout and "tests are off" in p.stdout.lower() and "result=off" in p.stdout, p.stdout


@case
def multi_line_command_stops_at_its_first_failing_line_and_pipefail_counts(tmp):
    root = repo(tmp, {"tier": "block", "command": "echo one > ./first\nfalse\necho two > ./second", "false_positive_test": FP})
    assert step(root).returncode == 1
    assert (root / "first").exists() and not (root / "second").exists()
    root = repo(tmp, {"tier": "block", "command": "false | cat", "false_positive_test": FP})
    assert step(root).returncode == 1


@case
def block_needs_a_clean_false_positive_record_and_runs_nothing_without_it(tmp):
    bad = {
        "no record": None,
        "not an object": "five clean runs",
        "no date": {"hits": 0, "legitimate": 0},
        "no hits": {"date": "2026-10-18", "legitimate": 0},
        "hits as text": {"date": "2026-10-18", "hits": "0", "legitimate": 0},
        "legitimate as bool": {"date": "2026-10-18", "hits": 0, "legitimate": False},
        "negative": {"date": "2026-10-18", "hits": 0, "legitimate": -1},
        "legitimate failures": {"date": "2026-10-18", "hits": 3, "legitimate": 2},
    }
    for name, rec in bad.items():
        tests = {"tier": "block", "command": "echo ran > ./marker"}
        if rec is not None:
            tests["false_positive_test"] = rec
        root = repo(tmp, tests)
        p = step(root)
        assert p.returncode == 2 and not (root / "marker").exists(), (name, p.returncode, p.stdout + p.stderr)
        assert "false-positive" in p.stderr, (name, p.stderr)
    # the same record, with failed runs that were all real regressions, is accepted
    ok = {"date": "2026-10-18", "corpus": "6 runs, 2 failed on real regressions", "hits": 2, "legitimate": 0, "decision": "block"}
    assert step(repo(tmp, {"tier": "block", "command": "true", "false_positive_test": ok})).returncode == 0


@case
def config_errors_exit_2_and_run_nothing(tmp):
    root = repo(tmp, {"tier": "blocking", "command": "echo ran > ./marker"})
    assert step(root).returncode == 2 and not (root / "marker").exists()
    assert step(repo(tmp, {"tier": "warn", "command": ["make", "check"]})).returncode == 2
    assert step(repo(tmp, raw='{"tests": "make check"}')).returncode == 2
    assert step(repo(tmp, raw="{not json")).returncode == 2
    assert step(repo(tmp), config="gate/missing.json").returncode == 2
    p = step(repo(tmp, {"tier": "blocking"}))
    assert "::error" in p.stdout, "a config error must show as an annotation"


@case
def step_summary_is_appended_when_github_sets_it(tmp):
    summary = Path(tmp) / "summary.md"
    summary.write_text("earlier step\n")
    p = step(repo(tmp, {"tier": "warn", "command": "exit 4"}), env={"GITHUB_STEP_SUMMARY": str(summary)})
    text = summary.read_text()
    assert p.returncode == 0 and text.startswith("earlier step\n") and "### Gate tests" in text, text
    assert "| Exit code | 4 |" in text and "failed on warn" in text, text


@case
def annotation_text_is_escaped(tmp):
    spec = importlib.util.spec_from_file_location("gate_run_tests", RUN_TESTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.esc("a%b\r\nc") == "a%25b%0D%0Ac"
    assert mod.label("make check") == "make check" and mod.label("make lint\nmake test") == "make lint ..."


# ---- the template ----

def jobs_of(text):
    """{job: {"needs": [...], "text": block}} for the jobs under `jobs:` of the shipped workflow (2-space job keys)."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"(?m)^  ([A-Za-z0-9_-]+):[ \t]*$", body)
    jobs = {}
    for name, block in zip(parts[1::2], parts[2::2]):
        needs = []
        m = re.search(r"(?m)^    needs:[ \t]*(.*)$", block)
        if m:
            inline = m.group(1).strip()
            if inline.startswith("["):
                needs = [x.strip() for x in inline.strip("[]").split(",") if x.strip()]
            elif inline:
                needs = [inline]
            else:
                needs = re.findall(r"(?m)^      - (\S+)", block[m.end():].split("\n    ", 1)[0] + "\n")
        jobs[name] = {"needs": needs, "text": block}
    return jobs


def install(tmp, tests=None):
    """The copy steps of /gate:gate-init, then the tests section of gate/gate.json set as given."""
    root = Path(tmp)
    shutil.copytree(TEMPLATES, root, dirs_exist_ok=True)
    for name in ("rule_fixtures.py", "actions_pinned.py"):
        shutil.copy(GATE / "checks" / name, root / ".github/actions/gate/rules")
    shutil.copytree(GATE / "checks/fixtures/gate.actions-pinned", root / "gate/fixtures/gate.actions-pinned")
    if tests is not None:
        cfg = json.loads((root / "gate/gate.json").read_text())
        cfg["tests"] = tests
        (root / "gate/gate.json").write_text(json.dumps(cfg))
    return root


def replay(root):
    """Run the shipped workflow's jobs on `root`. Returns ({job: success|failure|skipped}, output of the tests job)."""
    jobs = jobs_of(WORKFLOW.read_text())
    result, out = {}, ""
    pending = dict(jobs)
    while pending:
        name = next(n for n, j in pending.items() if all(d in result for d in j["needs"]))
        job = pending.pop(name)
        if any(result[d] != "success" for d in job["needs"]):
            result[name] = "skipped"  # GitHub: a job runs only when every job it needs succeeded
            continue
        if name == "gate":
            p = subprocess.run([sys.executable, str(root / ".github/actions/gate/run.py"), "--root", str(root), "--config", "gate/gate.json",
                                "--sha", "c1", "--dry-run", "--exit-code"], capture_output=True, text=True)
            result[name] = "success" if p.returncode == 0 else "failure"
        elif name == "tests":
            [cmd] = re.findall(r"(?m)^\s+run:[ \t]*(python3 \S*run_tests\.py.*)$", job["text"])
            p = subprocess.run(cmd.replace("python3", f'"{sys.executable}"', 1), shell=True, cwd=str(root), capture_output=True, text=True,
                               env={k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"})
            result[name] = "success" if p.returncode == 0 else "failure"
            out = p.stdout + p.stderr
        else:
            result[name] = "success"  # deploy: a placeholder in the template; reaching it is the point
    return result, out


@case
def shipped_defaults_are_warn_with_no_command(tmp):
    cfg = json.loads((TEMPLATES / "gate/gate.json").read_text())
    assert cfg["tests"] == {"tier": "warn", "command": ""}, cfg["tests"]


@case
def deploy_waits_for_the_gate_and_the_tests(tmp):
    jobs = jobs_of(WORKFLOW.read_text())
    assert set(jobs) == {"gate", "tests", "deploy"}, set(jobs)
    assert sorted(jobs["deploy"]["needs"]) == ["gate", "tests"], jobs["deploy"]["needs"]
    assert jobs["tests"]["needs"] == [], "tests runs next to the gate, not after it"


@case
def tests_job_gets_no_write_token(tmp):
    block = jobs_of(WORKFLOW.read_text())["tests"]["text"]
    assert "persist-credentials: false" in block and re.search(r"(?m)^      contents: read\b", block), block
    assert "timeout-minutes:" in block


@case
def replay_failing_tests_on_block_do_not_run_the_deploy(tmp):
    root = install(tmp, {"tier": "block", "command": "echo regression >&2; exit 1", "false_positive_test": FP})
    got, out = replay(root)
    assert got == {"gate": "success", "tests": "failure", "deploy": "skipped"}, (got, out)
    assert "deploy blocked" in out, out


@case
def replay_passing_tests_on_block_run_the_deploy(tmp):
    got, out = replay(install(tmp, {"tier": "block", "command": "true", "false_positive_test": FP}))
    assert got == {"gate": "success", "tests": "success", "deploy": "success"}, (got, out)


@case
def replay_failing_tests_on_warn_run_the_deploy_and_say_so(tmp):
    got, out = replay(install(tmp, {"tier": "warn", "command": "exit 1"}))
    assert got == {"gate": "success", "tests": "success", "deploy": "success"}, (got, out)
    assert "::warning" in out and "the deploy runs anyway" in out, out


@case
def replay_shipped_config_shows_the_missing_command(tmp):
    got, out = replay(install(tmp))
    assert got["deploy"] == "success" and "No test command is set" in out, (got, out)


@case
def replay_block_with_no_command_does_not_run_the_deploy(tmp):
    got, out = replay(install(tmp, {"tier": "block", "command": "", "false_positive_test": FP}))
    assert got == {"gate": "success", "tests": "failure", "deploy": "skipped"}, (got, out)


@case
def replay_block_without_a_record_does_not_run_the_deploy(tmp):
    root = install(tmp, {"tier": "block", "command": "true"})
    got, out = replay(root)
    assert got == {"gate": "success", "tests": "failure", "deploy": "skipped"}, (got, out)
    assert "false-positive" in out, out


@case
def replay_a_failing_gate_still_stops_the_deploy_when_the_tests_pass(tmp):
    root = install(tmp, {"tier": "block", "command": "true", "false_positive_test": FP})
    (root / ".github/workflows/deploy.yml").write_text("jobs:\n  deploy:\n    steps:\n      - uses: actions/deploy-pages@v4\n")
    got, out = replay(root)
    assert got == {"gate": "failure", "tests": "success", "deploy": "skipped"}, (got, out)


def main():
    failures = 0
    for fn in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn(tmp)
                print(f"ok   {fn.__name__}")
            except Exception as e:
                failures += 1
                print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(CASES)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
