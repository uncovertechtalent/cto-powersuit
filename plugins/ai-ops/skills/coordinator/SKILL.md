---
name: coordinator
description: >
  Run a coordinator session that routes work to worker sessions or subagents
  and verifies their artifacts, with all state in files: a ledger of tasks,
  briefs that name files and done criteria, caps on parallel workers, and
  resume after a stop. Use when one person runs several agent sessions at once,
  when a batch of tasks is too big for one session, or after a session limit cut
  work off. Activates on "/coordinator", "coordinate these sessions", "split
  this across agents", "resume the batch", "run a batch of tasks".
user-invocable: true
---

# Coordinator

One session plans, briefs, routes and verifies. Workers do the work. Everything the coordinator knows lives in files, so a stopped session resumes from the ledger and a person can read the state at any time.

## Rules of the pattern

- **State in files.** `work/ledger.md` holds every task: id, task, worker, state, artifact, verification, time. The coordinator writes it before it starts a worker and after it checks the result.
- **The coordinator routes and verifies.** It writes briefs and checks artifacts. It does the work itself only when the task is smaller than the brief would be.
- **Briefs are complete.** Each brief names the goal, the files the worker may touch, the files it must read, what done looks like, the checks to run, and what to report. A worker has none of the coordinator's context.
- **Verify the artifact.** A worker's report says what it did; the file, the commit or the test output shows it. A task moves to `done` only after the coordinator checks the artifact.
- **Caps.** At most two or three workers run at once. Workers never start workers of their own; every brief says so. Two workers never write the same files.
- **Resume.** Every long task leaves a marker in the ledger (state `running`, the worker, the start time). After a stop, read the ledger, check each `running` task's artifact, and set it to `done`, `failed` or `queued` before starting anything new.

## Steps

1. **Set up.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/work/ledger.md` to `work/ledger.md` without overwriting.
2. **Plan.** Split the work into tasks a worker can finish alone. One row per task, state `queued`.
3. **Brief and start.** For each task up to the cap: write the brief, set the row to `running`, start the worker.
4. **Verify.** When a worker reports, open the artifact: read the diff, run the tests or the checks the brief named. Set `done` with the check in the "Verified by" column, or `failed` with the reason.
5. **Integrate.** The coordinator commits, merges or publishes, one task at a time, after verification. Workers do not commit unless the brief says so.
6. **Report.** Summarise from the ledger: done, failed, blocked, and the evidence for each.

## Output

The ledger, the briefs, the verified artifacts and the report.

## Rules

- Never mark a task done from a report alone.
- Never let two workers write the same file.
- Never raise the cap or allow nested workers without the user's go.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/ai-ops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/ai-ops/` exists, read its `README.md` first, then the files in `ai-ops/coordinator/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
