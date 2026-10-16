---
title: Direction
summary: The weekly direction reviews: what moved per area, what is blocked, the allocation of the week and the decisions taken.
owner: <owner>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD>
type: reference
---
One memo per review, written by `/direction:review` from the tracker. A memo proposes; a decision counts once it is recorded in the tracker with `area:direction` and `kind:decision`, and the memo line names the record.

## Reviews

| Memo | Period | Decisions recorded | Open |
|---|---|---|---|
| [review-<YYYY-MM-DD>](review-<YYYY-MM-DD>.md) | <start>/<end> | <n> | <n> |

## How a review runs

1. `/direction:review` reads `bd list --json --all --limit 0`, `bd ready --json` and `bd blocked --json`.
2. It writes `review-<YYYY-MM-DD>.md` from `_templates/review.md` with the four sections: What moved, Blocked, Proposed allocation, Decisions needed.
3. The owner decides each line. A decision becomes a tracker item, closed with the decision as its reason; the memo line changes from `(open)` to `(recorded: <id>)`.
4. The gate rule `direction.review-memo` reports a memo without a date or period, without one of the four sections, or with a decision line that has no status.
