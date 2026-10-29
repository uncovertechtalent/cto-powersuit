# security

Security for a repository and the coding agents that work in it. The skills secure what the repository's CI and agents run from outside (actions, packages, agent skills, and MCP servers), keep secrets out of tracked files and rotate the ones that got out, review who can change the repository and every merge that went past a rule, list every admin entrance with the owner, the multi-factor method and the dated exceptions, model the threats of risky changes, turn vulnerability alerts into tickets with fix-by dates, and keep third-party text away from the agents that hold tools. Four gate checks run in the deploy gate of the `gate` module: no secret patterns in tracked files, actions only from owners on an allowlist, no private term in tracked files, file names and built pages, and an admin entrance inventory in which every entrance enforces multi-factor authentication or carries a dated exception. The third one reads a term list that stays on the owner's machine, so it runs in a pre-push hook and in local dry runs, and returns `n/a` in CI. The secrets check is also a pre-push hook, so a key is refused on the machine that pushes it, before the remote has it; the gate check then covers every tracked file from any machine.

The skills read, draft and propose. They never change repository settings, rulesets or organisation policies, never install anything without the user's go, and never print a secret value.

## Zero trust

The module works on one principle: nothing is trusted because of where it comes from. That covers inputs, identities, dependencies, and reports. Each is verified at the point where it is used, and every actor, human or agent, gets the least access its job needs. A report, such as a scan result or an agent's summary, counts once it has been checked against the thing it describes.

- `/security:supply-chain`: an action, package, skill, or MCP server counts by its pinned commit SHA, its provenance grade, and its known vulnerabilities, checked before install. Its name, its stars, and its owner's reputation count for nothing.
- `/security:private-terms`: every push is checked on the machine that pushes, before anything leaves it, whoever wrote the commits.
- `/security:secrets`: every push is scanned on the machine that pushes, before anything leaves it, and every tracked file is scanned in the gate, whoever wrote it. An exposed key is rotated, since nobody can prove it went unused.
- `/security:access-review`: every admin, key, and bypass actor is reviewed against the rules each window, and a merge past a rule is a finding, whoever made it.
- `/security:admin-entrances`: every place an admin signs in is listed, and its second factor is recorded from the system's setting, whoever says it is on. A deferral names the person who accepted it and the date it ends.
- `/security:quarantine`: third-party text never reaches an agent that holds tools. A reader with no tools turns it into a fixed-shape summary, and the agent treats every field as data.

