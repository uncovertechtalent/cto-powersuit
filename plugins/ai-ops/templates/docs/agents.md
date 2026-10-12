---
title: Agents in this repository
summary: Which coding agents work in this repository, with which plugins, permissions, hooks and MCP servers, how their spend is metered, and who owns the setup.
labels: agents, ai-ops, harness
owner: <who owns the agent setup>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
Every agent session in this repository starts from the same shared setup. Personal changes go into `.claude/settings.local.json`, which stays out of git.

## Harness

| Part | Where | What it holds |
|---|---|---|
| Shared settings | `.claude/settings.json` | Permissions (allow, ask, deny) and shared environment variables |
| Instructions | `CLAUDE.md` or `AGENTS.md` | Repository rules every session reads: how to build, test and open a pull request |
| Plugins | <marketplace and plugin list> | Skills, hooks and MCP servers the team uses |
| MCP servers | `.mcp.json` | Tool servers; secrets come from environment variables |
| Hooks | <plugin hooks in use> | Checks that run on every reply or every file write |

## Permissions

- Allowed without asking: read-only git commands, the test command, the gate dry run.
- Asked every time: `git push`, merges, anything that deploys.
- Denied: `.env` files and the secrets folder.
- Never in the shared settings: a rule that allows every shell command or every fetch, or the bypass mode. The gate check `ai-ops.agent-settings` fails on them.

Claude Code asks on a matching ask rule in every permission mode, the bypass mode included. These settings load only in a session started in this repository's folder; a session started elsewhere that works here does not get them.

## Spend

Agent spend is metered per API request: see [Agent spend](doc:fin/agent-spend).

## Audit

Every tool call and who allowed or denied it is recorded: see [Agent tool calls](doc:agent-tool-calls).

## Owner

<owner> owns this setup. A change to the shared settings, the plugin list or `.mcp.json` goes through a pull request.
