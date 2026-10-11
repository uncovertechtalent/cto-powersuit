---
title: "ADR-0003: Use one CI provider"
summary: All CI jobs move to one hosted CI provider; the self-hosted runners are shut down.
adr: 0003
status: accepted
date: 2026-03-09
owner: Platform lead
rfc:
supersedes: adr-0001-keep-ci-on-self-hosted-runners
superseded_by:
labels: adr, decision
reviewed: 2026-03-09
review_by: 2026-06-07
type: explanation
---
## Context

The package mirror is now public, so hosted runners can reach it. The self-hosted runners caused three merge stops in one quarter.

## Decision

All CI jobs move to one hosted CI provider. The self-hosted runners are shut down after the move.

## Consequences

Nobody on the team maintains runners. Build minutes are a monthly cost line, and the CI configuration uses one syntax.