Principle: [machinebehavior.io/inside/docs/sre/principle-zero-trust/](https://machinebehavior.io/inside/docs/sre/principle-zero-trust/), what the platform behind machinebehavior.io already does and the gaps it still has.

Install:

```bash
claude plugin install security@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/security:supply-chain` | Pins actions by commit SHA through the gate's `gate.actions-pinned` rule, sets the action-owner allowlist, adds Dependabot for actions and lock files, scans the lock files with osv-scanner (or the OSV database without an install), builds an SBOM, and grades the provenance and the data exposure of an agent skill, MCP server, or tool before anyone installs it, with a worked example of an honest project that trips two FakeGit signals. |
| `/security:secrets` | Installs a pre-push hook that refuses a push whose new commits add a secret or a `.env` file (an optional pre-commit hook does the same for a commit), with an allow file that needs a reason per entry. Installs the `security.secrets` gate check on `warn` and moves it to `block` after a recorded false-positive test, gives a one-line scan for repositories without the gate, and writes one key-rotation runbook per exposed secret: snapshot, generate inside the target, never print, verify, search for the old value, commit only redacted references. |
| `/security:access-review` | Read-only review of admins, collaborators, outside collaborators, deploy keys, visible token lists, rulesets and bypass actors, and every merge or push in the window that went past a rule, such as a merge with the admin bypass instead of the required review. For an organisation it reads whether two-factor authentication is required and which members and outside collaborators have it off, or says that the caller, who must be an organisation owner, could not read it. |
| `/security:admin-entrances` | Walks a team through every place an administrator can sign in (cloud consoles and root accounts, identity provider and email admin, directory, VPN and remote access, source control and CI/CD owners, DNS and registrar, password manager, SaaS admin consoles, on-premises servers, and device, backup, and vendor access) and records per entrance the owner, whether multi-factor authentication is enforced, the weakest method an admin can still use, and each exception with its reason, the person who accepted it and its end date. Writes `docs/security/admin-entrances.md` from a template, installs the `security.admin-entrances` check on `warn`, and names the page as the evidence for NIS2 Art 21(2)(j). |
| `/security:private-terms` | Keeps private terms out of public repositories and pages: names of prospective employers or clients, internal shorthand, family names in business copy, private hosts. The list stays outside every repository. A pre-push hook stops a push whose commits, messages, file names, or branch and tag names carry a term, before anything leaves the machine; a tree scan and the gate dry run read the files and the built pages. Reports show the file, the line and a label, never the term. |
| `/security:quarantine` | Keeps third-party text (posts, emails, READMEs, web pages, chat pastes) away from agents that hold tools. Raw text goes into a store outside every indexed folder and git work tree; the agent reads an item only as a fixed-shape envelope: facts measured in code, and a summary from a local model with no tools, typed, cleaned and capped. A PreToolUse hook and two deny rules refuse every other read of the store. A marking convention for knowledge bases: `trust: external` is excluded like a private note, `trust: third-party` stays searchable, with a label on every hit in a search index that reads the marker. |
| `/security:threat-model` | One page per RFC or risky change: assets, entry points including the text and tools of coding agents, threats by category, mitigations as tickets, and residual risk accepted by name. Linked from the RFC of `/decisions:rfc`. |
| `/security:vuln-intake` | Turns Dependabot alerts, advisories and scan results into ticket drafts in the `/sdlc:ticket` format, with a fix-by date per severity from the policy page, and lists what is past its date. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/security/` (see the root README). Use it for your owner allowlist, fix-by windows, approved registries, rotation schedules, and past access reviews.

## Scripts

Python 3.9+, standard library only. Each prints a grade or a list and changes nothing.

| Script | What it does |
|---|---|
| `skills/supply-chain/provenance.py` | Grades a GitHub repository before an install on two axes. Source risk (low, medium, high; exit 0, 1, 2) from the signals: owner against the registry or vendor, fork, account and repository age, copied history, the share of recent commits that touch only the README, README links to archives or executables, an archive or executable in the tree with little or no code beside it, and release binaries without a build provenance attestation. Exposure from what the tool reads once installed (`--data-scope`). Prints a recommendation and the commit SHA to pin; the user decides. Reads through `gh api`; downloads nothing. |
| `skills/supply-chain/osv_query.py` | Reads the package URLs of an SPDX or CycloneDX SBOM and asks the public OSV database for known vulnerabilities, with severity and fixed versions. For teams without a scanner installed. |
| `skills/access-review/access_review.py` | The access review: GET requests through `gh api` only. Maps every rule suite with result `bypass` to its pull request, and falls back to approvals per merged pull request when rule suites are not visible. Its MFA section reads the organisation's two-factor requirement and the members without it, and names what the caller could not read. |
| `checks/admin_entrances.py` | The `security.admin-entrances` check. Run on its own, `python3 checks/admin_entrances.py <repository root>` prints the hits of the inventory page and exits 1 when there are any; it reads the page and nothing else. |
| `skills/quarantine/quarantine.py` | The quarantine: `save` (from the clipboard or a file; prints the id and the hash, never the text), `list`, `remove`, `read` (the envelope from an ollama model with no tools; never the raw text or the raw reply, errors included), `guard` (the PreToolUse hook; fails open on input it cannot parse), and `settings` (the hook entry and deny rules to merge into `~/.claude/settings.json`). |
| `skills/vuln-intake/intake.py` | Ticket drafts from Dependabot alerts and OSV results, one per advisory and package, with fix-by dates from `docs/security/vuln-policy.md` and the already-tracked findings left out. |

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/.github/dependabot.yml` | `.github/dependabot.yml` | Monthly grouped updates for actions in workflows and composite actions; a commented block per package ecosystem |
| `templates/docs/security/index.md` | `docs/security/index.md` | Home page of the Security space: pages and records |
| `templates/docs/security/provenance-log.md` | `docs/security/provenance-log.md` | One row per third-party action, skill, MCP server, and tool with its source risk, data exposure, and decision |
| `templates/docs/security/admin-entrances.md` | `docs/security/admin-entrances.md` | One row per admin entrance: kind, admin holders, owner, MFA enforced, method, reason, accepted by, expires, last checked, and evidence, with the columns explained and a row hint per required kind |
| `templates/docs/security/vuln-policy.md` | `docs/security/vuln-policy.md` | Severity levels, fix-by windows (7, 30, 90, 180 days), exceptions and the monthly review |
| `templates/docs/security/_templates/runbook-key-rotation.md` | `docs/security/runbook-key-rotation-<secret>.md` | Rotation steps for one secret, with commands that never print the value |
| `templates/docs/security/_templates/threat-model.md` | `docs/security/threat-model-<name>.md` | Threat model for one RFC or change |

The doc pages carry the front matter of the `docs` module (`owner`, `reviewed`, `review_by`, `type`), so a filled page passes `docs.review`.

## Gate checks

### security.secrets

`checks/secrets.py` reads every file git tracks under the root (every file when the root is no git work tree) and reports values that match a secret pattern: Anthropic keys, `sk-` keys, AWS access key ids, GitHub tokens (classic and fine-grained), Slack tokens and private key blocks, plus any tracked `.env` file other than `.env.example`, `.env.sample`, `.env.template` and `.env.dist`. The patterns start at a word boundary. A hit shows the kind, the fixed prefix and the first 12 hex digits of the value's sha256, never the value. Options: `allow` (path globs), `allow_hashes` (sha256 prefixes of documented example values, 8 hex digits or more), `allow_file`, `tracked_only`, `env_files`, `patterns`, `max_bytes`. Known false positives go into `.secrets-allow` (path glob, kind or `*`, sha256 prefix or `*`, reason; an entry without a reason, with a bad hash, or one that allows every secret in every path is a hit). Fixtures: one file per hit kind and an allow entry without a reason in `fail/`; near misses in `pass/` (an HTML id with `risk-` and a long hex string, the patterns written as regular expressions, a public key block, environment variable references, an empty `.env.example`, a documented AWS example key allowed by its hash).

The same file is the pre-push hook, the optional pre-commit hook, and two read-only commands: `pre-push` (as `.git/hooks/pre-push`), `pre-commit`, `check` (what a push of the current branch would send) and `history` (the hits in the added lines of every commit, masked); see `/security:secrets`. The hook reads only what the push adds: the added lines of the commits the remote does not have yet, their messages, the names of added files, the messages of the tag objects on the way to the commit, the branch name, and new `.env` files; for a merge commit only what is new against every parent. It reads the patterns, `exclude`, `allow`, and `allow_hashes` from `gate/gate.json` of the pushed commit, so it agrees with the gate check. It ignores diff settings, text conversion programs, and replace refs in the clone, and reads files that git treats as binary, whatever their size (the gate check skips files over `max_bytes`). A scan step that runs longer than 60 seconds stops the push (`SECRETS_HOOK_SECONDS`, `0` for no limit, Unix only), so a pattern that backtracks without end cannot hang it. A hit is masked everywhere, file names and branch names included. `install-hook` writes `pre-push` (and `pre-commit`) as a dispatcher that runs `pre-push.d/*` in name order, so it runs beside the private-terms hook in either install order. **The hook ships on `block`**, although a new check starts on `warn` until a false-positive test moves it. Three reasons: the install is opt-in, since nothing runs until someone installs the hook; the exit from a false positive is one line in `.secrets-allow` with a reason; and the false-positive test below, over the added lines of every commit in 25 repositories, found no live secret and no hit outside this repository's made-up fixtures, which is the evidence the rule asks for before `block`. `--tier warn` reports and lets the push go on, for a trial on a repository with old test keys. The gate check `security.secrets` stays on `warn` until a repository records its own test. The exit from a false positive is a line in `.secrets-allow` with a reason; the hook output never names a way to skip it. Limits: a client-side hook runs only on the machines where it is installed, and a push that skips hooks is not checked, so GitHub secret scanning push protection (a repository setting the owner turns on, step 7 of the skill) stays the server-side control. The hook reads `gate/gate.json` and `.secrets-allow` from the pushed commit, so one push can change what it reads; it prints a note when a push changes either file, and both belong under CODEOWNERS. The hook trusts the remote-tracking refs of the clone to say what the remote has, and its globs follow `fnmatch`, where `*` also matches `/`.

### security.action-owners

`checks/action_owners.py` reads the same files as `gate.actions-pinned` and reports every action or reusable workflow from an owner not on the `owners` list, and every `docker://` image outside the `images` prefixes. Owners compare without case. The default list is the one owner this repository's own workflows use, `actions`; build yours with `python3 .github/actions/gate/rules/action_owners.py .`, which lists each owner and image with the files that use it. Pinning stays the job of `gate.actions-pinned`. Fixtures: an owner off the list, a typosquatted owner, a reusable workflow, a Docker image, flow style, and a composite action in `fail/`; mixed-case owners, local actions (`./` and `$/`), a commented reference, and a reference inside a string in `pass/`.

### security.private-terms

`checks/private_terms.py` reads the private term list from `$POWERSUIT_OVERLAY/security/private-terms.txt` (or the `terms_file` option) and reports every term in the tracked files, their file names, and the folders listed under `built`. Terms match without case, on word boundaries, across line breaks; HTML, XML and SVG are also read with tags removed and entities decoded, and soft hyphens and zero-width characters do not split a term. A hit names the file and line, with the term masked as `****` and named by its label from the list. Intended mentions go into `.private-terms-allow` (path glob, label, reason; an entry without a reason is a hit). Without a list the rule returns `n/a`, and it refuses a list inside the scanned tree. The same file is the pre-push hook (`pre-push`), a tree scan (`scan`), and a history count per label (`history`); see `/security:private-terms`. Fixtures: a made-up term list in `overlay/`; one file per hit kind in `fail/` (a lower-case term, a term across a line break, a term split by a tag, an entity, a soft hyphen, an address, a regular expression, a file name, an unlabelled term, an allow entry without a reason); near misses and an allowed mention in `pass/`.

### security.admin-entrances

`checks/admin_entrances.py` reads one page, `docs/security/admin-entrances.md` (option `page`), and finds its inventory tables by the columns Entrance and MFA enforced. Every such table counts, columns are read by name, and a row without outer pipes is still a row. It reads no provider API and needs no credentials: a gate check is a deterministic reader of files in the repository, and the live GitHub read belongs to `/security:access-review`. Without the page the rule returns `n/a`. A hit names the entrance and the field. It never prints a reason, owner, admin holders, accepted-by, or evidence text.

| Hit (`rule`) | Reported when |
|---|---|
| `no-table` | The page has no inventory table, or a table lacks one of the eleven columns |
| `kind-missing` | No row has a required kind (`required_kinds`: `cloud`, `identity`, `directory`, `remote-access`, `source-ci`, `dns-registrar`, `password-manager`, `saas`, `on-prem`, `endpoint`, `backup-monitoring`, `vendor`). A kind the organisation does not have needs a row with MFA enforced `n/a`, no admin holders, and a reason |
| `row-incomplete` | A row has no entrance name, owner, admin holders, or evidence, no valid last checked date (or one in the future), a kind or MFA enforced value outside the lists, a method outside the lists or `none` where MFA is enforced `yes`, `n/a` without a reason, or `n/a` with admin holders listed |
| `row-stale` | The row's last checked date lies more than `max_check_age_days` (120) before the page's `reviewed` date. A page without a valid `reviewed` date has no age to measure |
| `mfa-not-enforced` | MFA enforced is `no` or `partial` and the row lacks a reason, a person in Accepted by, or an Expires date in the form `YYYY-MM-DD` |
| `weak-method` | MFA enforced is `yes` and the weakest method is `push-no-match`, `sms`, `voice`, or `email` (with `phishing_resistant_only`, also `push` and `totp`), and the row lacks a reason, a person, or a date |
| `exception-expired` | A complete exception whose Expires date is before the day of the run. On the date itself it still holds |
| `exception-too-long` | A complete exception that ends more than `max_exception_days` (180) after the row's last checked date |

Placeholders in angle brackets, empty cells, and `-` count as missing. A row that holds only a kind and placeholders is an unfilled template row and is skipped, so a fresh copy of the template reports `kind-missing` for each required kind and nothing else. Several methods in one cell (`passkey, sms`) are read as the weakest of them. A few common spellings are read as their method: `security key`, `FIDO2`, `WebAuthn`, and `YubiKey` as `security-key`; `smart card` as `certificate`; `authenticator app` and `OTP` as `totp`; `text message` as `sms`; `push notification` as `push`.

Options: `page`, `required_kinds` (names without case), `phishing_resistant_only` (default `false`; set it as soon as admins hold keys, since CISA urges administrators to move to phishing-resistant methods), `max_exception_days`, and `max_check_age_days` (0 turns either off). Both spans are measured against dates on the page, never against the day of the run, so a pass fixture does not rot. For the same reason the pass fixture holds no exception: an exception carries a date that ends. The exception cases run in the module tests with a fixed date.

Ships on `warn`. The false-positive test that moves it to `block` needs a real inventory, and none exists yet (see the table below). Fixtures: a complete page in `pass/` (twelve rows, two methods in one cell, three kinds marked `n/a` with a reason and no admin holders); one row per hit rule in `fail/` (no exception, a weak method, an expired exception, a method of `none`, an unknown kind with no owner, a malformed date with no evidence, an exception that runs to 2099, an `n/a` row with admin holders, a row not read for 638 days) and four required kinds with no row.

### Enable them

With `/gate:add-rule` (path A: install a module's check), or by hand from a clone of this repository:

`security.private-terms` needs the private list on the machine that runs it; install it with `/security:private-terms`. The pre-push hook of `security.secrets` needs no gate: install it with `/security:secrets`, step 1. For the other three checks:

1. `cp plugins/security/checks/secrets.py plugins/security/checks/action_owners.py plugins/security/checks/admin_entrances.py <repo>/.github/actions/gate/rules/`
2. `mkdir -p <repo>/gate/fixtures && cp -R plugins/security/checks/fixtures/security.* <repo>/gate/fixtures/`
3. Add them to `gate/gate.json` on `warn`, with your owner list:

   ```json
   "security.secrets": {"tier": "warn"},
   "security.action-owners": {"tier": "warn", "options": {"owners": ["actions"], "images": []}},
   "security.admin-entrances": {"tier": "warn"}
   ```

4. Move each to `block` once the repository has no real hits, its fixtures are in place and your own false-positive test is recorded under the rule. Run one on its own with `python3 .github/actions/gate/run.py --only security.secrets --dry-run`.

False-positive tests, 2026-10-11, over 16 local repositories, 2 of them third-party clones, and 2026-10-18 for the hook:

| Rule | Corpus | Hits | Legitimate | Cross-check |
|---|---|---|---|---|
| `security.secrets` | 2,194 tracked text files | 0 | 0 | The `git grep -nIE` line of `/security:secrets` found 0 lines and 0 tracked `.env` files in the same repositories |
| `security.admin-entrances` | None: no repository has an inventory page yet | n/a | n/a | Not recorded. The first inventory a team fills is the corpus; until its hits are classified the rule stays on `warn` |
| `security.action-owners` (owners `actions`) | 5 repositories with workflows, 25 external references | 3 | 0 | A line count of `uses:` references gave the same 25. The 3 hits are owners not on the default list yet (an action publisher and the team's own organisation): the expected result before a team builds its list |
| `security.secrets` pre-push hook | The added lines of every commit on every branch, tag and remote-tracking ref of 25 local repositories (18 distinct, 1,062 distinct commits) | 11 | 0 | All 11 hits are made-up values in three clones of this repository: the check's own `fail/` fixtures (8), a repo-clinic test case (1), and two example keys in a test (2). `git log -p \| grep -E` with the same patterns found the same 10 lines, the eleventh hit being a `.env` file, and no line in any other repository. Decision: `block`. The 11 are listed in this repository's `.secrets-allow` with reasons, and the tests build their example keys at run time |

For the hook, *Legitimate* counts hits on a value that is neither a secret nor a planted test value. The hook reads the added lines of a commit, so a scan of all history is the same read as every push that was ever made.

## Compliance rows

The skills produce evidence for these rows of `compliance/control-map.csv`. The numbers are proposals with status `to-confirm`: map them with `/compliance:control-map`, and the control owner confirms each one against the licensed text. No standard text is used here.

| Skill | ISO/IEC 27001:2022 Annex A | NIS2 (Directive (EU) 2022/2555) |
|---|---|---|
| supply-chain | A.5.19, A.5.21, A.5.22, A.8.8 | Art 21(2)(d), Art 21(2)(e) |
| secrets | A.5.17, A.8.24 | Art 21(2)(h) |
| access-review | A.5.15, A.5.18, A.8.2 | Art 21(2)(i) |
| admin-entrances | A.5.17, A.8.2, A.8.5 | Art 21(2)(j) |
| threat-model | A.8.25, A.8.27 | Art 21(2)(a), Art 21(2)(e) |
| vuln-intake | A.8.8 | Art 21(2)(e) |

For TISAX, add the VDA ISA question numbers of the catalogue version you are assessed against.

## Tests

`tests/test_security.py` replays recorded cases with no network: 10 provenance cases (a vendor repository, an unverified owner, a throwaway fake, a taken-over account, a fork of the listed repository, a release-binary tool, a release with attested archives, copied history, README churn, a new tool installed from archives that reads agent data), 8 access-review cases (three of them for the MFA section), the access review's two-factor read against recorded organisation answers, the OSV lookup and the attestation lookup against recorded answers, the intake windows, and the four gate checks beyond their fixture runs (one hit per fail file, the allow options, tracked files only, the owner listing; for secrets the allow file, and the hooks in real pushes and commits against a local bare remote: each hit kind refused with the remote left unchanged, no value in any output, no output that names a way to skip the hook, only the added lines read, merges, messages, tags, branch names, and file names, the gate configuration of the pushed commit, git settings and attributes that would hide a line, the dispatcher beside the private-terms hook in both install orders, a git template, and the repository's own files; for admin entrances one case per hit rule, the expiry day, the method bar, the options, the page shape, the template in step with the check, and a canary that no cell value reaches the output; for private terms also no term in any output, list errors that name a line only, built folders, the history count, and the pre-push hook in real pushes to a local remote, with the exits from a missing list run and no output that names a way past the hook). `scripts/test_checks.py` at the repository root runs all four checks against their pass and fail fixtures, with the fixture list as `POWERSUIT_OVERLAY` for private terms.

`evals/secrets-hook-stops-push` is a behaviour eval for step 1 of `/security:secrets`, run with `claude plugin eval` (see "Evals" in the root README, results in EVALS.md). Every run is a model call, so it runs locally and not in CI. The fixture repository has an unpushed commit with a made-up access key id and a bare remote that logs every ref it receives. The eval sandbox switches git hooks off and blocks writes under `.git/hooks`, so the case writes the hook into a template folder and grades the skill's `check` run on the branch. The graders check that the hook is installed, that the hit shows masked and the reply does not repeat the value, that the branch does not reach the remote, that the reply offers a `.secrets-allow` entry with a reason and waits for the user, and that no command or reply goes around the hook.

Demo: [machinebehavior.io/conformity/](https://machinebehavior.io/conformity/), the gate page of the platform behind machinebehavior.io, where the pinned-actions check runs on every deploy.
