---
title: Cost baseline
summary: <one sentence: monthly cost per provider and service for the months in cost_period, and what the baseline is for>
parent: <slug of the parent page; leave empty for the space home>
order: 10
labels: finops, cost-baseline
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD, the day the figures were checked against the sources, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
cost_period: <YYYY-MM/YYYY-MM, the first and the last month in the tables>
cost_source: <every source behind the tables, for example the invoices and the cost export of each provider>
---
<Opening paragraph: the providers this baseline covers, the months, and what it is for, for example the budget for next year or a cost review.>

Every figure on this page covers the months in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`. Amounts stay in the currency the provider bills. A converted figure names the rate, the date of the rate and its source.

## Sources

| Source | Provider | Format | Months | Currency | Checked against |
|---|---|---|---|---|---|
| <file, export or invoice series> | <provider> | <FOCUS export, cost export CSV, invoice PDF or expense export> | <YYYY-MM to YYYY-MM> | <currency code> | <the invoice total or export total the converted rows match> |

## By provider

<The "By provider" table from `python3 scripts/focus_export.py baseline finops/focus/*.csv`: one row per provider and currency, one column per month.>

## By service

<The "By service" table from the same run.>

## Run rate

<Per provider: the monthly cost without one-off charges, as the median of the full months, with the months it is based on.>

## Flags

### Missing months

<Months without rows per provider, and the reason: invoice not received, no usage, or a provider that started or stopped within the range.>

### One-off charges

<Purchases, credits, adjustments and setup fees, with the month and the reason.>

### Spikes

<Service months above two times the median of their other months, with the cause when it is known.>

### Currency changes

<Providers billed in more than one currency, with the months per currency.>

## Method

<The commands that built the tables, the column maps in `finops/focus-maps/` and where the FOCUS files are kept.>

## Not in this baseline

<Costs left out and the reason: salaries, hardware, tools paid on personal cards, providers without data.>
