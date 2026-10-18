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
| Last restore test | 2026-10-12 |
| Restore result | pass |
| Restore time measured | 40 min |
| Restore time target | 60 min |
| Restore tested by | platform on-call |
| Runbook | doc:sre/runbook-restore-orders-database |

### uploads-bucket

| Field | Value |
|---|---|
| Service | none |
| Backup location | managed snapshots in the production account |
| Schedule | every 6 hours |
| Retention | 35 days |
| Data loss target | 6 h |
| Can delete or overwrite | platform-admin |
| Out-of-reach copy | immutable |
| Out-of-reach location | object lock in compliance mode, 35 days |
| Out-of-reach deletable by | nobody until retention ends |
| Last restore test | 2026-09-20 |
| Restore result | pass |
| Restore time measured | 1.5 h |
| Restore time target | 2 h |
| Restore tested by | platform on-call |
| Runbook | doc:sre/runbook-restore-uploads-bucket |

### ledger-archive

| Field | Value |
|---|---|
| Service | none |
| Backup location | managed snapshots in the production account |
| Schedule | every 6 hours |
| Retention | 35 days |
| Data loss target | 6 h |
| Can delete or overwrite | platform-admin |
| Out-of-reach copy | offline, separate-account |
| Out-of-reach location | vault in the backup account |
| Out-of-reach deletable by | vault-custodian (two approvers) |
| Last restore test | 2026-10-12 |
| Restore result | pass |
| Restore time measured | 40 min |
| Restore time target | 60 min |
| Restore tested by | platform on-call |
| Runbook | doc:sre/runbook-restore-ledger-archive |

## Not backed up on purpose

| Store | Why losing it is acceptable | How it is rebuilt, and how long that takes |
|---|---|---|
| session-cache | Holds copies of data kept in the orders database | Redeploy the cache, 5 min |

## Restore test log

| Date | Store | Tested by | Backup restored | Result | Minutes | Gaps found | Tickets |
|---|---|---|---|---|---|---|---|
| 2026-10-12 | orders-database | platform on-call | vault copy of 2026-10-12 02:00Z | pass | 40 | none | none |
