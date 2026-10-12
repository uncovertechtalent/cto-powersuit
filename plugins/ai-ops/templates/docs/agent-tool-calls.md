---
title: Agent tool calls
summary: The audit trail of the coding agents' tool calls, who decided each one, where to read it, and what to do when the denied-calls alert fires.
labels: agents, ai-ops, audit, security
owner: <who owns the agent setup>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: explanation
---
Every tool call a coding agent makes passes a permission decision first. Claude Code writes one `tool_decision` event per decision and one `tool_result` event per call that ran. The observability stack stores the events in Loki. The [agent harness](doc:agents) sets the policy, and this trail shows the policy at work.

## What the trail records

| Count | Event | Where the decision came from |
|---|---|---|
| Allowed by rule | `tool_decision`, `decision="accept"`, `source="config"` | An allow rule, a mode that allows it, or a tool that needs no permission |
| Allowed by hook | `decision="accept"`, `source="hook"` | A PreToolUse hook approved it |
| Asked, allowed | `decision="accept"`, `source` `user_temporary` or `user_permanent` | A person said yes at a prompt (once, or for the session) |
| Asked, denied | `decision="reject"`, `source` `user_reject` or `user_abort` | A person said no, or dismissed the prompt |
| Denied by rule | `decision="reject"`, `source="config"` | A deny rule, or a tool the session may not use |
| Denied by hook | `decision="reject"`, `source="hook"` | A PreToolUse hook blocked it |
| Failed | `tool_result`, `success="false"` | The call ran and failed |

Each event also carries `tool_name`, `tool_use_id`, `prompt_id` and the Claude Code version. With `OTEL_LOG_TOOL_DETAILS=1`, `tool_parameters` holds the call's parameters: the shell command, the file path, the skill name, and the MCP server and tool names.

Not recorded:

- A prompt nobody answered.
- Sessions that send no telemetry: another machine, another tool, or a shell without the telemetry variables.
- The names of MCP tools in the counts: calls to user-configured MCP servers count under `mcp_tool`. The server and tool names are in `tool_parameters` only.

## Where to read it

- Dashboard: Agent tool calls (`observability/grafana/specs/agent-tool-calls.json`). Keep it private: its denied-calls panel shows the parameters.
- Explore: `{service_name=~"claude-code.*"} | event_name="tool_decision" | decision="reject"` lists the denied calls; open a line for its fields.
- Review record: `python3 <tool-audit skill folder>/tool_audit.py --loki <loki url> --days 30` prints the counts per tool for the period, with no parameters.

## Retention and access

Loki keeps the events for <retention period>. With `OTEL_LOG_TOOL_DETAILS=1`, a command that carries a secret on its command line is stored with it, so access to Loki and Grafana stays with <who may read the trail>. Prompt and response text stay off.

## When AgentToolDenialsSpike fires

The alert fires when one decision source denies more than <denials per 15 minutes> calls in 15 minutes, and goes to the `platform` route as a ticket.

1. Open the dashboard. Note the source in the alert (`config`, `hook`, `user_reject`, or `user_abort`) and the tools in "Denied by tool and source".
2. Open the denied calls in the trail panel or in Explore. Group them by `prompt_id`: one prompt with many denials is one session that keeps trying.
3. Read the denied commands (`tool_parameters`):
   - The same command again and again: an agent in a loop against a deny rule. Stop that session and fix its instructions or the task.
   - A command that reaches for secrets, credentials, or a deploy: treat it as a security event. Stop the session, keep the events, and follow the incident process.
   - A command the team needs: change the rule through a pull request on the shared settings, never in a personal file.
4. Record what happened in the ticket the alert opened.

## Monthly review

Run the review command for the last month and file the output with the ticket or in <where review records live>. Compare the denials with the month before. A week without events while agents worked means a broken pipeline: the script exits 1 on an empty period.
