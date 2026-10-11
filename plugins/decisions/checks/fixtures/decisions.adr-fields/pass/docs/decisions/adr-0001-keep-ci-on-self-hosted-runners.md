---
title: "ADR-0001: Keep CI on self-hosted runners"
summary: All CI jobs run on two self-hosted runners in the office network.
adr: 0001
status: superseded
date: 2026-01-12
owner: Platform lead
rfc:
supersedes:
superseded_by: adr-0003-use-one-ci-provider
labels: adr, decision
reviewed: 2026-01-12
review_by: 2026-04-12
type: explanation
---
## Context

The build needs access to an internal package mirror. Hosted runners could not reach it.

## Decision

All CI jobs run on two self-hosted runners in the office network.

## Consequences

The team patches and restarts the runners. A runner outage stops every merge until someone restarts it.
