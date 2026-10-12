---
name: pre-push
description: >
  Run the check jobs of the repository's own GitHub Actions workflows locally,
  in a microVM with preloop, before a push, so a failing check is fixed before
  anything leaves the machine. Use before `git push`, before opening a pull
  request, after an agent changed files a workflow checks, or to reproduce a
  failed CI run. Activates on "/pre-push", "run CI locally", "test before I
  push", "preloop", "reproduce the CI failure".
user-invocable: true
---

# Pre-push: CI on the machine first

Runs the check jobs of the repository's workflows against the working tree with preloop (github.com/preloopdev/preloop, MIT), before `git push`. A red run stops the push. Deploy jobs never run here.

An agent that pushes to find out whether CI passes turns the shared remote into its test loop, and every failed run is a public commit and a wait. A local run of the same workflow file finds the failure first, and a failed job can be inspected in place.

## Setup (once per machine)

1. **Check the tool before installing it.** Run the provenance check of `/security:supply-chain` on `preloopdev/preloop`.
2. **Install a pinned release.** Never pipe a script from `main` into a shell. Take `preloop-cli-<target>.tar.gz` and its `.sha256` from a tagged release, verify the checksum, verify the build provenance with `gh attestation verify <asset> --repo preloopdev/preloop`, put `preloop` on the PATH, then run `preloop update` to install the pinned VM runtime. On Apple Silicon, prefer arm64 golden images; x86_64 ones run through Rosetta and are slower.
3. **The user runs `preloop init`.** It asks for a GitHub credential. Agents never handle that credential.
4. **Start the engine:** `preloop serve -d` (listens on 127.0.0.1:9090).

If `preloop` is missing or the engine is not running, say so in one line ("pre-push not run: preloop not installed"), run the pre-PR command from `docs/sdlc.md` instead, and continue. Never install it without the user's go.

## Steps

1. **Commit first.** The run snapshots the working tree, uncommitted changes included. Commit so the run tests what will be pushed.
2. **List what the push triggers.** For each file in `.github/workflows/` whose triggers match the push or the pull request, print the job graph: `preloop plan -f <file> --json`.
3. **Pick the check jobs:** tests, lint, build, and the gate. Skip any job that deploys, publishes, pushes, or reads secrets other than `GITHUB_TOKEN` (look for `deploy`, `environment:`, `pages`, `release`, `secrets.`).
4. **Run each check job:**

   ```bash
   preloop run -f <file> --job <job> --event pull_request --base origin/main --strict-secrets
   ```

   Use `--event push` for workflows that only run on push. `--strict-secrets` makes a job that needs an unstored secret fail instead of running half-configured.
5. **On a failure:** read the failing step with `preloop logs --job <job>`. Add `--preserve-on-failure` to keep the VM for `preloop shell`. Fix, commit, and rerun only what failed: `preloop rerun <run-id> --failed`.
6. **Push only when every selected job passed.** Report a table: workflow, job, result, and run id.

## Rules

- Never use `--push` or `--create-pr`. Pushing and opening pull requests stay with the normal flow and the user's go.
- Never pass a real secret with `--secret NAME=VALUE`: it lands in shell history and in the transcript. Let the user store it with `preloop secret set`, or skip the job.
- Never run deploy jobs locally.
- A local pass does not replace CI. The CI run on the pull request stays the record; this step only stops a red push early.
- A failing check is fixed, never skipped. `git push --no-verify` also skips the repository's own pre-push hooks.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/pre-push/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
