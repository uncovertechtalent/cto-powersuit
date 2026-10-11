---
name: adr
description: >
  Record one decision as a numbered architecture decision record (ADR) with
  context, decision and consequences, from an accepted or rejected RFC or
  directly for a small decision. Use when a decision is made, from a closed RFC
  or directly, and the team needs a record of it. Handles supersede links on
  both records and keeps the index in docs/decisions/index.md current. Never
  overwrites a file. Activates on "/adr", "write an ADR", "record a decision",
  "record this decision", "new decision record", "supersede ADR", "this replaces
  ADR".
user-invocable: true
---

# ADR

Writes one decision record per decision in `docs/decisions/`. A record states the context that forced the decision, the decision, and its consequences. Records are numbered, never deleted and never renumbered. When a later decision replaces one, both records name each other.

## Inputs

- **Source** (required): the slug of an RFC that reached a decision, or a short statement of the decision.
- **Owner**: the person who keeps the decision true. From the RFC, or ask.
- **Status**: `accepted` when the decision is in force, `proposed` when it is written down and not yet in force, `rejected` for a decision against a proposal. `deprecated` and `superseded` are set on existing records only.
- **Supersedes**: slugs of older records this one replaces, if any.
- **Folder**: default `docs/decisions/` at the repository root.

## Steps

1. **Set up the folder.** If `docs/decisions/index.md` or `docs/decisions/_templates/` is missing, copy the templates without overwriting:

   ```bash
   mkdir -p docs/decisions
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/" docs/decisions/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/." docs/decisions/`.
2. **Gather the content.**
   - From an RFC: read it in full, with the comments if the user gives the pull request. Context = the problem and the options that were on the table. Decision = the outcome as the owner stated it at close. Consequences = the costs, the risks the reviewers raised and the rollout work.
   - Directly: ask for the context, the decision and the consequences if the statement lacks one of them. If the decision touches more than one team or is hard to undo, suggest the `rfc` skill first. The user may go ahead without an RFC.
3. **Look for related records.** Search the titles and summaries of `docs/decisions/adr-*.md` for the same subject. For each accepted record on the same subject, ask whether the new record supersedes it. If the new record replaces only part of an old one, do not supersede: link the old record in Context.
4. **Pick the number.** Next number = highest existing ADR number + 1, from file names and `adr:` fields:

   ```bash
   python3 - docs/decisions adr <<'EOF'
   import re, sys, pathlib
   d, kind = pathlib.Path(sys.argv[1]), sys.argv[2]
   nums = [0]
   for p in d.glob(f"{kind}-[0-9]*.md"):
       nums.append(int(re.match(rf"{kind}-(\d+)", p.name).group(1)))
       m = re.search(rf"^{kind}:\s*\"?(\d+)", p.read_text(encoding="utf-8"), re.M)
       if m:
           nums.append(int(m.group(1)))
   print(f"{max(nums) + 1:04d}")
   EOF
   ```

   The slug is `adr-NNNN-short-name`: the number and two to five lowercase words joined by hyphens that name the decision. Run `test -e docs/decisions/<slug>.md`. If the file exists, never overwrite it: take the next free number.
5. **Write the record.** Start from `docs/decisions/_templates/adr.md` (or `${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/_templates/adr.md`). Fill the front matter:
   - `title: "ADR-NNNN: <the decision in one line>"`, quoted because it contains ": ".
   - `summary`: one sentence that states what was decided.
   - `adr: NNNN`, `status`, `date` today, `owner`.
   - `rfc`: the RFC slug, or empty. `supersedes`: comma-separated slugs, or empty. `superseded_by`: empty.
   - `labels: adr, decision`, `reviewed` today, `review_by` 90 days later, `type: explanation`.

   Write Context, Decision and Consequences. The Decision section names what the decision requires and what it forbids, in terms a reviewer can check in the code: file names, settings, libraries, commands. Consequences include the bad ones. Replace every `<placeholder>`. Quote any front matter value that contains ": ". Compute dates with `python3 -c 'import datetime as d; print(d.date.today() + d.timedelta(days=90))'`.
6. **Supersede, on both sides.** For each slug in `supersedes`:
   - Check that `docs/decisions/<old slug>.md` exists and its status is `accepted`, `proposed` or `deprecated`. If it is already superseded by another record, stop and ask.
   - In the old record, set `status: superseded` and `superseded_by: <new slug>`. Change nothing else in it.
   - Check both sides: the new record lists the old slug in `supersedes`, and the old record names the new slug in `superseded_by`.
7. **Link back to the RFC.** If the record came from an RFC, set the RFC's `decision: <adr slug>` and its `status` to `accepted` or `rejected`, and fill its Decision section (see the `rfc` skill, step 9).
8. **Update the index.** See the Index section below.
9. **Check.** If the repository runs the gate with this module's rule, run `python3 .github/actions/gate/run.py --only decisions.adr-fields --dry-run`. Otherwise check by reading: status in the list, owner set, date valid, supersede links agree on both sides, no other record with the same number.
10. **Report.**

## Index

`docs/decisions/index.md` holds two marker lines, each on a line of its own: `<!-- rfc-index -->` and `<!-- adr-index -->`.

First check whether a docs build fills the markers:

```bash
grep -rl --exclude-dir=.git --exclude-dir=node_modules --exclude='*.md' 'adr-index' . 2>/dev/null
```

- **A hit** (for example the build of the `docs` module): the build writes the tables at the markers. Leave the marker lines alone and write no table into the file.
- **No hit:** keep each table by hand on the lines directly below its marker, up to the first blank line. Rebuild the whole table from the files on every change, so the table matches the records. Keep the marker line.

ADR table, newest first:

```markdown
| Record | Decision | Date | Status |
|---|---|---|---|
| [ADR-0003](adr-0003-short-name.md) | <title after "ADR-0003: "> | 2026-03-09 | accepted |
| [ADR-0001](adr-0001-short-name.md) | <title> | 2026-01-12 | superseded by [ADR-0003](adr-0003-short-name.md) |
```

RFC table, newest first:

```markdown
| RFC | Proposal | Owner | Comments close | Status | Decision |
|---|---|---|---|---|---|
| [RFC-0002](rfc-0002-short-name.md) | <title after "RFC-0002: "> | <owner> | 2026-04-20 | review | |
| [RFC-0001](rfc-0001-short-name.md) | <title> | <owner> | 2026-02-27 | accepted | [ADR-0003](adr-0003-short-name.md) |
```

Records in the older header format use `created` in place of `date`. Read either.

## Output

The record path, number, status, the RFC it came from, the records it supersedes with their new status, and whether the index changed or a docs build fills it.

## Rules

- One decision per record.
- Never overwrite, delete or renumber a record. Never reuse a number, also not the number of a rejected record.
- The Decision section of an accepted record stays as written. A changed decision is a new record that supersedes the old one.
- On an existing record, change only `status`, `superseded_by`, `reviewed`, `review_by` and spelling, unless the user asks for more.
- Status values: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`. A superseded record always names its successor in `superseded_by`.
- Dates are ISO `YYYY-MM-DD`. Files and slugs follow `adr-NNNN-short-name`.
- A written record holds no `<placeholder>` and none of the words that the gate's placeholder rule flags.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/decisions" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/decisions/` exists, read its `README.md` first, then the files in `decisions/adr/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
