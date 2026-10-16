# Changelog

All notable changes to this project are listed here, newest first. Each release has a date and groups its changes under Added, Changed, Fixed, Removed and Security. A release is the git tag `v<version>` on `main`. Each plugin keeps its own version in its `plugin.json`, and every release lists them. To pin a release or roll back, see [Versions and rollback](README.md#versions-and-rollback).

## Unreleased

## [0.3.0] - 2026-10-16

A new module, `direction`, with the weekly direction review and its decision records, and `/fit:file-findings`, which files a review's findings as GitHub Issues with the cockpit's labels and writes a scorecard per area.

Plugin versions: ai-ops 0.2.0, aieo 0.1.0, compliance 0.1.0, decisions 0.1.0, direction 0.1.1, docs 0.1.0, finops 0.1.0, fit 0.3.1, gate 0.2.1, handover 0.1.3, hiring 0.1.0, observability 0.1.0, red-team 0.1.0, reliability 0.1.0, sdlc 0.2.3, security 0.3.0, stance 0.1.0, vault 0.1.0, vestige 0.1.0.

To roll back, pin v0.2.0 again: remove the marketplace, add it at `#v0.2.0`, and install the plugins again ([Versions and rollback](https://github.com/uncovertechtalent/cto-powersuit#versions-and-rollback)).

### Added

- `fit` 0.3.0: `/fit:file-findings` files a review's findings as GitHub Issues in the company's own repository, with the cockpit's labels (`area:<area>`, `kind:finding`, `kind:decision`, `kind:action`) and `severity:<level>` with the fix-by windows of `/security:vuln-intake`. A dry run prints every issue before anything is created; `--create` adds the missing labels, files each item of a review once, and holds an item whose title an issue already has. Security items and items marked private never go into an issue on a repository that is not private: they are kept back for a private channel and still count on the scorecard. A secret pattern or an @mention stops the run, and read-only access stops it before any write. `scorecard` writes one scorecard per area: checks run, findings by severity, and a one-line verdict.
- `direction` 0.1.0: the module for the direction area. `/direction:review` reads the tracker (`bd list --json --all --limit 0`, `bd ready --json`, `bd blocked --json`) across all areas and writes a dated memo: what moved per area, what is blocked and by what, the proposed allocation of the week, and the decisions the owner must take. Each decision the owner confirms becomes a tracker item with `area:direction` and `kind:decision`, closed with the decision as its reason, and the memo line names the record. The gate check `direction.review-memo` reports a memo without a date or period, without one of the four sections, with a decision line that has no status, or with a decisions section that has no line at all.

### Changed

- `direction` 0.1.1: the memo's page type is `reference`, the one the docs module's build and its `docs.review` check accept; the memo has one home, `docs/direction/review-<date>.md`, and an overlay names another folder; the tracker exports go to a `mktemp -d` folder; the report names the share of items without an `area:` label; the check reports a misconfigured `decisions` option once and accepts one pair of parentheses in a drop reason ([#24](https://github.com/uncovertechtalent/cto-powersuit/issues/24)).
- `fit` 0.3.1 and `handover` 0.1.3: the order table of `/fit:estate-assessment` and the training defaults of `/handover:owner-training` list `direction` ([#24](https://github.com/uncovertechtalent/cto-powersuit/issues/24)).
- `fit` 0.3.0 and `handover` 0.1.2: the module signal tables in `docs/fit.md` and `docs/handover.md` list `direction` (`docs/direction/index.md`).

## [0.2.0] - 2026-10-14

Two new skills, `/security:quarantine` and `/ai-ops:tool-audit`, a local review runner for pull requests, behaviour evals with failure paths, and release provenance: from this release on, every release carries a source tarball with its sha256 and a build provenance attestation.

Plugin versions: ai-ops 0.2.0, aieo 0.1.0, compliance 0.1.0, decisions 0.1.0, docs 0.1.0, finops 0.1.0, fit 0.2.0, gate 0.2.1, handover 0.1.1, hiring 0.1.0, observability 0.1.0, red-team 0.1.0, reliability 0.1.0, sdlc 0.2.3, security 0.3.0, stance 0.1.0, vault 0.1.0, vestige 0.1.0.

To roll back, pin v0.1.0 again: remove the marketplace, add it at `#v0.1.0`, and install the plugins again ([Versions and rollback](https://github.com/uncovertechtalent/cto-powersuit#versions-and-rollback)).

### Added

- `security` 0.3.0: `/security:quarantine` keeps third-party text away from agents that hold tools. `quarantine.py save` puts raw text (a post, an email, a README, a web page) into a store outside every indexed folder and git work tree; `read` returns a fixed-shape envelope from a local ollama model with no tools, and never the raw text; `guard` is a PreToolUse hook that, with two deny rules, refuses every other read of the store. A marking convention for knowledge bases: `trust: external` is excluded like a private note, `trust: third-party` stays searchable, with a label on every hit in a search index that reads the marker ([#15](https://github.com/uncovertechtalent/cto-powersuit/pull/15)).
- `ai-ops` 0.2.0: `/ai-ops:tool-audit`, an audit trail of agent tool calls from Claude Code's `tool_decision` and `tool_result` events: allowed, denied, and asked counts per tool on a dashboard, the `AgentToolDenialsSpike` alert, a runbook page, and `tool_audit.py` for the monthly review record.
- `sdlc` 0.2.3: `skills/change-review/review-pr.sh`, the local review runner until CI has a token. It runs `/sdlc:change-review <n> kb` with the limits of the CI workflow: the reviewer from a clean clone of `main`, the pull request as files, no shell and no network, the knowledge base through its MCP search tools only. It posts or updates one advisory comment after a private-terms scan, refuses forks, bots and drafts without `--allow-external`, and posts a saved review only while the pull request head is unchanged ([#9](https://github.com/uncovertechtalent/cto-powersuit/issues/9)).
- Behaviour evals for `/sdlc:sdlc-audit`, `/sdlc:pre-push`, and `/fit:repo-clinic` with `claude plugin eval`: six cases, five of them failure paths. Results and costs in [EVALS.md](https://github.com/uncovertechtalent/cto-powersuit/blob/v0.2.0/EVALS.md).
- Release provenance: pushing a tag `v<x.y.z>` builds a source tarball of the tag and its sha256, attests both with build provenance, and attaches them to the GitHub release. Check a file with `gh attestation verify <file> --repo uncovertechtalent/cto-powersuit` ([Versions and rollback](https://github.com/uncovertechtalent/cto-powersuit#versions-and-rollback)). v0.1.0 has no files and no attestation.
- CI: zizmor on `.github` with pinned wheel hashes, Dependabot for the actions, zizmor and Claude Code pins (monthly, grouped, 7-day cooldown), CODEOWNERS, a change-review workflow that runs `/sdlc:change-review` from the base branch on each pull request and posts one comment, and a `.coderabbit.yaml` with public path instructions.
- CI: a shellcheck job for every tracked shell script.

### Changed

- `sdlc` 0.2.2: `/sdlc:change-review` reads the repository's decision records and conventions before the diff, and writes a recorded choice as a note ("intentional per ADR-NNNN"), not a finding. With `kb`, on the user's machine only, it also reads a private knowledge base and posts one comment that cites public files only, after a private-terms scan: `claude "/sdlc:change-review 42 kb"`.
- `security` 0.2.1: `provenance.py` looks up a build provenance attestation for each release asset by its sha256 digest. An attested asset no longer counts as an unverified binary, and the recommendation names `gh attestation verify`.
- `sdlc` 0.2.1: the rules of `/sdlc:pre-push` hold when the user asks for the step. In the first eval run, 2 of 3 runs gave way to an explicit request for the deploy job or `--push`.
- `security`: the module README links the zero trust principle page, with what the platform behind machinebehavior.io already does and the gaps it still has ([#17](https://github.com/uncovertechtalent/cto-powersuit/pull/17)).

### Fixed

- CI: the tool pins (Claude Code, zizmor) moved from `.github/` to `ci/`. Dependabot's service refused to open a pull request for the npm pin under `.github/` ([#13](https://github.com/uncovertechtalent/cto-powersuit/issues/13)).
- `gate` 0.2.1 and `security` 0.2.2: `gate.actions-pinned` and `security.action-owners` treat GitHub's self-repository form (`uses: $/...`) as local, like `./`. Before, the pin check reported it as `no-ref` and the owner check as owner `$` ([#11](https://github.com/uncovertechtalent/cto-powersuit/issues/11)). Repositories that already have the checks keep the old files: `/gate:gate-init` copies `checks/actions_pinned.py` with `cp -n`, which never overwrites, and step 3 of `/security:supply-chain` copied `checks/action_owners.py` once. Copy both into `.github/actions/gate/rules/` again with plain `cp`, and their pass fixtures too, so the installed fixtures cover `$/`. A test now fails when the two checks' `LOCAL` prefixes or `USES` pattern differ.
- `ai-ops`: `/ai-ops:metering` told teams to put the telemetry variables in the repository's `.claude/settings.json`, where Claude Code ignores them. It now names the shell, user settings, and managed settings.

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
