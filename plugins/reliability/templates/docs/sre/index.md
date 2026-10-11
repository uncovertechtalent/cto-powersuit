---
title: Reliability
summary: How reliable each service must be, how the team measures it, and how incidents run from the first page to the postmortem.
labels: reliability, sre, slo, incidents
owner: <person or team that keeps this space true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This space holds the reliability pages: the SLO of each service, the on-call policy, and the postmortems. The service catalogue in `services/*.yml` names the owner, tier, SLO target, runbooks and dependencies of each service. The status page is built from the incident records in `incidents/incidents.json`.

## Pages

| Page | What it holds |
|---|---|
<!-- One row per page: a doc: link to the page, then one line on what it holds. -->

New SLO and postmortem pages start from the templates in `docs/sre/_templates/`.

## Tiers

| Tier | Meaning | Response |
|---|---|---|
| 1 | Users meet it directly, or revenue or data depends on it | <paged at any hour> |
| 2 | Supports a tier 1 service, or internal users depend on it | <paged in working hours, fixed the same day> |
| 3 | Internal tooling | <ticket, fixed in the next working days> |

## Records

| Path | What it is |
|---|---|
| `services/<id>.yml` | One catalogue entry per service: owner, tier, SLO, runbooks, dependencies. Start from `services/_template.yml`. |
| `incidents/incidents.json` | Every incident with its public updates. Schema: `incidents/incidents.schema.json`. |
| `scripts/build_status.py` | Builds the status page from the two records above. `--check` compares each SLO target with its dependency ceiling. |

The gate rule `reliability.service-catalog` reports catalogue entries without an owner, without a numeric SLO target or without a runbook link that resolves.
