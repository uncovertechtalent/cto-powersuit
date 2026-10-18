---
name: secrets
description: >
  Keep secret values out of the repository and rotate the ones that got out: a
  pre-push hook that refuses a push whose new commits add a secret, a gate
  check for secret patterns and .env files in tracked files, a one-line scan
  for repositories without the gate, and a key-rotation runbook per secret
  that never prints the value. Use when a scan or a review finds a key in the
  repository, before a repository goes public, when someone with access leaves,
  on a rotation schedule, or to stop a key before it is pushed. Activates on
  "/secrets", "scan for secrets", "we committed a key", "rotate this key", "key
  rotation runbook", "is there a secret in this repo", "block secrets in CI",
  "pre-push secrets hook", "stop a key before the push".
user-invocable: true
---

# Secrets

A secret in a tracked file reaches every clone, every fork and every CI log that prints the file. Removing the line later does not take it back: the value stays in the history. So the fix has three parts. A pre-push hook refuses the push that adds a secret, before anything leaves the machine. A gate check reads every tracked file on each deploy and on a schedule, which covers pushes from machines without the hook. A rotation retires every value that was ever exposed.

| Control | Runs | Effect | Covers |
|---|---|---|---|
| Pre-push hook (step 1) | On the pushing machine, at `git push` | Prevents: the push is refused before the remote has anything | Pushes from machines where it is installed |
| Pre-commit hook (step 1, optional) | On the committing machine, at `git commit` | Prevents: the commit is refused, so the value never enters local history | Commits on machines where it is installed |
| Gate check `security.secrets` (steps 2 to 4) | In CI, on a push to main, weekly, and by hand | Detects: the value is already in the remote's history when it reports | Every tracked file, from any machine |
| GitHub secret scanning push protection (step 7) | On GitHub, at the push | Prevents, for the token formats GitHub knows | Every push to the repository, from any machine; a repository setting the owner turns on |

A client-side hook runs only where it is installed, and a push that skips hooks is not checked. The gate check and push protection are the controls that do not depend on one machine.

## Inputs

- **Repository root** (default: the current directory).
- **For a rotation:** the secret's name, the one place the live value lives (a container's settings file, a secret store path, a CI secret), and the systems that read it.

## The gate check

`security.secrets` (file `checks/secrets.py` in this plugin) reads every file git tracks under the root, or every file when the root is no git work tree. It reports:

| Hit kind | Pattern |
|---|---|
| `anthropic-key` | `sk-ant-` and 20 or more key characters |
| `sk-key` | `sk-` and 32 or more letters and digits |
| `aws-access-key-id` | `AKIA` and 16 capitals or digits |
| `github-token` | `ghp_`, `gho_`, `ghu_`, `ghs_` or `ghr_` and 30 or more characters |
| `github-fine-grained-token` | `github_pat_` and 40 or more characters |
| `slack-token` | `xoxa-`, `xoxb-`, `xoxp-`, `xoxr-` or `xoxs-` and 10 or more characters |
| `private-key` | a `-----BEGIN ... PRIVATE KEY-----` line |
| `env-file` | a tracked `.env` or `.env.<name>` file; `.env.example`, `.env.sample`, `.env.template` and `.env.dist` are allowed |

Each pattern starts at a word boundary, so ids such as `risk-4f9a...` in HTML do not match. A hit shows the kind, the fixed prefix and the first 12 hex digits of the value's sha256, never the value: `config/app.ini:2 aws-access-key-id AKIA**** sha256:1a5d44a2dca1`. Binary files and files over 400,000 bytes are skipped, the second ones counted in the detail.

Options in `gate/gate.json`:

| Option | Default | Use |
|---|---|---|
| `allow` | `[]` | Path globs exempt from the rule, such as `docs/examples/*` |
| `allow_hashes` | `[]` | The sha256 prefixes of known example values, copied from the hits (8 hex digits or more). Allows one documented value without exempting a path |
| `allow_file` | `.secrets-allow` | The allow file with a reason per entry, relative to the root. The hooks read it too |
| `tracked_only` | `true` | `false` also reads untracked files, for a build output folder |
| `env_files` | `true` | `false` turns the `.env` rule off |
| `patterns` | the table above | Add the token formats of the team's own providers as `"kind": ["<regex>", "<prefix>****"]` |

## The hook

`checks/secrets.py` is the gate check and also the hook. At `git push`, for each ref, it reads what the remote does not have yet:

- every line the new commits add (a line that only moved is not an added line), also in files git treats as binary;
- the commit messages, the message of every tag object on the way from the pushed tag to its commit (a tag can point to a tag), and the branch or tag name;
- the names of the files the commits add, since a file can be named like a key;
- every new `.env` file other than `.env.example`, `.env.sample`, `.env.template` and `.env.dist`.

