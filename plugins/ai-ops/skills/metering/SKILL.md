---
name: metering
description: >
  Meter coding-agent spend per API request: send Claude Code telemetry to the
  observability stack, sum cost and tokens from the per-request api_request
  events in Loki, show them on a dashboard, and alert when spend passes an
  hourly budget. Use when agent spend is a line on the invoice nobody can break
  down, or before a team scales its agent use. Activates on "/metering",
  "meter agent spend", "what do our agents cost", "agent cost dashboard",
  "agent spend alert".
user-invocable: true
---

# Metering

Turns agent spend into a measured cost per request, per model and per hour, with a budget alert. It builds on the `observability` module's stack (Alloy, Loki, Prometheus, Grafana, Alertmanager); without it, run `/observability:stack-init` first.

## Method

Claude Code writes one `api_request` event per API call, with its cost, model and token counts. Sum those events. Claude Code's cumulative counters are not summed: parallel agent processes write the same series, which then reads as a stream of counter resets, and any sum over it is wrong. Identity attributes (email, account and organisation ids) are deleted in Alloy before storage; the observability template already does this.

## Steps

1. **Send telemetry.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/ai-ops/metering/claude-code.env.example` to `ai-ops/metering/`, set `<stack-host>`, and put the keys into the `env` block of `.claude/settings.json` (shared) or each developer's shell. Check before use: the variable names against the Claude Code monitoring documentation.
2. **Check the events arrive.** In Grafana Explore, query `{service_name=~"claude-code.*"} | event_name="api_request"` after a short agent session. No events: check the endpoint, the port (4317 gRPC) and that Alloy receives OTLP.
3. **Add the dashboard.** Copy `templates/observability/grafana/specs/agent-spend.json` into `observability/grafana/specs/` and run `python3 observability/grafana/build.py`.
4. **Add the budget alert.** Merge `templates/ai-ops/metering/loki-ruler.yml` into `observability/loki/loki.yml`, mount `observability/loki/rules` at `/loki/rules`, copy `templates/observability/loki/rules/fake/agent-spend.yml`, and replace `<hourly budget in USD>` with the budget the user sets. Add `observability/loki/rules/**/*.yml` to the `globs` of `observability.alert-routes` in `gate/gate.json`, so the rule needs a route and a runbook like every other.
5. **Write the cost page.** Copy `templates/docs/fin/agent-spend.md`, fill the budget table and the owner, and set `cost_period` and `cost_source` for any figure on the page (the `finops.cost-provenance` check reads them).
6. **Reconcile once a month.** Compare the summed events with the provider invoice for the same period. A gap above a few percent means a missing event source (another machine, another tool); find it before trusting the dashboard.

## Output

Telemetry configured, the Agent spend dashboard, the budget alert, and `docs/fin/agent-spend.md` with owner and budget.

## Rules

- Prompt and response text stay off in telemetry.
- Never set a budget yourself; the user sets it.
- Check before use: event and field names (`api_request`, `cost_usd`, `model`) against the Claude Code version in use.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/ai-ops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/ai-ops/` exists, read its `README.md` first, then the files in `ai-ops/metering/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
