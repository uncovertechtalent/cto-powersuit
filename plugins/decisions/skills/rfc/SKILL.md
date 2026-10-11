---
name: rfc
description: >
  Write a request for comments (RFC) from a problem statement and run it to a
  decision: draft, open for comments until comments_close, decide, then hand the
  outcome to the adr skill, which writes the decision record and links back. Use
  when a change touches more than one team, is hard to undo or needs comments
  before a decision. Never overwrites a file. Activates on "/rfc", "write an
  RFC", "draft an RFC", "request for comments", "propose a change for review",
  "open the RFC for comments", "close the RFC".
user-invocable: true
---

# RFC

Turns a problem statement into an RFC file in the decision log, opens it for comments with a fixed closing date, and closes it with a recorded outcome. The RFC holds the proposal and the discussion. The decision itself goes into an ADR, written by the `adr` skill.

Lifecycle: `draft`, then `review` (open for comments until `comments_close`), then `accepted`, `rejected` or `withdrawn`.

## Inputs

- **Problem statement** (required): what is wrong or missing, in the user's words.
- **Owner**: the person who drives the RFC to a decision. Ask if not given.
- **Reviewers**: names or teams who must comment. Ask if not given.
- **Comment window**: default 14 days from the day the RFC opens for comments.
- **Folder**: default `docs/decisions/` at the repository root.

## Steps

1. **Set up the folder.** If `docs/decisions/index.md` or `docs/decisions/_templates/` is missing, copy the templates without overwriting:

   ```bash
   mkdir -p docs/decisions
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/" docs/decisions/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/." docs/decisions/`. List the files copied and the files skipped.
2. **Check the problem statement.** It needs who is affected, how often or how much, and what happens if nothing changes. Ask at most three questions for the missing parts. Do not invent numbers.
3. **Look for earlier records.** Search the titles and summaries of `docs/decisions/rfc-*.md` and `docs/decisions/adr-*.md` for the same subject. If an open RFC covers it, stop and point the user to it. If an accepted ADR covers it, the RFC must name that ADR and say whether the proposal would supersede it.
4. **Pick the number.** Next number = highest existing RFC number + 1, from file names and `rfc:` fields:

   ```bash
   python3 - docs/decisions rfc <<'EOF'
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

   The slug is `rfc-NNNN-short-name`: the number and two to five lowercase words joined by hyphens. Run `test -e docs/decisions/<slug>.md`. If the file exists, never overwrite it: take the next free number.
5. **Draft.** Start from `docs/decisions/_templates/rfc.md` (or `${CLAUDE_PLUGIN_ROOT}/templates/docs/decisions/_templates/rfc.md` if the repository has none). Fill the front matter: `status: draft`, `date` and `reviewed` today, `review_by` 90 days later, `owner`, `reviewers`, `comments_close` empty until step 7, `decision` empty. Write every section:
   - Summary: problem, proposal and expected result in two or three sentences.
   - Problem: facts from step 2, with numbers where the user gave them.
   - Proposal: the systems, files, owners and interfaces it touches.
   - Alternatives considered: at least two, one of them doing nothing, each with the reason it is not the proposal.
   - Risks and open questions: the questions the reviewers must answer.
   - Rollout and rollback: ordered steps, the undo and the signal that starts the undo.
   - Decision: one line, `Open. No decision yet.`

   Replace every `<placeholder>`. Quote any front matter value that contains ": ". Compute dates with `python3 -c 'import datetime as d; print(d.date.today() + d.timedelta(days=90))'`.
6. **Show the draft.** Print the path and the summary, and ask the owner to read it. Apply their edits.
7. **Open for comments.** When the owner says the draft is ready: set `status: review` and `comments_close` (today plus the comment window). Add the RFC to the index, as the Index section of the `adr` skill describes. Comments go on a pull request that adds the RFC file, unless the overlay names another channel. Tell the user to send the pull request link to every reviewer.
8. **Close.** On or after `comments_close`, or when the owner asks for an early close:
   - Collect the comments. With the GitHub CLI: `gh pr view <number> --comments`.
   - List each open question from the RFC with its answer, or mark it unanswered.
   - List reviewers who did not comment.
   - Ask the owner for the outcome: accepted, rejected or withdrawn. The owner decides. Never pick the outcome yourself.
9. **Record the outcome.**
   - Accepted or rejected: run the `adr` skill with this RFC as input. The ADR gets `rfc: <rfc slug>` and status `accepted` or `rejected`. Then set the RFC's `status` to the outcome and `decision: <adr slug>`, and fill the Decision section: outcome, date, who decided, link to the ADR, and the open questions that stay open.
   - Withdrawn: set `status: withdrawn`, leave `decision` empty, and write the reason in the Decision section. No ADR.
10. **Update the index** and report.

## Output

The RFC path, its number and status, `comments_close` when open, the reviewers, and the next step: open for comments, close on the date, or the ADR slug after a decision.

## Rules

- Never overwrite or delete a file. Never reuse a number, also not the number of a withdrawn RFC.
- One problem per RFC. Split a statement that holds two problems and ask which one comes first.
- After close, the RFC body stays as it was at close. Only the front matter fields `status`, `decision`, `reviewed` and `review_by` and the Decision section change. A new proposal on the same subject is a new RFC.
- A comment window shorter than 5 days needs the owner's explicit go.
- Dates are ISO `YYYY-MM-DD`.
- A written RFC holds no `<placeholder>` and none of the words that the gate's placeholder rule flags.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/decisions" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/decisions/` exists, read its `README.md` first, then the files in `decisions/rfc/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
