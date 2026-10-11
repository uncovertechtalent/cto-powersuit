---
name: run-record
description: >
  Read the deploy gate's run records and report: the last result, why a deploy
  was blocked and the shortest fix, open and closed findings, what changed
  between two runs, and whether the weekly run still happens. Can also write a
  manual run record. Activates on "/run-record", "why did the gate block",
  "gate status", "what did the gate find", "record a gate run".
user-invocable: true
---

# Run record

Reports on the gate in the current repository from the files the runner writes. Read only, except step 6.

## Where the records are

| File | What it holds |
|---|---|
| `gate/latest.json` | The last 100 runs (time, trigger, commit, overall, open findings) and every finding with its status, in git |
| `gate/summary.md` | The last run as a table, open and recently closed findings, recent history |
| `gate/runs/<timestamp>-<id>.json` | One full record per run: each check's result, detail, evidence and hits, and the sha256 of `run.py`, the config and every rule file. Local runs keep it here; CI runs upload it as the artifact `gate-run-<run id>-<attempt>` for 90 days |

Fetch a CI record with `gh run download <run id> -n gate-run-<run id>-<attempt> -D gate/runs/`.

## Steps

1. **State the current result.** From `gate/latest.json`: last run time, trigger, commit, overall, open findings split by tier.
2. **Blocked deploy.** If the last overall is `fail`, list each failing `block`-tier check with its hits (file, line, snippet) and the fix the rule implies. Then give the shortest loop: fix, run `python3 .github/actions/gate/run.py --dry-run --exit-code`, push when it exits 0.
3. **Findings.** Open findings with the date opened and the number of runs that saw them; flag any open longer than 14 days. Closed findings since the date the user names (default: the last 7 days) with the commit that closed them. A finding closes only when a later run of its rule no longer sees the hit, so a closed finding has a commit to show.
4. **Compare two runs** when a result changed. Load both records and compare `components`: if the sha256 of `run.py`, the config or a rule file differs, the rules changed; if all match, the content changed. Name which one, and the files involved.
5. **Schedule.** Read `gate.schedule` in the last record. If no scheduled run happened within the interval, check that the workflow still has its `schedule` trigger and that GitHub has not disabled it. GitHub disables scheduled workflows in a public repository after 60 days without activity; re-enable the workflow on the Actions tab.
6. **Manual record** (only when the user asks): `python3 .github/actions/gate/run.py --trigger manual` writes a run record, `latest.json` and `summary.md`. Show the summary line. Commit `gate/latest.json` and `gate/summary.md` when the user says so.

## Output

A short report in this order: current state, what blocks (if anything) and the fix, findings opened and closed in the period, rule or content changes, schedule health. Quote file paths, rule ids and finding ids exactly.

## Rules

- Report what the records show. If a record is missing (artifact expired, run never committed), say so and name the gap.
- Never edit `gate/latest.json` or a run record by hand. A finding closes only through a run.
- Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/gate" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/gate/` exists, read its `README.md` first, then the files in `gate/run-record/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
