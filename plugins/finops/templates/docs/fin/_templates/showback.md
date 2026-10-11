---
title: Showback <YYYY-MM>
summary: <one sentence: cost per team for the month, from tags and the allocation file, with unallocated cost as its own line>
parent: <slug of the parent page; leave empty for the space home>
order: 30
labels: finops, showback
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD, the day the figures were checked against the sources, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
cost_period: <YYYY-MM-DD/YYYY-MM-DD, the month this page covers>
cost_source: <the FOCUS files behind the tables>; finops/allocation.json
---
<Opening paragraph: the teams, the providers and the month this page covers.>

This page reports cost per team. No cost is booked to any team's budget. To charge teams for their cost, the teams and finance first agree on the rules, the split of shared cost and the way to dispute a line.

Every figure covers the period in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`.

## Allocation rules

<The order of precedence, the tag key that names the team, the rules and the shared costs with their split. The rules are in `finops/allocation.json`.>

## Cost per team

<The "Cost per team" tables from `python3 scripts/focus_export.py showback --alloc finops/allocation.json --month <YYYY-MM> finops/focus/*.csv`, one per currency. Unallocated cost is its own row.>

## Unallocated

<The unallocated lines by provider, service and reason, largest first, and the action for each: the tag to add and who adds it, or the rule to write.>

## Shared costs

<Each shared cost, its amount and its split.>

## Tag coverage

<The share of cost with a team tag this month and in the month before.>

## Questions for the teams

<Lines a team may dispute, with the owner who answers.>
