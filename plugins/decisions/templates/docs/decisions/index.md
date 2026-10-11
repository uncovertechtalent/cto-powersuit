---
title: Decision log
summary: Requests for comments and numbered decision records for this repository, each with a status, an owner and the links between them.
labels: adr, rfc, decision
owner: <who keeps this log current>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This page lists every request for comments (RFC) and every architecture decision record (ADR) in this folder. An RFC proposes a change and collects comments until a fixed date. An ADR records one decision: the context, the decision and its consequences. Larger decisions start as an RFC and end as an ADR. Small decisions go straight to an ADR.

A record is never deleted. When a later decision replaces an ADR, the old record gets the status `superseded` and names the record that replaced it.

## Status

| Record | Status | Meaning |
|---|---|---|
| RFC | draft | The owner is still writing it |
| RFC | review | Open for comments until `comments_close` |
| RFC | accepted | The proposal goes ahead, with the decision in an ADR |
| RFC | rejected | The proposal does not go ahead, with the reasons in an ADR |
| RFC | withdrawn | The owner stopped it before a decision |
| ADR | proposed | Written down and waiting for a decision |
| ADR | accepted | In force |
| ADR | rejected | Considered and turned down |
| ADR | deprecated | No longer in force, with no replacement |
| ADR | superseded | Replaced by a later record, kept for the history |

## Requests for comments

<!-- rfc-index -->

## Decision records

<!-- adr-index -->

## Add a record

1. Pick the type. Write an RFC when the change touches more than one team, is hard to undo or needs comments from people outside the owner's team. Write an ADR directly for a small decision.
2. Copy `_templates/rfc.md` or `_templates/adr.md` to this folder as `rfc-NNNN-short-name.md` or `adr-NNNN-short-name.md`. NNNN is the highest number of that type plus one, with four digits. Never reuse a number.
3. Fill in the front matter and every section. Replace every `<placeholder>`. Quote any value that contains ": ".
4. For an RFC, set `status: review` and a `comments_close` date when it opens for comments. When it closes, record the outcome as an ADR with `rfc:` set to the RFC slug, and set `decision:` in the RFC to the ADR slug.
5. If the new ADR replaces an older one, add `supersedes:` to the new record, and set `status: superseded` and `superseded_by:` on the old record. Both sides must name each other.
6. Update the tables above. With a docs build that fills the markers, the build writes them. Without one, keep each table on the lines directly below its marker, with no blank line inside the table.
7. Run the gate dry run, then open a pull request.
