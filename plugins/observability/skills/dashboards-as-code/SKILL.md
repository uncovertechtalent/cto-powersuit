---
name: dashboards-as-code
description: >
  Keep Grafana dashboards in git as code: write a small JSON spec per
  dashboard, generate the dashboard JSON with a standard-library build script,
  let Grafana provision the files read-only, bring UI edits back into the spec,
  and review every change on the diff. Use when a team adds or changes a
  dashboard, edited one in the Grafana UI, or has dashboards that exist only in
  Grafana. Activates on "/dashboards-as-code", "add a dashboard", "change the
  dashboard", "dashboards as code", "export the dashboard to git", "I edited the
  dashboard in Grafana", "import this dashboard".
user-invocable: true
---

# Dashboards as code

Every dashboard has a spec in `observability/grafana/specs/<uid>.json`. `observability/grafana/build.py` turns each spec into `observability/grafana/dashboards/<uid>.json`, and Grafana provisions that folder read-only. The spec and the generated JSON are committed together. A reviewer reads the spec diff for intent and the JSON diff for the exact effect.

## Inputs

- The task: a new dashboard, a change to one, a UI edit to bring back, or dashboards that exist only in Grafana.
- For a new dashboard: the question it answers, the services it covers and the signals (request rate, errors, latency, saturation, logs).
- For a UI edit: the JSON exported from Grafana (dashboard menu, Export, Export as JSON, with "Export the dashboard to use in another instance" off).

## Spec format

```json
{
  "uid": "checkout",
  "title": "Checkout",
  "description": "One sentence: what the dashboard answers.",
  "tags": ["observability"],
  "refresh": "30s",
  "time": "now-6h",
  "variables": [{"name": "service", "label": "Service", "query": "label_values(up, job)"}],
  "rows": [
    {"title": "Traffic", "panels": [
      {"type": "stat", "title": "Requests / s", "unit": "reqps", "expr": "sum(rate(http_server_request_duration_seconds_count[5m]))"},
      {"type": "timeseries", "title": "Errors", "unit": "percentunit", "w": 12, "h": 8,
       "targets": [{"expr": "<PromQL>", "legend": "{{service_name}}"}],
       "thresholds": [["green", null], ["red", 0.05]]}
    ]}
  ]
}
```

| Field | Values |
|---|---|
| `type` | `stat`, `gauge`, `timeseries`, `table`, `logs`, `heatmap`, `text`, `raw` |
| `expr` or `targets` | One query, or a list of `{"expr", "legend"}` |
| `datasource` | `prometheus` (default) or `loki` (default for `logs`); the uids from `grafana/provisioning/datasources/datasources.yml` |
| `w`, `h` | Width 1 to 24 on Grafana's grid, height in grid units. Defaults: 6 x 4 for stat and gauge, 24 x 3 for text, 12 x 8 for the others |
| `unit`, `decimals`, `min`, `max`, `thresholds`, `stack`, `description` | Optional display settings; `thresholds` is a list of `[color, value]`, the first value `null` |
| `content` | Markdown for `text` panels |
| `panel` | For `raw`: a full Grafana panel object, used as it is |

Panels fill each row from left to right and wrap at 24 columns. A row without `title` places its panels without a row header. Files in `specs/` whose name starts with `_` are skipped.

## Steps

1. **Check the setup.** If `observability/grafana/build.py` is missing, copy it and the provisioning without overwriting:

   ```bash
   mkdir -p observability/grafana
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/observability/grafana/" observability/grafana/
   ```

   Run `python3 observability/grafana/build.py --check` to see the current state. A `DIFF` line means someone edited a generated file or forgot to build: run the build and show the diff before you change anything else.
2. **New dashboard.** Write `observability/grafana/specs/<uid>.json`. The uid is short, lowercase and stable: Grafana links and bookmarks use it. Start each dashboard with the question it answers in `description`. Use the signals the stack has: check metric names with `curl -fsS 'http://127.0.0.1:9090/api/v1/label/__name__/values'` and log labels with `curl -fsS http://127.0.0.1:3100/loki/api/v1/labels`. Put the panels a person reads first (rate, errors, latency) in the top row.
3. **Change a dashboard.** Edit the spec. Never edit a file in `dashboards/` by hand; the next build replaces it.
4. **Build.**

   ```bash
   python3 observability/grafana/build.py
   ```

   It prints one line per dashboard and a note for any file in `dashboards/` that no spec builds. It never deletes a file. Grafana reloads the folder within 30 seconds; no restart is needed.
5. **Bring a UI edit back.** Grafana cannot save a provisioned dashboard, so a UI edit ends as an export. Save the export outside the repository, then:

   ```bash
   python3 observability/grafana/build.py --diff /tmp/<uid>-export.json
   ```

   The output lists each difference by panel title: changed queries, units, thresholds, sizes, added or removed panels and variables. Apply each one to the spec, build, and run `--diff` again until it prints `no differences`. Use a `raw` panel for a panel that needs settings the spec fields do not cover.
6. **Adopt a dashboard that exists only in Grafana.** Export it, then:

   ```bash
   python3 observability/grafana/build.py --import /tmp/<uid>-export.json
   python3 observability/grafana/build.py
   ```

   The import writes `specs/<uid>.json` with every panel as `raw`. When the spec exists, it stops with an error; `--force` replaces the spec, so check first that git holds the old one. Replace `raw` panels with short forms where the fields cover them, build, and check with `--diff` against the export.
7. **Review.** Show `git diff -- observability/grafana/specs observability/grafana/dashboards`. Both files change in the same commit. In CI, `python3 observability/grafana/build.py --check` exits 1 when the committed JSON does not match its spec.
8. **Report.**

## Output

The spec and dashboard files written or changed, the build and check output, the `--diff` result for a UI edit, and the uids of new dashboards.

## Rules

- The spec is the source. Never hand-edit `dashboards/*.json`, and never save changes in the Grafana UI as the final step.
- Never delete a spec or a dashboard file. Report orphans; the user removes them.
- Keep uids stable. A new uid breaks links to the dashboard.
- No secrets, host names or customer names in specs. Queries filter with labels and variables.
- Data sources by provisioned uid only (`prometheus`, `loki`). An export made with "Export the dashboard to use in another instance" carries `${DS_...}` names; export again without it.
- When a panel threshold matches an alert rule, name the alert in the panel `description` and change both together.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/observability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/observability/` exists, read its `README.md` first, then the files in `observability/dashboards-as-code/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
