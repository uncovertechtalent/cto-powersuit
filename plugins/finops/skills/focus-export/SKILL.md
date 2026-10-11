---
name: focus-export
description: >
  Convert billing data (provider CSV exports, invoice lines, expense exports) to
  FOCUS, the FinOps Open Cost and Usage Specification, with a column map per
  format, a validation pass, a reconciliation against the source totals and a
  list of declared deviations. Use when costs from several providers must sit in
  one table, when a team wants FOCUS files for a FinOps tool, or before the
  cost-baseline, showback and unit-costs skills. Activates on "/focus-export",
  "FOCUS export", "convert billing to FOCUS", "normalise the bills", "FOCUS
  columns", "FinOps open cost format".
user-invocable: true
---

# FOCUS export

Writes billing data in FOCUS columns, one CSV per source and period. FOCUS gives every provider the same column names and meanings, so files from different providers can sit in one table. `scripts/focus_export.py convert` maps the columns of a billing file to FOCUS with a column map in JSON, parses dates and amounts, and validates every row. `check` validates an existing FOCUS file. The other finops skills read the files this skill writes.

Check before use: FOCUS spec version. The column list in `scripts/focus_export.py` (`COLUMNS`) and the allowed `ChargeCategory` values follow one release of the FOCUS Cost and Usage columns. Compare both with the current release on the FOCUS site of the FinOps Foundation before a file goes to anyone outside the team.

## Inputs

- **Source file** (required): a CSV export from a provider, a FOCUS export, or invoice lines typed into a CSV.
- **Provider**: the name to write into `ServiceProviderName`, `HostProviderName` and `InvoiceIssuerName`.
- **Period**: the days to keep, as `--start` (first day) and `--end` (day after the last day).
- **Output**: default `finops/focus/<provider>-<YYYY-MM>-to-<YYYY-MM>.csv`.

## Steps

1. **Set up.** Copy the script and the example map without overwriting:

   ```bash
   mkdir -p finops/focus finops/focus-maps scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/finops/focus-maps/" finops/focus-maps/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/focus_export.py" scripts/
   ```

   Without rsync, use `cp -n` for `finops/focus-maps/example.json` and `scripts/focus_export.py` from `${CLAUDE_PLUGIN_ROOT}/templates/`.
2. **Check for a native FOCUS export.** Some providers export FOCUS files. If the user has such a file, run `python3 scripts/focus_export.py check <file>` and go to step 6.
3. **Read the source format.** Print the header and five rows. Find the columns for the charge date, the billed amount, the currency, the service or product, the line description, the line type, the account or project, the quantity and unit, and the tags. Note the delimiter, the decimal mark and the date format.
4. **Write the map.** Copy `finops/focus-maps/example.json` to `finops/focus-maps/<provider>-<format>.json`:
   - `source`: the name of the export or the invoice series. It lands in `x_Source` on every row, so every figure can name its source.
   - `columns`: FOCUS column to source column. Remove the lines the source has no column for.
   - `constants`: values for every row, such as the provider name.
   - `values`: translate source values, for example line types to `ChargeCategory` (`Usage`, `Purchase`, `Tax`, `Credit`, `Adjustment`).
   - `tags`: tag key to source column. `extra`: custom columns, with the `x_` prefix.
   - `date_format` (`iso` or a strptime format), `decimal` (`.` or `,`), `delimiter`, and `granularity` (`day` or `month`) for rows with no end date.

   The script stops while the map holds a `<placeholder>`.
5. **Convert.**

   ```bash
   python3 scripts/focus_export.py convert --in <source file> --map finops/focus-maps/<provider>-<format>.json \
     --out finops/focus/<provider>-<YYYY-MM>-to-<YYYY-MM>.csv --start <YYYY-MM-DD> --end <YYYY-MM-DD>
   ```

   On invalid rows the script lists them and writes nothing. Fix the map, or ask the user about the rows. Use `--skip-invalid` only when the user agrees to leave those rows out, and record the count.
6. **Validate and reconcile.** Run `python3 scripts/focus_export.py check finops/focus/<file>.csv`. Compare the `BilledCost` total per currency with the total of the source: the invoice total, or the sum the provider's console shows for the same period. If the two differ, stop and ask the user for the reason before you go on.
7. **Declare the deviations.** List every required column the source cannot fill and every column filled with an approximation, for example `EffectiveCost` left empty, `ListCost` missing, or `BilledCost` from a provider estimate. Write the list on the page that uses the file, in its Method section.
8. **Store the file.** FOCUS files hold account ids and line items. Keep them out of a public repository, or remove `BillingAccountId`, `SubAccountId` and `ResourceId` before they go into one. Ask the user where to keep the files.
9. **Report.**

## Output

The output path, the row count, `BilledCost` per currency, the reconciliation result, the declared deviations and the map file.

## Rules

- `BilledCost` is the amount on the invoice. An estimate goes into another column, or the row stays out.
- Every row carries `x_Source`.
- Amounts stay in the billed currency.
- The skill reads billing files and writes FOCUS files. It changes no billing setting and no export setting at a provider.
- Check before use: FOCUS spec version, as above.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/finops" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/finops/` exists, read its `README.md` first, then the files in `finops/focus-export/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
