---
title: Module fit
summary: Which modules of the suit this repository has and which to fit next.
owner: Platform Team
reviewed: 2026-01-20
review_by: 2026-04-20
type: reference
---
The table below marks observability as fitted, and the repository has no observability stack.

## Modules

| Module | Recommendation | Reason | First step | Owner |
|---|---|---|---|---|
| observability | fitted | Stack copied last quarter | `/observability:stack-init` | Lee Example |
| fit | fitted | This page | `/fit:estate-assessment` | Dana Example |

## Module signals

The file or files a module leaves in the repository when it is fitted. The gate check reads this table.

| Module | Signal in the client repository |
|---|---|
| sdlc | `docs/sdlc.md` |
| decisions | `docs/decisions/index.md` |
| docs | `docs/docs.json` |
| gate | `gate/gate.json` |
| reliability | `services/*.yml` or `incidents/incidents.json` |
| observability | `observability/docker-compose.yml` |
| finops | `docs/fin/index.md` or `scripts/focus_export.py` |
| compliance | `compliance/control-map.csv` or `.well-known/security.txt` |
| ai-ops | `docs/agents.md` |
| hiring | `hiring/loop.md` |
| red-team | `red-team/plan.md` |
| aieo | `llms.txt` or `predictions/HASHES.txt` |
| fit | `docs/fit.md` |
| handover | `docs/handover.md` |
