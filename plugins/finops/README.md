# finops

Cost data for a repository: what the systems and tools cost each month, how the cost splits across teams, and the cost per unit of work. Bills from every provider are converted to FOCUS (FinOps Open Cost and Usage Specification) columns first, so one script can build the baseline, the showback and the unit costs from them. Every figure on a page names its period and its source. A gate check reports figures that do not.

The skills report and propose. They change no billing setting, plan, seat count or contract. To charge teams for their cost, the user makes an agreement with the teams and finance.

Install:

```bash
claude plugin install finops@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/finops:cost-baseline` | Builds the monthly cost per provider and service from invoices, billing exports and FOCUS files. Reconciles each source with its own total, flags missing months, one-off charges, spikes and currency changes, and writes `docs/fin/cost-baseline.md`. |
| `/finops:showback` | Splits one month of cost across teams from tags and `finops/allocation.json`. Shared costs follow a stated split; unallocated cost is its own line. Writes `docs/fin/showback-<YYYY-MM>.md`. Charges no team. |
| `/finops:unit-costs` | Divides monthly cost by a named count (requests, customers, deploys or another unit the team picks), with the count's source and owner, and explains the trend. Writes `docs/fin/unit-costs.md`. |
| `/finops:saas-stack-audit` | Lists every SaaS tool from invoices, the SSO app list and expense exports, with owner, seats paid and used, overlaps and a keep, cut or replace proposal. Replace options include open-source and agent-built tools with switching cost and risk. Cancels nothing. Writes `docs/fin/saas-inventory.md`. |
| `/finops:focus-export` | Converts billing files to FOCUS with a column map per format, validates the rows, reconciles the totals and lists the declared deviations. Check before use: FOCUS spec version. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/finops/` (see the root README). Use it for your providers, column maps, teams, tag rules, units and SaaS owners.

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/docs/fin/index.md` | `docs/fin/index.md` | Home page of the FinOps space: the pages, the provenance convention and the data files |
| `templates/docs/fin/_templates/cost-baseline.md` | `docs/fin/_templates/cost-baseline.md` | Baseline page: sources, tables by provider and service, run rate, flags, method |
| `templates/docs/fin/_templates/showback.md` | `docs/fin/_templates/showback.md` | Showback page: allocation rules, cost per team, unallocated, shared costs, tag coverage |
| `templates/docs/fin/_templates/unit-costs.md` | `docs/fin/_templates/unit-costs.md` | Unit cost page: unit definitions, series, causes of change, limits |
| `templates/docs/fin/_templates/saas-inventory.md` | `docs/fin/_templates/saas-inventory.md` | SaaS inventory: tools, overlaps, replace options, actions |
| `templates/finops/allocation.json` | `finops/allocation.json` | Allocation rules for showback: team tag, teams and owners, rules, shared costs and their split |
| `templates/finops/focus-maps/example.json` | `finops/focus-maps/example.json` | Column map from one billing CSV format to FOCUS |
| `templates/scripts/focus_export.py` | `scripts/focus_export.py` | Python 3.9+, standard library only. Subcommands `convert`, `check`, `baseline`, `showback` and `unit` |
| `templates/finops/aws-cost-exporter/` | `finops/aws-cost-exporter/` | Optional. A Prometheus exporter for AWS Cost Explorer and AWS Budgets, with a response cache. Needs Docker and boto3. Copied only on request. |

The page templates carry the front matter of the `docs` module (`owner`, `reviewed`, `review_by`, `type`) plus `cost_period` and `cost_source`, so a filled page passes `docs.review` and `finops.cost-provenance`. If `docs/docs.json` exists, the skills offer to add the `fin` space to it.

### Period and source of every figure

A page whose figures share one period and one set of sources states both in its front matter:

```yaml
cost_period: 2026-07/2026-09     # months YYYY-MM/YYYY-MM, or days YYYY-MM-DD/YYYY-MM-DD
cost_source: <provider> invoices; <provider> cost export
```

A figure from another period or source carries its own marker on the same line:

```markdown
The support plan cost EUR 1,200.00 in the year before (period 2025-01-01/2025-12-31, source: <provider> invoice <number>).
```

The marker is `(period <range>, source: <source>)`, with the same two range forms. The reports of `scripts/focus_export.py` print the `cost_period` and `cost_source` lines for the page they feed, and every converted row carries `x_Source`.

## Gate check

`checks/cost_provenance.py` defines the rule `finops.cost-provenance` for the deploy gate of the `gate` module. It reads every file that matches `docs/**/*.md` and skips any path with a segment that starts with `_`, such as `_templates/`. An amount is a number with a currency symbol or code directly before or after it: €, $, £, EUR, USD or GBP. Fenced code blocks and inline code spans are skipped; the `title` and `summary` lines of the front matter are scanned. A page passes when its front matter has a well-formed `cost_period` and a non-empty `cost_source`, or when every line with an amount carries a well-formed marker.

| Snippet | Problem |
|---|---|
| `malformed cost_period` | `cost_period` is set and is not `YYYY-MM-DD/YYYY-MM-DD` or `YYYY-MM/YYYY-MM` with real dates and the start not after the end. One hit per page. |
| `cost figure without period and source: <amount>` | A line with an amount on a page without page-level provenance, and no marker on the line. One hit per line. |
| `malformed inline period: <range>` | A line whose marker holds a range in neither form. One hit per line. |

The result is `fail` on any hit, `pass` when every figure is covered and `n/a` when no file matches. More currencies: set the options `symbols` and `codes`, for example `"codes": ["EUR", "USD", "GBP", "CHF"]`.

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp plugins/finops/checks/cost_provenance.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/finops/checks/fixtures/finops.cost-provenance <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first:

   ```json
   "finops.cost-provenance": {"tier": "warn"}
   ```

   For another docs folder, add `"options": {"globs": ["<folder>/**/*.md"]}`.
4. Move it to `"tier": "block"` once the fixtures are in place and a false-positive test over your own pages is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run it on its own with `python3 .github/actions/gate/run.py --only finops.cost-provenance --dry-run`.

## Example run

[`examples/`](examples/README.md) holds one run of `cost-baseline`, `showback` and `saas-stack-audit` on synthetic inputs: two invented billing exports, an invented SSO app list and an invented SaaS bill, with the FOCUS files, the script output and the three docs pages. The baseline flags a planted spike, the SaaS inventory has keep, cut and replace rows, and `finops.cost-provenance` passes on the pages and fails on a copy without `cost_period` and `cost_source`. Every figure is labelled synthetic; no real bill was used. One published FOCUS 1.0 sample file (CC BY 4.0, with its attribution) shows the converter on a file the module did not generate. No skill copies the folder into a client repository.

`tests/test_focus_export.py` tests `scripts/focus_export.py` on those inputs (convert, check, baseline, showback and unit, with their error cases) and checks the example pages against the inputs. Run it from the repository root with `python3 plugins/finops/tests/test_focus_export.py`; CI runs it.

Demo: [machinebehavior.io/inside/docs/fin/](https://machinebehavior.io/inside/docs/fin/), the FinOps space of the platform behind machinebehavior.io.
