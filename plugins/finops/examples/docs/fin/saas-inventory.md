---
title: SaaS inventory (synthetic sample)
summary: Eight invented SaaS tools with owner, seats paid and used, one overlap and a keep, cut or replace proposal for each, from a synthetic billing export and SSO app list.
parent:
order: 40
labels: finops, saas, vendors, synthetic
owner: synthetic owner: head of operations
reviewed: 2026-10-21
review_by: 2027-01-19
type: reference
cost_period: 2025-10/2026-09
cost_source: SYNTHETIC SaaS billing export 2025-10 to 2026-09; SYNTHETIC SSO app export 2026-09-30; SYNTHETIC owners and terms list 2026-10-21
---
**Synthetic sample.** The vendors, the owners, the seat counts and every figure on this page are invented for the finops example in `plugins/finops/examples/`. No real bill, vendor account or sign-in record was used. The tool names start with "Synth" so that none of them can be taken for a real product.

This inventory joins three views of the sample organisation, which has 40 people: what is billed (the card and invoice export of the last 12 months), what is connected (the SSO app list of 2026-09-30) and who answers for each tool (the owners list). The audit ran on 2026-10-21; the next audit is due by 2027-01-19.

The decisions on this page are proposals. The owner of each tool acts on them after they are agreed. Every figure covers the months in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`.

Eight tools cost EUR 1,575.00 per month together (EUR 18,900.00 over the 12 months). Renewals in the next 90 days, until 2027-01-19, with their notice dates:

- SynthMeet renews on 2026-12-15; notice by 2026-11-15.
- SynthSign renews on 2027-01-10; notice by 2026-12-11.

Proposals: cut SynthCall (EUR 120.00 per month), replace SynthDiagram (EUR 150.00 per month) and SynthForms (EUR 45.00 per month). Together that is EUR 315.00 per month of current spend before the running cost of any replacement. Right-sizing SynthMeet and SynthDocs at their renewals saves EUR 88.00 per month.

## Sources

| Source | What it lists | Date or months | Exported by |
|---|---|---|---|
| `inputs/synthetic-saas-billing-2025-10-to-2026-09.csv` | 63 recurring charges from eight vendors, by card and by invoice | 2025-10 to 2026-09 | synthetic owner: finance |
| `inputs/synthetic-sso-app-export-2026-09-30.csv` | eight connected apps, with users assigned and distinct users active in the last 90 days (counts only) | 2026-09-30 | synthetic owner: IT lead |
| `inputs/synthetic-saas-owners-and-terms.csv` | owner, renewal date and notice days per tool | 2026-10-21 | synthetic owner: head of operations |

Vendor names are normalised: SynthChat is billed as `SYNTHCHAT*SUBSCR` until 2026-02 and as `SynthChat Ltd` from 2026-03, and the page treats both as one tool.

## Tools

| Tool | Job | Owner | Billing | Renewal | Notice by | Seats paid | Seats used | Cost per month | Decision |
|---|---|---|---|---|---|---|---|---|---|
| SynthChat | chat | synthetic owner: IT lead | monthly, card | monthly on the 5th | any time; ends at the next cycle | 40 | 37 | EUR 320.00 | Keep: owned, used, no overlap. |
| SynthMeet | video calls | synthetic owner: IT lead | annual, invoice | 2026-12-15 | 2026-11-15 | 40 | 34 | EUR 280.00 (EUR 3,360.00 per year) | Keep: owned, used. Right-size at renewal from 40 to 36 seats: 4 seats at EUR 7.00, EUR 28.00 per month. |
| SynthCall | video calls | none after asking | monthly, card | monthly on the 5th | any time; ends at the next cycle | 15 | 2 | EUR 120.00 | Cut: no owner, 2 of 15 seats used, and SynthMeet does the same job. |
| SynthDocs | documents | synthetic owner: head of operations | annual, invoice | 2027-02-01 | 2026-12-03 | 40 | 31 | EUR 400.00 (EUR 4,800.00 per year) | Keep: owned, used. Right-size at renewal from 40 to 34 seats: 6 seats at EUR 10.00, EUR 60.00 per month. |
| SynthDiagram | diagrams | synthetic owner: engineering lead | monthly, card | monthly on the 5th | any time; plan minimum 25 seats | 25 | 4 | EUR 150.00 | Replace: 4 of 25 seats used, and the plan minimum of 25 seats rules out right-sizing. Options below. |
| SynthForms | forms | synthetic owner: marketing lead | monthly, card | monthly on the 5th | any time; ends at the next cycle | flat plan | 3 | EUR 45.00 | Replace: a flat plan for 3 active users on a simple job. Options below. |
| SynthSign | e-signature | synthetic owner: office manager | annual, invoice | 2027-01-10 | 2026-12-11 | 5 | 3 | EUR 60.00 (EUR 720.00 per year) | Keep: owned, used, no overlap. A signature tool carries compliance duties, so a replacement is high risk for a small saving. |
| SynthTickets | tickets | synthetic owner: engineering lead | monthly, invoice | monthly on the 5th | Check before use: notice period and auto-renewal terms in the contract | 20 | unknown | EUR 200.00 | Keep for now: billed with no SSO app, so use is unknown, which is different from zero. The owner sends an admin export. |

Seats used are the distinct users active in the last 90 days, from the SSO app export of 2026-09-30. SynthTickets has no SSO app, so its seats used are unknown. Cost per month is the monthly charge for a monthly plan and the annual charge divided by 12 for an annual plan. Renewal and notice dates come from the owners and terms list; notice by is the renewal date minus the notice days.

## Overlaps

| Job | Tools | Proposal |
|---|---|---|
| video calls | SynthMeet, SynthCall | SynthMeet stays: it has an owner and 34 of 40 seats in use. SynthCall goes: it has no owner and 2 of 15 seats in use. |

No other job has more than one paid tool.

## Replace options

The options are generic on purpose: a sample names no real product. Switching and running costs are sample estimates, not quotes.

| Tool | Option | Kind | Switching cost | Risk | Running cost |
|---|---|---|---|---|---|
| SynthDiagram | self-hosted diagram editor | open source | 3 person-days: export the diagrams as files, import them, re-share the links | low: the files export cleanly; the team patches the server | about EUR 10.00 hosting and 1 hour of maintenance per month |
| SynthDiagram | diagrams as code in the docs repository | agent-built | 5 person-days to convert the existing diagrams | medium: one person understands the build, and non-engineers have no visual editor | EUR 0.00 hosting and 1 hour of maintenance per month |
| SynthDiagram | another vendor with no seat minimum | other vendor | 1 person-day; no exit fee on a monthly plan | low: same job; check the contract terms of the new vendor | about EUR 32.00 per month for 4 seats at EUR 8.00 |
| SynthForms | self-hosted form builder | open source | 3 person-days | medium: form data now sits on the team's server, so the team carries the privacy duties and the spam handling | about EUR 10.00 hosting and 2 hours of maintenance per month |
| SynthForms | small form handler that writes to a shared mailbox | agent-built | 2 person-days | medium: one person understands it, and there is no spam filter at first | EUR 0.00 hosting and 1 hour of maintenance per month |
| SynthForms | another vendor, free tier | other vendor | 0.5 person-days | low to medium: the free tier limits the number of forms, and a data processing agreement is needed | EUR 0.00 |

## Actions

| Action | Tool | Who acts | By |
|---|---|---|---|
| Confirm that nobody uses SynthCall for a call that SynthMeet cannot host, then cancel before the charge on 2026-11-05 | SynthCall | synthetic owner: IT lead | 2026-11-04 |
| Send notice to cut the plan from 40 to 36 seats at renewal | SynthMeet | synthetic owner: IT lead | 2026-11-14 |
| Send notice to cut the plan from 40 to 34 seats at renewal | SynthDocs | synthetic owner: head of operations | 2026-12-02 |
| Confirm the renewal on 2027-01-10 | SynthSign | synthetic owner: office manager | 2026-12-10 |
| Send the admin export of active users in the last 90 days, and read the contract for the notice period | SynthTickets | synthetic owner: engineering lead | 2026-11-06 |
| Choose a replacement and start a trial; cancel only after the data export is checked | SynthDiagram | synthetic owner: engineering lead | 2026-11-20 |
| Choose a replacement and start a trial; cancel only after the data export is checked | SynthForms | synthetic owner: marketing lead | 2026-11-20 |

## Not on this page

- SynthPoll: connected in the SSO app list (12 users assigned, 9 active in the last 90 days) with no charge in the billing export. It looks like a free tier or a trial. The owner is not named yet; ask for it and for the data processing terms.
- Personal subscriptions and tools paid on personal cards: none are known in the sample.
