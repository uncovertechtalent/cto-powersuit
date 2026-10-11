---
name: agent-harness
description: >
  Set up the shared harness for an engineering team's coding agents: shared
  settings with narrow permissions, the instruction file, the plugin list, MCP
  servers with secrets from the environment, hooks, and docs/agents.md naming
  the owner. Use when a team starts using coding agents, when each developer
  runs a different setup, or after an agent did something nobody allowed.
  Activates on "/agent-harness", "set up our agents", "shared agent settings",
  "agent permissions", "harden the agent setup".
user-invocable: true
---

# Agent harness

Gives every agent session in a repository the same starting point: what it may do without asking, what it must ask for, what it never touches, which instructions it reads, and which plugins and tools it has. The shared part lives in git and changes through pull requests; personal changes stay in `.claude/settings.local.json`.

## Steps

1. **Read what exists.** `.claude/settings.json`, `.claude/settings.local.json` (do not commit it), `.mcp.json`, `CLAUDE.md` or `AGENTS.md`, `.gitignore`. Note every allow rule, every hook and every MCP server with the secrets it needs.
2. **Copy the templates** without overwriting:

   ```bash
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/.claude/" .claude/
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/agents.md" docs/
   ```

3. **Set the permissions.**
   - Allow without asking: read-only commands, the test command, the gate dry run.
   - Ask every time: `git push`, merges, deploys, anything that writes outside the repository.
   - Deny: `.env` files, the secrets folder, credential files.
   - Never: an allow rule for every shell command (`Bash`, `Bash(*)`) or every fetch (`WebFetch`), or `defaultMode: bypassPermissions` in the shared file. Fill `<test command>` with the repository's real command.
4. **Write the instruction file.** `CLAUDE.md` or `AGENTS.md`: how to build, test and run the gate dry run; the branch and commit rules (ticket id in every commit); what never to do (push, change CI, touch secrets). Keep it short; every line is read by every session.
5. **List the plugins** the team uses with their marketplace, in `docs/agents.md`. Stance and output filters (`stance`, `vestige`) and the knowledge base (`vault`) are optional parts of this module.
6. **Move secrets out.** Every MCP server and every setting reads secrets from environment variables (`"${VAR}"`). Add `.claude/settings.local.json` and `.env*` to `.gitignore`.
7. **Check.** With the gate installed, add `ai-ops.agent-settings` with `/gate:add-rule` on `warn` and run `python3 .github/actions/gate/run.py --only ai-ops.agent-settings`. Without the gate, read the shared files against the rules in step 3.
8. **Fill `docs/agents.md`**: owner, plugin list, MCP servers, hooks, and how a change is proposed.

## Output

`.claude/settings.json`, the instruction file, `docs/agents.md`, and a list of what changed and why.

## Rules

- Never write a secret into a file. If one is found, report it with the value masked and tell the user to rotate it first.
- Never commit `.claude/settings.local.json`.
- Show every change to an existing settings or instruction file before making it.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/ai-ops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/ai-ops/` exists, read its `README.md` first, then the files in `ai-ops/agent-harness/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
