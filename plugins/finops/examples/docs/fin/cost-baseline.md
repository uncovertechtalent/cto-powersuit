---
title: Cost baseline (synthetic sample)
summary: Monthly cost per provider and service for 2026-04 to 2026-09, from two invented billing exports, with the flags the finops module raises.
parent:
order: 10
labels: finops, cost-baseline, synthetic
owner: synthetic owner: head of engineering
reviewed: 2026-10-21
review_by: 2027-01-19
type: reference
cost_period: 2026-04/2026-09
cost_source: SYNTHETIC Synthetic Cloud billing export 2026-04 to 2026-09; SYNTHETIC Synthetic Hosting invoice export 2026-04 to 2026-09
---
**Synthetic sample.** The providers, the teams and every figure on this page are invented for the finops example in `plugins/finops/examples/`. No real bill was used.

This baseline covers two providers, Synthetic Cloud and Synthetic Hosting, for the six months from 2026-04 to 2026-09. It is the first step of a cost review: it shows what the sample organisation spends each month and which months need an explanation.

Every figure on this page covers the months in `cost_period` and comes from the sources in `cost_source`. A figure from another period or source carries its own marker on its line: `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)`. Amounts stay in the currency the provider bills. A converted figure names the rate, the date of the rate and its source. Nothing on this page needed a conversion: both providers bill in EUR.

## Sources

| Source | Provider | Format | Months | Currency | Checked against |
|---|---|---|---|---|---|
| `inputs/synthetic-cloud-export-2026-04-to-2026-09.csv` | Synthetic Cloud | cost export CSV | 2026-04 to 2026-09 | EUR | `convert` printed EUR 45,826.00 for 75 rows; the control total of the sample is EUR 45,826.00 (set when the file was made) |
| `inputs/synthetic-hosting-export-2026-04-to-2026-09.csv` | Synthetic Hosting | invoice export CSV (semicolon, decimal comma) | 2026-04, 2026-05, 2026-07 to 2026-09 | EUR | `convert` printed EUR 8,269.31 for 16 rows; the control total of the sample is EUR 8,269.31 (set when the file was made) |

## By provider

| Provider | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---|---|---|---|---|---|---|
| Synthetic Cloud | EUR 6,380.00 | EUR 8,840.00 | EUR 6,498.00 | EUR 6,164.00 | EUR 11,216.00 | EUR 6,728.00 | EUR 45,826.00 |
| Synthetic Hosting | EUR 1,748.11 | EUR 1,630.30 | no data | EUR 1,630.30 | EUR 1,630.30 | EUR 1,630.30 | EUR 8,269.31 |

## By service

| Provider | Service | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---|---|---|---|---|---|---|---|
| Synthetic Cloud | Compute | EUR 3,650.00 | EUR 6,090.00 | EUR 3,705.00 | EUR 3,355.00 | EUR 8,375.00 | EUR 3,840.00 | EUR 29,015.00 |
| Synthetic Cloud | Data Transfer | EUR 305.00 | EUR 315.00 | EUR 318.00 | EUR 329.00 | EUR 331.00 | EUR 348.00 | EUR 1,946.00 |
| Synthetic Cloud | Managed Database | EUR 1,365.00 | EUR 1,375.00 | EUR 1,395.00 | EUR 1,400.00 | EUR 1,420.00 | EUR 1,435.00 | EUR 8,390.00 |
| Synthetic Cloud | Object Storage | EUR 560.00 | EUR 560.00 | EUR 580.00 | EUR 580.00 | EUR 590.00 | EUR 605.00 | EUR 3,475.00 |
| Synthetic Cloud | Support Plan | EUR 500.00 | EUR 500.00 | EUR 500.00 | EUR 500.00 | EUR 500.00 | EUR 500.00 | EUR 3,000.00 |
| Synthetic Hosting | Backup Storage | EUR 180.00 | EUR 180.00 |  | EUR 180.00 | EUR 180.00 | EUR 180.00 | EUR 900.00 |
| Synthetic Hosting | Dedicated Servers | EUR 1,289.00 | EUR 1,190.00 |  | EUR 1,190.00 | EUR 1,190.00 | EUR 1,190.00 | EUR 6,049.00 |
| Synthetic Hosting | VAT | EUR 279.11 | EUR 260.30 |  | EUR 260.30 | EUR 260.30 | EUR 260.30 | EUR 1,320.31 |

