---
name: sdlc-audit
description: >
  Audit a repository for the stages of a software delivery lifecycle and return
  the missing ones ranked by the damage each does for what the repository ships
  to, each with the module or skill that fills it. Use when a team new to the
  suit wants to know where to start, typically on a repository built fast with
  coding agents and no process around them. Runs with no other module
  installed. Read only. Activates on "/sdlc-audit", "audit our lifecycle",
  "what is missing in this repo", "why does our vibe-coded app keep breaking",
  "where do we start".
user-invocable: true
---

# SDLC audit

Reads one repository and reports which stages of the lifecycle exist, which exist in part and which are missing. Agents write code fast. A product built that way breaks in the stages around the code: no ticket says what done means, no test runs before merge or deploy, nothing stops a bad deploy, nobody can roll back, and nobody sees the error before a user does. This audit names those gaps, ranked by what they cost for this repository's purpose.

It needs no other module. It reads files and runs read-only commands; it changes nothing. The probes run in `probe.py`, next to this file, so the same rules give the same states on every run.

## Inputs

- **Repository root** (default: the current directory).
- **Purpose**: what the repository ships to. Ask if it is not clear from the README.
  - `users`: a service, a site or an app that people use.
  - `grader`: a one-shot submission, a take-home, a hackathon entry.
  - `nothing`: a sandbox, a spike, a personal experiment.
