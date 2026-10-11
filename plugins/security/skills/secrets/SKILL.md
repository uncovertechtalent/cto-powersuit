---
name: secrets
description: >
  Keep secret values out of the repository and rotate the ones that got out: a
  blocking gate check for secret patterns and .env files in tracked files, a
  one-line scan for repositories without the gate, and a key-rotation runbook
  per secret that never prints the value. Use when a scan or a review finds a
  key in the repository, before a repository goes public, when someone with
  access leaves, or on a rotation schedule. Activates on "/secrets", "scan for
  secrets", "we committed a key", "rotate this key", "key rotation runbook",
  "is there a secret in this repo", "block secrets in CI".
user-invocable: true
---

# Secrets

A secret in a tracked file reaches every clone, every fork and every CI log that prints the file. Removing the line later does not take it back: the value stays in the history. So the fix has two parts. A gate check stops new secrets before a deploy, and a rotation retires every value that was ever exposed.

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
| `tracked_only` | `true` | `false` also reads untracked files, for a build output folder |
| `env_files` | `true` | `false` turns the `.env` rule off |
| `patterns` | the table above | Add the token formats of the team's own providers as `"kind": ["<regex>", "<prefix>****"]` |

## Steps

1. **Install the check.** With the gate in place, use `/gate:add-rule` (path A: install a module's check), or by hand:

   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/checks/secrets.py" .github/actions/gate/rules/
   mkdir -p gate/fixtures && cp -R "${CLAUDE_PLUGIN_ROOT}/checks/fixtures/security.secrets" gate/fixtures/
   ```

   Add `"security.secrets": {"tier": "warn"}` to `gate/gate.json`.
2. **Run it and read every hit** with the user:

   ```bash
   python3 .github/actions/gate/run.py --only security.secrets --dry-run
   ```

   For each hit, decide: a live value (go to step 4), a retired value (rotate anyway if nobody can confirm it was retired), or a documented example (add its hash to `allow_hashes` with a comment in the pull request that says where the example comes from).
3. **Record the false-positive test and block.** Once no live value is left, record the result under the rule and move it to `block`:

   ```json
   "security.secrets": {"tier": "block", "false_positive_test": {"date": "<YYYY-MM-DD>", "corpus": "<repository, tracked text files read>", "hits": 0, "legitimate": 0, "decision": "block"}}
   ```

   From then on a commit with a secret pattern fails the gate and the deploy waits.
4. **Rotate every exposed value.** One runbook per secret, from the template, without overwriting:

   ```bash
   mkdir -p docs/security && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/security/_templates/runbook-key-rotation.md" "docs/security/runbook-key-rotation-<secret>.md"
   ```

   Fill it with the user: where the value lives, what reads it, the exact commands. Then run it with the user, step by step. Rotation comes first. Removing the value from the history is a separate decision with the repository owner: it needs a force push, and it does not reach clones made before.
5. **Scan without the gate.** For a repository with no gate, or a quick look before a repository goes public, run this line from the root. It works with the regex engine of `git grep -E` on macOS and Linux, and the `sed` masks every value before it reaches the screen:

   ```bash
   git grep -nIE '(^|[^A-Za-z0-9_])sk-ant-[A-Za-z0-9_-]{20,}|(^|[^A-Za-z0-9_])sk-[A-Za-z0-9]{32,}|(^|[^A-Za-z0-9_])AKIA[0-9A-Z]{16}([^A-Za-z0-9_]|$)|(^|[^A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,}|(^|[^A-Za-z0-9_])github_pat_[A-Za-z0-9_]{40,}|(^|[^A-Za-z0-9_])xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' | sed -E 's/(sk-ant-|sk-|AKIA|gh[pousr]_|github_pat_|xox[abprs]-)[A-Za-z0-9_-]{8,}/\1****/g'
   git ls-files | grep -E '(^|/)\.env(\.[^/]+)?$' | grep -vE '\.(example|sample|template|dist)$'
   ```

   Use the character classes as written: `\b` does not work in `git grep -E` on macOS and finds only the private key lines there. Add `--no-index` to scan files git does not track. To search the history, use `git log --all -p | grep -cE '<the same pattern>'` for a count only.
6. **Turn on the provider's scanning.** GitHub secret scanning and push protection stop known token formats at push time. They are repository settings: tell the user where they are, and let the user turn them on.

## Worked example: a search service key, 2026-10-11

The `secret_key` of a self-hosted SearXNG instance sat in a settings reference file tracked in a private dotfiles repository, so the value was in that repository's history. The rotation:

1. A snapshot of the live settings file inside the container.
2. A new key generated inside the container and written straight into the settings file. The value was never printed, so it appears in no terminal, chat, or log.
3. The service restarted and verified.
4. The old value searched for in the files, with commands that print file names only.
5. The reference file committed with placeholders for the key and the metrics password (`"<random string; live value only in the container>"`), and a commit message saying the value in earlier history is retired.

The template `runbook-key-rotation.md` turns these five moves into steps with commands.

## Output

- `security.secrets` in the gate, on `block` once the repository is clean, with its false-positive test recorded.
- One rotation runbook per exposed secret, run and dated, with `last_rotated` set.
- A list of hits by file, line, kind, and hash prefix. Never the values.

## Rules

- Never print, paste, log, or commit a secret value, including in a commit message, a ticket, or a chat reply. Show the kind, the prefix and the hash prefix only.
- Rotation before any history rewrite. Both are the user's actions, and a history rewrite needs the repository owner's go.
- Never change repository settings; name the setting and let the user change it.
- Agent settings with literal secrets are covered by `ai-ops.agent-settings` from the `ai-ops` module; this check covers every tracked file.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/secrets/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
