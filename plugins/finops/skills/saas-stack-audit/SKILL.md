---
name: saas-stack-audit
description: >
  List every SaaS tool the organisation pays for, from invoices, the SSO app
  list or expense exports, with owner, seats paid and used, overlaps, and a
  keep, cut or replace proposal per tool, where replace options include open
  source and agent-built tools with switching cost and risk; the user acts on
  every proposal. Use when renewals come up, when SaaS spend grows faster than
  the team, or when nobody can name every tool the company pays for. Activates
  on "/saas-stack-audit", "SaaS audit", "audit our tools", "which tools do we
  pay for", "too many subscriptions", "cut SaaS spend", "unused seats".
user-invocable: true
---

# SaaS stack audit

Builds one inventory of the SaaS tools the organisation pays for and proposes a decision per tool. The inventory joins three views: what is billed (invoices, card and expense exports), what is connected (the SSO app list), and what is used (sign-ins and admin exports). Each tool gets an owner, seats paid and used, its overlaps with other tools, and a proposal: keep, cut or replace. For replace, the page lists open-source and agent-built options next to other vendors, each with its switching cost and risk.

The skill cancels nothing, changes no seat count and signs into no vendor console. The owner of each tool acts after the user agrees the decision.

## Inputs

- **Billing sources** (required): invoices, card statements, expense exports, accounts payable exports. Default the last 12 months, so annual plans show up.
- **SSO app list**: the export of connected apps from the identity provider, with the number of assigned users per app.
- **Usage**: sign-in counts per app from the identity provider, or active-user exports from each tool's admin page, with the export date.
- **Owners**: who answers for each tool. Ask the user for a first list.
- **Page**: default `docs/fin/saas-inventory.md`.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/fin
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/" docs/fin/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/fin/." docs/fin/`.
2. **Collect the tools.** From each billing source, take every recurring charge from a software vendor. Normalise vendor names: one vendor can appear under several billing names, cards or currencies. From the SSO list, take every app. Join the two lists by vendor. Mark tools that appear on one side only: billed with no SSO app (often a team that signs in with passwords), or connected with no bill (a free tier, a trial, or a charge on a personal card).
3. **Fill the facts per tool.** Billing cycle (monthly or annual), payment method, cost per month with the period and source, renewal date, notice period, seats paid. Contract terms come from the contract or the order form; where the user has none, write "Check before use: notice period and auto-renewal terms in the contract".
4. **Measure use.** Seats used = distinct users active in the last 90 days, from SSO sign-ins or the tool's admin export. Write the source and the export date. With no usage data, write `unknown`; unknown is different from zero. Keep names of individual users off the page; record counts only.
5. **Name the owners.** One person per tool. A tool with no owner after asking is a finding of its own.
6. **Find overlaps.** Group the tools by the job they do: chat, video calls, documents, diagrams, tickets, CI, monitoring, error tracking, password management, design, forms, e-signature. Flag every job with more than one paid tool.
7. **Propose a decision per tool.**
   - **Keep**: owned, used, no overlap. Add right-sizing when seats used are well below seats paid.
   - **Cut**: no owner and no use, or fully covered by another tool the team keeps.
   - **Replace**: list the options with:
     - **Kind**: open source (self-hosted or hosted by a third party), agent-built (a small internal tool written with a coding agent), or another vendor.
     - **Switching cost**: person-days to migrate, data export and import, retraining, integrations to rebuild, exit terms of the current contract.
     - **Running cost**: hosting, maintenance hours per month, upgrades and security patches.
     - **Risk**: low, medium or high, with the reason: data loss in the migration, a security surface the team must patch, a missing feature, compliance duties, or one person who understands an agent-built tool.

   Every proposal has a one-line reason. The decision stays with the user and the tool owner.
8. **Write the page.** Start from `docs/fin/_templates/saas-inventory.md`. Fill `cost_period` with the months the costs cover, `cost_source` with the sources and their dates, `reviewed` today and `review_by` 90 days later. Fill Tools, Overlaps, Replace options and Actions. Each action names the person who acts and the date, for example the day before the notice deadline. Add the page to the table in `docs/fin/index.md`.
9. **Check.** If the gate runs the rule, run `python3 .github/actions/gate/run.py --only finops.cost-provenance --dry-run`.
10. **Report.** List the renewals in the next 90 days with their notice dates first, then the cut and replace proposals with the monthly amount each one affects.

## Output

The page path, the number of tools, tools without an owner, overlaps, seats paid against seats used, renewals in the next 90 days, and the proposals with their reasons.

## Rules

- The skill never cancels a subscription, never changes a seat count and never signs into a vendor console. The tool owner acts after the decision is agreed.
- Seat and usage figures carry their source and export date. Unknown use is written as unknown.
- No individual user names or sign-in records on the page; counts only.
- Contract terms come from the contract. Without one, the page says "Check before use" next to the term.
- Every cost figure names its period and its source, in the front matter or on its line.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/finops" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/finops/` exists, read its `README.md` first, then the files in `finops/saas-stack-audit/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
