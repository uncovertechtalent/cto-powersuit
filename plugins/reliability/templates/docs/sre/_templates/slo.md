---
title: SLO <service name>
summary: <one sentence: the indicator, the target and the window of the service>
parent: <slug of the parent page; leave empty for the space home>
order: 20
labels: slo, reliability
owner: <person or team that owns the service>
reviewed: <YYYY-MM-DD, the day the SLO was checked against the data, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
<Opening paragraph: the service, its users, and the user journey this SLO covers.>

## Indicator

| Field | Value |
|---|---|
| Service | <catalogue id; the entry is services/id.yml> |
| Valid events | <the events that count, for example HTTP requests to the public endpoints, health checks left out> |
| Good events | <the valid events that count as good, for example a status below 500 within 1 s> |
| Measured at | <where the events are counted: load balancer logs, the client, a synthetic probe> |
| Query for good events | `<query>` |
| Query for valid events | `<query>` |

SLI = good events / valid events, over the window.

## Target and window

| Target | Window | Error budget | Error budget at <expected valid events per window> events |
|---|---|---|---|
| <target>% | <30 days, rolling> | <100 minus the target>% of valid events | <number of failed events allowed> |

During a full outage every event fails, so the budget can also be stated as time: see the downtime table of the `nines-per-service` skill. The target does not exceed the dependency ceiling that `python3 scripts/build_status.py --check` prints for the service.

## Burn-rate alerts

The burn rate is the speed at which the service uses its error budget. At rate 1 the budget lasts exactly one window. Each alert fires when both its long and its short window burn faster than the threshold. With the short window, the alert ends soon after recovery.

| Alert | Long window | Short window | Burn rate | Budget used when it fires | Action |
|---|---|---|---|---|---|
| Fast burn | 1 h | 5 min | 14.4 | 2% | Page |
| Slow burn | 6 h | 30 min | 6 | 5% | Page |
| Drift | 3 d | 6 h | 1 | 10% | Ticket |

For a 30-day window (720 h), burn rate = budget used × window / long window: 0.02 × 720 / 1 = 14.4, 0.05 × 720 / 6 = 6, 0.10 × 720 / 72 = 1. For another window, compute again with the same formula.

```yaml
# <rules file>, one rule per row of the table; this is the fast burn
- alert: <ServiceName>ErrorBudgetFastBurn
  expr: |
    (1 - sum(rate(<good events>[1h])) / sum(rate(<valid events>[1h]))) > (14.4 * (1 - <target as a fraction>))
    and
    (1 - sum(rate(<good events>[5m])) / sum(rate(<valid events>[5m]))) > (14.4 * (1 - <target as a fraction>))
  labels:
    severity: page
  annotations:
    summary: <service name> burns its error budget at 14.4 times the rate that lasts one window
    runbook_url: <link to the runbook for this symptom>
```

## Error budget policy

| Budget left in the window | What changes |
|---|---|
| More than 50% | Releases go out as usual. |
| 50% or less | <slower rollouts, longer canary time, no risky migrations> |
| Spent | <only fixes and reliability work go out until the budget is above zero again> |

- Decision makers: <the owner of the service, with the product owner>.
- Exceptions: <security fixes, legal deadlines>.
- An incident that uses more than <share>% of the budget gets a postmortem.
- Review of the SLO: <every quarter, with the product owner>. An SLO nobody acts on is removed.

## History

| Window | SLI | Budget left | Notes |
|---|---|---|---|
| <YYYY-MM-DD to YYYY-MM-DD> | <measured SLI>% | <budget left>% | <incidents and releases that used the budget> |
