---
name: alert-routes
description: >
  Give every Prometheus alert rule a route label and a runbook_url annotation,
  route alerts in Alertmanager by that label to one receiver per team and
  severity with grouping and inhibit rules, write the missing runbooks, and
  test rules with promtool and routes with amtool. Use when alerts reach the
  wrong people or nobody, a new team or alert is added, or alerts have no
  runbook. Activates on "/alert-routes", "route the alerts", "who gets this
  alert", "add an alert", "alert routing", "alertmanager routes", "alerts have no
  runbook", "test the alert rules".
user-invocable: true
---

# Alert routes

Every alert rule in `observability/prometheus/rules/` carries three things:

| Field | Where | Meaning |
|---|---|---|
| `route` | label | The team that owns the alert. Alertmanager routes on it. |
| `severity` | label | `page`: act now, at any hour. `ticket`: next working day. `info`: no notification, visible in Grafana and Alertmanager. |
| `runbook_url` | annotation | A runbook page in this repository (path from the repository root) or an `http(s)` URL. |

`observability/alertmanager/alertmanager.yml` has one child route per team, matched on `route`, and below it one route per severity. Each leaf has its own receiver, named `<team>-<severity>`. Alerts with no route label, or a value that no route matches, go to the receiver `default`. The gate check `observability.alert-routes` enforces the labels and the runbooks on every run.

## Inputs

- The teams: short names, and for each team the person who keeps its routes and runbooks current.
- Per team and severity: the integration the receiver uses (webhook, chat, email, paging service) and where its secret lives. The user creates the secret files; never ask for the secret values in the chat.
- The alert rules to add or change, if any: the symptom, the query, the threshold and the team.

## Steps

1. **Inventory.** List every alert with its labels and runbook:

   ```bash
   grep -n -A12 -- '- alert:' observability/prometheus/rules/*.yml
   ```

   If the gate is installed with this module's rule, `python3 .github/actions/gate/run.py --only observability.alert-routes --dry-run` lists the gaps directly. Show the user which alerts have no route, an unknown route, no runbook or a runbook path that points to no file.
2. **Agree the teams and severities.** One route value per team, lowercase with hyphens. Write down with the user what `page` means for each team (who is on call, hours). An alert that nobody acts on within a day is `info` or gets deleted; ask the user to decide.
3. **Label every rule.** Add `route` and `severity` under `labels` and `runbook_url` under `annotations`. A `summary` annotation states the symptom in one sentence with the labels that locate it (`{{ $labels.job }}`). Keep the threshold and the `for:` duration in the rule; the runbook explains them.
4. **Write the missing runbooks.** For every `runbook_url` that points to no file: with the `docs` module installed, run `/docs:runbook` for the symptom. Otherwise write the page with the docs front matter (`title`, `summary`, `owner`, `reviewed`, `review_by`, `type: how-to`) and the sections Symptom, Checks, Steps, Verify, Roll back or escalate. The Symptom section quotes the alert name. Set `reviewed` to a date only when the steps were checked against the system; otherwise `reviewed: no`.
5. **Write the routes.** In `observability/alertmanager/alertmanager.yml`, per team:

   ```yaml
   - matchers: ['route="<team>"']
     receiver: <team>-ticket
     routes:
       - matchers: ['severity="page"']
         receiver: <team>-page
         repeat_interval: 1h
   ```

   Keep `group_by: [alertname, route]` at the top, so one notification carries all instances of one alert for one team. Keep the two inhibit rules: a `page` mutes the `ticket` and `info` of the same alert and team, and `TargetDown` mutes the other alerts of the same `job` and `instance`. Add an inhibit rule only with a written reason in a comment above it.
6. **Write the receivers.** One receiver per name used in the routes, plus `default`. Each receiver reads its secret from a file: `url_file`, `api_url_file` or the `_file` field of its integration, pointing to `/etc/alertmanager/secrets/<name>`. The files live in `observability/alertmanager/secrets/`, which `observability/.gitignore` lists. Check before use: the field names of each integration in the Alertmanager docs for the pinned version. A receiver with no integration drops its alerts; report every such receiver.
7. **Test the rules.** Every alert gets two cases in `observability/prometheus/tests/alerts_test.yml`: one input that fires it and one that stays quiet (below the threshold, under the `for:` duration, or below a traffic floor). `exp_labels` list every label of the firing alert, `route` and `severity` included; `exp_annotations` list every annotation with the templates expanded.

   ```bash
   promtool check rules observability/prometheus/rules/*.yml
   promtool test rules observability/prometheus/tests/alerts_test.yml
   ```

8. **Test the routes.** Add one case per team and severity to `observability/alertmanager/tests/routes.sh`, plus one with an unknown route that must reach `default`. Then:

   ```bash
   amtool check-config observability/alertmanager/alertmanager.yml
   sh observability/alertmanager/tests/routes.sh
   ```

   Each case runs `amtool config routes test --verify.receivers=<receiver> <label>=<value> ...` and prints `ok` or `FAIL`.

   Run promtool and amtool only when they are installed (`command -v promtool amtool`). Otherwise tell the user, and give the image commands; ask before the first run, because it pulls an image:

   ```bash
   docker run --rm -v "$PWD/observability/prometheus:/p:ro" -w /p/tests --entrypoint promtool prom/prometheus:v3.5.0 test rules alerts_test.yml
   AMTOOL="docker run --rm -v $PWD/observability/alertmanager:/am:ro --entrypoint amtool prom/alertmanager:v0.28.1" \
     CONFIG=/am/alertmanager.yml sh observability/alertmanager/tests/routes.sh
   ```

9. **Reload.** With the stack running: `curl -fsS -X POST http://127.0.0.1:9090/-/reload` and `curl -fsS -X POST http://127.0.0.1:9093/-/reload`. Check `curl -fsS http://127.0.0.1:9093/api/v2/status` for the loaded config.
10. **Send a test alert, if the user agrees.** It reaches a real receiver:

    ```bash
    curl -fsS -X POST -H 'Content-Type: application/json' http://127.0.0.1:9093/api/v2/alerts \
      -d '[{"labels": {"alertname": "RouteTest", "route": "<team>", "severity": "ticket"}, "annotations": {"summary": "Routing test. No action needed."}}]'
    ```

    Ask the receiving team to confirm it arrived.
11. **Gate.** Tell the user how to add `observability.alert-routes` with `/gate:add-rule` (see the module README). Do it only when the user says so.
12. **Report.**

## Output

- Alert rules with `route`, `severity` and `runbook_url`; a runbook page for every relative `runbook_url`.
- `alertmanager.yml` with one route and one receiver per team and severity, grouping and inhibit rules.
- Tests: a firing and a quiet case per alert, a routing case per team and severity.
- A short report: alerts changed, runbooks written, receivers without an integration, test results with exit codes, or the note that promtool or amtool is not installed.

## Rules

- Never delete an alert rule, route or receiver without the user's yes. Never overwrite a runbook.
- No secrets in any committed file. Receivers read secrets from files under `alertmanager/secrets/`.
- Every alert has exactly one `route` and one `severity`. A shared alert gets one owning team; the others see it in Grafana.
- A `page` needs a runbook that a person on call can follow at night without other context.
- Do not send a test alert or run `docker run` without asking. Do not commit or push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/observability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/observability/` exists, read its `README.md` first, then the files in `observability/alert-routes/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
