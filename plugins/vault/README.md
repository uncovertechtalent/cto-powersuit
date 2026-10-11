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

## Templates

| Path in the plugin | Lands at | What it is |
|---|---|---|
| `templates/vault-starter/` | The vault path (default `~/vault`) | Folder conventions, a `CLAUDE.md` template, `.vsearchignore`, an inbox note, one example note and one example index |

## Gate check

`checks/private_boundary.py` defines `vault.private-boundary`: no published page (`docs/**/*.md` by default) carries a private tag (`private`, `status/private`, `status/sensitive`) in its front matter or as an inline tag outside code. The check guards the step where vault notes are published into a docs tree.

Enable it with `/gate:add-rule` (path A), on `warn` first. Move it to `block` after the false-positive test is recorded under `"false_positive_test"` in `gate/gate.json`.

Demo: [machinebehavior.io/inside/docs/sre/](https://machinebehavior.io/inside/docs/sre/), the SRE Handbook space, published from a knowledge vault with a review label on every note.
