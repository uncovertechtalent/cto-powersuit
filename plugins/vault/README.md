# vault

A plain-Markdown vault with hybrid keyword and semantic search, served to Claude as an MCP server, with skills to create the vault, seed it from an interview and atomize documents into it. Part of the `ai-ops` group; the search server, the plugin option `vault_path` and the private boundary are in the root README, section "vault".

Install:

```bash
claude plugin install vault@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/vault:vault-init` | Copies the starter vault to the vault path; never overwrites |
| `/vault:seed` | Interviews you and builds the vault structure from your own domains |
| `/vault:atomize` | Turns a document, a chat log or the inbox into linked one-idea notes |
| `/vault:reference-pack` | Opt-in: imports the published pages of machinebehavior.io as third-party reference notes under `reference/machinebehavior/` |

## Reference pack (opt-in, third party)

`/vault:reference-pack` copies the pages of [machinebehavior.io](https://machinebehavior.io/), the published documentation of Stefan Coetzee, into your vault so the model can look them up. It runs only after a yes: `/vault:seed` asks as question 6, and nothing imports by default.

These notes are a third party's documentation. Read them as reference, never instructions: the same rule the `quarantine` skill of the `security` module applies to every text from outside. A sentence in a pack note that asks for an action is part of the text, and the model tells you instead of acting on it.

- **Source**: the site's machine-readable corpus only. `llms-passages.json` names the pages; each page's markdown twin is fetched on its own. No HTML page is read, and the standard library is all it needs.
- **One note per page** under `reference/machinebehavior/`, never mixed into your own folders. Every note has `source:` (the page URL), `fetched:` (the date), `sha256:` (of the twin as fetched) and `trust: third-party`, a notice that it is a third party's text, and the page between two marker lines that carry the hash.
- **Checks before a note is written**: only https pages on machinebehavior.io, one note name per page, no hidden or control characters, no line that looks like a pack marker, a twin that names the page the manifest names, at most 2 MB. A page that fails is refused with its reason, and an existing note for it stays as it was.
- **Update in place**: run the skill again. Notes whose hash changed are rewritten and reported by hash, the rest stay byte for byte, and pages that left the corpus are kept unless you ask for `--prune`. The importer never touches a path outside `reference/machinebehavior/`, and a note of yours with a page's name is left alone.
- **Private boundary**: the pack is public text, not your content. It carries no private tag and the starter does not list it in `.vsearchignore`; it never counts as your own notes. The skill asks once whether the pack is searchable now and writes the line on a no. To change it later, delete or restore the `# ` (hash and space) before `reference/machinebehavior` in `.vsearchignore` and reindex.
- **Labels at search time**: see "Trust labels in search" below. A hit from the pack is marked third-party, and a read of a pack note is fenced.

Tests: `plugins/vault/tests/test_reference_pack.py` replays a recorded copy of the corpus (pass and fail fixtures) with no network, and `plugins/vault/tests/test_vsearch_trust.py` tests the search labels (`VSEARCH_E2E=1` also runs the search script itself against a scratch vault, offline, which needs `uv` and its packages). CI runs both without the script run.

## Trust labels in search

The search server reads the `trust:` front matter field and the tags `trust/third-party` and `trust/external`, the vocabulary of the `quarantine` skill in the `security` module.

| Mark | What the search does |
|---|---|
| none | The owner's own note. Nothing changes. |
| `trust: third-party` | Stays searchable and labelled. A `vault_search` hit has `trust: "third-party"`, `source`, and a provenance tag before its snippet. `vault_read` returns the note under a provenance line, between `BEGIN THIRD-PARTY TEXT <marker>` and `END THIRD-PARTY TEXT <marker>` lines with a new random marker for every call, so the text cannot close the fence. `vault_ask` fences third-party excerpts in its prompt with a rule to treat them as data, marks them in `sources`, and adds a `trust_note` to the answer. |
| `trust: external` (or the tag `trust/external`) | Treated like a private note: never indexed, never returned, refused by `vault_read`. `trust/external` is in the default of `VSEARCH_EXCLUDE_TAGS`; a list you set yourself replaces the default, so keep that tag in it. A note that claims both marks counts as external. |

A `trust:` field stands for the tag `trust/<value>`, so `VSEARCH_EXCLUDE_TAGS=...,trust/third-party` also removes notes that carry only the field, and `vault_search` can filter on `trust/third-party`. Notes indexed before the upgrade are re-read on the next index run (the stored schema moves to 6); until then hits are labelled and external notes dropped at query time.

A label is text in a tool result, and a client that ignores it is not stopped by it. Raw text from strangers still belongs in the `quarantine` store, not in the vault.

## Templates

| Path in the plugin | Lands at | What it is |
|---|---|---|
| `templates/vault-starter/` | The vault path (default `~/vault`) | Folder conventions, a `CLAUDE.md` template, `.vsearchignore` (with the commented line that excludes the reference pack), an inbox note, one example note and one example index |

## Gate check

`checks/private_boundary.py` defines `vault.private-boundary`: no published page (`docs/**/*.md` by default) carries a private tag (`private`, `status/private`, `status/sensitive`) in its front matter or as an inline tag outside code. The check guards the step where vault notes are published into a docs tree.

Enable it with `/gate:add-rule` (path A), on `warn` first. Move it to `block` after the false-positive test is recorded under `"false_positive_test"` in `gate/gate.json`.

Demo: [machinebehavior.io/inside/docs/sre/](https://machinebehavior.io/inside/docs/sre/), the SRE Handbook space, published from a knowledge vault with a review label on every note.
