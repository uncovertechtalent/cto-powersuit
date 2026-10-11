---
title: Unit costs
summary: <one sentence: cost per unit per month for the units on this page, with the trend>
parent: <slug of the parent page; leave empty for the space home>
order: 20
labels: finops, unit-costs
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD, the day the figures were checked against the sources, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: explanation
cost_period: <YYYY-MM/YYYY-MM, the first and the last month in the tables>
cost_source: <the FOCUS files behind the cost baseline>; <metric name and the system it comes from>
---
<Opening paragraph: the units on this page, why the team picked them, and who reads the figures.>

A unit cost is the cost of a month divided by the number of units in the same month. The cost comes from the [cost baseline](doc:fin/cost-baseline). The count comes from a named metric with its source. Both use calendar months in UTC.

Every figure covers the months in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`.

## Units

| Unit | Metric | Source of the count | Owner of the metric | Cost in the numerator |
|---|---|---|---|---|
| <one request, one customer, one deploy> | <metric or query name> | <system, dashboard or table, with the exact query> | <person or team> | <all cost, or the providers, services or tags included> |

## Cost per <unit>

<The table from `python3 scripts/focus_export.py unit --counts finops/units/<unit>.csv --unit <unit> finops/focus/*.csv`.>

## What moved the figure

<For each month with a change above 10%: the change in cost, the change in count, and the cause, for example a one-off charge from the baseline flags, a price change or a change in traffic.>

## Limits

<What the unit leaves out, months with partial data, and changes in the way the count is measured. A new counting rule starts a new series.>
