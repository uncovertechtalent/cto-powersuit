# security

Security for a repository and the coding agents that work in it. The skills secure what the repository's CI and agents run from outside (actions, packages, agent skills, and MCP servers), keep secrets out of tracked files and rotate the ones that got out, review who can change the repository and every merge that went past a rule, model the threats of risky changes, and turn vulnerability alerts into tickets with fix-by dates. Three gate checks run in the deploy gate of the `gate` module: no secret patterns in tracked files, actions only from owners on an allowlist, and no private term in tracked files, file names and built pages. The third one reads a term list that stays on the owner's machine, so it runs in a pre-push hook and in local dry runs, and returns `n/a` in CI.

The skills read, draft and propose. They never change repository settings, rulesets or organisation policies, never install anything without the user's go, and never print a secret value.

Install:

```bash
claude plugin install security@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/security:supply-chain` | Pins actions by commit SHA through the gate's `gate.actions-pinned` rule, sets the action-owner allowlist, adds Dependabot for actions and lock files, scans the lock files with osv-scanner (or the OSV database without an install), builds an SBOM, and grades the provenance and the data exposure of an agent skill, MCP server, or tool before anyone installs it, with a worked example of an honest project that trips two FakeGit signals. |
| `/security:secrets` | Installs the blocking `security.secrets` check, gives a one-line scan for repositories without the gate, and writes one key-rotation runbook per exposed secret: snapshot, generate inside the target, never print, verify, search for the old value, commit only redacted references. |
| `/security:access-review` | Read-only review of admins, collaborators, outside collaborators, deploy keys, visible token lists, rulesets and bypass actors, and every merge or push in the window that went past a rule, such as a merge with the admin bypass instead of the required review. |
| `/security:private-terms` | Keeps private terms out of public repositories and pages: names of prospective employers or clients, internal shorthand, family names in business copy, private hosts. The list stays outside every repository. A pre-push hook stops a push whose commits, messages, file names, or branch and tag names carry a term, before anything leaves the machine; a tree scan and the gate dry run read the files and the built pages. Reports show the file, the line and a label, never the term. |
| `/security:threat-model` | One page per RFC or risky change: assets, entry points including the text and tools of coding agents, threats by category, mitigations as tickets, and residual risk accepted by name. Linked from the RFC of `/decisions:rfc`. |
| `/security:vuln-intake` | Turns Dependabot alerts, advisories and scan results into ticket drafts in the `/sdlc:ticket` format, with a fix-by date per severity from the policy page, and lists what is past its date. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/security/` (see the root README). Use it for your owner allowlist, fix-by windows, approved registries, rotation schedules, and past access reviews.

## Scripts

Python 3.9+, standard library only. Each prints a grade or a list and changes nothing.

| Script | What it does |
|---|---|
| `skills/supply-chain/provenance.py` | Grades a GitHub repository before an install on two axes. Source risk (low, medium, high; exit 0, 1, 2) from the signals: owner against the registry or vendor, fork, account and repository age, copied history, the share of recent commits that touch only the README, README links to archives or executables, and release binaries without a build provenance attestation. Exposure from what the tool reads once installed (`--data-scope`). Prints a recommendation and the commit SHA to pin; the user decides. Reads through `gh api`; downloads nothing. |
| `skills/supply-chain/osv_query.py` | Reads the package URLs of an SPDX or CycloneDX SBOM and asks the public OSV database for known vulnerabilities, with severity and fixed versions. For teams without a scanner installed. |
| `skills/access-review/access_review.py` | The access review: GET requests through `gh api` only. Maps every rule suite with result `bypass` to its pull request, and falls back to approvals per merged pull request when rule suites are not visible. |
| `skills/vuln-intake/intake.py` | Ticket drafts from Dependabot alerts and OSV results, one per advisory and package, with fix-by dates from `docs/security/vuln-policy.md` and the already-tracked findings left out. |

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/.github/dependabot.yml` | `.github/dependabot.yml` | Monthly grouped updates for actions in workflows and composite actions; a commented block per package ecosystem |
| `templates/docs/security/index.md` | `docs/security/index.md` | Home page of the Security space: pages and records |
| `templates/docs/security/provenance-log.md` | `docs/security/provenance-log.md` | One row per third-party action, skill, MCP server, and tool with its source risk, data exposure, and decision |
| `templates/docs/security/vuln-policy.md` | `docs/security/vuln-policy.md` | Severity levels, fix-by windows (7, 30, 90, 180 days), exceptions and the monthly review |
| `templates/docs/security/_templates/runbook-key-rotation.md` | `docs/security/runbook-key-rotation-<secret>.md` | Rotation steps for one secret, with commands that never print the value |
| `templates/docs/security/_templates/threat-model.md` | `docs/security/threat-model-<name>.md` | Threat model for one RFC or change |

The doc pages carry the front matter of the `docs` module (`owner`, `reviewed`, `review_by`, `type`), so a filled page passes `docs.review`.

## Gate checks

### security.secrets

`checks/secrets.py` reads every file git tracks under the root (every file when the root is no git work tree) and reports values that match a secret pattern: Anthropic keys, `sk-` keys, AWS access key ids, GitHub tokens (classic and fine-grained), Slack tokens and private key blocks, plus any tracked `.env` file other than `.env.example`, `.env.sample`, `.env.template` and `.env.dist`. The patterns start at a word boundary. A hit shows the kind, the fixed prefix and the first 12 hex digits of the value's sha256, never the value. Options: `allow` (path globs), `allow_hashes` (sha256 prefixes of documented example values, 8 hex digits or more), `tracked_only`, `env_files`, `patterns`, `max_bytes`. Fixtures: one file per hit kind in `fail/`; near misses in `pass/` (an HTML id with `risk-` and a long hex string, the patterns written as regular expressions, a public key block, environment variable references, an empty `.env.example`).

