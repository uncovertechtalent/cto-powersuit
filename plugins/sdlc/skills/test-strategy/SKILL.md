---
name: test-strategy
description: >
  Decide what gets tested at which level (unit, integration, end to end,
  smoke) and define the one command an agent or a person runs before opening a
  pull request. Writes the test section of docs/sdlc.md. Use when a repository
  has no tests, tests that CI never runs, or tests nobody trusts. Activates on
  "/test-strategy", "what should we test", "set up the pre-PR check",
  "our tests are flaky", "add tests to this repo".
user-invocable: true
---

# Test strategy

Sets the levels, the pre-PR command and the rules for flaky tests, and writes them into the "Test strategy" section of `docs/sdlc.md`.

## Steps

1. **Find what exists.** Test folders, test frameworks in the manifests, the CI jobs that run tests, the last CI runs (`gh run list --limit 10`). Count tests per level if they are named by level.
2. **Pick the levels.**

   | Level | Covers | Rule |
   |---|---|---|
   | Unit | One function or module; no network, no clock, no shared state | Most tests live here; each runs in milliseconds |
   | Integration | The service with its real database, queue or file system, in containers | One per external dependency and per main path |
   | End to end | A user path through the deployed system | A handful, on the paths that make money or lose data |
   | Smoke | The service answers after a deploy | Runs in the deploy job; a failure triggers the rollback |

3. **Define the pre-PR command.** One command that runs lint, unit tests and the gate dry run, for example a `make check` target or an npm script. It must run in under five minutes on a laptop, or the agent and the person skip it. Write it into `docs/sdlc.md` and into the pull request template.
4. **Wire CI.** The same command runs on every pull request, and the merge waits for it. Show the workflow change before making it.
5. **Set the flaky-test rule.** A test that fails and passes on the same commit gets a ticket and a quarantine tag the same day; quarantined tests run but do not block; a quarantined test is fixed or deleted within two weeks.
6. **Set the agent rule.** An agent that changes source also changes or adds the tests for it, and runs the pre-PR command before it opens a pull request. A test changed only to make it pass is a review finding.

## Output

The "Test strategy" section of `docs/sdlc.md`, the pre-PR command, and a list of the first tests to write, ordered by the risk the audit found.

## Rules

- Coverage figures are a signal for where tests are missing. A coverage target alone is not a goal.
- Never delete or skip a failing test to make CI pass.
- Never change CI files without the user's go.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/test-strategy/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
