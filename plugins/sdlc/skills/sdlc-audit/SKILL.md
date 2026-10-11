---
name: sdlc-audit
description: >
  Audit a repository for the stages of a software delivery lifecycle and return
  a ranked list of the missing ones, each with the module or skill that fills
  it. Use when a team new to the suit wants to know where to start, typically on
  a repository built fast with coding agents and no process around them. Runs
  with no other module installed. Read only. Activates on "/sdlc-audit", "audit
  our lifecycle", "what is missing in this repo", "why does our vibe-coded app
  keep breaking", "where do we start".
user-invocable: true
---

# SDLC audit

Reads one repository and reports which stages of the lifecycle exist, which exist in part and which are missing. Agents write code fast; what usually breaks a fast-built product is the missing stages around the code: no ticket says what done means, no test runs before merge, nothing stops a bad deploy, nobody can roll back, and nobody sees the error before a user does. This audit names those gaps in the order they cost the most.

It needs no other module. It reads files and runs read-only commands; it changes nothing.

## Inputs

- The repository root (default: the current directory).
- Optional: GitHub access through `gh` for issues, pull requests and branch protection. Without it, the audit uses the files and the git history only and says so.

## Steps

1. **Collect signals per stage.** Run each probe and keep the command and its output as evidence.

   | Stage | Probes |
   |---|---|
   | Request | `.github/ISSUE_TEMPLATE/`; `gh issue list --limit 20 --state all`; share of commits on the main line that name a ticket (`git log --first-parent -n 100 --format=%s`) |
   | Decision | `docs/decisions/`, `docs/adr/`, `adr/`, any `adr-*.md` or `rfc-*.md` |
   | Build | Branch model: share of main-line commits that are merges or squashed pull requests; direct pushes to main |
   | Review | `.github/pull_request_template.md`, `CODEOWNERS`; `gh api repos/{owner}/{repo}/branches/main/protection` (read only) |
   | Test | Test folders and files; the test command in `package.json`, `pyproject.toml`, `Makefile`, `go.mod` and CI; whether CI runs it on pull requests; share of source-changing commits with test changes |
   | Gate | A CI job that must pass before the deploy job (`needs:`); required status checks |
   | Release | Tags, `CHANGELOG.md`, GitHub releases (`gh release list`), a rollback note, feature flag config |
   | Observe | Metrics, logs and alerts config (`prometheus`, `grafana`, `otel`, `sentry`, `alloy` in the tree), health endpoints, SLOs |
   | Incident | Runbooks, postmortems, an on-call note, a status page |
   | Docs | README with run instructions, `docs/`, owners and review dates on pages |
   | Secrets and dependencies | Lock files; `.env` files in git (`git ls-files | grep -E '(^|/)\.env'`); a secret scan if `gitleaks` is installed; dependency update config |

2. **Score each stage** as present, partial or missing. Partial means the artifact exists and something stops it from working, for example tests that CI never runs, or a CHANGELOG last touched a year ago.
3. **Rank the gaps.** Order by the damage a gap does to a team that ships every day. The default order:
   1. Secrets in git or no lock files.
   2. No tests run before merge.
   3. No gate before deploy.
   4. No rollback path.
   5. Direct pushes to main with no review.
   6. No observability: errors reach users first.
   7. No tickets or traceability: nobody can say why a line exists.
   8. No incident process.
   9. No decision records.
   10. Docs without owners.
   Move a gap up when the evidence shows it already hurt (a revert, a hotfix chain, an incident).
4. **Name the fix for each gap.**

   | Gap | Fills it |
   |---|---|
   | Request, traceability | `/sdlc:ticket`, gate check `sdlc.traceability` |
   | Decision | `decisions` module (`/decisions:rfc`, `/decisions:adr`) |
   | Review | `/sdlc:change-review`, pull request template |
   | Test | `/sdlc:test-strategy` |
   | Gate | `gate` module (`/gate:gate-init`) |
   | Release, rollback | `/sdlc:release` |
   | Observe | `observability` module, `reliability:slo` |
   | Incident | `reliability` module (`incident`, `postmortem`, `on-call`) |
   | Docs | `docs` module |
   | Secrets | Rotate the secret first, then remove it from history with the user; add a secret scan rule with `/gate:add-rule` |
   | Lifecycle as a whole | `/sdlc:sdlc-init` |

5. **Write the report.** Present it in the chat. Write `docs/sdlc-audit-<YYYY-MM-DD>.md` only when the user asks.

## Output

1. One paragraph: how many of the eleven stages are present, partial and missing.
2. The ranked gap list: rank, stage, evidence (file, command or count), the fix, and the first command to run.
3. What is present and working, in one short list, so the team keeps it.
4. Probes that could not run (no `gh`, no access) and what they would have shown.

## Rules

- Read only. No file changes, no labels, no settings, no pushes.
- Every finding cites its evidence. A stage with no probe result is "not checked", never "missing".
- A found secret is reported by file and line with the value masked. Rotation comes before any history rewrite, and both are the user's actions.
- Describe the repository. Do not judge the people who built it.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/sdlc-audit/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
