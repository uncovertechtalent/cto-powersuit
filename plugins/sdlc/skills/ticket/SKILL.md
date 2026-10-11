---
name: ticket
description: >
  Write a ticket from a request, a bug report, a chat or a postmortem action
  item: problem, testable acceptance criteria, risk, and labels for type, area,
  priority and status. Also sets up the label scheme in the tracker. Use when
  work is about to start without a ticket, or when a request is too vague to
  build. Activates on "/ticket", "write a ticket", "open an issue for",
  "turn this into a ticket", "set up our labels".
user-invocable: true
---

# Ticket

A ticket says what done means before anyone builds. The agent that builds the change, the reviewer and the person who closes the ticket all read the same acceptance criteria.

## Label scheme

| Group | Labels | Meaning |
|---|---|---|
| Type | `type: feature`, `type: bug`, `type: chore`, `type: docs` | What kind of work. An issue without a type label is untriaged |
| Area | `area: <part>` | Which part of the system; the team names its parts. An issue can carry more than one |
| Priority | `P0`, `P1`, `P2`, `P3` | P0 stops other work; P1 is next; P2 is planned; P3 is optional |
| Status | `status: ready`, `status: in progress`, `status: blocked` | The board column. No status label means backlog; closed means done |

Only maintainers set labels. On a public tracker, a report from outside counts as untriaged until someone sets its type.

## Steps

1. **Find duplicates.** `gh issue list --search "<key words>" --state all`. Link a duplicate and stop.
2. **Write the problem.** Who is affected, what they cannot do, how often. One paragraph, no solution in it.
3. **Write acceptance criteria.** Each one is a result someone can check without asking the author. "Uploads up to 2 GB succeed on the first try" can be checked; "uploads are faster" cannot.
4. **Write the risk.** What could break, who would notice, how to roll back.
5. **Pick labels.** One type, one or more areas, one priority. A new ticket has no status until it meets the team's definition of ready.
6. **Create it** after the user approves the text: `gh issue create --title "<title>" --body-file <file> --label "type: feature" --label "area: <part>" --label P2`. Without `gh`, give the user the text to paste.

## Set up the labels

Once per repository, with the user's go:

```bash
gh label create "type: feature" --color 1f6feb
gh label create "type: bug" --color d73a4a
gh label create "type: chore" --color 6e7781
gh label create "type: docs" --color 0e8a16
gh label create "status: ready" --color fbca04
gh label create "status: in progress" --color 5319e7
gh label create "status: blocked" --color b60205
for p in P0 P1 P2 P3; do gh label create "$p"; done
```

Add `area:` labels with the names the team uses. `gh label create` stops on a label that exists; existing labels stay as they are.

## Rules

- One problem per ticket. Split a ticket with two problems.
- Acceptance criteria are testable, or the ticket is not ready.
- Never create, label or close issues without the user's go.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/ticket/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
