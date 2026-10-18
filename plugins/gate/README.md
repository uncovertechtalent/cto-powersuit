# gate

A deploy gate for any repository. Rules run on every push to main, weekly and by hand, and so do the repository's own tests. A failing rule in the `block` tier stops the deploy, and so does a failing test run once the test tier is `block`; the previous build stays live. Each run writes a record, and each finding stays open until a later run passes it. Optional: a requirements file that maps check results to requirement states, and reporters that render pages or write records in other formats.

Demo: [machinebehavior.io/inside/docs/eng/conformity-gate/](https://machinebehavior.io/inside/docs/eng/conformity-gate/), the gate that runs before every deploy of the platform behind machinebehavior.io.

## Skills

| Skill | What it does |
|---|---|
| `/gate:gate-init` | Copies the runner, the action, the workflow, the config and four starter rules into the repository, asks for the test command, wires the deploy behind the gate and the tests, and records the first run |
| `/gate:add-rule` | Installs a check from another module or writes a new rule, with pass and fail fixtures, a false-positive test, and promotion from `warn` to `block`; the same promotion for the test job |
| `/gate:run-record` | Reports from the run records: why a deploy was blocked, open and closed findings, rule or content changes between runs, schedule health |

## Templates

| Lands at | What it is |
|---|---|
| `.github/actions/gate/run.py` | The runner. Python 3.9+, standard library only, no network |
| `.github/actions/gate/run_tests.py` | The test step. Python 3.9+, standard library only. Runs the test command named in `gate/gate.json` and exits by tier |
| `.github/actions/gate/action.yml` | Composite action that runs the checks and uploads the run record |
| `.github/actions/gate/rules/` | Rule contract (`README.md`, also covering requirements and reporters) and the starter rules `gate.placeholders` and `gate.schedule` |
| `.github/actions/gate/reporters/oscal.py` | Optional reporter: an OSCAL-shaped assessment-results record per run. Off until listed under `reporters` in `gate.json` |
| `.github/workflows/gate.yml` | Gate job, bot commit of `gate/` (`latest.json`, `summary.md`, reporter pages), tests job, deploy job with `needs: [gate, tests]` |
| `gate/gate.json` | Rules, tiers, options, excluded paths, schedule, the `tests` command and tier; optional `requirements`, `reporters`, and `write_summary` |
| `gate/fixtures/` | Pass and fail trees per blocking rule |

Run it by hand:

```bash
python3 .github/actions/gate/run.py --dry-run --exit-code
python3 .github/actions/gate/run.py --only docs.review
python3 .github/actions/gate/run.py --trigger manual
```

Exit codes: 0 run complete, 1 overall fail (with `--exit-code`), 2 config error, 3 internal error, 4 to 125 a reporter refused the run (nothing written).

## Tiers and findings

- `block`: a `fail` fails the run and stops the deploy.
- `warn`: a `fail` is recorded as `warn` and stops nothing.
- `off`: the rule does not run.

Every new rule starts on `warn`, in the starter config and in `/gate:add-rule`, and checks from other modules too. A rule moves to `block` only after its false-positive test is recorded in `gate.json`, its fixtures behave and the repository has no real hits left. Two rules are the exception: `/gate:gate-init` installs them on `block`. `gate.rule-fixtures` only reads the gate's own config and fixtures. `gate.actions-pinned` checks one syntax with no judgement in it, its false-positive test is recorded in the starter config, and its fix is mechanical: on the first run `/gate:gate-init` pins each hit on the user's yes, or sets the rule to `warn` until the user pins them.

`partial`, `pending`, `warn` and `n/a` results never fail the run.

A `fail` in either tier opens one finding per hit. The finding closes only when a later run of the same rule no longer sees the hit, and the record names the closing commit. Turning a rule off or moving it to `warn` closes nothing. Rules with `PHASE = "after"` run once the findings are built, read them, and open none.

The test job has the same three tiers and the same start on `warn`. It is configured under `tests` in `gate.json` and has no entry under `rules` (next section).

## Tests before the deploy

`gate.yml` has a `tests` job next to the `gate` job, and the `deploy` job needs both. The job runs one command from the repository root: the repository's own test command, named in `gate/gate.json`. The gate guesses no command from the language or the manifests.

```json
"tests": {"tier": "warn", "command": "make check"}
```

| Tier | A failing test run | No command set |
|---|---|---|
| `block` | Fails the job. The `deploy` job does not run, and the previous build stays live | Fails the job |
| `warn` | Shown as a warning in the run and its summary. The `deploy` job runs | Shown as a warning in the run and its summary. The `deploy` job runs |
| `off` | The command does not run, and the run shows a warning | The command does not run, and the run shows a warning |

The template ships `{"tier": "warn", "command": ""}`, so the tests job ships on `warn`. Until someone names the command, every run shows "No test command is set" as a warning. `/gate:gate-init` asks for the command and does not fill it from the language. A test gate that blocks a deploy because of a flaky test is a false positive, so the test job follows the rule of every new check: it stays on `warn` until the repository has recorded a false-positive test, and `/gate:add-rule` (path C) moves it to `block`. `run_tests.py` enforces this itself: with `"tier": "block"` and no `false_positive_test` (`date`, `hits`, `legitimate`), or with `legitimate` above zero, it exits 2 and runs nothing, so the job fails and the deploy waits. `gate.rule-fixtures` checks rules only, so it does not cover this record.

```json
"tests": {
  "tier": "block",
  "command": "make check",
  "false_positive_test": {"date": "2026-10-18", "corpus": "6 runs of the tests job on main", "hits": 2, "legitimate": 0, "decision": "block: both failed runs were real regressions"}
}
```

- The command can be the pre-PR command from the "Test strategy" section of `docs/sdlc.md` (`/sdlc:test-strategy`), or the part of it that runs the tests. Its gate dry run is redundant here, because the `gate` job runs the rules.
- The command runs with `bash -e -o pipefail`, so a multi-line command stops at its first failing line and a failing stage of a pipe fails the run.
- The `tests` job has a placeholder step, "Set up the toolchain", for the runtime, the dependencies, and the services the command needs. Pin each action in it by commit SHA, as `gate.actions-pinned` requires.
- The job gets a read-only token and does not keep the checkout credentials, because project test code runs in it.
- A job that does not finish (a runner failure, or the 30-minute `timeout-minutes`) fails on any tier, and the deploy waits, because nothing says the tests passed.
- `python3 .github/actions/gate/run_tests.py` runs the same step on your machine.
- A repository that installed the gate before this job existed keeps its `gate.yml`. Copy `run_tests.py` and the `tests` section, add the job, and change `needs: gate` to `needs: [gate, tests]`. `/gate:gate-init` shows the edit and asks first.

### Before the merge, before the deploy, or both

| Placement | What it stops | What it needs |
|---|---|---|
| Before the merge: the pre-PR command runs on every pull request (`/sdlc:test-strategy`, step 4) | The merge, once the CI check is a required status check | The branch protection setting, which a person changes |
| Before the deploy: the `tests` job of `gate.yml` | The `deploy` job. The failing commit stays on main until a fix or a revert lands | Nothing in the repository settings. It also covers a direct push to main |

The two can run together. The pull request check keeps most failures out of main, and the tests job stops the deploy of what gets through: a direct push, a check that is not required, two changes that pass alone and fail together. A repository that tests only before the deploy accepts that main can hold a broken commit until a fix or a revert lands.

## Gate checks

`checks/rule_fixtures.py`, id `gate.rule-fixtures`: every rule in the `block` tier passes its pass fixture, fails its fail fixture and has a recorded false-positive test in `gate.json`. `/gate:gate-init` installs it on `block`. Its own fixtures are in `checks/fixtures/gate.rule-fixtures/`.

`checks/actions_pinned.py`, id `gate.actions-pinned`: workflows (`.github/workflows/`) and composite actions (`.github/actions/**/action.yml`, a root `action.yml`) reference every action and reusable workflow from outside the repository by a full 40-character commit SHA, and every `docker://` image by a sha256 digest. A tag or a branch can be moved to other code; a commit SHA cannot. Local actions (`./...`, `../...` and the self-repository form `$/...`) are exempt; the `allow` option exempts reference prefixes such as your own organisation (empty by default). Hit kinds: `tag-or-branch`, `short-sha`, `no-ref`, `docker-tag`. `/gate:gate-init` installs it on `block`. Its fixtures are in `checks/fixtures/gate.actions-pinned/`.

To pin a reference, read the commit SHA from the action's own release tag, not from memory, and keep the tag as a comment:

```bash
gh api repos/<owner>/<repo>/commits/<tag> -q .sha
```

```yaml
- uses: <owner>/<repo>@<40-character sha> # <tag>
```

## Tests

`tests/test_run.py` runs the runner against small repositories built in a temporary folder: results, finding ids and closure, migration of findings written by run.py 0.1, the shared cache, after-phase rules, requirement states, reporters and their limits, `write_summary` and the warnings count. Two cases cover the starter set: the copy steps of `/gate:gate-init` give a passing run that an unpinned action then fails, and each fail fixture of `gate.actions-pinned` gives exactly one hit of its kind.

`tests/test_run_tests.py` covers the test step: each tier with a passing, a failing, and an empty command, the record that `block` requires, config errors, and the annotations. Its replay cases install the gate as `/gate:gate-init` does, read the `needs` of the shipped `gate.yml`, run the gate job and the tests job, and show whether the `deploy` job runs: a failing test run on `block` skips it, a failing run on `warn` does not, and a failing gate still skips it when the tests pass.

## Other CI systems

`run.py` needs only Python 3. In any CI, run `python3 .github/actions/gate/run.py --exit-code` and `python3 .github/actions/gate/run_tests.py` as the steps before the deploy step. Both exit 1 when the deploy must not run. Only the composite action and the workflow are specific to GitHub Actions.
