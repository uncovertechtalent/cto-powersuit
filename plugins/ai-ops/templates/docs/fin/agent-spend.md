---
title: Agent spend
summary: How the spend of coding agents is metered per API request, where to see it, and what happens when it passes the hourly budget.
labels: agents, finops, metering
owner: <who owns agent spend>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: explanation
cost_period: <YYYY-MM-DD/YYYY-MM-DD>
cost_source: Claude Code api_request events in Loki
---
Agent spend is metered per API request. Claude Code writes one `api_request` event per API call, with its cost, its model and its token counts. The observability stack stores the events in Loki; the dashboard and the alert sum them.

## Why events

Claude Code also exports cumulative cost and token counters. Several agent processes run at once on one machine and write the same counter series, so the series reads as a stream of counter resets and a sum over it is wrong. The per-request events carry each call once, including side calls such as compaction and web fetches.

## Where to see it

- Dashboard: Agent spend (`observability/grafana/specs/agent-spend.json`).
- Alert: `AgentSpendAboveBudget` fires when the spend of the last hour passes the hourly budget of <hourly budget in USD> for 15 minutes, and goes to the `platform` route as a ticket.

## Budget

| Period | Budget | Owner |
|---|---|---|
| Hour | <hourly budget> | <owner> |
| Month | <monthly budget> | <owner> |

## When the alert fires

1. Open the dashboard and find the model and the hour with the spend.
2. Find the sessions running at that time (`ps` on the machine, or the session list of the agent app).
3. Stop a session that loops. Ask its owner before stopping any other.
4. Record what happened in the ticket the alert opened.
