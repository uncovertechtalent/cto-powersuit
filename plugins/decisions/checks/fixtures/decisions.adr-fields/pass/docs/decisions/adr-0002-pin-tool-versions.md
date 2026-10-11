title: ADR-0002: Pin tool versions in the repository
summary: Every build tool has an exact version in one file at the repository root.
adr: 2
status: accepted
created: 2026-02-03
owner: Platform lead
labels: adr, decision
reviewed: 2026-02-03
review_by: 2026-05-04
type: explanation
---
## Context

Two developers got different build results from the same commit. Their compilers had different minor versions.

## Decision

Every build tool has an exact version in one file at the repository root. CI and local builds read the same file.

## Consequences

A tool upgrade is a one-line change with its own review. This record uses the older header format with `created`; the check accepts both formats.
