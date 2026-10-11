---
name: incident
description: >
  Run an incident from declaration to close: set the severity and the roles
  (incident lead, comms, operations), keep a timestamped log, post public
  updates to the incident records and the status page, resolve and close it,
  and hand over to the postmortem skill. Use when users see errors, slowness or
  wrong data, when an alert pages on a user-facing symptom, or when someone
  asks whether this is an incident. Activates on "/incident", "declare an
  incident", "we have an incident", "is this an incident", "site is down",
  "start incident", "update the status page", "resolve the incident".
user-invocable: true
---

# Incident

Runs one incident in the current repository. The internal log holds every fact, decision and action with its UTC time. The public record in `incidents/incidents.json` holds the updates users see, and `scripts/build_status.py` turns it into the status page. The skill prepares every file and command. The user publishes: the skill never pushes and never deploys.

## Inputs

- **What is seen** (required): the alert, the error, the user report, with the time it was first seen.
- **Services**: the catalogue ids users see failing.
- **People**: who is available for the three roles.
- **Log location**: default `incidents/log/<id>.md`. The internal log can hold internal names and details: ask whether the repository is public, and keep the log elsewhere if it is.

## Severity

| Severity | User impact | Response |
|---|---|---|
| sev1 | A tier 1 service is down for most users, data is lost or exposed, or a security breach is in progress | All three roles staffed at once; updates every 30 minutes |
| sev2 | A tier 1 service is degraded for many users, or a tier 2 service is down | Incident lead and operations at once; updates every 60 minutes |
| sev3 | Few users affected, or a tier 2 or tier 3 service is degraded, with a workaround | On call handles it; updates at each stage change |
| sev4 | No user impact yet; a risk to fix within hours | On call handles it; no status page entry |

The incident lead sets the severity and may change it at any time. The `impact` field on the status page (none, minor, major, critical) describes what users see and is set on its own.

## Roles

- **Incident lead**: coordinates, decides, sets the severity, keeps the log, and calls for help. In sev1 and sev2 the lead does not debug.
- **Comms**: writes the public updates and the internal updates on the cadence above.
- **Operations**: diagnoses and fixes. Several people can work in operations, with one of them leading it.

In a team of one or two, the incident lead also takes comms. Write down who holds which role, and every handover of a role, in the log.

## Steps

1. **Declare.** Pick the id `YYYY-MM-DD-short-name` (the start date and two to five words). Set the severity and the roles. Copy the records without overwriting, if they are missing:

   ```bash
   mkdir -p incidents/log scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/incidents/" incidents/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/build_status.py" scripts/
   ```

2. **Start the log.** One line per entry, UTC time from `date -u +%H:%MZ`:

   ```text
   # <id>
   Severity: <sev>. Incident lead: <name>. Comms: <name>. Operations: <names>.
   08:19Z declared: <what is seen>, first seen 08:12Z (<alert or report>)
   08:25Z action: <command or change>, result: <what happened>
   08:31Z decision: <what was decided, by whom>
   ```

   Log facts, decisions, actions with their result, and the commands run. A time comes from a record or the clock at the moment of writing.
3. **Post the first public update.** For sev1 to sev3, append the incident to `incidents/incidents.json` with `started`, `services`, `impact`, `severity`, a one-line `title`, a `summary`, and one update with stage `investigating`. Then build and show the result:

   ```bash
   python3 scripts/build_status.py --out <status page folder>
   ```

   The script validates the records and writes nothing when a record is wrong. Hand the change to the user to publish through the usual deploy.
4. **Mitigate first.** Look up the runbooks in `services/<id>.yml`. Prefer actions that stop the user impact: roll back the last change, fail over, turn off a feature flag, add capacity. The root cause can wait for the postmortem. Log each action and its result.
5. **Update on stage changes and on the cadence.** Stages only go forward: investigating, identified, monitoring, resolved. A stage can repeat. Each public update says what users see, what the team does, and when the next update comes. It names no person and no internal host, address or customer.
6. **Resolve.** When the SLI is back to normal and stays there for the monitoring period (default 15 minutes), append a `resolved` update and set `resolved` to its time. Build the status page again and hand the change to the user.
7. **Close.** Write the close entry in the log: duration, peak impact, mitigation, open risks. Collect the material for the postmortem: the log, alert and deploy history, graphs of the SLI, the queries for users and requests affected.
8. **Hand over to `postmortem`.** Required for sev1 and sev2, and for an incident that used more error budget than the limit in the SLO policy. The draft is due within five working days of the close. Name the author.
9. **Report.**

## Output

The incident id, the severity and roles, the log path, the public updates as posted, the status page build result, the duration, and the postmortem owner and due date.

## Rules

- One incident lead at any time. A handover of the lead is a log entry.
- Times are UTC. A clock time appears only with a record behind it; a date alone means the time was not recorded.
- Public text is blameless and holds no internal host names, addresses, customer names or personal details.
- The skill never pushes, deploys, rolls back or changes production by itself. It proposes the action, and a person in the operations role runs it.
- `incidents/incidents.json` passes `python3 scripts/build_status.py --check` before every publish.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/incident/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
