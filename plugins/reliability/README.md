# reliability

Reliability work for a repository, built on one service catalogue: one `services/<id>.yml` per service with its owner, tier, SLO, runbooks and dependencies. The skills set an availability target per service and check it against the dependencies, define SLOs with burn-rate alerts, run incidents, write blameless postmortems, publish a status page from the incident records, set the on-call rules, and record where each data store's backups live, who can delete them, and whether a restore works. A gate check reports catalogue entries without an owner, an SLO target or a runbook. A second gate check reports a data store without a backup copy outside the reach of production administrators, without a restore test, with a stale or failed one, or with a restore time above its target.

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
| `/reliability:backup-inventory` | Walks through each data store: where its backup lives, the schedule and retention, which identities can delete or overwrite it, whether a copy sits outside the reach of production administrators, the last restore test, and the measured restore time against its target. Writes `docs/sre/backups.md` and a restore-test runbook per store. It records what the team says and tests nothing in the cloud account. |
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
| `templates/docs/sre/backups.md` | `docs/sre/backups.md` | Backup inventory: production administrators, one table per data store (backup location, schedule, retention, data loss target, who can delete it, the out-of-reach copy, the last restore test, result, measured time, and target), the stores that are not backed up on purpose, and the restore test log |
| `templates/docs/sre/_templates/restore-test.md` | `docs/sre/_templates/restore-test.md` | Restore-test runbook: what to have ready, the steps, the verification that stops the clock, how to record the minutes, and clean up. The skill writes one page per store from it |

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

## Gate checks

### `reliability.service-catalog`

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

### `reliability.backup-inventory`

`checks/backup_inventory.py` defines the rule `reliability.backup-inventory`. It reads `docs/sre/backups.md` (option `globs`) and skips any path with a segment that starts with `_`. Each level 3 heading is a data store, and the `Field | Value` table under it holds the fields. The `Policy` table holds `Production administrators`. The rule reads the page the team writes and reads no cloud account, so a wrong entry passes until a restore test shows it.

| Snippet | Problem |
|---|---|
| `<store>: no copy outside production admin reach` | `Out-of-reach copy` is `none` |
| `<store>: no copy outside production admin reach recorded` | The field is missing, empty, or still a placeholder |
| `<store>: copy outside production admin reach has an unknown value: <value>` | A value other than `separate-account`, `immutable`, or `offline`, alone or in a comma or semicolon list |
| `<store>: out-of-reach copy can be deleted by production administrator <identity>` | An identity in `Out-of-reach deletable by` is also in `Production administrators` (compared in lower case, without a note in parentheses) |
| `<store>: identities that can delete or overwrite the out-of-reach copy not recorded` | A store claims an out-of-reach copy and leaves `Out-of-reach deletable by` empty |
| `no production administrators listed` | A store claims an out-of-reach copy and the `Policy` table lists no administrators |
| `<store>: no restore test` | `Last restore test` is `never`, empty, missing, or a placeholder |
| `<store>: restore test date is not a YYYY-MM-DD date: <value>`, `<store>: restore test date is in the future: <value>` | A date that is not a real ISO date, or one after the day of the run |
| `<store>: restore test has no result`, `<store>: restore result is not pass or fail: <value>` | `Restore result` is missing, or a value other than `pass` or `fail` |
| `<store>: last restore test failed` | `Restore result` is `fail` |
| `<store>: no measured restore time`, `<store>: no restore time target`, `... is not a duration: <value>` | A passed test without a measured time or a target, or one that is not a number with an optional unit (`min`, `h`, `d`; minutes without a unit) |
| `<store>: measured restore time <m> min is above the target <t> min` | The measured time is longer than the target |
| `<store>: restore test older than <N> days` | The last restore test is more than `max_age_days` days old |
| `no data store listed` | The page has no level 3 heading |

The result is `fail` on any hit except a stale restore test, `warn` when the only hits are restore tests older than `max_age_days`, `pass` when every store is clean, and `n/a` when no file matches. A stale test gives `warn`, so a pass fixture with a date in it does not start failing the day the date ages out. A `warn` result opens no finding and blocks nothing in either tier. Set `stale_fails` to `true` to make a stale test fail, and keep the dates in your fixtures current.

| Option | Default | What it sets |
|---|---|---|
| `globs` | `["docs/sre/backups.md"]` | The inventory pages to read |
| `max_age_days` | `90` | The age at which a restore test counts as stale |
| `stale_fails` | `false` | `true` makes a stale restore test a `fail` |

The rule ships on the `warn` tier. A `fail` on that tier records the hits and blocks nothing. Move it to `block` only after the fixtures are in place and a false-positive test over your own inventory is recorded.

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp plugins/reliability/checks/backup_inventory.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/reliability/checks/fixtures/reliability.backup-inventory <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first. For a restore test interval other than 90 days, add `options`:

   ```json
   "reliability.backup-inventory": {"tier": "warn", "options": {"max_age_days": 90}}
   ```

4. Move it to `"tier": "block"` once a false-positive test over your own `docs/sre/backups.md` is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks the fixtures and the record.

Run it on its own with `python3 .github/actions/gate/run.py --only reliability.backup-inventory --dry-run`. `tests/test_backup_inventory.py` tests the rule on its fixtures and on single changed fields, and CI runs it.

Demo: [machinebehavior.io/inside/status/](https://machinebehavior.io/inside/status/), the status page of the platform behind machinebehavior.io.
