---
name: review-sweep
description: >
  Find stale docs pages (review date passed, due within 30 days, reviewed: no,
  no owner or no type), group them by owner, check each page against the
  system it describes, and update reviewed and review_by only after that check.
  Reports what changed and what still needs the owner. Never bumps a date
  without a check. Activates on "/review-sweep", "review the docs", "which docs
  are stale", "docs review sweep", "fix docs health".
user-invocable: true
---

# Review sweep

Brings the review dates of a docs tree back in line with the systems. The `reviewed` date is the day someone last checked the page against the system it describes. This skill does that check for each stale page, fixes what differs, and only then moves the dates. A page that cannot be checked keeps its old dates and goes on the list for its owner.

## Inputs

- The repository with `docs/docs.json` and `scripts/build_docs.py` (set up by `/docs:docs-init`).
- Optional scope: one space, one owner, or a list of pages. Default: all pages.
- Today's date.

## Steps

1. **List the stale pages.**

   ```bash
   python3 scripts/build_docs.py --stale
   ```

   The list is grouped by owner. Each line names the source file and its reasons: `review overdue since <date>`, `review due <date>` (within 30 days), `not reviewed`, `missing owner`, `missing type`, `missing review_by`. If the command stops on errors (a malformed date, an unknown type), fix those first; they also stop the build. Read `review_interval_days` from `docs/docs.json` (90 by default).
2. **Agree the scope.** Show the list grouped by owner, with counts. Ask which owners or pages to sweep now. Overdue pages come first, then not reviewed, then due soon.
3. **Check each page against its system.** For one page at a time:
   - Read the page. List the claims that a reader acts on: file paths, commands, config keys and values, workflow and job names, ports, versions, limits, URLs, owners of other systems, the order of steps.
   - Read the code, config or output each claim names: open the file, search the repository, run the command with `--help` or in a mode that changes nothing, read the workflow. Note for each claim: matches, differs (with the current value), or cannot be checked here (with the reason).
   - Run no command that changes state: no deploys, no writes, no restarts, no migrations.
4. **Decide per page.**
   - Every claim matches: set `reviewed` to today and `review_by` to today plus `review_interval_days`.
   - Some claims differ and the source shows the right value: correct the text, show the diff to the user, then set the dates as above.
   - A claim cannot be checked (no access, an external system, knowledge only the owner has), or the right value is unclear: change nothing in the dates. Add the page to the owner list with the claims that need the owner.
   - The page describes a system that no longer exists: do not delete it. Propose to the user to mark it, or to move its content, and leave the decision to them.
   - `missing owner`: propose an owner from the space owner in `docs/docs.json` and from `git log --format='%an' -- <file> | sort | uniq -c | sort -rn`. Set it only when the user confirms.
   - `missing type`: pick tutorial, how-to, reference or explanation from what the page does, and state the reason in one line. Setting the type or the owner does not count as a review; leave the dates unless the page was checked.
5. **Build.** Run `python3 scripts/build_docs.py --check`, then `python3 scripts/build_docs.py --stale` to confirm the swept pages left the list. If the gate has `docs.review`, run `python3 .github/actions/gate/run.py --dry-run --only docs.review`.
6. **Report.**

## Output

A report in two parts:

- **Changed:** one row per page with the path, the claims checked, the corrections made, and the new `reviewed` and `review_by`.
- **Needs the owner:** grouped by owner, one row per page with the claims that could not be checked and why, and pages that still have no owner or type.

The page edits are left in the working tree for the user to commit.

## Rules

- Never bump `reviewed` or `review_by` without a check of the page against the system in this session. A date change without a check makes the health page false.
- A check means reading the code, config or command output the page names. A page that only reads well has not been checked.
- Run only commands that change nothing.
- Never delete a page and never change an owner without the user's confirmation.
- Keep edits to what the check showed. No rewrites of style.
- Do not commit or push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/docs" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/docs/` exists, read its `README.md` first, then the files in `docs/review-sweep/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
