---
title: Handover
summary: Who owns each module of the platform after the handover, how each owner was trained, the exit criteria for the person handing over, and the log of runs without help.
owner: <person handing over>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 30 days after reviewed>
type: reference
---
<Who hands over to whom, the start date and the planned exit date.>

## Owners

One row per installed module. A module is installed when its signal from the table at the end of this page is in the repository. Owner and backup are two different people. Trained on is the date the owner finished the module's training checklist. Exit criteria is `met` when every criterion for the module is met, otherwise `open`. The gate check `handover.module-owners` checks that every installed module has a row with a named owner.

| Module | Owner | Backup | Trained on | Exit criteria |
|---|---|---|---|---|
| handover | <owner> | <backup> | <YYYY-MM-DD> | <met or open> |
| <module> | <owner> | <backup> | <YYYY-MM-DD> | <met or open> |

## Training

One checklist per installed module, written by `/handover:owner-training`. The new owner does each step; the person handing over watches and answers questions.

### <module>

| Step | What | Done on | Evidence |
|---|---|---|---|
| Read | <pages and files to read> | <YYYY-MM-DD> | <link> |
| Run | <command or skill to run> | <YYYY-MM-DD> | <run record or output> |
| Change once, supervised | <one change, reviewed by the person handing over> | <YYYY-MM-DD> | <pull request> |
| Know it works | <the signal that shows the module works> | <YYYY-MM-DD> | <check result or record> |

## Exit criteria

Written by `/handover:exit-criteria`. The person handing over leaves when every criterion is `met`.

| Criterion | State | Evidence |
|---|---|---|
| Every installed module has a named owner and a backup | <met or open> | Owners table, gate check `handover.module-owners` |
| Every runbook was run by its new owner | <met or open> | <runbook, date, run record> |
| The gate was operated without help for <N> days | <met or open> | <gate runs and findings closed by the new owner> |
| The status page was operated without help for <N> days | <met or open> | <incident records updated by the new owner> |
| Open decisions are recorded | <met or open> | <decision log, open RFCs and proposed ADRs> |
| Access moved: accounts, secrets and billing name the new owners | <met or open> | <list of systems and their owner> |
| Every runs-without-me scenario passed with no help | <met or open> | Log below |

Exit date: <YYYY-MM-DD, the first day all criteria are met>

## Runs without me

Written by `/handover:runs-without-me`. The new owner runs each scenario from the docs alone. A question to the person handing over counts as help.

| Date | Scenario | Run by | Help needed | Time taken | Docs used | Gaps found | Tickets |
|---|---|---|---|---|---|---|---|
| <YYYY-MM-DD> | <deploy, blocked gate, incident, restore, cost spike, docs review, or new decision> | <owner> | <none, or the question asked> | <minutes> | <pages used> | <what was missing or wrong> | <ticket ids> |

## Module signals

The file or files a module leaves in the repository when it is installed. The gate check reads this table.

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
