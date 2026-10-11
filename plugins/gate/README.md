# gate

A deploy gate for any repository. Rules run on every push to main, weekly and by hand. A failing rule in the `block` tier stops the deploy, and the previous build stays live. Each run writes a record, and each finding stays open until a later run passes it.

Demo: [machinebehavior.io/inside/docs/eng/conformity-gate/](https://machinebehavior.io/inside/docs/eng/conformity-gate/), the gate that runs before every deploy of the platform behind machinebehavior.io.

## Skills

| Skill | What it does |
|---|---|
| `/gate:gate-init` | Copies the runner, the action, the workflow, the config and three starter rules into the repository, wires the deploy behind the gate and records the first run |
| `/gate:add-rule` | Installs a check from another module or writes a new rule, with pass and fail fixtures, a false-positive test, and promotion from `warn` to `block` |
| `/gate:run-record` | Reports from the run records: why a deploy was blocked, open and closed findings, rule or content changes between runs, schedule health |

## Templates

| Lands at | What it is |
|---|---|
| `.github/actions/gate/run.py` | The runner. Python 3.9+, standard library only, no network |
| `.github/actions/gate/action.yml` | Composite action that runs the checks and uploads the run record |
| `.github/actions/gate/rules/` | Rule contract (`README.md`) and the starter rules `gate.placeholders` and `gate.schedule` |
| `.github/workflows/gate.yml` | Gate job, bot commit of `latest.json` and `summary.md`, deploy job with `needs: gate` |
| `gate/gate.json` | Rules, tiers, options, excluded paths, schedule |
| `gate/fixtures/` | Pass and fail trees per blocking rule |

Run it by hand:

```bash
python3 .github/actions/gate/run.py --dry-run --exit-code
python3 .github/actions/gate/run.py --only docs.review
python3 .github/actions/gate/run.py --trigger manual
```

Exit codes: 0 run complete, 1 overall fail (with `--exit-code`), 2 config error, 3 internal error.

## Tiers and findings

- `block`: a `fail` fails the run and stops the deploy.
- `warn`: a `fail` is recorded as `warn` and stops nothing.
- `off`: the rule does not run.

A `fail` in either tier opens one finding per hit. The finding closes only when a later run of the same rule no longer sees the hit, and the record names the closing commit. Turning a rule off or moving it to `warn` closes nothing.

## Gate check

`checks/rule_fixtures.py`, id `gate.rule-fixtures`: every rule in the `block` tier passes its pass fixture, fails its fail fixture and has a recorded false-positive test in `gate.json`. `/gate:gate-init` installs it on `block`. Its own fixtures are in `checks/fixtures/gate.rule-fixtures/`.

## Other CI systems

`run.py` needs only Python 3. In any CI, run `python3 .github/actions/gate/run.py --exit-code` as the step before the deploy step. Only the composite action and the workflow are specific to GitHub Actions.
