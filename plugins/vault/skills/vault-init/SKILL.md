---
name: vault-init
description: >
  Copy the starter vault from this plugin to the user's vault path (default
  ~/vault). Never overwrites: an existing file is skipped and reported. Run once
  before /vault:seed. Activates on "/vault-init", "create my vault",
  "copy the starter vault".
user-invocable: true
---

# Vault init

Copies the starter vault to the user's vault path. The starter holds the folder conventions, a `CLAUDE.md` template with `{{PLACEHOLDERS}}`, a commented `.vsearchignore`, an inbox README, and one example atom and MOC.

## Steps

1. **Pick the path.** Use the argument if the user gave one. Otherwise use `$VAULT_PATH` if set, else `~/vault`. State the path in one line before copying.
2. **Check the target.** If the path exists and holds files, list what is there and ask before going on. Never delete or replace anything in it.
3. **Copy without overwriting.**

   ```bash
   mkdir -p "<path>"
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/vault-starter/" "<path>/"
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/vault-starter/." "<path>/"`. Hidden files (`.vsearchignore`, `.gitignore`) must come across.
4. **Report.** List the files copied and any that already existed and were skipped.
5. **Point at the search path.** The plugin's `vault-search` MCP server reads the vault path from the plugin option `vault_path` (default `~/vault`). If the user picked another path, tell them to set it: `claude plugin configure vault@<marketplace>` or reinstall with `--config vault_path=<path>`, then restart Claude Code.
6. **Next step.** Tell them to run `/vault:seed`. It replaces the starter's generic structure with one built from their own domains.

## Rules

- No overwrite, no delete, no move. A user with an existing vault gets enrichment from `/vault:seed`, not a reset.
- Do not index here. Indexing happens at the end of `/vault:seed`, once real atoms exist.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/vault" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/vault/` exists, read its `README.md` first, then the files in `vault/vault-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
