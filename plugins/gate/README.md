# gate

A deploy gate for any repository. Rules run on every push to main, weekly and by hand. A failing rule in the `block` tier stops the deploy, and the previous build stays live. Each run writes a record, and each finding stays open until a later run passes it. Optional: a requirements file that maps check results to requirement states, and reporters that render pages or write records in other formats.

Demo: [machinebehavior.io/inside/docs/eng/conformity-gate/](https://machinebehavior.io/inside/docs/eng/conformity-gate/), the gate that runs before every deploy of the platform behind machinebehavior.io.

## Skills

| Skill | What it does |
|---|---|
| `/gate:gate-init` | Copies the runner, the action, the workflow, the config and four starter rules into the repository, wires the deploy behind the gate and records the first run |
| `/gate:add-rule` | Installs a check from another module or writes a new rule, with pass and fail fixtures, a false-positive test, and promotion from `warn` to `block` |
| `/gate:run-record` | Reports from the run records: why a deploy was blocked, open and closed findings, rule or content changes between runs, schedule health |

## Templates

| Lands at | What it is |
|---|---|
| `.github/actions/gate/run.py` | The runner. Python 3.9+, standard library only, no network |
| `.github/actions/gate/action.yml` | Composite action that runs the checks and uploads the run record |
| `.github/actions/gate/rules/` | Rule contract (`README.md`, also covering requirements and reporters) and the starter rules `gate.placeholders` and `gate.schedule` |
| `.github/actions/gate/reporters/oscal.py` | Optional reporter: an OSCAL-shaped assessment-results record per run. Off until listed under `reporters` in `gate.json` |
| `.github/workflows/gate.yml` | Gate job, bot commit of `gate/` (`latest.json`, `summary.md`, reporter pages), deploy job with `needs: gate` |
| `gate/gate.json` | Rules, tiers, options, excluded paths, schedule; optional `requirements`, `reporters` and `write_summary` |
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

## Other CI systems

`run.py` needs only Python 3. In any CI, run `python3 .github/actions/gate/run.py --exit-code` as the step before the deploy step. Only the composite action and the workflow are specific to GitHub Actions.
