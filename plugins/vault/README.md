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
- **Limit**: the search server does not read `trust:` yet, so a search hit from the pack has no label of its own. The folder, the tag `trust/third-party`, the notice, and the paragraph the skill adds to `CLAUDE.md` are the labels until it does.

Tests: `plugins/vault/tests/test_reference_pack.py` replays a recorded copy of the corpus (pass and fail fixtures) with no network, and CI runs it.

## Templates

| Path in the plugin | Lands at | What it is |
|---|---|---|
| `templates/vault-starter/` | The vault path (default `~/vault`) | Folder conventions, a `CLAUDE.md` template, `.vsearchignore` (with the commented line that excludes the reference pack), an inbox note, one example note and one example index |

## Gate check

`checks/private_boundary.py` defines `vault.private-boundary`: no published page (`docs/**/*.md` by default) carries a private tag (`private`, `status/private`, `status/sensitive`) in its front matter or as an inline tag outside code. The check guards the step where vault notes are published into a docs tree.

Enable it with `/gate:add-rule` (path A), on `warn` first. Move it to `block` after the false-positive test is recorded under `"false_positive_test"` in `gate/gate.json`.

Demo: [machinebehavior.io/inside/docs/sre/](https://machinebehavior.io/inside/docs/sre/), the SRE Handbook space, published from a knowledge vault with a review label on every note.
