---
name: decision-log-review
description: >
  Sweep the decision log in docs/decisions/ and report what needs attention:
  records missing status, owner or date, proposed ADRs older than 30 days, RFCs
  past comments_close still in draft or review, broken supersede links,
  duplicate numbers, decisions past their review_by date, and a spot check of a
  few accepted decisions against the code. Use for a regular review of the
  decision log, or before a planning round. Read-only until the user says go.
  Activates on "/decision-log-review", "review the decision log", "audit the
  ADRs", "check the decision records", "which decisions are stale".
user-invocable: true
---

# Decision log review

Reads every RFC and ADR in the decision log, checks the fields and the links between records, and compares a few accepted decisions with the code. The result is a report. Files change only after the user approves a fix.

## Inputs

- **Folder**: default `docs/decisions/` at the repository root.
- **Today**: the date of the review, from `date +%F`.
- **Spot checks**: how many accepted decisions to check against the code, default 3.

## Steps

1. **List the records.** Take `docs/decisions/adr-[0-9]*.md` and `docs/decisions/rfc-[0-9]*.md`. Skip any path with a segment that starts with `_`, such as `_templates/`. Read the front matter of each file: a block between two `---` lines, or a header of `key: value` lines ended by `---`. Older records use `created` in place of `date`; accept either.
2. **Run the gate rule if it is installed.** If `.github/actions/gate/rules/adr_fields.py` exists, run `python3 .github/actions/gate/run.py --only decisions.adr-fields --dry-run` and take its hits as the field findings for ADRs. The rule must be enabled in `gate/gate.json` for `--only` to run it. Check RFCs by reading in any case.
3. **Missing fields.** Every record needs `status`, `owner` and a date (`date` or `created`) in ISO form `YYYY-MM-DD`. ADR statuses: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`. RFC statuses: `draft`, `review`, `accepted`, `rejected`, `withdrawn`. Report each missing or unknown value.
4. **Stale proposals.** ADRs with `status: proposed` and a date more than 30 days before today. For each, the question for the owner is: accept or reject.
5. **Overdue RFCs.** RFCs with status `draft` or `review` and a `comments_close` before today. Also RFCs in `review` with no `comments_close`. For each, the next step is the close step of the `rfc` skill.
6. **Broken links.** For every link, check the target file exists in the same folder and points back:
   - `supersedes: <old>` on a record: the old record has `status: superseded` and `superseded_by` names this record.
   - `status: superseded`: `superseded_by` is set, the file exists, and that record lists this one in `supersedes`.
   - `superseded_by` on a record whose status is not `superseded`.
   - ADR `rfc: <slug>`: the RFC exists and its `decision` names this ADR.
   - RFC with status `accepted` or `rejected`: `decision` names an existing ADR, and that ADR names the RFC in `rfc`.
7. **Duplicate numbers.** Two ADRs with the same number, or two RFCs with the same number. Compare the numbers as integers, from the `adr:` or `rfc:` field and from the file name. Gaps in the numbering are fine.
8. **Past review date.** Records with a `review_by` before today. For each accepted ADR in this list, the questions are: is the decision still true in the system? Has a later record replaced it without a supersede link? Name the evidence to look at, from the Decision section.
9. **Spot check against the code.** Pick accepted ADRs up to the spot-check count. Prefer the records with the oldest `reviewed` date and a Decision section that names something concrete: a library, a setting, a file, a command, a pattern in code. For each:
   - Write down the claim: what the decision requires or forbids.
   - Turn it into one or two searches, for example `git grep -n '<forbidden library>'` or `git grep -L '<required setting>' -- '<config files>'`.
   - Run them and record the command, the number of hits and up to five paths.
   - Classify the result: `holds` (the code matches the decision), `drifted` (the code contradicts it) or `cannot tell` (the claim has no clear trace in the code). Say why in one line.
10. **Index.** If `docs/decisions/index.md` keeps hand tables below the markers `<!-- rfc-index -->` and `<!-- adr-index -->`, compare them with the files: records missing from a table, rows for files that do not exist, statuses that differ. Skip this when a docs build fills the markers (see the Index section of the `adr` skill).
11. **Write the report** in the format below and show it.
12. **Fix on approval.** Ask which findings to fix. Apply only those. Use the `adr` skill for new records and supersede links, and the `rfc` skill to close an RFC. After a review the owner confirms, set `reviewed` to today and `review_by` to 90 days later on the records that were checked.

## Output

```markdown
# Decision log review, <YYYY-MM-DD>

Records: <n> ADRs, <n> RFCs. Findings: <n>.

## Missing or invalid fields
- `<file>`: missing owner

## Stale proposals (proposed for more than 30 days)
- `<file>`: proposed on <date>. Accept or reject.

## RFCs past comments_close
- `<file>`: status review, comments closed on <date>.

## Broken links
- `<file>`: supersedes `<slug>`, which is not marked superseded.

## Duplicate numbers
- ADR <NNNN>: `<file>`, `<file>`

## Past review_by
- `<file>`: review was due on <date>. Check: <what to look at>.

## Spot checks
| Record | Claim | Search | Hits | Result |
|---|---|---|---|---|
| `<file>` | <requires or forbids> | `<command>` | <n> | holds, drifted or cannot tell |

## Index
- <rows missing, extra or out of date>

## Proposed fixes
1. <one line per fix, with the file>
```

Write "None." under a heading with no findings.

## Rules

- Read-only until the user says which fixes to apply.
- Never change the Decision section of an accepted record. A drifted decision goes to its owner, with two options: change the code, or write a new ADR that supersedes the record.
- Never delete a record. Renumber a record only to resolve a duplicate number: propose a new number for the newer file, list the files that link to it, and ask first.
- Report facts from the files and the searches. A `cannot tell` result stays `cannot tell`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/decisions" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/decisions/` exists, read its `README.md` first, then the files in `decisions/decision-log-review/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
