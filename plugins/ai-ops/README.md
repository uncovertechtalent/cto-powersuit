# ai-ops

Operations for an engineering team's coding agents: one shared harness, spend metered per API request, an audit trail of tool calls, and a coordinator pattern for running several agent sessions at once. The knowledge infrastructure plugins are its optional parts:

| Part | Plugin | What it adds |
|---|---|---|
| Harness, metering, tool audit, coordinator | `ai-ops` (this plugin) | Shared settings, spend per request, who allowed each tool call, state in files |
| Output filter | [`vestige`](../vestige/) | A catalog of unwanted output patterns, calibrated to you, with hooks |
| Stance filters | [`stance`](../stance/) | Receipts, plain register, holding a position under pushback |
| Knowledge base | [`vault`](../vault/) | A Markdown vault with local search as an MCP server |

Install:

```bash
claude plugin install ai-ops@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/ai-ops:agent-harness` | Shared settings with narrow permissions, the instruction file, plugin list, MCP servers with secrets from the environment, and `docs/agents.md` with the owner |
| `/ai-ops:metering` | Claude Code telemetry to the observability stack, spend summed from per-request events, a dashboard and an hourly budget alert |
| `/ai-ops:tool-audit` | Every tool call with who decided it (a rule, a hook, or a person), allowed, denied, and asked counts per tool on a dashboard, an alert on a spike of denied calls, and a monthly review record from `tool_audit.py` |
| `/ai-ops:coordinator` | One session routes and verifies, workers do the work, all state in `work/ledger.md`, caps on parallel workers, resume after a stop |

## Templates

| Lands at | What it is |
|---|---|
| `.claude/settings.json` | Shared permissions: allow read-only commands and tests, ask before push and merge, deny secrets |
| `docs/agents.md` | The harness page: parts, permissions policy, plugins, owner |
| `ai-ops/metering/claude-code.env.example` | Telemetry variables for Claude Code |
| `ai-ops/metering/loki-ruler.yml` | Loki ruler block that sends log-based alerts to Alertmanager |
| `observability/loki/rules/fake/agent-spend.yml` | Hourly budget alert on the summed `api_request` events, with route and runbook |
| `observability/grafana/specs/agent-spend.json` | Dashboard spec for the `observability` module's generator: spend, requests, spend per hour by model |
| `docs/fin/agent-spend.md` | The cost page: method, budget table, what to do when the alert fires |
| `observability/grafana/specs/agent-tool-calls.json` | Dashboard spec: allowed, denied, asked, and hook-blocked calls, per tool and per source, and the trail of denied calls |
| `observability/loki/rules/fake/agent-tool-calls.yml` | `AgentToolDenialsSpike`: denied calls per decision source in 15 minutes above the threshold, with route and runbook |
| `docs/agent-tool-calls.md` | The audit page: what the trail records and what it misses, retention and access, the alert runbook, the monthly review |
| `work/ledger.md` | The coordinator's task ledger |

Metering and the tool audit build on the `observability` module. The spend page follows the `finops` module's provenance fields (`cost_period`, `cost_source`).

## Gate check

`checks/agent_settings.py` defines `ai-ops.agent-settings`. In the shared agent settings (`.claude/settings.json`, `.mcp.json`) it reports:

| Snippet | Problem |
|---|---|
| `permissions.allow grants a wildcard: <rule>` | An allow rule for every shell command, every fetch or every MCP tool (`Bash`, `Bash(*)`, `WebFetch`, `mcp__*` and similar) |
| `permissions.defaultMode is bypassPermissions` | Every permission check is off for every session |
| `<path> holds a literal value; use an environment variable reference` | A secret-named key (token, secret, password, API key) with a literal value in place of `${VAR}` |
| `secret pattern <pattern>` | A value that looks like a provider key or a private key |

The result is `n/a` when neither file exists. Personal settings in `.claude/settings.local.json` stay out of scope; keep that file out of git.

Enable it with `/gate:add-rule` (path A). It starts on `warn` and moves to `block` after the false-positive test is recorded under `"false_positive_test"` in `gate/gate.json`; `gate.rule-fixtures` checks this.

Demo: [machinebehavior.io/inside/services/agent-sessions/](https://machinebehavior.io/inside/services/agent-sessions/), the agent sessions service of the platform behind machinebehavior.io, metered per request.
