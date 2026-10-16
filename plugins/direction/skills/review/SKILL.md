---
name: review
description: >
  Weekly direction review from the tracker: reads every item in bd across all
  areas, writes a dated memo with what moved per area, what is blocked, the
  proposed allocation for the week, and the decisions the owner must take, then
  records each decision the owner confirms as a tracker item with area:direction
  and kind:decision. Read-only until the owner confirms. Use at the start of a
  week, before a planning round, or when the owner asks where the company
  stands. Activates on "/direction:review", "direction review", "where do we
  stand", "what moved this week", "what is blocked", "allocation for the week",
  "which decisions are waiting".
user-invocable: true
---

# Direction review

Reads the tracker (`bd`, [beads](https://github.com/steveyegge/beads)) across all areas and writes one memo: what moved per area in the period, what is blocked and by what, a proposed allocation of the week, and the decisions the owner must take. The memo is a proposal. Nothing in the tracker changes until the owner confirms a decision; a confirmed decision becomes a tracker item with `area:direction` and `kind:decision`, closed with the decision as its reason. The gate rule `direction.review-memo` checks memos kept in a repository.

## Inputs

- **Tracker root**: the folder where `bd` runs (it holds `.beads/`). Default: the current folder; otherwise ask.
- **Period**: default the 7 days ending today, from `date +%F`. The owner may name another range.
- **Areas**: the eight areas of the cockpit by default: `direction`, `delivery`, `operations`, `money`, `security`, `ai`, `people`, `knowledge`. An install with other `area:` labels names them in the overlay.
- **Owner**: the person who takes the decisions. Ask, unless the overlay names the owner.
- **Memo**: `docs/direction/review-<YYYY-MM-DD>.md` under the tracker root. The overlay may name another folder; a memo outside `docs/direction/` is not read by the gate check.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p docs/direction
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/direction/" docs/direction/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/direction/." docs/direction/`. If `docs/direction/index.md` was new, fill its `owner`, `reviewed`, and `review_by`. If `docs/docs.json` exists and lists no space with the key `direction`, show this entry and add it after the user agrees:

   ```json
   {"key": "direction", "name": "Direction", "about": "The weekly direction reviews: what moved, what is blocked, the allocation, and the decisions taken.", "owner": ""}
   ```

2. **Read the tracker.** Three commands, all read-only:

   ```bash
   tmp="$(mktemp -d)"
   bd list --json --all --limit 0 > "$tmp/beads.json"
   bd ready --json > "$tmp/ready.json"
   bd blocked --json > "$tmp/blocked.json"
   ```

   Every item carries `id`, `title`, `status`, `priority`, `owner`, `created_at`, `updated_at`, and, when set, `labels`, `closed_at`, `close_reason`, and `notes`. `bd blocked --json` adds `blocked_by`, the ids that block the item. Keep the files for the run and remove the folder after the report (`rm -rf "$tmp"`).
3. **Place every item.** An item's area is its `area:<key>` label. An item with no `area:` label goes under "no area label"; never guess its area from the title. Its kind is its `kind:` label (`finding`, `decision`, `action`, `lead`); an item without one counts as an action in the tables and is named as "kind not set" where it is listed. A lead is counted and never listed by title.
4. **What moved, per area.** For each area, and for "no area label", count: opened (`created_at` in the period), closed (`closed_at` in the period), in progress (`status` `in_progress`), deferred (`status` `deferred`), open at the end of the period (`status` `open`, `in_progress`, or `blocked`). Under the table, name the items closed in the period per area as `id: title`, and the P0 and P1 items opened in the period. Closed leads are counted, not named.
5. **Blocked.** One line per item in `blocked.json`: id, area (from its `area:` label), priority, and each id in `blocked_by` with that item's status looked up in `beads.json`. Where one id blocks several items, say so: that blocker comes first in the allocation. Write "None." when the list is empty.
6. **Proposed allocation.** Split the five working days of the coming week across the areas, in half days, with one reason per line. Weigh, in this order: open P0 and P1 items per area, a blocker that blocks several items, a `kind:decision` item older than 7 days, an area whose open count rose over the last four weeks (from `created_at` and `closed_at`), and ready items from `ready.json` that nobody has started. An area with no open work gets "none this week". The shares add up to five days.
7. **Decisions needed.** List, oldest first, every open item with `kind:decision`, as `id: title (open)`. Then add the decisions found in the review, each as one line that names the choice, with `(open)` at its end: a blocker with an empty `owner`, an area whose open count rises for four weeks, a P0 or P1 item untouched for 30 days (`updated_at`). Write "None." when there is nothing.
8. **Write the memo.** Start from `docs/direction/_templates/review.md`. Fill the front matter: `date` today, `period` as `<start>/<end>` in ISO dates, `areas`, `owner`, `reviewed` today, `review_by` 7 days later. Paste the four sections. Replace every `<placeholder>`. If the memo path exists, show the diff and update it after the owner agrees; git keeps the earlier version. Add the memo to the table in `docs/direction/index.md`.
9. **Walk the decisions with the owner.** Show the "Decisions needed" list and ask, for each line, whether the owner decides now, leaves it open, or drops it. Record only what the owner states:
   - *An existing decision item, decided:* append the decision to its notes, then close it with the decision as the reason.

     ```bash
     bd update <id> --append-notes="<YYYY-MM-DD> decided by <owner>: <the decision in one or two lines>. Memo: <memo path>"
     bd close <id> --reason="Decided: <the decision in one line>"
     ```

   - *A decision found in the review, decided:* create the item, then append the notes, then close it.

     ```bash
     bd create "<the decision in one line>" --type=task --priority=<0-4> --labels=area:direction,kind:decision --json
     bd update <new id> --append-notes="<YYYY-MM-DD> decided by <owner>: <the decision>. Context: <what the review found>. Memo: <memo path>"
     bd close <new id> --reason="Decided: <the decision in one line>"
     ```

     Take the id from the `id` field of the JSON that `bd create --json` prints. Append the notes in a second command: on bd 1.0.3 (`bd version`), `--append-notes` on `bd create` wrote nothing in a test on a throwaway database.
   - *Left open:* change nothing in the tracker. A decision found in the review that the owner wants to keep becomes an open item with the same two labels, without a close; it then shows in the cockpit's queue.
   - *Dropped:* change nothing in the tracker; the memo line gives the reason, with at most one pair of parentheses inside it.

   After each recorded decision, change its memo line from `(open)` to `(recorded: <id>)`; a dropped one gets `(dropped: <reason>)`. Where a decision calls for work, offer to create the follow-up items in their own areas with `kind:action`; create them only on the owner's yes.
10. **Check.** In a repository that runs the gate with this module's rule, run `python3 .github/actions/gate/run.py --only direction.review-memo --dry-run`. Otherwise read the memo: date and period set, the four sections present, every decision line ends with a status.
11. **Report.** Name the share of items without an `area:` label (open and deferred items), so the owner sees the labelling gap behind an empty area table.

## Output

```markdown
---
title: "Direction review <YYYY-MM-DD>"
summary: What moved, what is blocked, the proposed allocation for the week, and the decisions needed, from the tracker.
date: <YYYY-MM-DD>
period: <YYYY-MM-DD>/<YYYY-MM-DD>
areas: direction, delivery, operations, money, security, ai, people, knowledge
owner: <owner>
labels: direction, review
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD>
type: reference
---
## What moved

| Area | Opened | Closed | In progress | Deferred | Open |
|---|---|---|---|---|---|
| direction | 1 | 2 | 0 | 3 | 4 |
| no area label | 0 | 1 | 2 | 10 | 12 |

Closed: `<id>`: <title> (direction). Opened at P1: `<id>`: <title> (delivery).

## Blocked

- `<id>` (knowledge, P2): blocked by `<id>` (open), `<id>` (deferred).

## Proposed allocation

| Area | Days | Why |
|---|---|---|
| delivery | 2.0 | two P1 items opened this week; `<id>` blocks three others |
| money | 0.5 | cost baseline past review |

## Decisions needed

- `<id>`: <title> (open)
- <the choice in one line> (recorded: <id>)
- <the choice in one line> (dropped: <reason>)
```

The report after the memo: the memo path, the counts per area, the share of items without an `area:` label, the blockers, the shares, and per decision what the owner did and the id of its record.

## Rules

- Read-only until the owner confirms a decision. The memo is a proposal; the tracker changes only on a confirmed decision.
- An item's area and kind come from its labels. An item without an `area:` label stays under "no area label" in every table. Never set a label the owner did not ask for.
- Never use `--notes` on `bd update`: it replaces the notes. Use `--append-notes`.
- Never create, close or edit an item for a decision the owner did not state. Never change a title or a description.
- Every count in the memo comes from the three command outputs of this run. Name the period on the memo.
- Leads (`kind:lead`) are counted and never named in a memo that leaves the owner's machine.
- One memo per review. A second review on the same day updates the memo after the owner agrees; it never overwrites it unseen.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/direction" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/direction/` exists, read its `README.md` first, then the files in `direction/review/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
