# Vault instructions for AI agents

This is a personal knowledge vault: plain markdown, one idea per file, linked with `[[wikilinks]]`. You read it, search it, and write to it. Treat it as the durable memory layer; conclusions that took real work get written back as atoms.

<!-- /seed replaces the placeholders and prunes this file to match the owner's
     actual structure. Until then, these are the starter conventions. -->

## Structure

- `_inbox/` — unsorted input. Anything can land here; a periodic atomize pass files it. Never leave your own work-products here.
- `{{DOMAIN_FOLDERS}}` — one folder per active domain of the owner's life/work. Atoms live here.
- Each domain grows a `_MOC.md` (map of content) once it has enough atoms to need an index. Do not create MOCs ahead of content.

## Conventions you follow

1. One idea per file. If an atom you're writing needs sections, it is multiple atoms; split and link.
2. Frontmatter: `tags` (hierarchical, e.g. `project/x`), `created` (ISO date). Nothing else unless the owner's conventions add it.
3. Link liberally with `[[Atom Name]]`. Unresolved links are allowed; they mark atoms worth writing.
4. Filenames are titles, sentence-cased, no dates in names unless the atom is inherently dated (meeting notes, sessions).
5. Write back: when a session produces a non-obvious conclusion (a decision plus its why, a debugged root cause, a mapped system), create the atom without being asked, and say you did.
6. Search before writing: check whether an atom already covers the topic; update it rather than creating a near-duplicate.

## Private boundary

{{PRIVATE_FOLDERS}} are private. The search index enforces this through `.vsearchignore` at the vault root: listed paths, and any atom tagged `private`, `status/private` or `status/sensitive`, are never indexed, never returned by search, and refused by `vault_read`. You enforce the other half: nothing from those folders goes into content that leaves this machine (published artifacts, pasted excerpts, commit messages). If you create a new private folder, add it to `.vsearchignore` in the same step. When in doubt about whether something crosses the boundary, ask.

## Search

The `vault-search` MCP tools (if wired): `vault_search` (hybrid keyword+semantic; use before grep), `vault_read` (fetch an atom by path), `vault_reindex` (after batch changes). Degraded results marked `fts-fallback` mean semantic search was down for that query.
