---
title: Software delivery lifecycle
summary: The stages a change moves through in this repository, from request to production and back, with the entry and exit criteria, the owner and the record of each stage.
labels: sdlc, process, delivery
owner: <who keeps this page true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
Every change moves through the stages below, in this order. A stage is done when its exit criteria hold and its record exists. Each record links the one before it, so any line in production traces back to the request that asked for it.

## Stages

| Stage | Entry | Exit | Owner | Record | Served by |
|---|---|---|---|---|---|
| Request | Someone needs a change | A ticket with problem, acceptance criteria and risk | <owner> | Ticket | `sdlc:ticket` |
| RFC | The change touches more than one team, is hard to undo or needs comments | RFC decided | <owner> | `docs/decisions/rfc-NNNN-*.md` | `decisions:rfc` |
| Decision | A choice was made that others need to know | ADR accepted | <owner> | `docs/decisions/adr-NNNN-*.md` | `decisions:adr` |
| Build | Ticket in `status: ready` | Branch with commits that name the ticket | <owner> | Branch, commits | `sdlc:work-item` |
| Review | Pull request open | Approved by a person who did not write it | <owner> | Pull request | `sdlc:change-review` |
| Test | Code changed | The pre-PR command passes locally and in CI | <owner> | CI run | `sdlc:test-strategy` |
| Gate | Merge to main | Gate run passes | <owner> | Gate run record | `gate` |
| Release | Gate passed | Deployed, changelog entry written, rollback path known | <owner> | Deploy run, `CHANGELOG.md` | `sdlc:release` |
| Observe | Deployed | SLO and cost within target after the release | <owner> | Dashboard, SLO report | `observability`, `reliability:slo`, `finops` |
| Incident | A user-facing symptom | Service restored, postmortem written, action items ticketed | <owner> | Incident log, postmortem | `reliability:incident`, `reliability:postmortem` |

Action items from a postmortem go back to Request as tickets.

## Gaps

Stages with no module or practice yet:

| Stage | What is missing | Fills it |
|---|---|---|
| <stage> | <what is missing> | <module or skill> |

## Tickets

Labels:

| Group | Labels | Meaning |
|---|---|---|
| Type | `type: feature`, `type: bug`, `type: chore`, `type: docs` | What kind of work. An issue without a type label is untriaged |
| Area | `area: <part>` | Which part of the system. An issue can carry more than one |
| Priority | `P0`, `P1`, `P2`, `P3` | P0 stops other work; P3 is optional |
| Status | `status: ready`, `status: in progress`, `status: blocked` | The board column. No status label means backlog; closed means done |

Commit subjects and pull request titles name the ticket (`#123`) or the decision (`ADR-0007`). The gate check `sdlc.traceability` reads them.

## Test strategy

| Level | What it covers | Where it runs |
|---|---|---|
| Unit | <one function or module, no network> | Pre-PR command, CI |
| Integration | <the service with its real database or queue> | CI |
| End to end | <a user path through the deployed system> | CI on main, after deploy |
| Smoke | <the service answers after a deploy> | Deploy job |

Before opening a pull request, run:

```bash
<the one command that runs lint, unit tests and the gate dry run>
```

## Release and rollback

- Changelog: `CHANGELOG.md`, one entry per release under Added, Changed, Fixed, Removed or Security.
- Rollback: <how to return to the previous release, and how long it takes>.
- Feature flags: <where flags live, who owns each one, and the date each one is removed>.
