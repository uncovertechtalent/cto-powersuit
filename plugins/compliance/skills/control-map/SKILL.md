---
name: control-map
description: >
  Map the team's existing controls and their evidence to ISO 27001 Annex A
  control numbers, TISAX (VDA ISA question numbers), NIS2 articles and GDPR
  articles, in one CSV with control id, owner, evidence link, status and gap per
  row. Numbers only: the client adds titles from their own licensed copies. Use
  when a team prepares for an audit, a customer questionnaire or a TISAX
  assessment, or needs to know which requirements have no control yet.
  Activates on "/control-map", "map our controls", "control mapping", "ISO 27001
  gap analysis", "TISAX readiness", "NIS2 gap", "where is our evidence", "which
  controls do we have".
user-invocable: true
---

# Control map

Keeps one table, `compliance/control-map.csv`, that links each requirement number of each framework in scope to the team's own control, its owner, the evidence and the gap. One control can serve many rows. The table holds numbers and the team's own words only.

## Licence boundary

Standards are licensed texts. Under the terms of the standards publishers, processing their text with AI tools needs a separate licence (for example DIN Media AGB 5.4).

- Write numbers only: ISO/IEC 27001:2022 Annex A control numbers (`A.5.1` to `A.8.34`), VDA ISA question numbers, article numbers.
- The `title` column is for the client, filled by hand from their licensed copy. Never fill it, quote it, summarise it or use it as input.
- Never write a title, requirement text or paraphrase of ISO 27001, VDA ISA or any other standard into any file, commit message or chat reply.
- If the user pastes standards text, do not process it. Ask for the number and the team's own one-line description of what their control does.
- EU legal acts are public. Cite article numbers and link EUR-Lex; do not paste article text. NIS2: Directive (EU) 2022/2555, <https://eur-lex.europa.eu/eli/dir/2022/2555/oj>. GDPR: Regulation (EU) 2016/679, <https://eur-lex.europa.eu/eli/reg/2016/679/oj>. Check before use: the links resolve to the current consolidated versions.

## Inputs

- Frameworks in scope: ISO/IEC 27001:2022, TISAX (with the VDA ISA catalogue version and the assessment objectives the team holds), NIS2 (and whether the company is an essential or important entity, which the user confirms), GDPR.
- The team's controls: what exists today, in the team's own words. Sources in the repository: `gate/gate.json` and its rules, `.github/workflows/`, `CODEOWNERS`, branch protection, `docs/` (policies, runbooks, decision records), `observability/` (logging, alerting), backup and restore jobs, access reviews, incident records.
- Owners: a person or team per control.

## Columns

| Column | Content |
|---|---|
| `framework` | `ISO/IEC 27001:2022`, `VDA ISA <version>`, `NIS2`, `GDPR` |
| `number` | `A.8.13`, `<question number>`, `Art 21(2)(c)`, `Art 32` |
| `title` | Empty. The client fills it from their licensed copy |
| `control_id` | The team's own control id, for example `CTL-014`. Several ids are separated by `;` |
| `owner` | Person or team that keeps the control working |
| `evidence` | A path in the repository, a CI run URL, a dashboard URL or a ticket. One a reviewer can open |
| `status` | `implemented`, `partial`, `missing`, `not-applicable`, `to-confirm` |
| `gap` | What is missing, in one sentence of the team's own words, or empty |

`to-confirm` marks a mapping this skill proposed and the owner has not yet checked against the licensed text.

## Steps

1. **Copy the table without overwriting.**

   ```bash
   mkdir -p compliance
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/compliance/control-map.csv" compliance/
   ```

   The template has one row per ISO/IEC 27001:2022 Annex A control number, the NIS2 points of Art 20, Art 21(2) and Art 23, a set of GDPR articles and one placeholder row for VDA ISA. If `compliance/control-map.csv` exists, work in it.
2. **Set the scope.** Ask which frameworks apply. Remove the rows of frameworks out of scope, after the user confirms. For TISAX, ask the user for the question numbers of their catalogue version and objectives, and add one row per number. For GDPR, add the articles the team's processing touches.
3. **List the controls.** Build a list of the team's controls from the inputs: one line each, in the team's words, with an id `CTL-NNN` (or the team's own scheme), an owner and an evidence link. Read the repository to find evidence; ask the user for controls that live outside it (HR, office, contracts).
4. **Map.** For each control, propose the row numbers it covers and set `status: to-confirm`. Propose from the team's own description of the control. Where a row has no control, set `status: missing` and write the gap. Mark `not-applicable` only with a reason in `gap` that the owner confirms.
5. **Confirm with the owners.** Group the `to-confirm` rows by owner. Each owner checks the mapping against their licensed copy and sets `implemented`, `partial` or `missing`. Change a status only on the owner's word.
6. **Check the evidence.** Every `implemented` and `partial` row has an evidence link that resolves: a path that exists (`test -e <path>`) or a URL the user confirms. Evidence older than one year gets a note in `gap`.
7. **Report.**

   ```bash
   python3 - compliance/control-map.csv <<'EOF'
   import csv, sys, collections
   rows = list(csv.DictReader(open(sys.argv[1], newline="", encoding="utf-8")))
   count = collections.Counter((r["framework"], r["status"] or "unassessed") for r in rows)
   for (fw, st), n in sorted(count.items()):
       print(f"{fw:24} {st:15} {n}")
   EOF
   ```

## Output

- `compliance/control-map.csv` with numbers, control ids, owners, evidence links, status and gaps.
- A short report: rows per framework and status, the `missing` rows with their gaps, the `to-confirm` rows grouped by owner, and evidence links that did not resolve.

## Rules

- Numbers only. No standards text, titles or paraphrases anywhere, see the licence boundary above.
- Never overwrite or delete `compliance/control-map.csv`. Remove rows only after the user confirms the scope.
- The map shows what exists. Certification bodies and assessors decide on conformity.
- No secrets, personal data or customer names in the table. An evidence link gives the location of the evidence.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/compliance" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/compliance/` exists, read its `README.md` first, then the files in `compliance/control-map/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
