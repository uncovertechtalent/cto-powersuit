---
name: cost-baseline
description: >
  Build a monthly cost baseline per provider and service from invoices or
  billing exports (CSV, FOCUS, cloud cost exports), with the period and source
  of every figure, flags for missing months, one-off charges, spikes and
  currency changes, written to a docs page. Use when a team needs to know what
  it spends each month, before a budget, a cost review, a vendor negotiation or
  a showback. Activates on "/cost-baseline", "cost baseline", "what do we
  spend", "monthly spend per provider", "build a cost baseline", "where does the
  money go".
user-invocable: true
---

# Cost baseline

Builds the monthly cost per provider and service from the bills themselves. Each source is converted to FOCUS (FinOps Open Cost and Usage Specification) columns first, so every provider has the same columns. `scripts/focus_export.py baseline` then writes the tables and the flags. The page states the period and the source of every figure. The gate rule `finops.cost-provenance` checks that.

## Inputs

- **Sources** (required): invoices (PDF or e-mail), billing exports (CSV), FOCUS exports, cloud cost exports, expense or card exports. Ask where they are. Raw billing files can hold account ids, names and addresses: keep them outside the repository, or in a folder the user names as private.
- **Months**: default the last 12 full calendar months, or what the sources hold. Use at least three full months.
- **Owner**: the person or team that keeps the page true.
- **Page**: default `docs/fin/cost-baseline.md`.
- **Audience**: whether the docs site is public. Ask before any amount, account id or contract term goes onto a public page.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/fin finops scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/" docs/fin/
   rsync -a --ignore-existing --exclude aws-cost-exporter "${CLAUDE_PLUGIN_ROOT}/templates/finops/" finops/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/focus_export.py" scripts/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/." docs/fin/`, `cp -n "${CLAUDE_PLUGIN_ROOT}/templates/finops/allocation.json" finops/`, `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/finops/focus-maps" finops/` and `cp -n "${CLAUDE_PLUGIN_ROOT}/templates/scripts/focus_export.py" scripts/`. If `docs/fin/index.md` was new, fill its `owner`, `reviewed` and `review_by`. If `docs/docs.json` exists and lists no space with the key `fin`, show this entry and add it after the user agrees:

   ```json
   {"key": "fin", "name": "FinOps", "about": "What the systems and tools cost, per provider, team and unit of work.", "owner": ""}
   ```

2. **List the sources.** One row per source: file or export, provider, format, months covered, currency. Note the months each source misses before you convert anything.
3. **Convert each source to FOCUS rows.** Write the output to `finops/focus/<provider>-<YYYY-MM>-to-<YYYY-MM>.csv`.
   - A FOCUS export from the provider: run `python3 scripts/focus_export.py check <file>`. Copy it to `finops/focus/` when it passes.
   - A CSV export: copy `finops/focus-maps/example.json` to `finops/focus-maps/<provider>-<format>.json`, map the columns, set `source` to the name of the export, and run:

     ```bash
     python3 scripts/focus_export.py convert --in <file> --map finops/focus-maps/<provider>-<format>.json \
       --out finops/focus/<provider>-<YYYY-MM>-to-<YYYY-MM>.csv
     ```

     The script stops while the map holds a `<placeholder>`, and it writes nothing while a row is invalid.
   - An invoice PDF or e-mail: read the invoice and type each line into a small CSV with the columns `date, invoice, description, type, amount, currency`. Show the lines to the user, then convert them with a map whose `source` names the invoice series. Map tax, setup fees and credits to the `ChargeCategory` values `Tax`, `Purchase` and `Credit`.
4. **Reconcile.** For each source and month, compare the `BilledCost` total that `convert` or `check` prints with the invoice total or the export's own total. If the two differ, stop and ask the user for the reason before you go on. Record each check in the Sources table of the page.
5. **Run the baseline.**

   ```bash
   python3 scripts/focus_export.py baseline finops/focus/*.csv --from <YYYY-MM> --to <YYYY-MM>
   ```

   The output holds the `cost_period` and `cost_source` lines for the front matter, the tables by provider and by service, and the flags.
6. **Go through the flags with the user.**
   - Missing months: ask for the missing invoice or export. A month without data stays empty in the table and named in the flags. Never fill it with an estimate.
   - One-off charges and single months: confirm each one. Compute the run rate per provider as the median of its full months without the one-off charges, and name the months it uses.
   - Spikes: ask for the cause, for example a load test, a migration or a pricing change. Write the cause next to the flag.
   - Currency changes: keep one row per currency. Convert only when the user gives a rate, its date and its source, and write all three on the line of the converted figure.
7. **Write the page.** Start from `docs/fin/_templates/cost-baseline.md`. Fill the front matter: `cost_period` and `cost_source` from the script output, `reviewed` today, `review_by` 90 days later. Paste the tables and the flags. A figure from another period or source, such as a one-off charge from an earlier year, carries `(period <YYYY-MM-DD/YYYY-MM-DD>, source: <source>)` on its line. Replace every `<placeholder>`. If the page exists, show the diff and update it after the user agrees; git keeps the earlier version. Add the page to the table in `docs/fin/index.md`.
8. **Check.** If the gate runs the rule, run `python3 .github/actions/gate/run.py --only finops.cost-provenance --dry-run`. With the `docs` module, also run `python3 scripts/build_docs.py --check`. Otherwise read the page: every line with an amount is covered by the front matter or carries its own marker.
9. **Report.**

## Output

The page path, the period, the sources with their reconciliation result, the total per provider per month, the run rate, the flags with their causes, and the open questions.

## Rules

- Every figure comes from a source file. Never estimate a missing month, never round to make totals match, never invent a figure.
- Every figure names its period and its source, in the front matter or on its line.
- Amounts stay in the billed currency. A conversion names the rate, its date and its source.
- The baseline reports. It changes no billing setting, plan or contract.
- Raw billing files and FOCUS files with account ids stay out of public repositories. Ask before any amount goes onto a public page.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/finops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/finops/` exists, read its `README.md` first, then the files in `finops/cost-baseline/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