For a merge commit it reads what is new against every parent, so lines that come in with commits the remote already has are not read twice. It uses the patterns, the `exclude` list, `allow`, and `allow_hashes` of `gate/gate.json` in the pushed commit when the file is there, so the hook and the gate check agree; the defaults of the table above apply otherwise. It ignores diff settings, text conversion programs, and replace refs of the clone, which could otherwise hide a line. A push to a URL reads like a push by remote name when a configured remote has that URL; to any other URL, a new ref is read from the start of its history. A scan step that runs longer than 60 seconds (`SECRETS_HOOK_SECONDS`, `0` turns the limit off, Unix only) stops the push, so a pattern that backtracks without end cannot hang it.

A hit shows the commit, the place, the kind, the fixed prefix, and the first 12 hex digits of the sha256, never the value, also not inside a file name or a branch name:

```text
secrets: push to origin (1 commits) stopped, 1 hits:
  3f2a9c1b7d4e config/app.ini:2 aws-access-key-id AKIA**** sha256:1a5d44a2dca1
```

**Level: the hook ships on `block`.** A hit stops the push and exits 1. The false-positive test is recorded in the README of this plugin: the added lines of every commit in 25 local repositories gave no hit on a live secret and no hit outside the made-up values of this repository's own test fixtures. `--tier warn` reports the hits and lets the push go on, for a first week on a repository where you expect old test keys. A scan that cannot run (a broken `gate/gate.json`, a ref that is no commit) stops the push on `block`, because nothing was checked.

**The way out of a false positive is the allow file.** `.secrets-allow` at the repository root, one line per known value, committed with the change that needs it:

```text
docs/aws-example.md aws-access-key-id sha256:1a5d44a2dca1 Example key id from the vendor documentation
```

The fields are a path glob, a kind or `*`, the sha256 prefix from the hit (8 hex digits or more) or `*`, and the reason. An entry without a reason, with a bad hash, or with `*` for the hash on a glob that matches every path counts for nothing and is a hit itself. A message, a tag message, and a ref name are matched as `commit-message`, `tag-message`, and `ref-name`. The hook reads the file as the pushed commit has it, so an edit in the work tree allows nothing, and the entry shows in the diff that a reviewer reads. The gate check reads the same file (`allow_file` option). A live value is never allowed: take it out of the commits that carry it and rotate it (step 5).

A glob follows `fnmatch`: `*` matches any characters, `/` included, so `docs/*` covers everything under `docs/`. An entry with `*` for the hash stays in force for every later value in those paths, so prefer the hash of the one value.

**What the pusher controls.** `gate/gate.json` and `.secrets-allow` are read from the pushed commit, so one push can change what the hook reads, and the gate check reads the same files. The hook prints a note when a push changes either file and how many hits entries allowed, and an empty `patterns` map is a config error. Put both files under CODEOWNERS, so that a reviewer reads every change to them.

Hook and check cover patterns, not meaning. A secret without a fixed prefix, an encoded or split value, and a file git does not track pass both. The hook reads every added line, whatever the size of the file, where the gate check skips files over `max_bytes`.

## Steps

1. **Install the hook.** Copy the script out of the plugin first, so an update of the plugin cannot break the hook, then write the hook into one repository:

   ```bash
   mkdir -p ~/.config/secrets-hook && cp "${CLAUDE_PLUGIN_ROOT}/checks/secrets.py" ~/.config/secrets-hook/
   python3 ~/.config/secrets-hook/secrets.py install-hook --into .git/hooks
   ```

   Add `--pre-commit` to refuse a commit that stages a secret as well, and `--tier warn` for a trial. With `core.hooksPath` set, pass that folder to `--into` instead of `.git/hooks`. The hook needs `python3` on the PATH of the process that runs `git push`; without it the push stops, since nothing was checked.

   For every clone made from now on, write the hook into a git template folder. `init.templateDir` holds one folder, and `/security:private-terms` may have set it already, so look first. If a folder is set, install into its `hooks`, and both hooks reach new clones from that one template:

   ```bash
   git config --global --type=path --get init.templateDir
   python3 ~/.config/secrets-hook/secrets.py install-hook --into "$(git config --global --type=path --get init.templateDir)/hooks" --pre-commit
   ```

   If none is set, the user creates one, since it changes the global git configuration:

   ```bash
   python3 ~/.config/secrets-hook/secrets.py install-hook --into ~/.config/secrets-hook/template/hooks --pre-commit
   git config --global init.templateDir ~/.config/secrets-hook/template
   ```

   `install-hook` writes `pre-push` as a small dispatcher that runs every executable in `pre-push.d` in name order, each with the same arguments and standard input, and the hook is `pre-push.d/20-secrets`. A `pre-push` hook of `/security:private-terms` that is already there moves to `pre-push.d/10-private-terms`, and `private_terms.py install-hook` writes into `pre-push.d` when the dispatcher is there, so both hooks run in either order, and a failing one does not hide the other. Any other hook is left as it is and the install stops: add the line `python3 ~/.config/secrets-hook/secrets.py pre-push "$@"` to it by hand, after it has read its standard input into a file, or move it to `pre-push.d` yourself.

   Check the result without pushing: `python3 ~/.config/secrets-hook/secrets.py check` reads what a push of the current branch would send. `python3 ~/.config/secrets-hook/secrets.py history` lists every secret hit in the added lines of all commits, masked, to find what an earlier push already sent (rotate those, step 5).

   `/sdlc:pre-push` runs the check jobs of the workflows before the push. The hook then runs at `git push` itself, so a run of that skill that ends in a push passes both.
