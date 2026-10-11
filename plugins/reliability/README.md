# reliability

Reliability work for a repository, built on one service catalogue: one `services/<id>.yml` per service with its owner, tier, SLO, runbooks and dependencies. The skills set an availability target per service and check it against the dependencies, define SLOs with burn-rate alerts, run incidents, write blameless postmortems, publish a status page from the incident records, and set the on-call rules. A gate check reports catalogue entries without an owner, an SLO target or a runbook.

The skills prepare files, rules and commands. They never push, deploy, page, or change production, and the user publishes every change.

Install:

```bash
claude plugin install reliability@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/reliability:nines-per-service` | Picks an availability target per service from user impact, tier and dependencies. Shows the allowed downtime per 30 days, quarter and year, checks the target against the product of its serial dependencies, and writes it into `services/<id>.yml`. |
| `/reliability:slo` | Defines the SLI as good events over valid events with exact queries, the target and window, the error budget, multiwindow burn-rate alerts and an error-budget policy. Writes `docs/sre/slo-<id>.md` and links it from the catalogue. |
| `/reliability:incident` | Runs an incident: declaration, severity, roles (incident lead, comms, operations), a timestamped log, public updates in `incidents/incidents.json`, the status page build, resolve and close, then hands over to `postmortem`. |
| `/reliability:postmortem` | Writes a blameless postmortem with timeline, impact in minutes, users and requests, contributing factors, what went well and poorly, and action items with owners and dates. Links it from the incident record. |
| `/reliability:status-page` | Sets up a static status page built by `scripts/build_status.py` from the catalogue and the incident records, and adds the build to the deploy job. |
| `/reliability:on-call` | Writes the rotation, the escalation policy, the handover checklist and the paging rules (page only on user-facing symptoms, every alert links a runbook), with an audit of the existing alert rules. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/reliability/` (see the root README). Use it for your tiers, severity levels, starting targets, policy thresholds, rotation and incident history.

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/services/_template.yml` | `services/_template.yml` | Catalogue entry: id, name, description, owner, tier, lifecycle, slo (sli, target, window, doc), runbooks, depends_on, soft_depends_on, docs, status_page |
| `templates/incidents/incidents.json` | `incidents/incidents.json` | The incident records, empty to start |
| `templates/incidents/incidents.schema.json` | `incidents/incidents.schema.json` | JSON Schema of the records, with a full example incident under `examples` |
| `templates/scripts/build_status.py` | `scripts/build_status.py` | Python 3.9+, standard library only. Builds `index.html` and `status.json`; `--check` validates the records and prints each target next to its dependency ceiling |
| `templates/docs/sre/index.md` | `docs/sre/index.md` | Home page of the Reliability space: pages, tiers, records |
| `templates/docs/sre/_templates/slo.md` | `docs/sre/_templates/slo.md` | SLO page: indicator, target and window, burn-rate alerts, error-budget policy, history |
| `templates/docs/sre/_templates/postmortem.md` | `docs/sre/_templates/postmortem.md` | Postmortem page: summary, impact, timeline, contributing factors, what went well and poorly, action items |
| `templates/docs/sre/on-call.md` | `docs/sre/on-call.md` | On-call policy: rotation, load limits, escalation, paging rules, handover checklist, review |

The doc pages carry the front matter of the `docs` module (`owner`, `reviewed`, `review_by`, `type`), so a filled page passes `docs.review`. If `docs/docs.json` exists, the skills offer to add the `sre` space to it.

### Catalogue entry

```yaml
id: web-app
name: Web app
owner: Web team
tier: 1
lifecycle: production
slo:
  sli: page requests answered below 500 within 1 s, over valid page requests
  target: 99.9
  window: 30d
  doc: doc:sre/slo-web-app
runbooks:
  - doc:sre/runbook-web-app-down
depends_on: [api, database]   # serial: the service fails when one of them fails
soft_depends_on: [search]     # the service survives these with a fallback
```

`depends_on` feeds the dependency ceiling: the product of the targets of the serial dependencies. A serial dependency outside the team, such as a managed database, gets its own entry with `lifecycle: external`, the provider's commitment as its target, and `status_page: hidden` when users do not know it by name.

## Gate check

`checks/service_catalog.py` defines the rule `reliability.service-catalog` for the deploy gate of the `gate` module. It reads every file that matches `services/*.yml` or `services/*.yaml` and skips any path with a segment that starts with `_`, such as `services/_template.yml`. It parses a YAML subset inside the rule file: top-level `key: value`, flow lists `[a, b]`, block lists, folded and literal blocks (`>` and `|`), and one nested level such as `slo:`.

| Snippet | Problem |
|---|---|
| `missing owner` | No `owner`, or an empty one |
| `missing slo`, `slo is not a mapping`, `slo without target` | No `slo` block, or one without `target` |
| `slo target is not a number: <value>`, `slo target outside 0 to 100: <value>` | A target that is not a number (a trailing `%` is allowed), or one at or below 0 or at or above 100 |
| `no runbook link` | No `runbooks`, or an empty list |
| `runbook link does not resolve: <link>` | A link that resolves to nothing. A link resolves when it is a relative path to an existing file (from the `services/` folder or the repository root), a `doc:<space>/<slug>` link with `docs/<space>/<slug>.md` present, or an http(s) URL. Every link in the list must resolve. |
| `unreadable entry: <reason>` | A line outside the YAML subset |

The result is `fail` on any hit, `pass` when every entry is clean and `n/a` when no file matches. For another docs folder, set the option `docs_dir`.

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp plugins/reliability/checks/service_catalog.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/reliability/checks/fixtures/reliability.service-catalog <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first:

   ```json
   "reliability.service-catalog": {"tier": "warn"}
   ```

   For another catalogue folder, add `"options": {"globs": ["<folder>/*.yml"]}`.
4. Move it to `"tier": "block"` once the fixtures are in place and a false-positive test over your own catalogue is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run it on its own with `python3 .github/actions/gate/run.py --only reliability.service-catalog --dry-run`.

Demo: [machinebehavior.io/inside/status/](https://machinebehavior.io/inside/status/), the status page of the platform behind machinebehavior.io.
