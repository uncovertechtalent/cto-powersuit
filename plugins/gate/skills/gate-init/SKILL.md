---
name: gate-init
description: >
  Set up a deploy gate in the current repository: a rules folder, a runner that
  writes run records, a GitHub Actions workflow whose deploy job waits for the
  gate and for the repository's tests, and four starter rules. Use when a
  repository has no deploy gate yet and the team wants checks and tests to run
  before every deploy. Copies templates and
  never overwrites a file. Activates on "/gate-init", "set up the gate", "add a
  deploy gate", "gate the deploy".
user-invocable: true
---

# Gate init

Sets up the gate in the repository the user is working in. After setup, every push to main runs the rules and the repository's own tests first. A failing rule in the `block` tier stops the deploy, and so does a failing test run once the test tier is `block`; the previous build stays live.

## What lands in the repository

| Path | What it is |
|---|---|
| `.github/actions/gate/run.py` | The runner. Python 3.9+, standard library only, no network |
| `.github/actions/gate/run_tests.py` | The test step: runs the test command named in `gate/gate.json` and exits by tier |
| `.github/actions/gate/action.yml` | Composite action: runs `run.py`, uploads the run record as an artifact |
| `.github/actions/gate/rules/` | One file per rule, plus `README.md` with the rule contract |
| `.github/actions/gate/reporters/oscal.py` | Optional reporter for an OSCAL-shaped record per run; off until listed in `gate.json` |
| `.github/workflows/gate.yml` | Gate job and tests job on push to main, weekly and by hand; the deploy job has `needs: [gate, tests]` |
| `gate/gate.json` | Which rules run, in which tier, with which options; the `tests` command and tier |
| `gate/fixtures/` | A pass tree and a fail tree for each blocking rule |
| `gate/.gitignore` | Keeps `runs/` and `.result` out of git |

Each run writes `gate/latest.json` (history and findings; the workflow commits it), `gate/summary.md`, `gate/runs/<timestamp>-<id>.json` (kept as a workflow artifact for 90 days) and `gate/.result`.

Starter rules: `gate.placeholders` (`TODO`, `TBD` and fill-in markers in Markdown and HTML), `gate.schedule` (the weekly run happened), `gate.actions-pinned` (every action from outside the repository is pinned to a full commit SHA) and `gate.rule-fixtures` (every blocking rule passes its pass fixture, fails its fail fixture and has a recorded false-positive test).

## Steps

1. **Check the repository.** Find the root with `git rev-parse --show-toplevel`. List `.github/workflows/` and name the workflow that deploys, if any. If `gate/` or `.github/actions/gate/` exists, list what is there and ask before going on.
2. **Copy without overwriting.**

   ```bash
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/" ./
   cp -n "${CLAUDE_PLUGIN_ROOT}/checks/rule_fixtures.py" "${CLAUDE_PLUGIN_ROOT}/checks/actions_pinned.py" .github/actions/gate/rules/
   mkdir -p gate/fixtures/gate.actions-pinned && cp -Rn "${CLAUDE_PLUGIN_ROOT}/checks/fixtures/gate.actions-pinned/." gate/fixtures/gate.actions-pinned/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/." ./`. Hidden folders (`.github`) and `gate/.gitignore` must come across. Report the files copied and the files skipped because they existed.
3. **Fill the config.** In `gate/gate.json`, set `name` to the repository name and `owner` to the person who keeps the gate true (ask). Keep the starter tiers: `gate.placeholders` and `gate.schedule` on `warn`, `gate.actions-pinned` and `gate.rule-fixtures` on `block`.
4. **Name the test command.** The `tests` job runs one command, `tests.command` in `gate/gate.json`. The template ships it empty on the `warn` tier. Never guess it from the language.
   - If `docs/sdlc.md` has a "Test strategy" section, read its pre-PR command and show it. That command may include lint and the gate dry run; ask which part runs the tests.
   - Otherwise list what the repository itself offers (a `test` script in `package.json`, a `Makefile` target, a `tox` or `pytest` configuration, a CI job that runs tests) as candidates, and ask the user to name the command. If the repository has no tests, say so, leave `command` empty, and point to `/sdlc:test-strategy`.

   Write the answer to `tests.command` and leave `tests.tier` on `warn`. Show the "Set up the toolchain" step of the `tests` job in `gate.yml` and fill it with what the command needs (runtime, dependencies, services); pin each action by commit SHA. Then run the step once:

   ```bash
   python3 .github/actions/gate/run_tests.py
   ```

   Report the exit code and the `tests:` line. If the command fails on the current commit, say so: it is a failing test or a command that needs more setup. Do not change the tier to hide it.

   An install from before the test job existed has a `gate.yml` without a `tests` job. Copy `run_tests.py` with `cp -n`, show the job and the change from `needs: gate` to `needs: [gate, tests]`, and ask before editing the workflow.

   Tell the user what `warn` means: a failing test run is reported and the deploy still runs. The deploy waits for the tests only after `tests.tier` is `block`, which `/gate:add-rule` (path C) sets once a false-positive test is recorded.
5. **Wire the deploy.** The deploy must run only after the gate and the tests pass. Pick one and show the change before you make it:
   - No deploy workflow yet: put the deploy steps in the `deploy` job of `gate.yml`; it has `needs: [gate, tests]`.
   - A deploy workflow exists: move its deploy steps into the `deploy` job of `gate.yml`, or change its trigger to `workflow_run` on the `Gate` workflow and add `if: github.event.workflow_run.conclusion == 'success'` to its job. The `Gate` workflow concludes `success` only when the gate job and the tests job both did.
   - Another CI system: run `python3 .github/actions/gate/run.py --exit-code` and `python3 .github/actions/gate/run_tests.py` as the steps before the deploy step.
   Ask before editing an existing workflow.
6. **First run, locally.**

   ```bash
   python3 .github/actions/gate/run.py --dry-run
   ```

   Expect `overall=pass`. `gate.placeholders` may print warnings; go through them with the user and fix them or leave them on `warn`. `gate.actions-pinned` fails when a workflow uses an action by tag or branch. For each hit, read the commit SHA from the action's release tag (`gh api repos/<owner>/<repo>/commits/<tag> -q .sha`), show the pinned line (`uses: <owner>/<repo>@<sha> # <tag>`) and pin it on the user's yes. If the user wants to pin later, set `gate.actions-pinned` to `warn` and say that the deploy then runs on unpinned actions. `gate.rule-fixtures` runs `gate.actions-pinned` against its fixtures in `gate/fixtures/gate.actions-pinned/`.
7. **Record the first run.** `python3 .github/actions/gate/run.py --trigger manual` writes `gate/latest.json` and `gate/summary.md`. Commit the new files when the user says so.
8. **Next.** Add rules with `/gate:add-rule`. Installed modules ship their own checks, for example `decisions.adr-fields` and `docs.review`. Tell the user to mark the `Gate checks` job as a required status check in the branch protection settings; that is a repository setting the user changes.

## Rules

- Never overwrite, delete or move an existing file. Ask before editing an existing workflow.
- Never push. The user pushes.
- Before a push, compare the result value; do not grep for it. `grep overall= && git push` pushes on a failing run, because grep also matches `overall=fail`. Use the exit code: `python3 .github/actions/gate/run.py --dry-run --exit-code && git push`.
- A rule goes to `block` only through `/gate:add-rule`, with fixtures and a false-positive test. The test tier goes to `block` only through its path C, with a recorded false-positive test.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/gate" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/gate/` exists, read its `README.md` first, then the files in `gate/gate-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