2. **Install the check.** With the gate in place, use `/gate:add-rule` (path A: install a module's check), or by hand:

   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/checks/secrets.py" .github/actions/gate/rules/
   mkdir -p gate/fixtures && cp -R "${CLAUDE_PLUGIN_ROOT}/checks/fixtures/security.secrets" gate/fixtures/
   ```

   Add `"security.secrets": {"tier": "warn"}` to `gate/gate.json`.
3. **Run it and read every hit** with the user:

   ```bash
   python3 .github/actions/gate/run.py --only security.secrets --dry-run
   ```

   For each hit, decide: a live value (go to step 5), a retired value (rotate anyway if nobody can confirm it was retired), or a documented example (add a line with its hash and the reason to `.secrets-allow`).
4. **Record the false-positive test and block.** Once no live value is left, record the result under the rule and move it to `block`:

   ```json
   "security.secrets": {"tier": "block", "false_positive_test": {"date": "<YYYY-MM-DD>", "corpus": "<repository, tracked text files read>", "hits": 0, "legitimate": 0, "decision": "block"}}
   ```

   From then on a commit with a secret pattern fails the gate and the deploy waits.
5. **Rotate every exposed value.** One runbook per secret, from the template, without overwriting:

   ```bash
   mkdir -p docs/security && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/security/_templates/runbook-key-rotation.md" "docs/security/runbook-key-rotation-<secret>.md"
   ```

   Fill it with the user: where the value lives, what reads it, the exact commands. Then run it with the user, step by step. Rotation comes first. Removing the value from the history is a separate decision with the repository owner: it needs a force push, and it does not reach clones made before.
6. **Scan without the gate.** For a repository with no gate, or a quick look before a repository goes public, run this line from the root. It works with the regex engine of `git grep -E` on macOS and Linux, and the `sed` masks every value before it reaches the screen:

   ```bash
   git grep -nIE '(^|[^A-Za-z0-9_])sk-ant-[A-Za-z0-9_-]{20,}|(^|[^A-Za-z0-9_])sk-[A-Za-z0-9]{32,}|(^|[^A-Za-z0-9_])AKIA[0-9A-Z]{16}([^A-Za-z0-9_]|$)|(^|[^A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,}|(^|[^A-Za-z0-9_])github_pat_[A-Za-z0-9_]{40,}|(^|[^A-Za-z0-9_])xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' | sed -E 's/(sk-ant-|sk-|AKIA|gh[pousr]_|github_pat_|xox[abprs]-)[A-Za-z0-9_-]{8,}/\1****/g'
   git ls-files | grep -E '(^|/)\.env(\.[^/]+)?$' | grep -vE '\.(example|sample|template|dist)$'
   ```

   Use the character classes as written: `\b` does not work in `git grep -E` on macOS and finds only the private key lines there. Add `--no-index` to scan files git does not track. To search the history, use `git log --all -p | grep -cE '<the same pattern>'` for a count only.
7. **Turn on the provider's scanning.** GitHub secret scanning and push protection stop known token formats at push time, from any machine, which no client-side hook can promise. They are repository settings: tell the user where they are, and let the user turn them on.

## Worked example: a search service key, 2026-10-11

The `secret_key` of a self-hosted SearXNG instance sat in a settings reference file tracked in a private dotfiles repository, so the value was in that repository's history. The rotation:

1. A snapshot of the live settings file inside the container.
2. A new key generated inside the container and written straight into the settings file. The value was never printed, so it appears in no terminal, chat, or log.
3. The service restarted and verified.
4. The old value searched for in the files, with commands that print file names only.
5. The reference file committed with placeholders for the key and the metrics password (`"<random string; live value only in the container>"`), and a commit message saying the value in earlier history is retired.

The template `runbook-key-rotation.md` turns these five moves into steps with commands.

## Output

- The pre-push hook on `block` in each repository that publishes, or in the git template for every new clone, beside the private-terms hook where there is one.
- `.secrets-allow` with a reason per known false positive.
- `security.secrets` in the gate, on `block` once the repository is clean, with its false-positive test recorded.
- One rotation runbook per exposed secret, run and dated, with `last_rotated` set.
- A list of hits by file, line, kind, and hash prefix. Never the values.

## Rules

- Never print, paste, log, or commit a secret value, including in a commit message, a ticket, or a chat reply. Show the kind, the prefix and the hash prefix only.
- A hit the hook reports is fixed or documented. Take the value out of the commits and rotate it, or add an entry with a reason to `.secrets-allow` for a documented example value. Never offer a way around the hook as the answer, and never put a live value on the allow list.
- The hook is installed by the user's go. A change to the global git configuration (`init.templateDir`) is the user's action.
- Rotation before any history rewrite. Both are the user's actions, and a history rewrite needs the repository owner's go.
- Never change repository settings; name the setting and let the user change it.
- Agent settings with literal secrets are covered by `ai-ops.agent-settings` from the `ai-ops` module; this check covers every tracked file.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/secrets/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
