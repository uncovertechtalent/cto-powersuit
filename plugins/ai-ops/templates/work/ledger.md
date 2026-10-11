---
title: Coordinator ledger
summary: The state of every task the coordinator session routes to worker sessions: owner, state, the artifact that proves it done, and who verified it.
labels: agents, coordinator, ai-ops
owner: <who runs the coordinator>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
One row per task. The coordinator writes this file before it starts a worker and after it checks the worker's artifact. A session that resumes after a stop reads this file first.

| Id | Task | Worker | State | Artifact | Verified by | Updated |
|---|---|---|---|---|---|---|
| T-001 | <task in one line> | <worker session or agent> | queued | <path, commit or link> | <coordinator check> | <YYYY-MM-DD HH:MM> |

States: `queued`, `running`, `done` (artifact checked), `failed`, `blocked` (needs a person). A worker's own report never moves a task to `done`; the coordinator's check of the artifact does.
