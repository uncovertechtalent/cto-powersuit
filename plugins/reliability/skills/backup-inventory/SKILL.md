---
name: backup-inventory
description: >
  Walk a team through a backup inventory, one data store at a time: where the
  backup lives, the schedule and retention, which identities can delete or
  overwrite it, whether a copy sits outside the reach of production
  administrators, the date and result of the last restore test, and the
  measured restore time against its target. Writes docs/sre/backups.md and a
  restore-test runbook per store. Use when nobody can say where the backups
  are, who can delete them, or when a restore was last tried. Activates on
  "/backup-inventory", "backup inventory", "where do our backups live", "who
  can delete our backups", "can we restore", "restore test", "backup audit",
  "ransomware backups".
user-invocable: true
---

# Backup inventory

Writes the backup inventory in `docs/sre/backups.md`: one section per data store, with the fields the gate rule `reliability.backup-inventory` reads. A backup that the production administrators can delete protects against a failed disk and fails against an intruder who holds their access. A backup that nobody restored is a claim. The inventory makes both visible, and the restore-test runbook gives the team the steps to turn the claim into evidence.

The skill records what the team says and tests nothing in the cloud account. It runs no cloud command, restores nothing, and deletes nothing. An entry stays a claim until a person runs the restore with the runbook and logs the result.

## Inputs

