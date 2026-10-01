---
name: seed
description: >
  Seed the user's personal vault from an interview about their actual domains,
  re-explained facts, and privacy boundary. Generates domain folders, first
  atoms, starter MOCs, and a fitted CLAUDE.md from the vault-starter template.
  Activates on "/seed", "seed my vault", "set up my vault".
user-invocable: true
---

# Seed

You are growing a vault around THIS user's life, not installing a filing system. Structure that arrives before content is decoration; create only what their answers justify.

## Phase 1: locate

Confirm the vault path (default `~/vault`, or `VAULT_PATH`). If the starter isn't copied yet, run `/vault:vault-init` first (it copies `${CLAUDE_PLUGIN_ROOT}/vault-starter/` without overwriting anything). If a vault already exists with content, switch to enrichment mode: propose additions, never restructure what exists without explicit approval.

## Phase 2: interview

Ask these, one block, wait for answers:

1. What do you actually work on? The 3-6 areas with real activity in the last month, not aspirational ones.
2. What do you find yourself re-explaining to the model across sessions? (people, projects, constraints, preferences, history)
3. What do you look up more than twice a week?
4. What must stay private? (folders excluded from indexing and from anything that leaves the machine)
5. Where does raw material arrive from? (chats, meetings, browser, email, voice notes)

## Phase 3: generate

From the answers, create ONLY:

- One folder per named active domain (kebab-case or the user's preferred casing; ask if unclear).
- `_inbox/` (from starter, keep its README).
- The first atoms: every item from question 2 becomes an atom NOW, in its domain folder, following the starter conventions (one idea per file, minimal frontmatter, filename = title). These are the highest-value atoms the vault will ever hold; do not defer them.
- A starter `_MOC.md` only for domains that got 3+ atoms in this pass.
- `.vsearchignore` at the vault root listing every private folder from question 4, one per line. This is what keeps them out of the index; the sentence in CLAUDE.md alone does not. After the reindex, prove it: search for a word that only occurs in a private folder and show that it returns nothing.
- `CLAUDE.md` from the starter template with placeholders resolved: real folder list, real private boundary, the inbox-pass rule, and any user-specific conventions they stated.

Show the tree and every atom title for confirmation before writing. After writing, run a reindex (`vault_reindex` MCP tool or `uv run ${CLAUDE_PLUGIN_ROOT}/search/vsearch.py index`) and demonstrate one search hit so the user sees the loop close.

## Phase 4: hand over the habits

Tell the user the three habits that keep the vault alive, in one short block:

1. Everything unsorted goes to `_inbox/`; the agent sweeps it with `/atomize` on request or on a schedule.
2. When the model re-derives something that took work, ask it to write the atom (or it should offer).
3. Empty folders get deleted, not filled out of duty.

## Rules for you, the seeding model

- Do not import the kit author's domains or taxonomy. The starter's example files are shapes, not content; tell the user to delete them once real atoms exist.
- Five atoms that get read beat fifty stubs. Do not pad.
- Question 4's boundary goes in CLAUDE.md verbatim. When later work touches that boundary, asking beats guessing.
- No automation on day one: no watchers, no cron, no sync. Mention `uv run ${CLAUDE_PLUGIN_ROOT}/search/vsearch.py watch` exists; wire it only when the user asks.
