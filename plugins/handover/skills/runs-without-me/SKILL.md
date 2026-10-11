---
name: runs-without-me
description: >
  Plan and log a test that proves the named owner runs the platform from the
  docs alone: scenarios such as a deploy, a blocked gate, an incident, a cost
  spike, a docs review and a new decision, each run by the new owner with no
  help, with the time taken, the docs used and the gaps found, and every gap
  turned into a ticket. Use when the person who built a platform is about to
  leave, or to test whether the docs are enough to operate it. Activates on
  "/runs-without-me", "does it run without me", "handover test", "test the
  runbooks with the new owner", "game day for the handover".
user-invocable: true
---

# Runs without me

A test plan for the handover. The new owner runs each scenario from the docs alone, with no help from the person handing over. Each run records the time taken, the docs used and the gaps found. Every gap becomes a ticket. A scenario passes when a run needs no help.

## Inputs

- `docs/handover.md` with the owners table (run `/handover:owner-training` first if it is missing).
- The installed modules, found by the signal table in `${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md`.
- From the user: the new owner per scenario, a non-production environment or a game-day window for staged failures, and a time box per scenario.

## Steps

1. **Copy the template** if the page is missing:

   ```bash
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md" docs/handover.md
   ```

2. **Plan the scenarios** with the user. Defaults:

   | Scenario | Trigger | Passes when | Modules |
   |---|---|---|---|
   | A deploy | A real change merged to the main line | The change is live, the gate run passed, the changelog entry and the rollback line exist | sdlc, gate |
   | A blocked gate | A commit on a branch that breaks one rule on purpose | The owner finds the rule from the gate summary, fixes the cause, the rerun passes and the finding closes | gate |
   | An incident | A staged failure in a non-production environment, or a game day | Declared, status page updated, service restored, postmortem written with action items ticketed | reliability, observability |
   | A cost spike | A staged line in a copy of a billing export, or a real spike | The cause and its owner are found from the cost pages, and the action is ticketed | finops |
   | A docs review | The page with the oldest `review_by` | The page is checked against the system it describes, fixed, and its review dates updated | docs |
   | A new decision | A real open question | An RFC or ADR is written, reviewed by the right people and listed in the index | decisions |

   Drop a scenario whose modules are not installed and say so in the report. Add scenarios for other installed modules with the same columns. Write the plan with its time boxes into the "Runs without me" section.
3. **Set the run rules** before the first run:
   - The person handing over is not in the room or the chat. A question to them counts as help, ends the "no help" condition and is written down word for word.
   - The new owner uses only the docs, the repository and the tools. Search engines and assistants are allowed; a private conversation with a colleague who built the system counts as help.
   - Staged failures run only in a non-production environment, or in production with the user's go and a rollback ready. Stop the run when users are at risk, and log it as help needed.
4. **Run each scenario.** The new owner starts a timer at the trigger and stops it when the pass condition holds or the time box ends.
5. **Log the run** as one row in the "Runs without me" table: date, scenario, who ran it, help needed (none, or the question), time taken in minutes, the docs pages used, and the gaps found (a missing step, a wrong command, a page that was out of date, an access the owner lacked).
6. **Turn every gap into a ticket.** With the sdlc module installed, use `/sdlc:ticket`; otherwise give the user the ticket text: the scenario, the gap, the page to fix and the acceptance criterion "the next run of this scenario needs no help at this step". Label each ticket `handover`. Write the ticket ids into the log row.
7. **Repeat** a scenario after its tickets are closed, until a run passes with no help. Keep every earlier row.
8. **Hand the result to the exit criteria.** Run `/handover:exit-criteria`, which reads the log.

## Output

The scenario plan and the run log in `docs/handover.md`, the tickets for the gaps, and a report per scenario: passed or not, the runs so far, the time per run and the open tickets.

## Rules

- No help means no help. A hint, a nod or a shared screen counts as help and is logged.
- Never write a run that did not happen, and never fill a row for the owner.
- Every gap gets a ticket. A gap fixed in the moment still gets a ticket, so the docs change is reviewed.
- Write only `docs/handover.md` and the tickets the user approves. Never overwrite an existing file with the template. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/handover" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/handover/` exists, read its `README.md` first, then the files in `handover/runs-without-me/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