- **Data stores in scope**: default every store that holds data the company cannot recreate from code, and the things a restore depends on (see step 2).
- **Production administrators**: the roles, groups, or accounts that can change or delete production resources. The skill uses these names to compare against who can delete the out-of-reach copy.
- **Restore time target and data loss target** per store, from the service owner. Take them from `services/<id>.yml` or the SLO page when they exist there.
- **Restore tests already run**: dates, results, and minutes, with who ran them. Ask for the record. A date without a record stays a claim and is written as one.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/sre
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/" docs/sre/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/." docs/sre/`. If `docs/sre/index.md` was new, fill its `owner`, `reviewed`, `review_by` and the tier table. If `docs/docs.json` exists and lists no space with the key `sre`, show this entry and add it after the user agrees:

   ```json
   {"key": "sre", "name": "Reliability", "about": "SLOs, on-call, backups and postmortems for the services in the catalogue.", "owner": ""}
   ```

2. **List the data stores.** Read, without changing anything: `services/*.yml` (databases and entries with `lifecycle: external`), infrastructure code (databases, buckets, volumes, queues with state, search indexes, key-value stores), compose files and Kubernetes manifests (volumes, persistent volume claims, stateful sets), and the migrations folder. Add what a restore depends on, because a restore fails without it:
   - The keys that decrypt the backups. A backup under a key that a production administrator can schedule for deletion is lost with the key.
   - The infrastructure code and its state, and the secret store.
   - The source repositories and the CI configuration, when they live in one hosted account.

   Show the list to the user. Ask what lives outside the repository: hosted databases, SaaS tools that hold company data, file shares. The user confirms or corrects the list. A store that can be rebuilt from code or from another store goes under "Not backed up on purpose" with the reason and the minutes to rebuild. Anything else gets a section.
3. **Ask the production administrators** once, and write them in the Policy table. Use the same spelling in every later answer, so the comparison works.
4. **Walk through each store**, one at a time, and fill its table. Ask for the answer and for the place it comes from (a console page, a policy, a ticket). A field the team cannot answer stays a placeholder, and the report lists it as a question for the owner. Never fill a field from a guess.

   | Field | Question |
   |---|---|
   | Backup location, Schedule, Retention | Where does the main backup live (service, account, region, name), how often does it run, and how long is each backup kept? |
   | Data loss target | What is the most recent data the business accepts to lose? Compare it with the schedule. A schedule longer than the target is a gap for the report. |
   | Can delete or overwrite | Which identities can delete or overwrite the main backup? |
   | Out-of-reach copy | Is there a copy that no production administrator can delete or overwrite with production credentials? Use the kinds on the page: `separate-account`, `immutable`, `offline`, or `none`. |
   | Out-of-reach location, Out-of-reach deletable by | Where is that copy, under which lock or account, and which identities can delete or overwrite it? |
   | Last restore test, Restore result, Restore time measured, Restore tested by | When did a person last restore this store from a backup, did the verification pass, how many minutes passed from the first action to the passed check, and who ran it? `never` when it was not tested. |
   | Restore time target | What is the longest restore the business accepts? |

   For the out-of-reach copy, ask these four questions and record `none` when any answer is yes, because the copy is then within reach:
   - Can a production administrator, with production credentials only, delete or overwrite the copy?
   - Can they shorten its retention or remove its lock?
   - Can they delete the account, subscription, or project that holds it, or change who administers it?
   - Can they schedule the key that encrypts it for deletion?

   To read the answers from the account, the user can run read-only commands and paste the output. For an AWS account: `aws s3api get-object-lock-configuration --bucket <bucket>`, `aws backup describe-backup-vault --backup-vault-name <vault>`, and `aws backup get-backup-vault-access-policy --backup-vault-name <vault>`. The skill does not run them. For another provider, ask the user to name the page or command that shows the lock and the access policy.
5. **Write the page.** Fill `docs/sre/backups.md`: front matter with `reviewed` today and `review_by` 90 days later, the Policy table, one section per store, the "Not backed up on purpose" table, and the restore test log. Add a log row for each restore test the user gave a record for. Replace every `<placeholder>` that has an answer; leave the others. Add the page to the table in `docs/sre/index.md`.
6. **Write the restore-test runbooks.** For each store with no restore test, a failed test, a stale test, or a measured time above target, offer a runbook at `docs/sre/runbook-restore-<store id>.md`, started from `docs/sre/_templates/restore-test.md`. Fill it from the facts the user gave and from the repository. Check every path and script the page names against the repository: read the file or run `--help`. Run no cloud command. Never invent a command: leave the step as a placeholder and say so. Set `reviewed: no` until a person has run the steps. Set the store's `Runbook` row to its `doc:sre/runbook-restore-<store id>` link. With the user's agreement, add the same link to the `runbooks` list in `services/<id>.yml` of the service that uses the store. Change no other field without asking.
7. **Log a restore test** when the user reports one. The person who ran it gives the date, the backup restored, the minutes, and the gaps. Update the store's fields and add a row to the restore test log. A failed test, or minutes above the target, gets a ticket for each gap. With the `sdlc` module use `/sdlc:ticket`; otherwise give the ticket text: the store, the gap, the page to fix, and the acceptance criterion "the next restore test of this store passes within its target".
8. **Check.** With the `docs` module, run `python3 scripts/build_docs.py --check`. If the gate runs the rule, run `python3 .github/actions/gate/run.py --only reliability.backup-inventory --dry-run`. If the gate does not run it, point to the module README for the install steps and the `warn` tier it starts on.
9. **Report.**

## Output

The page path, a table with one row per store (out-of-reach copy kind, last restore test, result, measured minutes against the target), the gaps in this order (no copy outside production admin reach, no restore test, failed restore test, measured time above the target, restore test older than the interval, schedule longer than the data loss target), the fields still open with the person to ask, the runbooks written, the tickets proposed, and the gate result if it ran.

## Rules

- The skill records the claim and tests nothing in the cloud account. It never runs a cloud command, restores a backup, or deletes a copy. The gate rule reads the page, so a wrong entry passes until a restore test shows it.
- A copy that a production administrator can delete, shorten, unlock, or reach through the account or the key is recorded as `none` in `Out-of-reach copy`.
- Never write a restore test that did not happen, and never fill a date, a result, or a duration from memory or from a guess. The person who ran the test supplies them, with the record.
- A restore test restores into a target that holds no production traffic, from the out-of-reach copy where one exists, and the restored copy is deleted after the checks.
- No secrets in the pages: names of roles, vaults, and accounts, never keys, passwords, or tokens.
- Never overwrite an existing file. Never push, deploy, or change production.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/backup-inventory/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
