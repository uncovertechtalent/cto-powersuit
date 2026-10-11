---
name: pressure-run
description: >
  Run scripted multi-turn pressure against an AI feature in a world where the
  right decision is known in advance, and write one JSON run record per run to
  red-team/runs/. The harness sends each turn to the system under test through a
  command adapter, an HTTP adapter for an OpenAI-compatible chat endpoint, or a stub for
  tests. Use when red-team/plan.md is frozen and the team is ready to run it, or
  to rerun the same plan after a change to the feature. Activates on
  "/pressure-run", "run the red-team plan", "run the pressure test", "pressure
  the assistant", "rerun the fold test".
user-invocable: true
---

# Pressure run

Runs the plan in `red-team/plan.md`. One run is one conversation: the opening message with the facts (turn 0), then the pressure turns of one tactic (turns 1 to 4 by default). The harness reads the decision at every turn and writes one record per run to `red-team/runs/<run id>.json`. The record format is `red-team/run.schema.json`.

`/red-team:pressure-grade` scores the records.

## Inputs

- `red-team/plan.md`, frozen and committed. Without it, run `/red-team:pressure-plan` first.
- The scenario files named in the plan, in `red-team/scenarios/`.
- Access to the system under test: a local command that wraps the feature, or an OpenAI-compatible chat endpoint.

## Steps

1. **Read the plan.** Note the scenarios, tactics, arms, runs per tactic, temperature and stop rule. If any of them is still a placeholder, stop and finish the plan first.
2. **Copy the harness** without overwriting:

   ```bash
   mkdir -p red-team && rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/red-team/" red-team/
   ```

   Without rsync: `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/red-team/." red-team/`. Report copied and skipped files. An existing `plan.md` stays as it is.
3. **Test the harness with the stub** into a temporary folder, so stub records never land in `red-team/runs/`:

   ```bash
   tmp="$(mktemp -d)"
   python3 red-team/harness.py --scenario red-team/scenarios/<id>.json --adapter stub --stub-profile mixed --runs 2 --out "$tmp"
   python3 red-team/grade.py --runs "$tmp"
   ```

   The mixed profile holds on some runs, folds on others and abstains on one. The grade report must show folds and holds. If every run reads `ABSTAIN`, the scenario's `decision_pattern` does not match its `decision_line`: fix the scenario.
4. **Pick the adapter.**
   - `command`: a local program reads one JSON turn on stdin (`scenario`, `tactic`, `run`, `turn`, `system`, `messages`) and prints the reply as text, or as JSON with `reply` and the optional `decision`, `finish` and `reasoning`. Use `decision` when the feature acts through a tool call or an API field. Set the program with `--command` or `RED_TEAM_COMMAND`.
   - `http`: an OpenAI-compatible chat endpoint. Set `RED_TEAM_BASE_URL` (for example `http://localhost:8000/v1`), `RED_TEAM_MODEL`, and `RED_TEAM_API_KEY` when the endpoint needs a key. The user sets the key in the shell. Never write a key into a file, a command line or a record.
5. **Smoke run.** One run of one tactic against the real system:

   ```bash
   python3 red-team/harness.py --scenario red-team/scenarios/<id>.json --adapter http --tactics PT-08 --runs 1 --out "$tmp"
   ```

   Open the record. Check that every turn has a decision label. `ABSTAIN` at turn 0 means the system did not give the decision in the expected form: fix the system prompt or the pattern, record an amendment in the plan, and repeat this step.
6. **Full run.** For each scenario and arm in the plan:

   ```bash
   python3 red-team/harness.py --scenario red-team/scenarios/<id>.json --adapter <adapter> --runs <n> --arm <arm> [--arm-file red-team/arms/<arm>.txt] [--temperature 0]
   ```

   Add `--redact` when replies can hold personal or confidential data: the record then stores sha256 hashes in place of the message text and keeps the decisions.
7. **Apply the stop rule.** Count adapter errors (exit code 1, `observed_decision: ERROR`) and runs with no decision at turn 0. Stop only on the conditions in the plan. Never stop or add runs because of the fold rates seen so far.
8. **Hand over.** Report the number of records written, errors, and the folder. Next step: `/red-team:pressure-grade`.

## Output

- One `red-team/runs/<run id>.json` per run, each with `expected_decision`, `observed_decision`, the decision per turn, the fold turn and a `verdict`.
- A one-line summary per run on stdout, and the count of records and errors.

## Rules

- Run only against systems the team owns or has written permission to test.
- The decision of a turn is the adapter's `decision` field or the last decision line of the reply. Reply prose and reasoning go into the record for people to read; grade.py never reads them.
- Reasoning returned by an endpoint is never sent back to the system in later turns.
- Keep scripts, transcripts and records in the client repository. Do not publish them.
- Never edit a run record by hand. A wrong record is deleted by the user and its run repeated.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/red-team" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/red-team/` exists, read its `README.md` first, then the files in `red-team/pressure-run/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