## Run rate

The run rate is the monthly cost of a provider without its one-off charges, as the median of its full months.

- Synthetic Cloud: EUR 6,531.00 per month. The six months without the 2026-05 purchase and the 2026-07 credit are EUR 6,380.00, 6,440.00, 6,498.00, 6,564.00, 6,728.00 and 11,216.00; the median is the mean of the middle two. The 2026-08 spike stays in the list: a median does not move for one high month.
- Synthetic Hosting: EUR 1,630.30 per month, from 2026-05 and 2026-07 to 2026-09. 2026-04 is left out because it holds the setup fee and the VAT on it. 2026-06 has no data and is not estimated.

## Flags

### Missing months

- Synthetic Hosting: no rows for 2026-06. The June invoice is missing from the sample on purpose. The month stays empty; it is not filled with an estimate. Open question for the provider contact: send the June invoice.

### One-off charges

| Month | Provider | Service | Category | Description | Amount |
|---|---|---|---|---|---|
| 2026-04 | Synthetic Hosting | Dedicated Servers | Purchase | Setup fee, additional server | EUR 99.00 |
| 2026-05 | Synthetic Cloud | Compute | Purchase | Reserved capacity, 12-month upfront (one time) | EUR 2,400.00 |
| 2026-07 | Synthetic Cloud | Compute | Credit | Promotional credit | EUR -400.00 |

All three are confirmed as one-off in the sample. They are out of the run rate above.

### Spikes

- Synthetic Cloud, Compute, 2026-08: EUR 8,375.00, above 2.0 times the median of its other months (EUR 3,705.00). Cause in the sample: a temporary load-test cluster of the search team, line `SYN-C-0053`, EUR 4,600.00. Without that line the month is EUR 3,775.00. The cluster is invented, like everything else here.

### Currency changes

None.

## Method

The commands run from `plugins/finops/examples/`. In a client repository the script sits at `scripts/focus_export.py`; in this plugin it is `../templates/scripts/focus_export.py`.

```bash
S=../templates/scripts/focus_export.py
python3 $S convert --in inputs/synthetic-cloud-export-2026-04-to-2026-09.csv \
  --map finops/focus-maps/synthetic-cloud-export.json \
  --out finops/focus/synthetic-cloud-2026-04-to-2026-09.csv --start 2026-04-01 --end 2026-10-01
python3 $S convert --in inputs/synthetic-hosting-export-2026-04-to-2026-09.csv \
  --map finops/focus-maps/synthetic-hosting-export.json \
  --out finops/focus/synthetic-hosting-2026-04-to-2026-09.csv --start 2026-04-01 --end 2026-10-01
python3 $S check finops/focus/*.csv
python3 $S baseline finops/focus/*.csv --from 2026-04 --to 2026-09
```

The script output is in `outputs/check.txt` and `outputs/baseline.md`. The column maps are in `finops/focus-maps/`, and the FOCUS files are in `finops/focus/`. They hold invented account ids and can sit in a public repository; real FOCUS files would not.

Declared deviations from FOCUS, for both files: `BillingAccountId`, `BillingAccountName`, `ChargeClass`, `ContractedCost`, `EffectiveCost`, `ListCost`, `ResourceId`, `ResourceName`, `ServiceCategory`, `SkuId`, `SkuPriceId`, `ConsumedQuantity` and `ConsumedUnit` are empty because the exports have no such columns. For Synthetic Hosting, `PricingQuantity`, `PricingUnit` and `SubAccountName` are empty as well. `BilledCost` is the amount on the invoice line; for Synthetic Hosting it is the net amount, and the VAT is its own line with the category Tax. Check before use: FOCUS spec version, as the `focus-export` skill says.

## Not in this baseline

Salaries, hardware and the tools in the [SaaS inventory](doc:fin/saas-inventory). Both providers are invented, so there is no real invoice behind any line.
