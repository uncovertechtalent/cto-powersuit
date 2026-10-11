---
name: exit-criteria
description: >
  Set and track the conditions under which the person handing over a platform
  leaves: every installed module has a named owner and a backup, every runbook
  was run by its new owner, the gate and the status page were operated without
  help for a set period, open decisions are recorded and access has moved,
  with the state and evidence of each written to docs/handover.md. Use when a
  handover needs an exit date that follows from evidence, or to check how
  close the handover is to done. Activates on "/exit-criteria", "when can I
  leave", "are we ready for the handover", "exit criteria", "handover status".
user-invocable: true
---

# Exit criteria

Writes the conditions for the exit of the person handing over into `docs/handover.md`, checks each one against evidence in the repository and its records, and sets the exit date to the first day all of them are met. A criterion without evidence stays `open`.

## Inputs

- `docs/handover.md` with the owners table (run `/handover:owner-training` first if it is missing).
- From the user: the person handing over and their git author names, the new owners, the start date of the handover, and the period of operation without help (default 30 days).

## Steps

1. **Copy the template** if the page is missing:

   ```bash
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md" docs/handover.md
   ```

2. **Agree the criteria and the period** with the user and the new owners. The defaults are the rows of the "Exit criteria" table in the template. Replace `<N>` with the period. A team can add criteria; removing one is a decision the user records as an ADR or in the page, with the reason.
3. **Collect the evidence for each criterion.** Keep each command and its output.

   | Criterion | Evidence |
   |---|---|
   | Owner and backup per installed module | The owners table; `python3 .github/actions/gate/run.py --only handover.module-owners` with the gate installed; owner and backup are two different people |
   | Every runbook run by its new owner | The runbooks from the runbooks index and from the `runbook_url` of each alert rule; for each, a date and a record (drill log, incident record, pull request) with the new owner as the person who ran it |
   | Gate operated without help | `gate/latest.json` history for the period; findings closed in the period and who closed them: `git log --since=<start of period> --format='%an %s' -- gate .github/actions/gate`; no commit by the person handing over on those paths in the period |
   | Status page operated without help | Incident records in the period and who updated them: `git log --since=<start of period> --format='%an %s' -- incidents`; no update by the person handing over |
   | Open decisions recorded | Open RFCs and proposed ADRs in `docs/decisions/index.md`; a list from the person handing over of decisions they carry that are not written down, each one turned into an RFC, an ADR or a ticket |
   | Access moved | A list of the systems (cloud accounts, domains and DNS, CI secrets, billing, admin roles in each tool, the on-call tool) with the admin of each; the user confirms every row |
   | Runs-without-me scenarios passed | The "Runs without me" log: each scenario has a row with "Help needed" set to none |

   A module that is not installed has no criterion. A criterion with no way to check it is `open` until the user names the evidence.
4. **Write the state.** In the "Exit criteria" table, set each criterion to `met` or `open` with its evidence. In the owners table, set "Exit criteria" per module to `met` when the module's owner, backup, runbooks and training are all met.
5. **Set the exit date.** All criteria `met`: the exit date is the date of the last one met. Any criterion `open`: write the earliest date it can be met, from the period and the next scenario run, and name the next action for each open criterion.
6. **Rerun** this skill after each training step, scenario run or access change, and before the planned exit date.

## Output

The "Exit criteria" table in `docs/handover.md` with state and evidence per criterion, the exit date, and a report: criteria met, criteria open with the next action and its owner.

## Rules

- A criterion is `met` only with evidence from the repository, a record or the user's written confirmation. Never mark one met on a promise.
- The exit date follows the evidence. While a criterion is open, the exit date moves.
- If the person handing over helps during the period, the period for that criterion starts again. Record what was asked.
- Write only `docs/handover.md`. Never overwrite an existing file with the template; update its rows and keep the rest. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/handover" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/handover/` exists, read its `README.md` first, then the files in `handover/exit-criteria/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