### security.action-owners

`checks/action_owners.py` reads the same files as `gate.actions-pinned` and reports every action or reusable workflow from an owner not on the `owners` list, and every `docker://` image outside the `images` prefixes. Owners compare without case. The default list is the one owner this repository's own workflows use, `actions`; build yours with `python3 .github/actions/gate/rules/action_owners.py .`, which lists each owner and image with the files that use it. Pinning stays the job of `gate.actions-pinned`. Fixtures: an owner off the list, a typosquatted owner, a reusable workflow, a Docker image, flow style, and a composite action in `fail/`; mixed-case owners, a local action, a commented reference, and a reference inside a string in `pass/`.

### security.private-terms

`checks/private_terms.py` reads the private term list from `$POWERSUIT_OVERLAY/security/private-terms.txt` (or the `terms_file` option) and reports every term in the tracked files, their file names, and the folders listed under `built`. Terms match without case, on word boundaries, across line breaks; HTML, XML and SVG are also read with tags removed and entities decoded, and soft hyphens and zero-width characters do not split a term. A hit names the file and line, with the term masked as `****` and named by its label from the list. Intended mentions go into `.private-terms-allow` (path glob, label, reason; an entry without a reason is a hit). Without a list the rule returns `n/a`, and it refuses a list inside the scanned tree. The same file is the pre-push hook (`pre-push`), a tree scan (`scan`), and a history count per label (`history`); see `/security:private-terms`. Fixtures: a made-up term list in `overlay/`; one file per hit kind in `fail/` (a lower-case term, a term across a line break, a term split by a tag, an entity, a soft hyphen, an address, a regular expression, a file name, an unlabelled term, an allow entry without a reason); near misses and an allowed mention in `pass/`.

### Enable them

With `/gate:add-rule` (path A: install a module's check), or by hand from a clone of this repository:

`security.private-terms` needs the private list on the machine that runs it; install it with `/security:private-terms`. For the other two:

1. `cp plugins/security/checks/secrets.py plugins/security/checks/action_owners.py <repo>/.github/actions/gate/rules/`
2. `mkdir -p <repo>/gate/fixtures && cp -R plugins/security/checks/fixtures/security.* <repo>/gate/fixtures/`
3. Add both to `gate/gate.json` on `warn`, with your owner list:

   ```json
   "security.secrets": {"tier": "warn"},
   "security.action-owners": {"tier": "warn", "options": {"owners": ["actions"], "images": []}}
   ```

4. Move each to `block` once the repository has no real hits, its fixtures are in place and your own false-positive test is recorded under the rule. Run one on its own with `python3 .github/actions/gate/run.py --only security.secrets --dry-run`.

False-positive tests, 2026-10-11, over 16 local repositories, 2 of them third-party clones:

| Rule | Corpus | Hits | Legitimate | Cross-check |
|---|---|---|---|---|
| `security.secrets` | 2,194 tracked text files | 0 | 0 | The `git grep -nIE` line of `/security:secrets` found 0 lines and 0 tracked `.env` files in the same repositories |
| `security.action-owners` (owners `actions`) | 5 repositories with workflows, 25 external references | 3 | 0 | A line count of `uses:` references gave the same 25. The 3 hits are owners not on the default list yet (an action publisher and the team's own organisation): the expected result before a team builds its list |

## Compliance rows

The skills produce evidence for these rows of `compliance/control-map.csv`. The numbers are proposals with status `to-confirm`: map them with `/compliance:control-map`, and the control owner confirms each one against the licensed text. No standard text is used here.

| Skill | ISO/IEC 27001:2022 Annex A | NIS2 (Directive (EU) 2022/2555) |
|---|---|---|
| supply-chain | A.5.19, A.5.21, A.5.22, A.8.8 | Art 21(2)(d), Art 21(2)(e) |
| secrets | A.5.17, A.8.24 | Art 21(2)(h) |
| access-review | A.5.15, A.5.18, A.8.2 | Art 21(2)(i) |
| threat-model | A.8.25, A.8.27 | Art 21(2)(a), Art 21(2)(e) |
| vuln-intake | A.8.8 | Art 21(2)(e) |

For TISAX, add the VDA ISA question numbers of the catalogue version you are assessed against.

## Tests

`tests/test_security.py` replays recorded cases with no network: 10 provenance cases (a vendor repository, an unverified owner, a throwaway fake, a taken-over account, a fork of the listed repository, a release-binary tool, a release with attested archives, copied history, README churn, a new tool installed from archives that reads agent data), 5 access-review cases, the OSV lookup against recorded answers, the intake windows, and the three gate checks beyond their fixture runs (one hit per fail file, the allow options, tracked files only, the owner listing; for private terms also no term in any output, list errors that name a line only, built folders, the history count, and the pre-push hook in real pushes to a local remote). `scripts/test_checks.py` at the repository root runs all three checks against their pass and fail fixtures, with the fixture list as `POWERSUIT_OVERLAY` for private terms.

Demo: [machinebehavior.io/conformity/](https://machinebehavior.io/conformity/), the gate page of the platform behind machinebehavior.io, where the pinned-actions check runs on every deploy.
