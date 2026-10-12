---
name: tool-audit
description: >
  Audit the tool calls of coding agents: every call with who decided it (a
  rule in the settings, a hook, or a person at a prompt), counts of allowed,
  denied, and asked calls per tool on a dashboard, an alert on a spike of
  denied calls, and a monthly review record. Builds on the telemetry of
  /ai-ops:metering and the observability stack. Use after setting the agent
  permissions, when someone asks what the agents did and who allowed it, or
  when an agent was stopped by a rule and nobody noticed. Activates on
  "/tool-audit", "audit agent tool calls", "what did the agents run",
  "denied tool calls", "agent audit trail".
user-invocable: true
---

# Tool audit

The policy for agent tool calls lives in `/ai-ops:agent-harness`: allow, ask, and deny rules and hooks. This skill adds the record. Claude Code writes a `tool_decision` event for every permission decision and a `tool_result` event for every call that ran. The observability stack keeps them in Loki, and this skill turns them into a dashboard, an alert, and a review record.

## Steps

1. **Check the telemetry.** The events need the variables from `/ai-ops:metering` step 1. Claude Code reads the telemetry variables from the shell, the user settings, or managed settings, and ignores them in a repository's `.claude/settings.json`. For an audit trail that a developer cannot switch off, put them in the `env` block of managed settings (`/Library/Application Support/ClaudeCode/managed-settings.json` on macOS, `/etc/claude-code/managed-settings.json` on Linux). Check before use: the paths and the variable names against the Claude Code settings documentation for the version in use.
2. **Decide on the parameters.** `OTEL_LOG_TOOL_DETAILS=1` adds each call's parameters: the shell command, the file path, the skill name, and the MCP server and tool names. Without it the trail has tool names only, and every call to a user-configured MCP server reads `mcp_tool`. With it, a command that carries a secret is stored in Loki. Write the choice, the retention, and who may read Loki into the page in step 6. The user decides.
3. **Check the events arrive.** After a short agent session, run in Grafana Explore:

   ```
   {service_name=~"claude-code.*"} | event_name="tool_decision"
   ```

   No events: check the variables in the session's environment, then the path from the agent to Alloy.
4. **Add the dashboard.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/observability/grafana/specs/agent-tool-calls.json` into `observability/grafana/specs/` and run `python3 observability/grafana/build.py`. Keep it off any public dashboard list: its trail panel shows the parameters.
5. **Set the alert threshold from history.** Run the review script for the last 30 days. It prints the busiest 15 minutes of denials and twice that number, with a floor of 5:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/tool-audit/tool_audit.py" --loki http://<stack-host>:3100 --days 30
   ```

   Show the user both numbers and let the user set the threshold. Copy `templates/observability/loki/rules/fake/agent-tool-calls.yml` and replace `<denials per 15 minutes>`. The Loki ruler must run with the block from `templates/ai-ops/metering/loki-ruler.yml`, and `observability/loki/rules/**/*.yml` must be in the `globs` of `observability.alert-routes` in `gate/gate.json` (metering step 4 sets up both).
6. **Write the page.** Copy `templates/docs/agent-tool-calls.md` to `docs/`, fill the owner, the threshold, the retention, who may read the trail, and where review records go. Link it from `docs/agents.md`.
7. **File the first review record.** Save the script's output for the last 30 days where the page says. The script exits 1 when the period has no `tool_decision` events: that means the trail is broken, not that the agents were idle.

## Output

The dashboard, the alert with the user's threshold, `docs/agent-tool-calls.md`, and the first review record: allowed, denied, and asked counts per tool, the busiest 15 minutes of denials, and what the trail does not record.

## Reading the counts

| Count | `decision` | `source` |
|---|---|---|
| Allowed by rule | `accept` | `config` |
| Allowed by hook | `accept` | `hook` |
| Asked, allowed | `accept` | `user_temporary`, `user_permanent` |
| Asked, denied | `reject` | `user_reject`, `user_abort` |
| Denied by rule | `reject` | `config` |
| Denied by hook | `reject` | `hook` |

A PreToolUse hook that blocks a call writes a `tool_decision` with `decision="reject"` and `source="hook"`, and its `hook_execution_complete` event counts one in `num_blocking`. On a recorded week of one developer's sessions both counts were 3. `tool_result` events carry `success` and `duration_ms`. The counts take the decision from `tool_decision` only.

## Rules

- Never set the alert threshold yourself; the user sets it.
- Never copy tool parameters into a review record, a ticket, or a public page. The review script prints counts only.
- Prompt and response text stay off in telemetry.
- Check before use: event and attribute names (`tool_decision`, `decision`, `source`, `tool_result`, `success`) against the Claude Code version in use.

## Check the script

`python3 "${CLAUDE_PLUGIN_ROOT}/skills/tool-audit/test_tool_audit.py"` runs the column mapping, the totals, the threshold, the Markdown, the exit codes, and the queries against a fake Loki server. Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/ai-ops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/ai-ops/` exists, read its `README.md` first, then the files in `ai-ops/tool-audit/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
