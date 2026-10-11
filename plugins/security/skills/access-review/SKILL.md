---
name: access-review
description: >
  Read-only review of who can change a GitHub repository and how: admins,
  collaborators and outside collaborators, deploy keys, token lists where the
  caller can see them, rulesets and their bypass actors, classic branch
  protection, and every merge or push that went past a rule, such as a pull
  request merged with the admin bypass instead of the required review. Never
  changes a setting. Use for a quarterly access review, before an audit, when
  someone leaves, or when a team wants to know whether its review rule holds.
  Activates on "/access-review", "who has access", "access review", "who can
  push to main", "were reviews bypassed", "admin merges", "list deploy keys".
user-invocable: true
---

# Access review

A review rule protects main only when nobody goes around it. This review lists who can change the repository, with which rights, and every push or merge in the window that went past a rule. It reads through `gh api` with GET requests only and changes nothing.

## Inputs

- **Repository**: `owner/repo`.
- **Window**: default 30 days. The bypass history comes from the rule suites of the last day, week or month, whichever covers the window.
- **Caller**: `gh` logged in as an account that can read the repository's settings. Admin rights give the full picture; with less, the review says what it could not see.

## Steps

1. **Run the review.**

   ```bash
   python3 <this skill's folder>/access_review.py <owner/repo> --days 30 --observations-out access-<repo>-<YYYY-MM-DD>.json
   ```

   It reads, in this order: the repository; collaborators with their roles; outside collaborators and organisation admins (organisations only); fine-grained token and credential lists (organisations only, where visible); deploy keys; rulesets with their rules and bypass actors; classic branch protection of the default branch; and the rule suites with result `bypass` on the default branch, each mapped to the pull request that carried it. Without access to rule suites, it reads the merged pull requests of the window and their approving reviews instead.
2. **Read the flags.**

   | Flag | Level | Meaning |
   |---|---|---|
   | `bypass-merge` | red | A pull request merged past a rule, for example with `gh pr merge --admin` when the required approving review was missing. The flag names the pull request, the actor, the time, and the rule suite id |
   | `bypass-push` | red | A push to the default branch past a rule, such as the rule that changes go through a pull request |
   | `merged-below-approvals` | red | Fallback without rule suite access: a pull request merged with fewer approvals than the rules require |
   | `no-branch-rules` | red | No active ruleset and no branch protection on the default branch |
   | `bypass-always` | amber | A ruleset lets an actor bypass on every push and merge. Bypass mode `pull_request` limits the bypass to pull requests, where it shows in the record |
   | `admins-not-enforced` | amber | Classic branch protection does not apply to admins |
   | `outside-collaborator` | amber | An outside collaborator holds write, maintain or admin rights |
   | `deploy-key-write` | amber | A deploy key can push |
   | `deploy-key-stale` | amber | A deploy key unused for more than 90 days, or never used since it was added |

   The output also names the admins, the required number of approvals, and each list the caller could not see, with the API's answer. A fine-grained token list needs a GitHub App token, and the credential list exists only for organisations with SAML single sign-on. A 404 on either means the caller could not see the list; it says nothing about its content.
3. **Check by hand where the script cannot see.** Personal access tokens and SSH keys of members, GitHub App and OAuth app installations with access to the repository (the organisation's settings list them), and the CI secrets (`gh api repos/<owner>/<repo>/actions/secrets` lists names and dates, never values).
4. **Name the cause of each bypass.** For every red flag, ask the user why. A one-person repository with a required review has no reviewer, so every merge needs the bypass. Recording that as a known exception is honest; leaving a rule in place that every merge breaks is not a control. The user then picks one of: a second reviewer, a required status check in place of the review (a ruleset with `required_status_checks` and no approval count), or a written exception with an owner and an end date.
5. **Propose changes; the user makes them.** Each proposal names the setting, the current value, the new value, and the reason. Typical ones: bypass mode `pull_request` instead of `always`; fewer admins; read-only deploy keys; remove stale keys and departed collaborators; expiry dates on tokens. Do not change any of them yourself.
6. **Write the record** when the user asks: `docs/security/access-review-<YYYY-MM-DD>.md` with the window, the caller, the flags with their evidence, the lists that were not visible, and the decisions with their owners. Keep logins and key titles; leave out email addresses.

## Output

- The flag list with evidence: pull request numbers, rule suite ids, actors, and times.
- Admins, collaborators by role, deploy keys, rulesets, and bypass actors.
- What the caller could not see.
- Proposed changes, each for the user to make.

## Rules

- Read only. GET requests only; no `gh api -X`, no `-f` fields, no settings pages changed, no rulesets edited.
- Every finding cites its evidence: a rule suite id, a pull request number or the API answer.
- Describe the access and the events. Do not judge the people who used a bypass; ask why.
- Keep the observations file out of public repositories: it lists people and keys.

## Check the script

`python3 "${CLAUDE_PLUGIN_ROOT}/tests/test_security.py"` replays recorded cases: a clean repository, admin bypass merges and pushes, no branch rules, no rule suite access with the fallback, and stale or writable deploy keys with outside collaborators. Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/access-review/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
