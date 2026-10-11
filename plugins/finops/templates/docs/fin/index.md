---
title: FinOps
summary: What the systems and tools cost, how the cost splits across teams and the cost per unit of work, with the period and the source of every figure.
labels: finops, cost
owner: <person or team that keeps this space true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This space holds the cost pages: the monthly cost baseline per provider and service, showback per team, unit costs, and the inventory of SaaS tools. The figures come from invoices and billing exports, converted to FOCUS (FinOps Open Cost and Usage Specification) columns, so every provider has the same columns.

## Pages

| Page | What it holds |
|---|---|
<!-- One row per page: a doc: link to the page, then one line on what it holds. -->

New pages start from the templates in `docs/fin/_templates/`.

## Period and source of every figure

Every cost figure names the period it covers and the source it comes from. A page whose figures share one period and one set of sources states both in its front matter:

```yaml
cost_period: 2026-07/2026-09     # months YYYY-MM/YYYY-MM, or days YYYY-MM-DD/YYYY-MM-DD
cost_source: <provider> invoices; <provider> cost export
```

A figure from another period or another source carries its own marker on the same line, for example `EUR 120.00 (period 2026-09-01/2026-09-30, source: <provider> invoice <number>)`. The gate rule `finops.cost-provenance` reports any line with an amount (a number next to €, $, £, EUR, USD or GBP) on a page that has neither. Code blocks and code spans are skipped.

Amounts stay in the currency the provider bills. A converted figure names the rate, the date of the rate and its source on the same line.

## Files

| Path | What it is |
|---|---|
| `finops/focus/` | FOCUS CSV files, one per source and period. They can hold account ids and line items: keep them out of a public repository. |
| `finops/focus-maps/` | One column map per billing format, for `scripts/focus_export.py convert` |
| `finops/allocation.json` | The allocation rules for showback |
| `finops/units/` | Monthly counts per unit, each with its source |
| `scripts/focus_export.py` | Converts billing files to FOCUS, checks them and writes the baseline, showback and unit cost tables |
