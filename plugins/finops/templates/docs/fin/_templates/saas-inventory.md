---
title: SaaS inventory
summary: <one sentence: every SaaS tool the organisation pays for, with owner, seats paid and used, overlaps and a keep, cut or replace decision>
parent: <slug of the parent page; leave empty for the space home>
order: 40
labels: finops, saas, vendors
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD, the day the list was checked against the sources, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
cost_period: <YYYY-MM/YYYY-MM, the months the costs on this page cover>
cost_source: <invoices, card statements, expense export and SSO app list, each with its date>
---
<Opening paragraph: the sources, the date of the audit and the next audit.>

The decisions on this page are proposals. The owner of each tool acts on them after they are agreed. Every figure covers the months in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`.

## Sources

| Source | What it lists | Date or months | Exported by |
|---|---|---|---|
| <invoices, card statements, expense export, SSO app list, admin console export> | <tools, charges, seats or sign-ins> | <YYYY-MM-DD or YYYY-MM to YYYY-MM> | <person> |

## Tools

| Tool | Job | Owner | Billing | Renewal | Notice by | Seats paid | Seats used | Cost per month | Decision |
|---|---|---|---|---|---|---|---|---|---|
| <tool> | <the job it does, for example chat or diagrams> | <person> | <monthly or annual; card or invoice> | <YYYY-MM-DD> | <YYYY-MM-DD> | <number> | <active users in the last 90 days, or unknown> | <amount with currency code> | <keep, cut or replace, with one line of reason> |

Seats used come from <SSO sign-ins or the tool's admin export, with the export date>. Unknown means no usage data, which is different from zero use.

## Overlaps

| Job | Tools | Proposal |
|---|---|---|
| <job> | <two or more tools that do it> | <which one stays, and the reason> |

## Replace options

| Tool | Option | Kind | Switching cost | Risk | Running cost |
|---|---|---|---|---|---|
| <tool> | <name or short description> | <open source, agent-built or other vendor> | <person-days to migrate, data export, retraining, exit terms> | <low, medium or high, and the reason> | <hosting and maintenance per month> |

## Actions

| Action | Tool | Who acts | By |
|---|---|---|---|
| <remove unused seats, cancel before the notice date, start a trial of the replacement> | <tool> | <owner> | <YYYY-MM-DD> |

## Not on this page

<Tools with no invoice and no sign-in record, personal subscriptions and free tiers, and the reason each is left out.>
