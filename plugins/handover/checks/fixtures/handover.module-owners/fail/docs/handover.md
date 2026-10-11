---
title: Handover
summary: Who owns each module after the handover.
owner: Dana Example
reviewed: 2026-01-20
review_by: 2026-02-19
type: reference
---
The sdlc module is installed and its row has no named owner.

## Owners

| Module | Owner | Backup | Trained on | Exit criteria |
|---|---|---|---|---|
| sdlc | <owner> | Sam Example | <YYYY-MM-DD> | open |
| handover | Sam Example | Lee Example | 2026-01-12 | open |

## Module signals

The file or files a module leaves in the repository when it is installed. The gate check reads this table.

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