- **Author**: the user's commit email or name (default: `git config user.email`). History probes count only the user's commits; inherited history (a template, a fork, an organiser's starter repo) is reported apart.
- **Remote**: run `git remote -v` first. If `origin` belongs to another account or organisation, every GitHub probe is "not checked (upstream)". Issues, pull requests and branch protection of someone else's repository say nothing about this team.

## Steps

1. **Run the probe.**

   ```bash
   python3 <this skill's folder>/probe.py <repo> --purpose <users|grader|nothing> --author <email>
   ```

   Add `--no-gh` when `gh` is missing or not logged in, and `--own <owner,...>` when the user's GitHub owners differ from the logged-in account. The output is JSON: `scope`, `history`, `hurt` and one state per stage with its evidence. Keep the command and the output as evidence.
2. **Read the states.** The probe applies these rules:

   | Stage | Present | Partial | Missing |
   |---|---|---|---|
   | Request | Issue templates and at least half of the user's main-line commits name a ticket | Some of it | Neither |
   | Decision | ADR or RFC files | | None |
   | Build | At least half of the user's main-line commits arrive through pull requests | Direct pushes with a documented protocol and a gate before deploy | Direct pushes with neither |
   | Review | Branch protection on, with CODEOWNERS or a pull request template | One of those, or a pull-request flow | Protection off ("Branch not protected"), or direct pushes with no review artifact. "Not Found" from the protection API means no access: not checked |
   | Test | Tests, an eval harness or verify functions, and CI runs them | They exist; nothing runs them on a trigger | None |
   | Gate | A deploy job waits for a check job (`needs:`) | CI exists; the deploy waits for nothing, or no deploy job | No CI |
   | Release record | Tags or a changelog | | Neither |
   | Rollback | A rollback note that names this repository's deploy path | Notes exist, none names this repository's deploy path (an imported generic runbook) | No note |
   | Observe | Metrics, logs or alert config of the repository's own | | None |
   | Incident | Runbooks, postmortems, on-call or status files | | None |
   | Docs | README with run instructions | README without them | No README |
   | Dependencies | No manifest and no third-party imports; or manifests with lock files or `==` pins | Manifests with ranges and no lock; tool scripts that pin their package in an install line | Third-party imports with no manifest |
   | Secrets | No secret pattern in tracked files, no `.env` in git | | A hit (value masked) |
   | Hygiene | No generated files tracked | | `__pycache__`, `.pyc`, `.zip`, `node_modules` or `.DS_Store` in git |

   Files under `templates/`, `fixtures/`, `examples/` and vendored folders are not evidence of the repository's own practice; test fixtures still count as tests. With purpose `grader` or `nothing`, Gate, Release record, Rollback, Observe and Incident are out of scope; say so in the report.
3. **Check the history basis.** If `history.thin` is true (three or fewer commits by the user), say "history too thin" and name the largest commit by lines (`history.largest_user_commit`). Commit-share findings rest on that basis; give the denominator with every share.
4. **Find what already hurt.** `hurt.revert_or_hotfix_commits` and `hurt.failed_runs_last_30` from the probe, plus a look at `notes/`, `incidents/`, review notes and the README for problems someone already wrote down. A gap that already caused damage moves up.
5. **Rank the gaps by damage for this repository's purpose.** For each missing or partial stage, answer three questions from the evidence: who is hurt when this stage fails, how soon would anyone notice, and how hard is it to undo. Rank by those answers. Starting points, which the evidence overrides:
   - **users**: secrets; no tests before merge or deploy; no gate before deploy; no rollback path; no review on main; no observability; no release record; no tickets; no incident process; no decisions; docs.
   - **grader**: secrets; no verification that runs before submission (tests, the eval harness, the packaging check); hygiene (generated files and archives in git); undeclared dependencies; docs a grader needs to run it; no tickets or decisions last.
   - **nothing**: secrets and hygiene first; the rest only if the user plans to ship it.
6. **Name the fix and the first command for each gap.** If the module is not installed in this session (its skills are not in the skill list), the first command starts with `claude plugin install <module>@cto-powersuit`.

   | Gap | Fills it |
   |---|---|
   | Request, traceability | `/sdlc:ticket`; gate check `sdlc.traceability` |
   | Decision | `decisions` module: `/decisions:rfc`, `/decisions:adr` |
   | Build, review | `/sdlc:change-review`, the pull request template; branch protection is a repository setting the user changes; `/security:access-review` lists the merges and pushes that went past the review rule |
   | Test | `/sdlc:test-strategy` |
   | Gate | `gate` module: `/gate:gate-init` |
   | Release record | `/sdlc:release` (changelog and tags) |
   | Rollback | `/sdlc:release` (rollback plan for this repository's deploy path) |
   | Observe | `observability` module; `/reliability:slo` |
   | Incident | `reliability` module: `/reliability:incident`, `/reliability:postmortem`, `/reliability:on-call` |
   | Docs | `docs` module |
   | Dependencies | Add a lock file with the package manager (`npm install --package-lock-only`, `uv lock`, `poetry lock`, `go mod tidy`), or pin with `==`; declare the dependencies of tool scripts in a manifest. Then `/security:supply-chain`: vulnerability scan of the lock files, SBOM, Dependabot, and pinned actions from listed owners |
   | Secrets | `/security:secrets`: rotate the secret first with its rotation runbook, then remove it from history with the user; add the blocking check `security.secrets` with `/gate:add-rule` |
   | Hygiene | Remove the files from git (`git rm --cached`) and add them to `.gitignore`, with the user's go |
   | Lifecycle as a whole | `/sdlc:sdlc-init` |

7. **Write the report.** Present it in the chat. Write `docs/sdlc-audit-<YYYY-MM-DD>.md` only when the user asks.

## Output

1. One paragraph: the purpose, the history basis (the user's commits out of all), and how many stages are present, partial, missing, out of scope and not checked.
2. The ranked gap list: rank, stage, evidence (file, command or count with its denominator), why it ranks there for this purpose, the fix, and the first command.
3. What is present and working, in one short list, so the team keeps it.
4. Probes that did not run (no `gh`, upstream remote, no access) and what they would have shown.

## Rules

- Read only. No file changes, no labels, no settings, no pushes.
- Every finding cites its evidence. A stage with no probe result is "not checked", never "missing".
- A found secret is reported by file and line with the value masked. Rotation comes before any history rewrite, and both are the user's actions.
- Describe the repository. Do not judge the people who built it.

## Check the probe

`python3 <this skill's folder>/test_probe.py` runs the recorded cases in `cases/`: one pair per rule that once gave a wrong finding (upstream remote, branch protection answers, dependencies, rollback fit, trunk-based flow, inherited history, purpose). Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/sdlc-audit/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
