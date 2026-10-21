# finops example: a run you can watch

**Everything in this folder is synthetic.** The providers (Synthetic Cloud, Synthetic Hosting), the SaaS tools (every name starts with "Synth"), the teams, the owners, the account ids and every figure are invented. No real company's billing data was used, and no figure here is a result of any real organisation. Each file, page and output says so: the raw files start with `synthetic-`, every FOCUS row has an `x_Source` that starts with `SYNTHETIC`, every report prints that source, and every page opens with a "Synthetic sample" line.

The folder is one run of three skills on those inputs: `/finops:cost-baseline` (with `/finops:focus-export` as its first step), `/finops:showback` and `/finops:saas-stack-audit`. The layout is the one the skills create in a client repository, so a reader sees what lands where.

## What each file shows

| File | What it shows |
|---|---|
| `inputs/synthetic-cloud-export-2026-04-to-2026-09.csv` | A raw cloud billing export: 75 lines, six months, EUR, one line per service, account and team tag per month. It holds the planted load-test line that makes August spike, a one-time reservation purchase (2026-05) and a credit (2026-07). Control total: EUR 45,826.00 (synthetic). |
| `inputs/synthetic-hosting-export-2026-04-to-2026-09.csv` | A raw hosting invoice export in a second format: semicolon, decimal comma, `dd.mm.yyyy` dates, VAT as its own line. It has a setup fee in 2026-04 and no invoice for 2026-06, on purpose. Control total: EUR 8,269.31 (synthetic). |
| `inputs/synthetic-saas-billing-2025-10-to-2026-09.csv` | Card and invoice lines for eight SaaS vendors over 12 months, with one vendor under two billing names. Total EUR 18,900.00 (synthetic). |
| `inputs/synthetic-sso-app-export-2026-09-30.csv` | The SSO app list: users assigned and distinct users active in the last 90 days, counts only. One app has a user count and no bill; one billed tool has no SSO app. |
| `inputs/synthetic-saas-owners-and-terms.csv` | Owner, job, renewal date and notice days per tool, as an owner list would give them. One tool has no owner. |
| `finops/focus-maps/*.json` | One column map per raw format. They turn the two raw files into FOCUS columns. |
| `finops/focus/*.csv` | The two raw files in FOCUS columns, written by `convert`. Every row carries its `x_Source`. |
| `finops/allocation.json` | The showback rules: the `team` tag, three teams, one sub-account rule, and two shared costs (the support plan and the VAT) split in proportion to direct cost. |
| `outputs/check.txt` | What `check` prints: 91 rows, the `BilledCost` per provider, the sources. |
| `outputs/baseline.md` | What `baseline` prints: cost per provider and per service for six months, and the flags: the missing hosting month, three one-off charges and one spike. |
| `outputs/showback-2026-08.md` | What `showback` prints for 2026-08: cost per team, the unallocated lines, the shared costs, tag coverage, and a reconciliation line that reads zero. |
| `outputs/cost-provenance-pass.txt` | The gate check `finops.cost-provenance` on the three pages: pass. |
| `outputs/cost-provenance-fail.txt` | The same check on a copy of the baseline page without `cost_period` and `cost_source`: every line with an amount is reported. |
| `docs/fin/cost-baseline.md` | The baseline page: the script tables, the run rate per provider, the flags with their causes, the method and the declared FOCUS deviations. |
| `docs/fin/showback-2026-08.md` | The showback page: the allocation rules, cost per team, the proposed fixes for unallocated lines, and the questions for the teams. It charges no team. |
| `docs/fin/saas-inventory.md` | The SaaS inventory: eight tools with owner, seats paid and used, cost per month, renewal and notice dates, one overlap, replace options with switching cost and risk, and actions with owners and dates. It cancels nothing. |

## What a video can show

- Spike flag: `outputs/baseline.md` flags the planted compute spike, Synthetic Cloud Compute in 2026-08 at EUR 8,375.00 (synthetic), above 2.0 times the median of its other months, EUR 3,705.00 (synthetic); `outputs/showback-2026-08.md` then shows the search team carrying it.
- Keep, cut, replace: in the Tools table of `docs/fin/saas-inventory.md`, SynthCall is a Cut (no owner, 2 of 15 seats used, SynthMeet does the same job, EUR 120.00 per month (synthetic)), SynthMeet a Keep and SynthDiagram a Replace with three options.
- Cost provenance: `finops.cost-provenance` passes on the three pages (`outputs/cost-provenance-pass.txt`) and reports the figure lines of the baseline page once `cost_period` and `cost_source` are removed (`outputs/cost-provenance-fail.txt`).

## Run it again

From `plugins/finops/examples/`. In a client repository the script sits at `scripts/focus_export.py`; here it is `../templates/scripts/focus_export.py`.

```bash
S=../templates/scripts/focus_export.py
python3 $S convert --in inputs/synthetic-cloud-export-2026-04-to-2026-09.csv --map finops/focus-maps/synthetic-cloud-export.json --out finops/focus/synthetic-cloud-2026-04-to-2026-09.csv --start 2026-04-01 --end 2026-10-01
python3 $S convert --in inputs/synthetic-hosting-export-2026-04-to-2026-09.csv --map finops/focus-maps/synthetic-hosting-export.json --out finops/focus/synthetic-hosting-2026-04-to-2026-09.csv --start 2026-04-01 --end 2026-10-01
python3 $S check finops/focus/*.csv
python3 $S baseline finops/focus/*.csv --from 2026-04 --to 2026-09
python3 $S showback --alloc finops/allocation.json --month 2026-08 finops/focus/*.csv
```

The check on the pages needs a gate config with the rule. Save this as `gate.json` outside the folder, with the path of this plugin's `checks` folder:

```json
{"name": "finops-example", "rules_dir": "<path to plugins/finops/checks>", "rules": {"finops.cost-provenance": {"tier": "block"}}}
```

```bash
python3 ../../gate/templates/.github/actions/gate/run.py --config gate.json --root . --dry-run --exit-code --sha example
```

To see it fail, copy `docs/` to a scratch folder, delete the two `cost_` lines from the front matter of the copy's `cost-baseline.md`, and run the same command with `--root` set to that folder.

The tests run all of this and compare the results with the committed files: `python3 plugins/finops/tests/test_focus_export.py` from the repository root. CI runs them next to the other plugin tests.

## What is not here

- The `saas-stack-audit` skill has no script, so `docs/fin/saas-inventory.md` is not regenerated by a command. The tests check its tool rows against the three SaaS inputs: owners, seats paid and used, cost per month, renewal and notice dates, and the totals.
- The `unit-costs` skill was not run: it needs a count from a real metric. The tests cover `focus_export.py unit` on counts written by the test, labelled synthetic.
- The replace options and their switching and running costs are invented estimates, not quotes. They name no real product.
- The cause of the August spike, the answers to the open questions and the owners are invented, like the data. A real run takes them from people.
- The raw exports hold one line per service, account and team per month, not one per day. A real cloud export is far bigger; the column maps and the script do not change for it (`granularity: day` is the default).
- Check before use: FOCUS spec version. The script's column list follows one release of the FOCUS columns; the baseline page declares the columns the sample leaves empty.
