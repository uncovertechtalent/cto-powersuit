---
title: Backups and restores
summary: Fixture page for the check reliability.backup-inventory.
owner: Platform team
reviewed: 2026-10-12
review_by: 2027-01-10
type: reference
---
This page is a fixture.

## Policy

| Field | Value |
|---|---|
| Production administrators | platform-admin, prod-root (break-glass) |

## Data stores

### orders-database

| Field | Value |
|---|---|
| Service | none |
| Backup location | managed snapshots in the production account |
| Schedule | every 6 hours |
| Retention | 35 days |
| Data loss target | 6 h |
| Can delete or overwrite | platform-admin |
| Out-of-reach copy | separate-account |
| Out-of-reach location | vault in the backup account |
| Out-of-reach deletable by | backup-admin |
| Last restore test | 2025-06-02 |
| Restore result | pass |
| Restore time measured | 40 min |
| Restore time target | 60 min |
| Restore tested by | platform on-call |
| Runbook | doc:sre/runbook-restore-orders-database |

## Not backed up on purpose

| Store | Why losing it is acceptable | How it is rebuilt, and how long that takes |
|---|---|---|
| session-cache | Holds copies of data kept in the orders database | Redeploy the cache, 5 min |

## Restore test log

| Date | Store | Tested by | Backup restored | Result | Minutes | Gaps found | Tickets |
|---|---|---|---|---|---|---|---|
| 2026-10-12 | orders-database | platform on-call | vault copy of 2026-10-12 02:00Z | pass | 40 | none | none |
