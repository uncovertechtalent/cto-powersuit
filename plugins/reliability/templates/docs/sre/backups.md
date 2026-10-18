---
title: Backups and restores
summary: Where the backup of each data store lives, who can delete it, whether a copy sits outside the reach of production administrators, and when a restore was last tested and how long it took.
order: 40
labels: backups, restore, reliability
owner: <person or team that keeps this inventory true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This inventory records, for each data store, what the team says about its backups. The gate rule `reliability.backup-inventory` reads this page. It does not read any cloud account, so a wrong entry passes until a restore test shows it. A restore test is the only evidence that a backup works.

## Policy

| Field | Value |
|---|---|
| Production administrators | <identities that can change or delete production resources: roles, groups, accounts, separated by commas> |

The gate rule warns when a restore test is older than its option `max_age_days`, 90 days by default. Each store has its own restore runbook, written from `docs/sre/_templates/restore-test.md`.

An out-of-reach copy is a copy that no production administrator can delete or overwrite with production credentials. The kinds, as they are written in the `Out-of-reach copy` field below:

- `separate-account`: the copy sits in an account, subscription, or project whose administrators are not the production administrators, and production roles have no delete permission on it.
- `immutable`: the copy is under object lock, a vault lock, or a retention lock that nobody can shorten or remove before the retention ends, the production administrators included.
- `offline`: the copy is on media or in a system that production credentials cannot reach.
- `none`: no such copy exists. Say so; the gate rule reports it.

## Data stores

One section per data store, with a level 3 heading. Copy the section below for each store. Keep the field names; the gate rule reads them. Write `never` in `Last restore test` when no restore was tested, and `YYYY-MM-DD` dates and durations such as `40 min` or `3 h` elsewhere.

### <store id, for example orders-database>

| Field | Value |
|---|---|
| Service | <catalogue id of the service that uses the store, or none> |
| Backup location | <service, account, region, and name of the main backup, for example managed snapshots in the production account> |
| Schedule | <how often, for example every 6 hours, plus point-in-time recovery> |
| Retention | <how long each backup is kept> |
| Data loss target | <the most recent data the business accepts to lose, for example 6 h; the schedule is at most this long> |
| Can delete or overwrite | <identities that can delete or overwrite the main backup> |
| Out-of-reach copy | <separate-account, immutable, offline, or none> |
| Out-of-reach location | <account, vault, or media, and the lock mode and period if any> |
| Out-of-reach deletable by | <identities that can delete or overwrite the out-of-reach copy, or nobody until retention ends> |
| Last restore test | <YYYY-MM-DD or never> |
| Restore result | <pass or fail> |
| Restore time measured | <duration from the start of the restore to a passed verification, for example 40 min> |
| Restore time target | <the longest the business accepts, for example 60 min> |
| Restore tested by | <person who ran the restore with the runbook> |
| Runbook | <doc:sre/runbook-restore-store-id> |

## Not backed up on purpose

A data store that has no backup is listed here with the reason. Anything not listed here and not above is unaccounted for.

| Store | Why losing it is acceptable | How it is rebuilt, and how long that takes |
|---|---|---|
| <store id> | <for example a cache that holds copies of data kept elsewhere> | <command or runbook, and minutes> |

## Restore test log

One row per restore test, newest first. The fields of the store above hold the latest row.

| Date | Store | Tested by | Backup restored | Result | Minutes | Gaps found | Tickets |
|---|---|---|---|---|---|---|---|
| <YYYY-MM-DD> | <store id> | <person> | <which backup: copy and timestamp> | <pass or fail> | <minutes> | <what was missing or wrong> | <ticket ids> |
