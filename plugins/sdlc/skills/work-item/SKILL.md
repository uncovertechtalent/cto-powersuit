---
name: work-item
description: >
  Walk one change through the lifecycle stages and link the record at each stop:
  ticket, RFC or ADR, branch, pull request, test run, gate run, deploy record and
  dashboard. Use when starting a change, when handing a change to another person
  or agent, or when asked where a change stands. Activates on "/work-item",
  "walk this change through", "where is this change", "trace this ticket",
  "start work on".
user-invocable: true
---

# Work item

Takes one change from request to production, stage by stage, and keeps a trace table with the record of each stage. The stages and their exit criteria come from `docs/sdlc.md`; without it, use the default stages from `/sdlc:sdlc-init`.

## Inputs

- A ticket number, or a description of the change (then the first step writes the ticket).

## Steps

1. **Ticket.** Find it (`gh issue view <n>`) or write it with `/sdlc:ticket`. It needs a problem, acceptance criteria and a risk note before work starts.
2. **RFC or ADR.** If the change touches more than one team, is hard to undo or needs comments, start `/decisions:rfc`. If it makes a choice others need to know, record `/decisions:adr`. Otherwise mark the stage "not needed" with one line on why.
3. **Build.** Branch named `<ticket>-<short-name>`. Every commit subject names the ticket (`#123`) or the decision (`ADR-0007`).
4. **Test.** Run the pre-PR command from `docs/sdlc.md`. Add or change tests with the source; if none are needed, say why in the pull request.
5. **Review.** Open the pull request with the template. Run `/sdlc:change-review` on the diff before asking a person.
6. **Gate.** `python3 .github/actions/gate/run.py --dry-run --exit-code` before merge, if the gate is installed. After merge, link the gate run.
7. **Release.** Link the deploy run. Add the changelog entry with `/sdlc:release`.
8. **Observe.** Link the dashboard or SLO that shows the change working. Check it once after the deploy.
9. **Close.** Close the ticket when its acceptance criteria hold in production. Post the trace table on the ticket only when the user says so.

## Output

A trace table, kept current as the change moves:

| Stage | Record | Link | State |
|---|---|---|---|
| Ticket | #123 | <url> | done |
| Decision | not needed: no shared interface changes | | done |
| Build | branch `123-retry-uploads` | <url> | done |
| Review | pull request #130 | <url> | waiting for approval |

## Rules

- One change per work item. Split a change that needs two tickets.
- A stage is done when its record exists and its exit criteria hold. Say "not needed" only with a reason.
- Never merge, deploy, close a ticket or comment on it without the user's go.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/work-item/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
