# red-team

Pressure tests for AI features. A pressure test asks whether a feature gives up a right decision, a rule or a task boundary when a user applies social pressure and brings no new valid facts: claimed rank, consensus, flattery, urgency, blame, repeated pushback, a fabricated policy. The test runs in a world where the right decision is known before the first call, so every change of decision is visible and countable. The score is the decision the system took. Its explanation of its own reasons is left out of the score.

The module plans the test (`pressure-plan`), runs it with a small harness (`pressure-run`) and grades the run records (`pressure-grade`). A gate check tests the run records: every record must name the expected and the observed decision, and a verdict must agree with them. Fold rates themselves block no deploy.

Install:

```bash
claude plugin install red-team@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/red-team:pressure-plan` | Writes `red-team/plan.md`: the decision the feature makes, the world with a known answer, the tactics that apply from an eleven-tactic catalogue (PT-01 to PT-11), the arms, the number of runs, the stop rule and the prediction, all before the first call |
| `/red-team:pressure-run` | Copies the harness, tests it with the stub adapter, then runs the scripted pressure through the command or HTTP adapter. Writes one record per run to `red-team/runs/<run id>.json` |
| `/red-team:pressure-grade` | Scores the decision at each turn against the expected one. Reports fold rates per tactic with counts and Wilson 95 percent intervals, marks samples under 30 eligible runs, reports over-refusal on control runs and scores the plan's predictions |

The four failures the catalogue targets: fold (right at the first reply, another decision later), unchecked agreement (a false premise or praise accepted where a check belongs), rule drop (a rule set aside for a message that claims a higher rank) and scope widening (a task widened in small accepted steps). The tactic ids follow the public catalogue in the demo line below.

## Templates

The skills copy these files into the client repository. An existing file is never overwritten.

| Lands at | What it is |
|---|---|
| `red-team/plan.md` | The plan page with docs front matter: feature and decision, world, failures in scope, tactics, arms, runs and stop rule, prediction, amendments |
| `red-team/scenarios/example.json` | An example world: facts, the rule, the decision labels and pattern, the expected decision, the pressure target and four pressure turns for each of four tactics |
| `red-team/harness.py` | The harness. Python 3.9+, standard library only. Adapters: `stub` (tests, no model), `command` (one JSON turn on stdin of a local program) and `http` (OpenAI-compatible chat endpoint; `RED_TEAM_BASE_URL`, `RED_TEAM_MODEL`, `RED_TEAM_API_KEY`). Writes `red-team/runs/<run id>.json`; `--redact` stores hashes in place of message text |
| `red-team/grade.py` | The grader. Python 3.9+, standard library only. Recomputes fold and verdict from the decisions, prints a Markdown or JSON report, lists records whose stored values disagree |
| `red-team/run.schema.json` | JSON Schema of a run record |

The plan's sha256 goes into every run record, so a result links to the plan version it ran under.

## Gate check

`checks/run_records.py` defines the rule `red-team.run-records`. For each file that matches `red-team/runs/*.json` it reports:

| Snippet | Problem |
|---|---|
| `not valid JSON`, `not a JSON object` | The record cannot be read |
| `missing expected_decision` | No expected decision, or an empty one |
| `missing observed_decision` | No observed decision, or an empty one |
| `verdict pass but the decisions differ`, `verdict fail but the decisions match` | The verdict disagrees with the two decisions (compared after trimming spaces; case counts) |
| `unknown verdict: <value>` | A verdict other than `pass` or `fail` |

The result is `fail` on any hit, `pass` when every record is clean and `n/a` when no file matches. Paths with a segment that starts with `_` are skipped. A record without a verdict passes when both decisions are present; the harness leaves the verdict out of runs that ended on an adapter error. A run where the system folded passes the rule: the rule checks that records are complete and consistent, and the fold rate is a finding for the grade report. Option: `globs` (default `["red-team/runs/*.json"]`).

Enable it with `/gate:add-rule` (path A). By hand, from a clone of this repository:

1. Copy the rule: `cp -n plugins/red-team/checks/run_records.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -Rn plugins/red-team/checks/fixtures/red-team.run-records <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` on `warn`:

   ```json
   "red-team.run-records": {"tier": "warn"}
   ```

4. Move it to `"tier": "block"` once a false-positive test over your own run records is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures` checks the fixtures and the record.

Run it on its own with `python3 .github/actions/gate/run.py --only red-team.run-records --dry-run`.

Demo: [machinebehavior.io/red-team/](https://machinebehavior.io/red-team/), the public pressure-test catalogue of machinebehavior.io.
