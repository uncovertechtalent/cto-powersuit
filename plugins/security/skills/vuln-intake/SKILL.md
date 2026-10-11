---
name: vuln-intake
description: >
  Turn Dependabot alerts, security advisories and scan results into tickets
  with a fix-by date per severity: critical 7 days, high 30, medium 90, low
  180 by default, from a policy page the team can change. Drafts each ticket
  in the format of the sdlc/ticket skill, skips findings that already have a
  ticket, and lists the ones past their date. Creates nothing without the
  user's go. Use after a scan, on a weekly intake, or when alerts pile up.
  Activates on "/vuln-intake", "triage our Dependabot alerts", "turn the
  alerts into tickets", "which vulnerabilities are overdue", "fix-by dates",
  "security backlog".
user-invocable: true
---

# Vulnerability intake

A vulnerability alert nobody owns stays open. Intake gives each one an owner, a ticket and a date: the fix-by window starts on the day the alert appeared, and its length follows the severity. The policy page holds the windows; `intake.py` next to this file applies them, so every run gives the same dates.

## Inputs

- **Repository**: `owner/repo`.
- **Sources**, any of:
  - Dependabot alerts. Reading them needs the alerts turned on and a caller with access to them. A 403 with "Dependabot alerts are disabled" means the setting is off: tell the user where it is, and use the other sources.
  - The repository's own security advisories, for vulnerabilities in the team's own code.
  - Scan results from `/security:supply-chain` (osv-scanner, or `osv_query.py --json`).
- **Policy**: `docs/security/vuln-policy.md`. If it is missing, copy the template without overwriting and ask the user who owns it:

  ```bash
  mkdir -p docs/security && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/security/vuln-policy.md" docs/security/
  ```

## Steps

1. **Collect.** Read only:

   ```bash
   gh api --paginate --slurp "repos/<owner>/<repo>/dependabot/alerts?state=open&per_page=100" > dependabot-alerts.json
   gh api "repos/<owner>/<repo>/security-advisories?state=draft" > advisories.json
   gh issue list --repo <owner>/<repo> --label security --state all --limit 500 --json number,title,state > security-issues.json
   ```

   Draft advisories in `advisories.json` are private records of the team's own vulnerabilities: list them in the report with their fix-by dates, and keep them out of the issue tracker. Add `osv-results.json` from the OSV lookup when there is one: `python3 <supply-chain skill folder>/osv_query.py sbom.spdx.json --json > osv-results.json`.
2. **Draft the tickets.**

   ```bash
   python3 <this skill's folder>/intake.py --dependabot dependabot-alerts.json --osv osv-results.json \
     --existing security-issues.json --policy docs/security/vuln-policy.md
   ```

   It prints one draft per advisory and package, with the fix-by date, the priority label, and the labels `type: bug` and `security`. Findings whose id appears in an existing issue title are listed as tracked. Drafts past their date are marked `OVERDUE`. Add `--json` for the full ticket bodies.
3. **Check the severity** with the user for each draft. Raise it when the vulnerable code is reachable from the internet or handles credentials. Lower it only with a written reason in the ticket, such as the search that shows the vulnerable function is never called. Set a level for every `unknown` within 2 working days; until then it takes the high window.
4. **Create the tickets** with the user's go, one per draft, in the format of `/sdlc:ticket`:

   ```bash
   gh issue create --repo <owner>/<repo> --title "<draft title>" --body-file <draft body file> --label "type: bug" --label security --label <P0 to P3>
   ```

   Create the `security` label first if it is missing: `gh label create security --color b60205`.
5. **Keep vulnerabilities in the team's own code private.** A vulnerability in code the team wrote, not yet fixed, goes into a draft repository security advisory, never into a public issue. Dependency alerts point to public advisories and can go into the tracker.
6. **Report overdue items.** List the tickets past their fix-by date and the exceptions that end within 30 days, with their owners. An exception follows the policy page: the reason, the compensating control, the new date, and the approver, who is not the person asking.

## Output

- Ticket drafts with fix-by dates, priorities and acceptance criteria, then the created issue numbers.
- The findings already tracked, the overdue tickets and the exceptions due to end.

## Rules

- Draft first. Create, label or close issues only with the user's go.
- The window starts on the day the alert appeared, whatever day the team read it.
- No exploit details in a public issue. Vulnerabilities in the team's own code go into a draft security advisory.
- Never change repository settings; name the setting and let the user change it.

## Check the script

`python3 "${CLAUDE_PLUGIN_ROOT}/tests/test_security.py"` runs the intake cases: default windows, the policy template, a custom policy, a duplicate alert, an already-tracked finding, an unrated finding, and a finding with no fix. Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/vuln-intake/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
