---
name: unit-costs
description: >
  Compute cost per unit of work per month (per request, customer, deploy or
  another unit the team picks), with the cost from the cost baseline, the count
  from a named metric with its source, and the trend, written to a docs page.
  Use when the team needs to know whether the systems get cheaper or dearer to
  run as usage grows, or when it prices a plan or writes a business case.
  Activates on "/unit-costs", "unit cost", "cost per request", "cost per
  customer", "cost per deploy", "unit economics".
user-invocable: true
---

# Unit costs

Divides the cost of each month by the number of units in the same month. The cost comes from the FOCUS files behind the cost baseline. The count comes from one named metric with a stated source and owner. `scripts/focus_export.py unit` computes the series and the change from month to month. The page explains what moved the figure.

## Inputs

- **Unit** (required): what one unit is, for example one API request, one active customer, one deploy, one build, one stored gigabyte. The team picks it.
- **Count**: the metric, the system it comes from, the exact query or report, and its owner.
- **Cost scope**: all cost, or only some providers, services or tags.
- **Months**: default the months of the cost baseline.
- **Page**: default `docs/fin/unit-costs.md`, one section per unit.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/fin finops/units scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/" docs/fin/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/focus_export.py" scripts/
   ```

   Without rsync, use `cp -n` for `docs/fin/_templates/unit-costs.md` and `scripts/focus_export.py` from `${CLAUDE_PLUGIN_ROOT}/templates/`. The page links the cost baseline: if `docs/fin/cost-baseline.md` does not exist, run the `cost-baseline` skill first.
2. **Pick the unit with the user.** Check each candidate against three tests. The count already exists and is measured the same way every month. It moves with the cost: more units cause more cost. The team can act on it. Offer two or three candidates from the services in the baseline, and say which test each one fails, if any.
3. **Define the numerator.** Name the cost lines in scope: all rows, or filters by provider (`--provider`), service (`--service`) or tag (`--tag key=value`). Use one currency. If the scope holds more than one, narrow it or ask the user for a rate with its date and source.
4. **Collect the counts.** One row per calendar month in UTC, in `finops/units/<unit>.csv`:

   ```text
   month,count,source
   2026-07,<count>,<metric name, system and query>
   ```

   Ask the metric owner for the query or report, and run it or have the user run it. A month with no count stays out of the file. Record the counting rule: what counts as one unit, what is left out, and how duplicates are removed.
5. **Compute the series.**

   ```bash
   python3 scripts/focus_export.py unit --counts finops/units/<unit>.csv --unit <unit> \
     [--per 1000] [--provider "<provider>"] [--service "<service>"] [--tag <key>=<value>] finops/focus/*.csv
   ```

   Use `--per 1000` or `--per 1000000` when the cost per single unit is a small fraction of a cent.
6. **Explain the trend.** For each month with a change above 10%, split it into the change in cost and the change in count, and name the cause. Check the flags on the cost baseline page: many jumps come from a one-off charge or a spike. Show the unit cost with and without one-off charges when they differ.
7. **Write the page.** Start from `docs/fin/_templates/unit-costs.md`. Fill `cost_period` and `cost_source` from the script output; `cost_source` names both the cost files and the metric. Fill the Units table, paste the series, and write the causes and limits. For a second unit on the same page, add a section with its own table. Add the page to the table in `docs/fin/index.md`.
8. **Check.** If the gate runs the rule, run `python3 .github/actions/gate/run.py --only finops.cost-provenance --dry-run`.
9. **Report.**

## Output

The page path, the unit and its counting rule, the metric and its source, the series by month, the changes above 10% with their causes, and the limits.

## Rules

- No unit cost without a named count source. A count from an unnamed source stays off the page.
- Cost and count cover the same calendar months.
- One currency per series.
- A change in the counting rule or the count source ends the series. Start a new series and note the month of the change.
- Every figure names its period and its source, in the front matter or on its line.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/finops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/finops/` exists, read its `README.md` first, then the files in `finops/unit-costs/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
