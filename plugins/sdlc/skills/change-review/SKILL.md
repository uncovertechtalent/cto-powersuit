---
name: change-review
description: >
  Review a change before a person approves it, with a checklist for
  agent-written code: diff size, scope against the ticket, tests touched,
  secrets, new dependencies, migrations, generated files and changed tests. Use
  when a pull request is open, before asking a person to review, or when an
  agent wrote most of the diff. Activates on "/change-review", "review this PR",
  "check this diff", "review the agent's change", "is this ready to merge".
user-invocable: true
---

# Change review

Checks one diff against the ticket and a fixed list, and writes a review the human reviewer starts from. The human approves; this skill never does.

## Inputs

- A pull request (`gh pr view <n>` and `gh pr diff <n>`) or a local range (`git diff main...HEAD`).
- The ticket the change names.

## Checklist

| Item | Check | Finding when |
|---|---|---|
| Traceability | Title or commits name a ticket or decision | No id |
| Scope | Every changed file serves the ticket's acceptance criteria | Files outside the ticket's scope |
| Size | Changed lines (`git diff --stat`), default limit 400 outside tests and generated files | Over the limit: propose a split |
| Tests | Source changes come with test changes | Source changed, no test changed, and no reason in the description |
| Changed tests | Assertions removed, loosened or skipped (`skip`, `xfail`, `.only`, `|| true`) | A test was weakened to pass |
| Secrets | Keys, tokens, passwords, private URLs in the diff; `gitleaks` if installed | Any hit (mask the value in the review) |
| Dependencies | New entries in lock files or manifests | A new dependency without a reason; a name that resolves to no package in the lock file; a licence the team does not allow |
| Migrations | Schema or data changes | No way back, or a destructive step without a backup note |
| Generated files | Files a tool writes (lock files, builds, snapshots, docs output) | Edited by hand, or changed with no change to their source |
| Errors and logs | New error handling | Broad catch-alls that hide failures; personal data in log lines |
| Config and access | Permissions, auth, CI, infrastructure files | Any change here gets a person who owns that area |
| Docs and changelog | User-visible behaviour changed | No docs or changelog update |

Agent-written diffs need extra care on three items: changed tests, dependencies (names that do not exist or do not match the lock file) and scope (refactors nobody asked for).

## Steps

1. Read the ticket, then the diff, then the files around each changed hunk.
2. Run the checklist. Run the pre-PR command from `docs/sdlc.md` if the user agrees.
3. Write the review: findings ordered **block**, **should**, **note**, each with file, line and the fix.
4. Post it as a pull request comment only when the user says so (`gh pr review <n> --comment --body-file <file>`).

## Rules

- Never approve, request changes as the user, merge or push.
- Each finding names file and line. No finding without evidence.
- Mask secrets in every output.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/change-review/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
