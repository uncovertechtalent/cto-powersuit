---
name: postmortem
description: >
  Write a blameless postmortem for one incident: summary, impact in minutes,
  users and requests, a timeline with a source for every time, contributing
  factors as mechanisms, what went well and what went poorly, and action items
  with one owner and a due date each, linked from the incident record. Use when
  a sev1 or sev2 incident is closed, when an incident used a large share of the
  error budget, or when the same problem comes back. Activates on "/postmortem",
  "write the postmortem", "incident review", "post-incident review", "retro for
  the outage", "blameless review".
user-invocable: true
---

# Postmortem

Writes one postmortem page per incident in `docs/sre/postmortem-<incident id>.md` and links it from the incident record. The page describes what the systems did and what information people had at each point. It names people only as owners of action items. Every number and every time comes from a record.

## Inputs

- **Incident id** (required): from `incidents/incidents.json`.
- **Records**: the incident log, alert history, deploy and change history, graphs of the SLI, chat transcripts.
- **People**: the incident lead and the people in the roles. Ask the user who can answer questions.
- **Author**: default the incident lead.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/sre
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/" docs/sre/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/." docs/sre/`.
2. **Build the timeline.** From the log and the records, list every event with its UTC time and its source: the change or condition that started it, the first alert or report, the declaration, each mitigation step, recovery. A time with no record behind it stays a date or is marked as an estimate. Compute the time to detect (start to first alert) and the time to mitigate (start to the end of user impact).
3. **Measure the impact.** Minutes of user impact, users affected, requests failed and their share of valid requests, error budget used, data lost or wrong. Run the queries, or ask the owner of the data to run them, and record each query next to its number. An unknown figure stays "unknown".
4. **Find the contributing factors.** For each phase ask what made the incident possible, what made it last, and what made it larger: the change, the detection, the diagnosis, the mitigation, the process. Write each factor as a mechanism: a system, a signal, a tool or a process. Where the records show a person's action, ask what made that action look right at the time: the signal they saw, the tool they used, the instructions they had. An incident usually has several factors.
5. **List what went well and what went poorly.** Detection, response, communication, tooling. State each point as a fact.
6. **Write the action items.** Each item is one change, specific enough to close, traced to a factor. Kind: prevent, detect, mitigate or process. One named owner, a due date, a ticket link. Prefer a few items that close to a long list that stays open. An item like "be more careful" is no action item: turn it into the change in the system that removes the need.
7. **Write the page.** Start from `docs/sre/_templates/postmortem.md`. Fill the front matter: `incident`, `severity`, `date`, `owner`, `reviewed: no` until the review, `review_by` the due date of the last open action item. Replace every `<placeholder>`.
8. **Check the language.** Search the draft for names outside the action item table and for blame words:

   ```bash
   grep -niE 'should have|failed to|forgot|careless|human error|mistake|blame|fault' docs/sre/postmortem-<incident id>.md
   ```

   Rewrite each hit as a mechanism. Show the draft to the user.
9. **Hold the review.** The people involved read the draft and correct facts. Set `reviewed` to the date of the review.
10. **Link it.** In `incidents/incidents.json`, set `"postmortem": "doc:sre/postmortem-<incident id>"` on the incident and run `python3 scripts/build_status.py --check`. Add the page to the table in `docs/sre/index.md`. If the incident showed a symptom with no runbook, write one (the `docs` module has a `runbook` skill) and add it to `runbooks` in the catalogue entry of the service.
11. **Check.** With the `docs` module, run `python3 scripts/build_docs.py --check`.
12. **Report.**

## Output

The page path, the impact figures with their queries, the timeline, the contributing factors, the action items with owners and due dates, and the links added to the incident record and the catalogue.

## Rules

- Blameless: the page describes conditions and mechanisms. People appear only as owners of action items.
- Every number and every time has a source. Unknown stays unknown.
- Every action item has one named person as owner, a due date and a ticket. "The team" is no owner.
- The draft is due within five working days of the close. Memory of the details fades fast.
- The owner of the page checks the action items at `review_by` and moves the date until the last item is done.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/postmortem/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
