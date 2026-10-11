---
name: slo
description: >
  Define a service level objective for one service: the SLI as good events over
  valid events with exact queries, the target and window, the error budget,
  multiwindow burn-rate alerts and an error-budget policy, written to a docs
  page and linked from the service catalogue. Use when a service has a target
  and no way to measure it, when alerts page on causes users never see, or when
  releases and reliability work compete for the same time. Activates on "/slo",
  "define an SLO", "write an SLO", "error budget", "burn rate alert", "SLI for",
  "error budget policy".
user-invocable: true
---

# SLO

Writes one SLO page per service in `docs/sre/slo-<id>.md` and links it from `services/<id>.yml`. The page names the events, the exact queries, the target and window, the error budget in events and in time, the burn-rate alerts, and the policy that applies when the budget runs low. The target comes from the catalogue; run the `nines-per-service` skill first when it is missing.

## Inputs

- **Service** (required): the catalogue id, with `slo.target` set.
- **User journey**: what users do with the service, for example sign in, load the dashboard, pay.
- **Data**: the metrics or logs system and the metric names, or the probe that measures the service.
- **Product owner**: the person who agrees the error-budget policy with the service owner.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/sre
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/" docs/sre/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/." docs/sre/`. If `docs/sre/index.md` was new, fill its `owner`, `reviewed`, `review_by` and the tier table. If `docs/docs.json` exists and lists no space with the key `sre`, show this entry and add it after the user agrees:

   ```json
   {"key": "sre", "name": "Reliability", "about": "SLOs, on-call and postmortems for the services in the catalogue.", "owner": ""}
   ```

2. **Pick the SLI kind.** One or two per service to start: availability (the share of valid requests answered without a server error), latency (the share answered under a threshold), freshness (the share of reads that see data newer than a limit) or correctness. Measure as close to the user as possible: prefer the load balancer or the client to the application's own metrics.
3. **Define the events.** Valid events: which requests count, and which are left out (health checks, synthetic traffic, requests the client cancelled). Good events: which valid events count as good. Decide how to count client errors: a 4xx answer usually means the service behaved as designed, except throttling. Write both as exact queries.
4. **Test the queries on real data.** Run both over the last 30 days. Compute the SLI and compare it with the target. If the SLI is far below the target, stop and agree with the owner: fix the service first, or lower the target with the `nines-per-service` skill.
5. **Set the window.** Default a rolling 30 days, the same window as the target in the catalogue.
6. **Compute the error budget.** Error budget = (1 - target) × valid events in the window. Give it in events, from the expected volume, and in time, from the downtime table of the `nines-per-service` skill.
7. **Write the burn-rate alerts.** Use the table on the SLO template: fast burn (1 h and 5 min, burn rate 14.4, page), slow burn (6 h and 30 min, burn rate 6, page), drift (3 days and 6 h, burn rate 1, ticket). For a 30-day window, burn rate = budget used × 720 h / long window. For another window, compute the rates again with the same formula. Each alert fires only when the long and the short window both exceed the rate. Write the rules in the team's alerting system, with a `runbook_url` on each. Show the rules to the user; the user merges and deploys them.
8. **Draft the error-budget policy.** What changes at more than 50% budget left, at 50% or less, and when the budget is spent; who decides; the exceptions; and the share of budget one incident may use before a postmortem is required. The service owner and the product owner agree the policy. The skill drafts it.
9. **Write the page.** Start from `docs/sre/_templates/slo.md`. Fill every field, `reviewed` today and `review_by` 90 days later. Replace every `<placeholder>`. Add the page to the table in `docs/sre/index.md`.
10. **Link it from the catalogue.** In `services/<id>.yml` set `slo.sli` to the good-over-valid definition in one line and `slo.doc: doc:sre/slo-<id>`. Change no other field without asking.
11. **Check.** With the `docs` module, run `python3 scripts/build_docs.py --check`. If the gate runs the rule, run `python3 .github/actions/gate/run.py --only reliability.service-catalog --dry-run`.
12. **Report.**

## Output

The page path, the SLI with both queries, the measured value over the last 30 days, the target and window, the budget in events and minutes, the alert rules, the policy draft, and the catalogue diff.

## Rules

- An SLI is a ratio of good events to valid events, from data that exists today. No SLO page with a query nobody ran.
- Alerts page on budget burn, a symptom users feel. Every alert links a runbook.
- The target on the page equals `slo.target` in the catalogue.
- The policy binds only after the service owner and the product owner agree it. Until then the page marks it as a draft.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/slo/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
