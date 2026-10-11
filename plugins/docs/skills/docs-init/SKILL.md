---
name: docs-init
description: >
  Set up a docs tree in the current repository: ask for the spaces, copy the
  config, a home page per space, the page templates and the build script, fill
  the front matter (owner, review dates, type) and run the first build. Use when
  a repository has no docs tree yet, or its docs pages have no owners and review
  dates. Never overwrites a file. Activates on "/docs-init", "set up docs", "add
  a docs tree", "docs as code for this repo", "start the documentation".
user-invocable: true
---

# Docs init

Sets up documentation as code in the repository the user is working in. Pages are Markdown files in `docs/<space>/`. `scripts/build_docs.py` turns them into a static site with a health page that lists pages without an owner and pages past their review date.

## Inputs

- The repository: the current working directory, or a path the user names.
- The spaces. A space is one section of the docs with its own home page. For each: `key` (folder name, a-z, 0-9 and -), `name`, `about` (one sentence) and `owner` (a person or a team).
- Optional: the output folder (default `site/docs`), the URL prefix (default `/docs/`) and the base URL for canonical links (default none).

## Steps

1. **Check the repository.** Find the root with `git rev-parse --show-toplevel`. Check `python3 --version` (3.9 or later). If `docs/docs.json`, `docs/_templates/` or `scripts/build_docs.py` exists, list what is there and ask before going on. Look at how the site deploys (`.github/workflows/`, a `site/` or `public/` folder) so the output folder fits it.
2. **Interview, briefly.** Propose the defaults: `eng` (Engineering) and `decisions` (Decisions, written by the `decisions` module). Ask which spaces to keep or add, and the name, about line and owner of each. Ask for the output folder, URL prefix and base URL only when the defaults do not fit the deploy. One round of questions; do not ask for more than these fields.
3. **Copy without overwriting.**

   ```bash
   mkdir -p docs scripts
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/docs.json" docs/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/_templates/" docs/_templates/
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/scripts/build_docs.py" scripts/
   ```

   If the user keeps the `eng` space, also copy its two pages:

   ```bash
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/eng/" docs/eng/
   ```

   Without rsync, use `cp -Rn <source>/. <target>/`. Report the files copied and the files skipped because they existed.
4. **Write the config.** In `docs/docs.json`, set the `spaces` list from the interview, plus `out`, `url_prefix` and `base_url` if they changed. Keep the `decisions` entry when the user plans to use the `decisions` module; the build skips it until `docs/decisions/` exists. If `docs/docs.json` existed before this run, show the change and ask before you write it.
5. **Write a home page per space.** For every space other than `eng` and `decisions`, write `docs/<key>/index.md` with `${CLAUDE_PLUGIN_ROOT}/templates/docs/eng/index.md` as the model: `title` is the space name, `summary` is the about line, the body has one paragraph on the content of the space. Skip a space whose `index.md` exists. Do not create `docs/decisions/`; the `decisions` module does that.
6. **Fill the front matter.** In every page this run created (not in `docs/_templates/`), replace each `<...>` placeholder:
   - `owner`: the space owner.
   - `reviewed`: today's date, since the page is written now from what the user said. Use `no` for a page whose content nobody has checked.
   - `review_by`: `reviewed` plus `review_interval_days` from the config (90 by default).
   - `type`: keep `reference` for space homes and the runbooks index.
   Replace the placeholder rows in body tables with real rows from the interview, or remove the rows. Then check that no placeholder is left: `grep -rn '<[A-Za-z][^>]*>' docs --include='*.md' --exclude-dir=_templates`.
7. **Check the build.** Run `python3 scripts/build_docs.py --check`. Fix every error it prints and run it again until it passes. Read the warnings to the user.
8. **Build.** Run `python3 scripts/build_docs.py`. Report the page count and the output folder, and check that `<out>/health/index.html` exists. If the deploy builds the site in CI, add the build command to that workflow before the deploy step, and suggest adding the output folder to `.gitignore`. Ask before editing a workflow.
9. **Gate.** Tell the user how to add the `docs.review` check to the deploy gate:
   - The gate must exist (`.github/actions/gate/run.py`). If it does not, `/gate:gate-init` sets it up.
   - Copy `${CLAUDE_PLUGIN_ROOT}/checks/docs_review.py` to `.github/actions/gate/rules/` and `${CLAUDE_PLUGIN_ROOT}/checks/fixtures/docs.review/` to `gate/fixtures/docs.review/`, with `cp -n` and `rsync --ignore-existing`.
   - Add `"docs.review": {"tier": "warn"}` to `rules` in `gate/gate.json`.
   - Run `python3 .github/actions/gate/run.py --dry-run`.
   Do these steps only when the user says so.

## Output

- `docs/docs.json`, one `index.md` per space, `docs/eng/runbooks.md`, `docs/_templates/page.md`, `docs/_templates/runbook.md` and `scripts/build_docs.py` in the repository.
- A built site in the output folder, with `health/index.html` and `search.json`.
- A short report: files copied, files skipped, build result, warnings, and the next steps (write pages, `/docs:runbook`, the gate check).

## Rules

- Never overwrite, delete or move an existing file. Ask before editing an existing config or workflow.
- Leave the placeholders in `docs/_templates/` as they are; they are the starting point for new pages.
- Set `reviewed` to a date only for a page whose content was written or checked in this session. Otherwise use `no`.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/docs" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/docs/` exists, read its `README.md` first, then the files in `docs/docs-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
