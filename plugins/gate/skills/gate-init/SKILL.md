---
name: gate-init
description: >
  Set up a deploy gate in the current repository: a rules folder, a runner that
  writes run records, a GitHub Actions workflow whose deploy job waits for the
  gate, and three starter rules. Use when a repository has no deploy gate yet
  and the team wants checks to run before every deploy. Copies templates and
  never overwrites a file. Activates on "/gate-init", "set up the gate", "add a
  deploy gate", "gate the deploy".
user-invocable: true
---

# Gate init

Sets up the gate in the repository the user is working in. After setup, every push to main runs the rules first. A failing rule in the `block` tier stops the deploy, and the previous build stays live.

## What lands in the repository

| Path | What it is |
|---|---|
| `.github/actions/gate/run.py` | The runner. Python 3.9+, standard library only, no network |
| `.github/actions/gate/action.yml` | Composite action: runs `run.py`, uploads the run record as an artifact |
| `.github/actions/gate/rules/` | One file per rule, plus `README.md` with the rule contract |
| `.github/actions/gate/reporters/oscal.py` | Optional reporter for an OSCAL-shaped record per run; off until listed in `gate.json` |
| `.github/workflows/gate.yml` | Gate job on push to main, weekly and by hand; the deploy job has `needs: gate` |
| `gate/gate.json` | Which rules run, in which tier, with which options |
| `gate/fixtures/` | A pass tree and a fail tree for each blocking rule |
| `gate/.gitignore` | Keeps `runs/` and `.result` out of git |

Each run writes `gate/latest.json` (history and findings; the workflow commits it), `gate/summary.md`, `gate/runs/<timestamp>-<id>.json` (kept as a workflow artifact for 90 days) and `gate/.result`.

Starter rules: `gate.placeholders` (`TODO`, `TBD` and fill-in markers in Markdown and HTML), `gate.schedule` (the weekly run happened) and `gate.rule-fixtures` (every blocking rule passes its pass fixture, fails its fail fixture and has a recorded false-positive test).

## Steps

1. **Check the repository.** Find the root with `git rev-parse --show-toplevel`. List `.github/workflows/` and name the workflow that deploys, if any. If `gate/` or `.github/actions/gate/` exists, list what is there and ask before going on.
2. **Copy without overwriting.**

   ```bash
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/" ./
   cp -n "${CLAUDE_PLUGIN_ROOT}/checks/rule_fixtures.py" .github/actions/gate/rules/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/." ./`. Hidden folders (`.github`) and `gate/.gitignore` must come across. Report the files copied and the files skipped because they existed.
3. **Fill the config.** In `gate/gate.json`, set `name` to the repository name and `owner` to the person who keeps the gate true (ask). Keep the starter tiers: `gate.placeholders` and `gate.schedule` on `warn`, `gate.rule-fixtures` on `block`.
4. **Wire the deploy.** The deploy must run only after the gate passes. Pick one and show the change before you make it:
   - No deploy workflow yet: put the deploy steps in the `deploy` job of `gate.yml`.
   - A deploy workflow exists: move its deploy steps into the `deploy` job of `gate.yml`, or change its trigger to `workflow_run` on the `Gate` workflow and add `if: github.event.workflow_run.conclusion == 'success'` to its job.
   - Another CI system: run `python3 .github/actions/gate/run.py --exit-code` as the step before the deploy step.
   Ask before editing an existing workflow.
5. **First run, locally.**

   ```bash
   python3 .github/actions/gate/run.py --dry-run
   ```

   Expect `overall=pass`. `gate.placeholders` may print warnings; go through them with the user and fix them or leave them on `warn`. `gate.rule-fixtures` reports `n/a` until a second blocking rule exists.
6. **Record the first run.** `python3 .github/actions/gate/run.py --trigger manual` writes `gate/latest.json` and `gate/summary.md`. Commit the new files when the user says so.
7. **Next.** Add rules with `/gate:add-rule`. Installed modules ship their own checks, for example `decisions.adr-fields` and `docs.review`. Tell the user to mark the `Gate checks` job as a required status check in the branch protection settings; that is a repository setting the user changes.

## Rules

- Never overwrite, delete or move an existing file. Ask before editing an existing workflow.
- Never push. The user pushes.
- Before a push, compare the result value; do not grep for it. `grep overall= && git push` pushes on a failing run, because grep also matches `overall=fail`. Use the exit code: `python3 .github/actions/gate/run.py --dry-run --exit-code && git push`.
- A rule goes to `block` only through `/gate:add-rule`, with fixtures and a false-positive test.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/gate" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/gate/` exists, read its `README.md` first, then the files in `gate/gate-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
