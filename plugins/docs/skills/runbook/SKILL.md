---
name: runbook
description: >
  Write a runbook page for one symptom or procedure, from an incident, a chat
  or the user's notes: Symptom, Checks, Steps, Verify, Roll back or escalate,
  with owner and review dates, linked from the runbooks index. One runbook per
  symptom. Activates on "/runbook", "write a runbook", "turn this incident
  into a runbook", "document this fix", "add a runbook for".
user-invocable: true
---

# Runbook

Writes one runbook page in the docs tree of the current repository. A runbook covers one symptom: what you see, how to confirm it, the steps that fix it, how to verify the fix, and how to roll back or whom to call. The person who reads it is on call and under time pressure, so every step names the exact command.

## Inputs

- The symptom or procedure, in the user's words.
- The source: incident notes, a chat log, a postmortem, a ticket, shell history or the user's notes. Ask for it if the user gave none.
- The space (default `eng`) and the owner (a person or a team). Ask when they are not clear from the source.

## Steps

1. **Find the docs tree.** Read `docs/docs.json`. If it does not exist, tell the user to run `/docs:docs-init` first and stop. Note `review_interval_days` (90 by default).
2. **Find the runbooks index.** It is `docs/<space>/runbooks.md`. If it is missing, copy `${CLAUDE_PLUGIN_ROOT}/templates/docs/eng/runbooks.md` to that path with `cp -n`, fill its owner and dates, and change `doc:eng/` links to the space.
3. **One runbook per symptom.** Search the existing runbooks for the same symptom: `grep -rli '<key words of the symptom>' docs/<space>/`, and read the `## Symptom` sections of the children of `runbooks`. If one covers this symptom, show it to the user and propose to add the new checks or steps to that page. Write a second page only when the symptom differs: other error text, other alert, other component.
4. **Extract the facts from the source.** Write down, before you draft:
   - Symptom: the alert name, error text, failed job or user report, quoted exactly.
   - Checks: the commands or dashboards that confirmed it, and what they showed.
   - Steps: the actions that fixed it, in order, with exact commands.
   - Verify: the command or check that showed the fix worked, with its expected output.
   - Roll back or escalate: how to undo the steps, and who to contact when they do not clear the symptom.
   - The date and a link to the incident, ticket or chat, if there is one.
5. **Check the facts against the repository.** For every command, path, script, workflow or config the runbook names, confirm it exists: read the file, run `--help`, or list the folder. Run only commands that change nothing. Fix names that differ and tell the user. Ask the user for any fact the source does not give. Never invent a command, a path, a dashboard, a threshold or a contact.
6. **Write the page.** Start from `docs/_templates/runbook.md`, or from `${CLAUDE_PLUGIN_ROOT}/templates/docs/_templates/runbook.md` when the repository has no copy. Save it as `docs/<space>/runbook-<symptom-words>.md` (lowercase, a-z, 0-9 and -), and stop if that file exists. Fill it:
   - `title`: the symptom in a few words, as the person on call would describe it.
   - `summary`: one sentence with the symptom, the usual cause and the fix.
   - `parent: runbooks`, `type: how-to`, `labels: runbook, <system>`.
   - `order`: 10 more than the highest `order` among the other runbooks.
   - `owner`: from the inputs.
   - `reviewed`: today's date when the steps ran in the incident or you checked them in step 5; otherwise `no`.
   - `review_by`: `reviewed` plus `review_interval_days`; with `reviewed: no`, today plus `review_interval_days`.
   - The sections Symptom, Checks, Steps, Verify, Roll back or escalate, in that order. Numbered steps, one action each, commands in fenced code blocks. Remove every `<...>` placeholder.
7. **Link it from the index.** In `docs/<space>/runbooks.md`, add one row to the table: `| <what you see> | [<title>](doc:<space>/<slug>) |`, above the comment line.
8. **Build.** Run `python3 scripts/build_docs.py --check`. Fix every error it prints. If the repository has the gate with `docs.review`, run `python3 .github/actions/gate/run.py --dry-run --only docs.review`.

## Output

- One new page `docs/<space>/runbook-<slug>.md`, or a change to the existing runbook for the same symptom.
- One new row in `docs/<space>/runbooks.md`.
- A short report: the path, the facts taken from the source, the facts confirmed in the repository, the questions the user still needs to answer, and the build result.

## Rules

- One runbook per symptom. Extend the existing page before you write a second one.
- Never invent a command, path, threshold, dashboard or contact. Ask, or leave the step out and say so.
- No secrets in the page: no passwords, tokens, keys or private connection strings. Name the store that holds the secret and the name of the entry.
- Run only commands that change nothing while you check the facts.
- Never overwrite an existing file. Do not commit or push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/docs" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/docs/` exists, read its `README.md` first, then the files in `docs/runbook/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
