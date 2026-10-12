# Clinic notes for acme/widget

2026-10-12, at commit 1a2b3c4. You asked for feedback in https://example.com/post/1. Three gaps, ranked by the damage each can do to the people who install it.

## 1. Nothing runs before a release
The release workflow builds and uploads on every tag. No test or lint job runs first, so a broken build reaches users.
Evidence: `.github/workflows/release.yml:9`, no `needs:` on the upload job; 0 test files tracked; see also src/server.js:42.
Fix: add a `check` job that runs the existing lint, and `needs: check` on the upload job.

## 2. Actions are pinned to tags
Three actions use a tag such as `@v4`. A tag can be moved to other code, and that code runs with the release token.
Evidence: `gate.actions-pinned` fails on 3 references in `.github/workflows/release.yml`.
Fix: pin each action to its full commit SHA, with the tag as a comment.

## 3. No lock file
`package.json` lists 12 dependencies with `^` ranges and no `package-lock.json`, so two installs a week apart can differ.
Evidence: `git ls-files` shows `package.json` and no lock file.
Fix: run `npm install --package-lock-only --ignore-scripts` and commit `package-lock.json`.

Checked: sdlc audit probe, action pins and owners, lock files, OSV lookup of the dependency graph, secret patterns in tracked files, and provenance signals. Not checked: branch rules (no admin access), the signed release assets (not downloaded), and the app at runtime (not run).

Audited with the CTO Powersuit (github.com/uncovertechtalent/cto-powersuit).
