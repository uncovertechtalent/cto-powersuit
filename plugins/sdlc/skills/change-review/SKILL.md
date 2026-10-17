---
name: change-review
description: >
  Review a change before a person approves it, with a checklist for
  agent-written code: diff size, scope against the ticket, tests touched,
  secrets, new dependencies, migrations, generated files and changed tests. Use
  when a pull request is open, before asking a person to review, or when an
  agent wrote most of the diff. Reads the repository's recorded decisions and
  conventions first, so a deliberate choice is not flagged; with `kb` it also
  reads a private knowledge base on the user's machine and posts one comment that
  cites public files only. Activates on "/change-review", "review this PR",
  "check this diff", "review the agent's change", "is this ready to merge".
user-invocable: true
---

# Change review

Checks one diff against the ticket and a fixed list, and writes a review the human reviewer starts from. The human approves; this skill never does.

## Inputs

- A pull request (`gh pr view <n>` and `gh pr diff <n>`) or a local range (`git diff main...HEAD`).
- The ticket the change names: the issue the pull request links (`gh issue view <n>`), or the decision it cites.
- The repository's own record of its decisions and conventions, where present: decision records (`docs/decisions/`, `docs/adr/`, files named `adr-*.md`), `docs/`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`, and the sections of `README.md` that the change touches.
- With `kb` in the arguments, and only on the user's machine: a private knowledge base (see below).

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

1. Read the ticket, then the repository's decisions and conventions, then the diff, then the files around each changed hunk. Read the decision records whose title or summary matches a changed path or topic, and note which ones a later record supersedes.
2. Run the checklist. A choice that a recorded decision covers is not a finding: write it as a note, "intentional per ADR-NNNN" (or the file and line that records it). Flag it only when the change contradicts the record, or when the record no longer fits what the change does; then name the record. If the user agrees, run `/sdlc:pre-push` (the check jobs of the workflows, locally), or the pre-PR command from `docs/sdlc.md` when preloop is not installed.
3. Write the review: findings ordered **block**, **should**, **note**, each with file, line and the fix.
4. Post it as a pull request comment only when the user says so (`gh pr review <n> --comment --body-file <file>`).

## Private knowledge base (local runs only)

A review that knows the team's history catches more: the decision behind a pattern, a trap that bit before, an incident in the same file. That history often sits in a private knowledge base that must never reach a public repository, a CI runner, or a review bot. This section runs only when both hold:

- the user asked for it, with `kb` in the arguments ("/sdlc:change-review 42 kb");
- a private knowledge base is reachable on this machine: a search tool such as the `vault-search` MCP server (`vault_search`, `vault_read`), or a folder that `$POWERSUIT_OVERLAY/sdlc/README.md` names.

In CI neither holds, and none may be added there. Without both, skip this section and say so in one line.

1. **Search.** Query the knowledge base for the files, modules, and decisions the diff touches: decisions and their reasons, known traps, prior incidents, and rejected alternatives. Read only the notes that match.
2. **Translate.** Turn what you learn into findings about the public change. Each finding cites public evidence only: a file and line in the repository, the diff, a public page, or a public issue. Never quote, name, or link a private note, and never copy its wording. If a finding cannot be stated without private detail, drop it and tell the user in the session instead.
3. **Write one comment** to a file in a new, empty temporary folder. Start it with the heading "Change review with local context", list the findings ordered block, should, note, and say in its last line which public files it cites.
4. **Scan it** with the private-terms check (`/security:private-terms`) and the term list your pre-push hook uses, by default `$POWERSUIT_OVERLAY/security/private-terms.txt`. A hit (exit 1) stops the post, and you rewrite the line. If the check is not installed or finds no list (exit 2), tell the user the comment is unscanned:

   ```bash
   python3 ~/.config/private-terms/private_terms.py scan <folder> --terms <term list>
   ```

5. **Post it** as one comment, after the user has read it in the session: `gh pr comment <n> --body-file <file>` (add `--repo <owner/repo>` outside the checkout). An unscanned comment goes out only on the user's explicit go.

The one-liner, run in the repository's checkout or from anywhere with `owner/repo#n`:

```bash
claude "/sdlc:change-review 42 kb"
claude "/sdlc:change-review owner/repo#42 kb"
```

It is interactive on purpose: the comment draws on private notes, so the user sees it before it goes public.

`review-pr.sh` in this skill's folder runs the same review end to end with the limits of the CI workflow, for repositories whose CI has no token yet. It loads this plugin from a clean clone of the suit's `main`. It gives the model the pull request as files, with no shell and no network, and the knowledge base through its MCP search tools only. It then scans the comment, saves it, and posts or updates one comment: `review-pr.sh <owner/repo> <n>`, then `--post-saved` after reading it.

### Large pull requests (`review-pr.sh`)

- **GitHub refuses the diff above 300 files** (`gh pr diff` answers HTTP 406, `too_large`). The script then fetches the base branch into its checkout, deeper until it shares a commit with the head, and runs `git diff <merge-base> <head>`: the same three-dot diff the pull request page shows. `pr.json` records the source (`.diff.source` is `gh` or `local-git`, with `.diff.mergeBase`), and the prompt tells the model.
- **A diff over `$POWERSUIT_MAX_DIFF_BYTES` (default 200000) is reduced** before the model sees it. `pr.diff` keeps the full diff of the files that look hand-written. Every file that looks generated gets one line in `pr.generated-stat.txt` (lines added, lines removed, group, reason, path), and `pr.generated-sample.diff` holds one file for each of the five largest groups of identical changes. A line over 500 characters is cut and marked, in the reduced diff and the sample. The model must say in the comment that these files were sampled.
- **A file looks generated when** it matches one of four rules, checked in this order:

  | Reason | Rule |
  |---|---|
  | `attribute` | `.gitattributes` sets `linguist-generated` for it |
  | `name` | it is a lock file (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `Gemfile.lock`, `poetry.lock`, `uv.lock`, `composer.lock`, `go.sum`), ends in `.lock`, `.min.js`, `.min.css`, `.map`, `.snap`, `.pb.go` or `_pb2.py`, or sits in a folder named `dist`, `generated`, `__generated__`, `__snapshots__` or `node_modules` |
  | `header` | one of its first 10 lines says `@generated`, `DO NOT EDIT`, `Code generated` or `auto-generated`, in any case |
  | `repeat` | at least 20 files of the pull request have the same added and removed lines |

  The first three follow the checklist's "Generated files" row (lock files, builds, snapshots, docs output) and the markers that tools write. The fourth catches output with no marker, such as one label changed on hundreds of built pages, which is the case that stopped the runner. Files in one `repeat` group carry the identical change, so the sample shows every changed line of the group once.
- **The residual:** a generated-looking file is not read line by line. The stat lists every one, so a file whose counts do not fit its group stands out, and the checkout holds the full content. A marker line sits in the pull request's own head, so it proves nothing about who wrote the file.
- **Every stop says so.** A run that ends without a review (gh cannot read the pull request, an empty diff, a base branch that cannot be fetched, a model that fails or returns a blank comment) exits 1 with the reason on stderr and "no review was produced".

## Rules

- Never approve, request changes as the user, merge or push.
- Each finding names file and line. No finding without evidence.
- Mask secrets in every output.
- Private knowledge stays private: no note from a private knowledge base is quoted, named, or linked in a comment, a commit, or a file in the repository.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/change-review/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
