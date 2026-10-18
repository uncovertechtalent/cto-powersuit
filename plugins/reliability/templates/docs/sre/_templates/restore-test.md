---
title: Restore <store id>
summary: How to restore <store id> from its out-of-reach copy into a test target, verify the data, and record the minutes.
parent: backups
order: 10
labels: runbook, backups, restore
owner: <person or team that owns the store>
reviewed: <YYYY-MM-DD, the day a person last ran these steps, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: how-to
---
<Opening paragraph: the store, what it holds, the service that uses it, and the restore time target from the inventory.>

The same steps serve a restore test and a real restore. A test restores into a target that holds no production traffic. A real restore changes the target and needs the go of the incident lead.

## Before you start

| Item | Value |
|---|---|
| Store | <store id, as in docs/sre/backups.md> |
| Backup to restore | <the out-of-reach copy: account, vault, or media, and how to pick the latest recovery point or a point in time; the main backup for a store that has no out-of-reach copy yet> |
| Restore target | <non-production account, cluster, or host, and its name; for a real restore, the replacement store> |
| Who runs it | <role; the person who runs the test is the person who would run the restore in an incident> |
| Access | <the role that reads the out-of-reach copy and how the person gets it, with the name of the secret store entry and the approval path. Count the minutes it takes to get access.> |
| Time target | <minutes from the inventory> |
| Production credentials | The restore uses no production administrator credentials. If a step needs them, the copy is not out of reach: write that down as a gap. |

## Steps

1. Write down the start time in UTC: `date -u +%H:%MZ`. The clock starts when the person starts the first action, access requests included.
2. <Find the backup to restore: command, and the check that the recovery point is the one you want.>
3. <Restore into the target: exact commands, one action per step.>
4. <Wait for the restore to finish and show its state: command and expected output.>
5. <Point the application or a test client at the target, when the verification needs it.>

## Verify

The restore is done when every check below passes, and the clock stops at the last one.

1. <Row or object counts per table or bucket against the source on the day of the backup: command and expected value.>
2. <A checksum or a sample of known records: command and expected value.>
3. <A request the service answers from the restored data: command and expected output.>
4. The newest record in the restored data has the time of the recovery point, within <the data loss the business accepts, in minutes>.

## Record

1. Write the stop time in UTC and the minutes from the first action to the last passed check.
2. In `docs/sre/backups.md`, set `Last restore test`, `Restore result`, `Restore time measured`, `Restore tested by` and, if the target changed, `Restore time target` for the store. Add a row to the restore test log.
3. If the minutes are above the target, the test fails on time: open a ticket to bring the restore under the target, or have the owner and the business agree a new target in writing.
4. Every gap becomes a ticket: a missing or wrong step, a page that was out of date, an access the person lacked, a check that did not exist. Write the ticket ids in the log row.

## Clean up

1. Delete the restored copy when the checks and the record are done. It holds production data: keep it only as long as the test needs it, and give it the same access rules as production while it exists.
2. Remove any temporary access you were given, and write in the log row that you did.

## Roll back or escalate

A real restore that goes wrong: stop, keep the failed target as it is, tell the incident lead, and start again from step 1 with the previous recovery point. If the out-of-reach copy cannot be read, escalate to <the owner of the account that holds it, with the contact in the paging tool>.
