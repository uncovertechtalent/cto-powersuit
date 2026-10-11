---
name: stack-init
description: >
  Set up an observability stack in the current repository: Alloy, Prometheus,
  Loki, Grafana and Alertmanager in docker compose, with config files,
  provisioned data sources and dashboards, retention settings and an
  .env.example, then start it and check that each component answers. Use when a
  team has no metrics, logs or alerting yet, or runs them by hand outside git.
  Never overwrites a file. Activates on "/stack-init", "set up observability",
  "add monitoring", "set up prometheus and grafana", "observability stack",
  "start the monitoring stack".
user-invocable: true
---

# Stack init

Copies a five-component observability stack into `observability/` in the repository and brings it up with docker compose. Alloy receives OTLP from the services and forwards metrics to Prometheus and logs to Loki. Prometheus scrapes targets, evaluates the alert rules and sends alerts to Alertmanager. Grafana reads all three through provisioned data sources and loads dashboards from files in git.

## Inputs

- The repository: the current working directory, or a path the user names.
- The services to observe: for each, its name, and whether it serves `/metrics` (host and port) or sends OTLP.
- The teams that receive alerts, as short names (`platform`, `app`). The `alert-routes` skill uses them.
- Retention for metrics, logs and silences. Defaults: 30 days, 30 days, 120 hours.
- Where the stack runs: this machine only (default), or a host on the network.

## Steps

1. **Check the repository and the tools.** Find the root with `git rev-parse --show-toplevel`. Run `docker compose version` and `python3 --version` (3.9 or later). If `observability/` exists, list what is in it and ask before going on.
2. **Copy without overwriting.**

   ```bash
   mkdir -p observability
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/observability/" observability/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/observability/." observability/`. Report the files copied and the files skipped because they existed.
3. **Create `.env`.** Run `cp -n observability/.env.example observability/.env`. Ask the user to set `GRAFANA_ADMIN_PASSWORD` in `observability/.env` themselves. Never write a password into a file, a command or the chat. Set the retention values and `BIND_ADDR` from the inputs. Check that `observability/.gitignore` lists `.env` and `alertmanager/secrets/`, and that `git check-ignore observability/.env` prints the path.
4. **Add the services.**
   - Services with `/metrics`: add one scrape job per service at the end of `observability/prometheus/prometheus.yml`, from the commented example there. The job name is the service name.
   - Services that send OTLP: set `OTEL_EXPORTER_OTLP_ENDPOINT=http://<stack-host>:4318`, `OTEL_SERVICE_NAME=<service>` and `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative` in each service's environment. Show the change and ask before you edit a service's deploy config.
   - Personal data: if the services send attributes with personal data, add their keys to the `scrub` block in `observability/alloy/config.alloy`.
5. **Set the teams.** Replace the example teams `platform` and `app` in `observability/prometheus/rules/alerts.yml`, `observability/alertmanager/alertmanager.yml` and `observability/alertmanager/tests/routes.sh` with the user's team names, or keep them. The `alert-routes` skill covers the receivers.
6. **Validate the configs before the first start.** These commands read files only:

   ```bash
   docker compose --project-directory observability config --quiet
   python3 observability/grafana/build.py --check
   ```

   If `promtool` and `amtool` are installed, also run `promtool check config observability/prometheus/prometheus.yml`, `promtool test rules observability/prometheus/tests/alerts_test.yml` and `amtool check-config observability/alertmanager/alertmanager.yml`. Without them, the same tools run from the images (see the `alert-routes` skill); ask before the first `docker run`, because it pulls images.
7. **Start.** Ask first: the first start pulls five images. Then:

   ```bash
   docker compose --project-directory observability up -d
   docker compose --project-directory observability ps
   ```

8. **Check that each component answers.** Each command exits 0 when the component is ready. Use the host from `BIND_ADDR` in place of `127.0.0.1` when it differs.

   ```bash
   curl -fsS http://127.0.0.1:9090/-/ready      # Prometheus
   curl -fsS http://127.0.0.1:9093/-/ready      # Alertmanager
   curl -fsS http://127.0.0.1:3100/ready        # Loki; can take up to a minute after the start
   curl -fsS http://127.0.0.1:12345/-/ready     # Alloy
   curl -fsS http://127.0.0.1:3000/api/health   # Grafana; the JSON shows "database": "ok"
   ```

   Then check that the pieces see each other:

   ```bash
   curl -fsS http://127.0.0.1:9090/api/v1/targets | python3 -c 'import json,sys; [print(t["labels"]["job"], t["health"]) for t in json.load(sys.stdin)["data"]["activeTargets"]]'
   curl -fsS http://127.0.0.1:9090/api/v1/rules | python3 -c 'import json,sys; print(sum(len(g["rules"]) for g in json.load(sys.stdin)["data"]["groups"]), "rules loaded")'
   curl -fsS http://127.0.0.1:9090/api/v1/alertmanagers | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["activeAlertmanagers"])'
   ```

   Every target reads `up`, the rule count matches `observability/prometheus/rules/`, and one Alertmanager is active. For a component that does not answer, read `docker compose --project-directory observability logs <service> --tail 50` and fix the config before you go on.
9. **Check Grafana.** Ask the user to log in at `http://127.0.0.1:3000` and open the folder "Observability". The dashboard "Service overview" is there, and the three data sources under Connections test green.
10. **Report.**

## Retention

| Component | Setting | Where |
|---|---|---|
| Prometheus | `PROM_RETENTION` (time). For a size cap, add `--storage.tsdb.retention.size=<size>` to the command in `docker-compose.yml`. | `observability/.env` |
| Loki | `LOKI_RETENTION`, a multiple of 24h. The compactor deletes older chunks. | `observability/.env`, read by `loki/loki.yml` |
| Alertmanager | `AM_RETENTION`: silences and the notification log | `observability/.env` |
| Grafana | Dashboards live in git; the volume holds users and preferences only | |

Disk use grows with the number of series and log lines. Check it after a week with `docker system df -v` and adjust the retention.

## Output

- `observability/` in the repository: `docker-compose.yml`, `.env.example`, `.gitignore`, `alloy/config.alloy`, `prometheus/prometheus.yml`, `prometheus/rules/alerts.yml`, `prometheus/tests/alerts_test.yml`, `alertmanager/alertmanager.yml`, `alertmanager/tests/routes.sh`, `loki/loki.yml`, `grafana/provisioning/`, `grafana/build.py`, `grafana/specs/service-overview.json`, `grafana/dashboards/service-overview.json`.
- A running stack, or the reason it does not start.
- A short report: files copied and skipped, the result of each health check, the targets and their state, and the next steps (`alert-routes` for receivers, `dashboards-as-code` for dashboards, the runbooks the alerts point to).

## Rules

- Never overwrite, delete or move an existing file. Ask before editing a service's config or a CI workflow.
- No secrets in any committed file. Passwords go in `observability/.env`; receiver URLs and tokens go in files under `observability/alertmanager/secrets/`. Both stay out of git.
- Ask before `docker compose up` and before any `docker run`: both pull images.
- Keep the image tags pinned. Check before use: image versions. Compare each tag in `docker-compose.yml` with the release page of its project before the first start and before an upgrade.
- Keep `BIND_ADDR=127.0.0.1` unless the user wants network access and has authentication in front of the ports.
- The alert rules point to runbook pages under `docs/eng/`. Tell the user which ones do not exist yet; the `alert-routes` skill writes them.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/observability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/observability/` exists, read its `README.md` first, then the files in `observability/stack-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
