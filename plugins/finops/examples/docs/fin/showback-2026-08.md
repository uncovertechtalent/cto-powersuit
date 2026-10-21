---
title: Showback 2026-08 (synthetic sample)
summary: Cost per team for 2026-08 from tags and the allocation file, with unallocated cost as its own line, on two invented billing exports.
parent:
order: 30
labels: finops, showback, synthetic
owner: synthetic owner: head of engineering
reviewed: 2026-10-21
review_by: 2027-01-19
type: reference
cost_period: 2026-08-01/2026-08-31
cost_source: SYNTHETIC Synthetic Cloud billing export 2026-04 to 2026-09; SYNTHETIC Synthetic Hosting invoice export 2026-04 to 2026-09; allocation.json
---
**Synthetic sample.** The teams, the owners and every figure on this page are invented for the finops example in `plugins/finops/examples/`. No real bill was used.

This page splits the cost of 2026-08 across three teams, checkout, search and platform. August is the month in which the [cost baseline](doc:fin/cost-baseline) flags a spike on Synthetic Cloud Compute, so the page shows which team the spike lands on.

This page reports cost per team. No cost is booked to any team's budget. To charge teams for their cost, the teams and finance first agree on the rules, the split of shared cost and the way to dispute a line.

Every figure covers the period in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`.

## Allocation rules

The rules are in `finops/allocation.json`. The order of precedence is: shared costs first, then the rules from top to bottom, then the value of the `team` tag.

- Shared cost, split in proportion to each team's direct cost: the Synthetic Cloud support plan and the VAT on the Synthetic Hosting invoice.
- Rule: everything in the sub-account `acct-syn-dev` belongs to the platform team. The dev rows carry no `team` tag.
- Tag: every other row with a `team` tag goes to the team the tag names.
- A row that matches none of these stays unallocated.

## Cost per team

| Team | Owner | Direct | Shared | Total | Share |
|---|---|---|---|---|---|
| search | synthetic owner: search lead | EUR 6,740.00 | EUR 436.86 | EUR 7,176.86 | 55.9% |
| checkout | synthetic owner: checkout lead | EUR 3,360.00 | EUR 217.78 | EUR 3,577.78 | 27.9% |
| platform | synthetic owner: platform lead | EUR 1,630.00 | EUR 105.65 | EUR 1,735.65 | 13.5% |
| Unallocated |  |  |  | EUR 356.00 | 2.8% |
| Total |  |  |  | EUR 12,846.30 | 100.0% |

Reconciliation: teams plus unallocated minus total = EUR 0.00.

The search team carries 55.9% of the month. EUR 4,600.00 of its direct cost is the temporary load-test cluster behind the spike flag (line `SYN-C-0053`).

## Unallocated

| Provider | Service | Reason | Amount |
|---|---|---|---|
| Synthetic Cloud | Compute | no team tag and no rule | EUR 255.00 |
| Synthetic Cloud | Data Transfer | no team tag and no rule | EUR 101.00 |

Proposed fixes, largest first. Nothing is moved to a team to make the table look complete.

1. Compute, EUR 255.00: the line is "Compute, untagged instances" in the sub-account `acct-syn-prod`. The platform lead tags the instances with `team`, then the line moves to a team by itself.
2. Data Transfer, EUR 101.00: the line is "Data transfer, internet egress (untagged)". The checkout lead tags the load balancer that causes it, or the teams agree on a rule.

## Shared costs

| Shared cost | Amount | Split |
|---|---|---|
| Cloud support plan | EUR 500.00 | proportional |
| Hosting VAT | EUR 260.30 | proportional |

Proportional means in proportion to each team's direct cost of the month, so a month with a spike moves shared cost toward the team that caused it. A team may ask for an even split instead.

## Tag coverage

Cost with a `team` tag: EUR 11,290.00, 87.9% of the total in 2026-08. In the month before, EUR 6,635.00, 85.1% of EUR 7,794.30 (period 2026-07-01/2026-07-31, source: SYNTHETIC Synthetic Cloud billing export 2026-04 to 2026-09; SYNTHETIC Synthetic Hosting invoice export 2026-04 to 2026-09; allocation.json).

## Questions for the teams

- Search: is the load-test cluster (EUR 4,600.00) a cost the search team wants to carry, or does it belong to a shared test budget? Owner who answers: synthetic owner: search lead.
- Platform: its direct cost of EUR 1,630.00 is the dev sub-account (EUR 440.00) and the Synthetic Hosting servers (EUR 1,190.00). Does the dev environment belong to the platform team alone? Owner who answers: synthetic owner: platform lead.

## Method

The command runs from `plugins/finops/examples/`:

```bash
python3 ../templates/scripts/focus_export.py showback --alloc finops/allocation.json --month 2026-08 finops/focus/*.csv
```

The script output is in `outputs/showback-2026-08.md`.
