---
name: showback
description: >
  Allocate one month of cost per team or service from tags and an allocation
  file, with shared costs split by a stated rule and unallocated cost as its own
  line, as a report on a docs page that charges no team. Use when teams should
  see the cost they cause, when the team wants a number for tag coverage, or
  before a talk about budgets per team. Activates on "/showback", "cost per
  team", "showback", "who spends what", "allocate the cloud bill", "split the
  bill by team".
user-invocable: true
---

# Showback

Splits one month of cost across teams and reports it. The input is FOCUS files, usually the ones behind the cost baseline, and the allocation rules in `finops/allocation.json`. `scripts/focus_export.py showback` applies the rules: shared costs first, then the rules from top to bottom, then the value of the team tag. A line that matches nothing stays unallocated and shows as its own row. The figures on the page add up to the bill.

Nothing is booked to a team's budget. For chargeback, where each team pays its share from its own budget, the teams and finance first make an agreement. This skill can list what that agreement has to cover. The user makes the agreement.

## Inputs

- **Month** (required): `YYYY-MM`.
- **FOCUS files** for that month: default `finops/focus/*.csv`. Run the `cost-baseline` skill first if they do not exist.
- **Teams**: names and the owner who answers for each team's cost.
- **Allocation inputs**: the tag key that names the team, sub-accounts or projects per team, services per team, and the shared costs (support plans, networks, shared clusters, tools everyone uses).
- **Page**: default `docs/fin/showback-<YYYY-MM>.md`.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/fin finops scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/" docs/fin/
   rsync -a --ignore-existing --exclude aws-cost-exporter "${CLAUDE_PLUGIN_ROOT}/templates/finops/" finops/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/focus_export.py" scripts/
   ```

   Without rsync, use `cp -n` for each file: `docs/fin/_templates/showback.md`, `finops/allocation.json` and `scripts/focus_export.py` from `${CLAUDE_PLUGIN_ROOT}/templates/`.
2. **Check the data.** Run `python3 scripts/focus_export.py check finops/focus/*.csv`. Stop on errors.
3. **Look at the tags first.** Before any rule, list the tag keys and values the rows carry, with the cost per value:

   ```bash
   python3 - finops/focus/*.csv <<'EOF'
   import csv, json, sys
   from collections import defaultdict
   from decimal import Decimal
   cost = defaultdict(Decimal)
   for path in sys.argv[1:]:
       for r in csv.DictReader(open(path, encoding="utf-8-sig")):
           tags = json.loads(r.get("Tags") or "{}") or {"(no tags)": ""}
           for k, v in tags.items():
               cost[(r["BillingCurrency"], k, v)] += Decimal(r["BilledCost"])
   for (cur, k, v), x in sorted(cost.items(), key=lambda kv: -kv[1]):
       print(f"{cur} {x:,.2f}  {k}={v}")
   EOF
   ```

   Show the result. Agree on the tag key that names the team, and on spelling variants that mean the same team.
4. **Write the allocation file.** Fill `finops/allocation.json` with the user: `team_tag`, `teams` with owners, `rules` for cost without a usable tag (sub-accounts, services, providers), and `shared` costs with their split: `proportional` to each team's direct cost, `even`, or fixed weights. Each rule has a reason the user can state. The script stops while a `<placeholder>` is left.
5. **Run the showback.**

   ```bash
   python3 scripts/focus_export.py showback --alloc finops/allocation.json --month <YYYY-MM> finops/focus/*.csv
   ```

   The output holds the front matter lines, one table per currency, the unallocated lines, the shared costs, the tag coverage and a reconciliation line. The reconciliation must read zero.
6. **Work through the unallocated lines.** Largest first. For each one, propose a fix: a tag on the resource and the person who adds it, or a new rule. Add rules only with the user's agreement. Never move unallocated cost to a team to make the table look complete. What stays unallocated keeps its own row.
7. **Write the page.** Start from `docs/fin/_templates/showback.md`. Fill `cost_period` with the month as a day range (`YYYY-MM-01/YYYY-MM-<last day>`), `cost_source` from the script output, `reviewed` today and `review_by` 90 days later. Paste the tables. List the lines a team may dispute, with the owner who answers. Add the page to the table in `docs/fin/index.md`.
8. **Check.** If the gate runs the rule, run `python3 .github/actions/gate/run.py --only finops.cost-provenance --dry-run`.
9. **Report.** If the user asks for chargeback, list what the agreement must settle: who signs it, the allocation rules, the split of shared cost, the treatment of unallocated cost, the period, and the way to dispute a line. Stop there.

## Output

The page path, cost per team per currency, unallocated cost and its share, tag coverage, the shared costs and their split, the fixes proposed for unallocated lines, and the reconciliation result.

## Rules

- This skill writes a report. It never books cost to a team's budget and never sends an invoice.
- Unallocated cost is its own line. It is never spread across teams without a rule the user agreed.
- Teams plus unallocated equal the total. A page with a non-zero reconciliation is not written.
- Amounts stay in the billed currency, one table per currency.
- Every figure names its period and its source, in the front matter or on its line.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/finops" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/finops/` exists, read its `README.md` first, then the files in `finops/showback/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
