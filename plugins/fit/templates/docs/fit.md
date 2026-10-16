---
title: Module fit
summary: Which modules of the suit this repository has, which to fit next and in which order, with the reason, the first step and the owner of each.
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
<Two or three sentences on the state of the repository, from the sdlc audit of <YYYY-MM-DD>: the stages present, partial and missing, and the gap that costs the most.>

## Modules

Recommendation is one of `fit now`, `fit later`, `not needed` or `fitted`. A module is `fitted` when its signal from the table at the end of this page is in the repository. The gate check `fit.assessment-matches` checks every `fitted` row.

| Module | Recommendation | Reason | First step | Owner |
|---|---|---|---|---|
| sdlc | <recommendation> | <reason, with the audit evidence> | <first skill or command> | <owner> |
| gate | <recommendation> | <reason> | <first step> | <owner> |
| docs | <recommendation> | <reason> | <first step> | <owner> |
| decisions | <recommendation> | <reason> | <first step> | <owner> |
| direction | <recommendation> | <reason> | <first step> | <owner> |
| reliability | <recommendation> | <reason> | <first step> | <owner> |
| observability | <recommendation> | <reason> | <first step> | <owner> |
| finops | <recommendation> | <reason> | <first step> | <owner> |
| compliance | <recommendation> | <reason> | <first step> | <owner> |
| security | <recommendation> | <reason> | <first step> | <owner> |
| ai-ops | <recommendation> | <reason> | <first step> | <owner> |
| hiring | <recommendation> | <reason> | <first step> | <owner> |
| red-team | <recommendation> | <reason> | <first step> | <owner> |
| aieo | <recommendation> | <reason> | <first step> | <owner> |
| fit | fitted | This page | `/fit:estate-assessment` to update it | <owner> |
| handover | <recommendation> | <reason> | <first step> | <owner> |

## Order

The modules to fit, in order. A module starts after the modules it depends on.

| Step | Module | Depends on | Effort | First skill |
|---|---|---|---|---|
| 1 | <module> | <module, or none> | <hours, days or weeks> | <first skill> |
| 2 | <module> | <module, or none> | <hours, days or weeks> | <first skill> |

## Module signals

The file or files a module leaves in the repository when it is fitted. The gate check reads this table.

| Module | Signal in the client repository |
|---|---|
| sdlc | `docs/sdlc.md` |
| decisions | `docs/decisions/index.md` |
| direction | `docs/direction/index.md` |
| docs | `docs/docs.json` |
| gate | `gate/gate.json` |
| reliability | `services/*.yml` or `incidents/incidents.json` |
| observability | `observability/docker-compose.yml` |
| finops | `docs/fin/index.md` or `scripts/focus_export.py` |
| compliance | `compliance/control-map.csv` or `.well-known/security.txt` |
| security | `docs/security/index.md` or `docs/security/vuln-policy.md` |
| ai-ops | `docs/agents.md` |
| hiring | `hiring/loop.md` |
| red-team | `red-team/plan.md` |
| aieo | `llms.txt` or `predictions/HASHES.txt` |
| fit | `docs/fit.md` |
| handover | `docs/handover.md` |
