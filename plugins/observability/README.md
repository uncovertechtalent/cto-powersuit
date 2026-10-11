# observability

Metrics, logs, dashboards and alerting for a repository, kept in git. Alloy receives OpenTelemetry from the services, Prometheus stores metrics and evaluates the alert rules, Loki stores logs, Alertmanager routes alerts and Grafana shows all of it. The whole stack runs from one docker compose file. Dashboards are generated from small specs, every alert rule carries a route label and a runbook, and a gate check reports alert rules that break this format.

Install:

```bash
claude plugin install observability@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/observability:stack-init` | Copies the stack into `observability/`, creates `.env` from the example, adds the scrape jobs and OTLP settings for the services, validates the configs, starts the stack and checks that each component answers. |
| `/observability:dashboards-as-code` | Writes or changes a dashboard spec, builds the dashboard JSON, brings an edit made in the Grafana UI back into the spec with `build.py --diff`, adopts dashboards that exist only in Grafana with `build.py --import`, and shows the diff for review. |
| `/observability:alert-routes` | Adds `route`, `severity` and `runbook_url` to every alert rule, writes one Alertmanager route and receiver per team and severity with grouping and inhibit rules, writes the missing runbooks, and tests rules with `promtool test rules` and routes with `amtool config routes test`. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/observability/` (see the root README). Use it for your teams and receivers, your retention, your services and your dashboard conventions.

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/observability/docker-compose.yml` | `observability/docker-compose.yml` | Alloy, Prometheus, Alertmanager, Loki and Grafana with pinned image tags, ports bound to `BIND_ADDR` |
| `templates/observability/.env.example` | `observability/.env.example` | Grafana login, bind address and retention settings, with placeholders |
| `templates/observability/.gitignore` | `observability/.gitignore` | Keeps `.env` and `alertmanager/secrets/` out of git |
| `templates/observability/alloy/config.alloy` | `observability/alloy/config.alloy` | OTLP receiver on 4317 and 4318, deletes identity attributes, sends metrics to Prometheus and logs to Loki |
| `templates/observability/prometheus/prometheus.yml` | `observability/prometheus/prometheus.yml` | Scrape jobs for the stack, OTLP settings, the Alertmanager target and an example job for a service |
| `templates/observability/prometheus/rules/alerts.yml` | `observability/prometheus/rules/alerts.yml` | Alert rules for the stack and one example service alert, each with `route`, `severity` and `runbook_url` |
| `templates/observability/prometheus/tests/alerts_test.yml` | `observability/prometheus/tests/alerts_test.yml` | promtool unit tests: a firing and a quiet case per alert |
| `templates/observability/alertmanager/alertmanager.yml` | `observability/alertmanager/alertmanager.yml` | Routes by `route` and `severity`, grouping, inhibit rules, one receiver per team and severity |
| `templates/observability/alertmanager/tests/routes.sh` | `observability/alertmanager/tests/routes.sh` | amtool routing tests, one case per team and severity |
| `templates/observability/loki/loki.yml` | `observability/loki/loki.yml` | Single-binary Loki on the file system, retention from `LOKI_RETENTION` |
| `templates/observability/grafana/provisioning/` | `observability/grafana/provisioning/` | Data sources with fixed uids, and a read-only file provider for the dashboards |
| `templates/observability/grafana/build.py` | `observability/grafana/build.py` | Dashboard generator. Python 3.9+, standard library only. `--check`, `--diff` and `--import` modes |
| `templates/observability/grafana/specs/service-overview.json` | `observability/grafana/specs/service-overview.json` | Example spec: request rate, errors, latency, error logs and scrape targets |
| `templates/observability/grafana/dashboards/service-overview.json` | `observability/grafana/dashboards/service-overview.json` | The dashboard JSON that `build.py` writes from the example spec |

Check before use: image versions. The tags in `docker-compose.yml` are pinned; compare each one with the release page of its project before the first start and before an upgrade.

## Gate check

`checks/alert_routes.py` defines the rule `observability.alert-routes` for the deploy gate of the `gate` module. For each alert rule in the files that match `observability/prometheus/rules/*.yml` (and `*.yaml`) it reports:

| Snippet | Problem |
|---|---|
| `<alert>: missing route label` | No `route` label, or an empty one |
| `<alert>: route <value> matches no Alertmanager route or receiver` | The Alertmanager config exists and no route matcher (`matchers`, `match`, `match_re`) or receiver name accepts the value |
| `<alert>: missing runbook_url` | No `runbook_url` annotation, or an empty one |
| `<alert>: runbook_url points to no file: <path>` | A relative `runbook_url` that names no file in the repository. The path is read from the repository root, then from the folder of the rule file; `#anchor` and `?query` are ignored |
| `<alert>: runbook_url scheme is not http or https: <scheme>` | A URL with another scheme |
| `not a rule file: no groups list` | A matched file without a `groups` list |
| `alertmanager config has no route tree` | The Alertmanager config has no `route` |

Recording rules are skipped, and so is any path with a segment that starts with `_`. The result is `fail` on any hit, `pass` when every alert is clean and `n/a` when no file matches. The rule parses YAML with a small parser inside the rule file, so it needs no third-party package.

Options:

| Option | Default | Meaning |
|---|---|---|
| `globs` | `["observability/prometheus/rules/*.yml", "observability/prometheus/rules/*.yaml"]` | The rule files |
| `route_label` | `route` | The label Alertmanager routes on |
| `alertmanager` | `observability/alertmanager/alertmanager.yml` | The Alertmanager config. When the file is missing, route values are not checked against it |

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp -n plugins/observability/checks/alert_routes.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -Rn plugins/observability/checks/fixtures/observability.alert-routes <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first:

   ```json
   "observability.alert-routes": {"tier": "warn"}
   ```

   For rules in another folder, add `"options": {"globs": ["<folder>/*.yml"], "alertmanager": "<path>/alertmanager.yml"}`, and move the fixture files to the same paths in `gate/fixtures/observability.alert-routes/pass/` and `fail/`, so `gate.rule-fixtures` runs them with your options.
4. Move it to `"tier": "block"` once the fixtures are in place and a false-positive test over your own rules is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run it on its own with `python3 .github/actions/gate/run.py --only observability.alert-routes --dry-run`.

The template alerts point to runbook pages under `docs/eng/`. Until those pages exist, the rule reports one hit per alert; `/observability:alert-routes` writes them.

Demo: [machinebehavior.io/inside/mission-control/](https://machinebehavior.io/inside/mission-control/), the live operations view of the platform behind machinebehavior.io.
