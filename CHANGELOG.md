# Changelog

All notable changes to this project are listed here, newest first. Each release has a date and groups its changes under Added, Changed, Fixed, Removed and Security. A release is the git tag `v<version>` on `main`. Each plugin keeps its own version in its `plugin.json`, and every release lists them. To pin a release or roll back, see [Versions and rollback](README.md#versions-and-rollback).

## Unreleased

## [0.1.0] - 2026-10-12

The first tagged release. It covers all work on `main` from 2026-10-01 to 2026-10-12: 18 plugins with 72 skills.

Plugin versions: ai-ops 0.1.0, aieo 0.1.0, compliance 0.1.0, decisions 0.1.0, docs 0.1.0, finops 0.1.0, fit 0.2.0, gate 0.2.0, handover 0.1.1, hiring 0.1.0, observability 0.1.0, red-team 0.1.0, reliability 0.1.0, sdlc 0.2.0, security 0.2.0, stance 0.1.0, vault 0.1.0, vestige 0.1.0.

### Added

- `fit`: `/fit:repo-clinic` audits a public repository at its owner's request. It drafts one short public report with the top three gaps and one small pull request plan, and keeps secrets and security holes in a private note ([#4](https://github.com/uncovertechtalent/cto-powersuit/pull/4)).
- `sdlc`: `/sdlc:pre-push` runs the check jobs of a repository's workflows locally with preloop before a push ([#3](https://github.com/uncovertechtalent/cto-powersuit/pull/3)).
- `security`: `/security:private-terms`, a pre-push hook and a gate check that keep private terms out of public repositories. The term list stays on your machine ([#2](https://github.com/uncovertechtalent/cto-powersuit/pull/2)).
- `security` module: actions pinned by commit SHA and limited to an owner allowlist, a vulnerability scan of the lock files and an SBOM, a provenance check before you install a skill or an MCP server, key rotation, a read-only access review, threat models, and vulnerability intake, with gate checks for secrets and action owners ([#1](https://github.com/uncovertechtalent/cto-powersuit/pull/1)).
- `gate`: the `gate.actions-pinned` check fails a workflow that uses an action by tag or branch instead of by commit SHA ([e6cf1d2](https://github.com/uncovertechtalent/cto-powersuit/commit/e6cf1d2)).
- `gate`: runner 0.2 with partial and pending results, stable finding ids, a shared cache for rules, an after phase, requirement ids, and reporters such as an OSCAL-shaped run record ([827dab5](https://github.com/uncovertechtalent/cto-powersuit/commit/827dab5)).
- Modules, one plugin per CTO function, each with a gate check and its pass and fail fixtures: `ai-ops`, `aieo`, `compliance`, `decisions`, `docs`, `finops`, `fit`, `gate`, `handover`, `hiring`, `observability`, `red-team`, `reliability`, and `sdlc`.
- Knowledge infrastructure plugins: `vestige` (an output filter you calibrate to yourself), `vault` (a plain-Markdown vault with local search as an MCP server), and `stance` (stance filters).
- The overlay: every skill checks `$POWERSUIT_OVERLAY` for a private layer with your own data, and reports when the permission settings block that check.
- Releases: this changelog, the suit version in the marketplace manifest, and the commands to pin a release and roll back with both installers.
- A CI check that every plugin whose files changed since the last release tag carries a higher version, because `claude plugin update` compares the version in `plugin.json` only.
- A German README and man pages.

### Changed

- `gate`: the gate templates pin their actions to commit SHAs ([1eef984](https://github.com/uncovertechtalent/cto-powersuit/commit/1eef984)).
- `sdlc`: the review skill is now `/sdlc:change-review`.
- `sdlc`: `/sdlc:release` asks for a plugin version bump when the repository is a plugin marketplace.
- The README names the only install source: the two owner-qualified install commands or a clone of this repository.

### Fixed

- `sdlc`: `/sdlc:sdlc-audit` defects from its first live run. The probes moved into a script with recorded cases that pin each wrong finding ([1ee8b93](https://github.com/uncovertechtalent/cto-powersuit/commit/1ee8b93)).
- `sdlc`: the changelog draft script read any `word:` prefix, such as `README:`, as a Conventional Commits type and dropped it from the entry. It now reads only the standard types.
- `gate`: the `add-rule` finder works in zsh.
- Plugin versions: `gate`, `sdlc`, and `security` gained checks or skills after their version was public, without a version bump, so `claude plugin update` did not deliver them. They are now 0.2.0, and `handover` is 0.1.1.
