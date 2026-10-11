---
title: Agent stance in this repository
summary: Which stance filters run for every agent session in this repository, how to switch them, and who owns the defaults.
labels: agents, stance, ai-ops
owner: <who owns the agent defaults>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
Agent sessions in this repository load the stance plugin. The shared defaults live in `.claude/settings.json`; personal changes go into `.claude/settings.local.json`, which stays out of git.

## Defaults

| Filter | Shared default | What it does |
|---|---|---|
| `receipts` | on | Claims about state, access or completion need a probe from the current session |
| `professional-b2` | <lite, full or ultra> | Plain professional register, no politeness filler |
| `good-chad` | on | Holds a position under pushback; takes correction without grovelling |
| Exemplar pairs | <on or off> | Two corrected-output examples at session start |

The gate check `stance.shared-defaults` fails when the shared settings switch `receipts`, `good-chad` or `professional-b2` off, or disable all hooks.

## Switch in a session

`/stance:professional-b2 lite|full|ultra`, `stop b2`, `/stance:good-chad off`, `normal mode` (all off). The switch lasts for that session only.

## Owner

<owner> decides the shared defaults. A change to them goes through a pull request.
