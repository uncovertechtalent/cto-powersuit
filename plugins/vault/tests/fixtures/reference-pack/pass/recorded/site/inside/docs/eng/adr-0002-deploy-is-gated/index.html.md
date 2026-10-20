---
url: https://machinebehavior.io/inside/docs/eng/adr-0002-deploy-is-gated/
title: "ADR-0002: The deploy is gated"
date: 2026-10-07
published: 2026-10-07
description: "GitHub Pages deploys from GitHub Actions, and the deploy job depends on the conformity job."
source: machinebehavior.io, Stefan Coetzee
---
# ADR-0002: The deploy is gated

accepted owner Stefan Coetzee created 2026-10-07 updated 2026-10-07 reviewed 2026-10-09 review by 2027-01-07 1 min read explanation

## Context

The conformity checks ran after a page was live, so they could only detect a problem that readers already saw.

## Decision

GitHub Pages deploys from GitHub Actions, and the deploy job depends on the conformity job. A failed check stops the deploy and the previous build stays live.

## Consequences

A false positive blocks a deploy until the sentence is rewritten or the rule is demoted by the gate owner. The bot commit after each run moves `main`, so every push needs a rebase first. See [Conformity gate](https://machinebehavior.io/inside/docs/eng/conformity-gate/).

Built from [scripts/docs](https://github.com/uncovertechtalent/machinebehavior.io/tree/main/scripts/docs) by [build_docs.py](https://github.com/uncovertechtalent/machinebehavior.io/blob/main/scripts/build_docs.py).
