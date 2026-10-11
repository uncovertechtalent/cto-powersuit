---
name: hiring-debrief
description: >
  Run a hiring debrief with evidence before votes: each interviewer writes
  evidence and a level per rubric dimension before seeing other scores, the
  debrief goes through the evidence first, the levels after it, and the
  decision comes last and is recorded with its reasons and any dissent. Use
  when a candidate has finished the loop, or when the most senior or most vocal
  panel member sets the outcome of debriefs. Activates on "/hiring-debrief", "run the
  debrief", "hiring decision for this candidate", "collect the scorecards",
  "write up the debrief".
user-invocable: true
---

# Hiring debrief

Prepares and records the debrief for one candidate. The order is fixed: independent scorecards, then the evidence round, then the levels, then the decision. Each interviewer writes the scorecard before the debrief, so the evidence is written without knowledge of the other scores. The evidence round comes before the levels, so the discussion starts from what the candidate said and did.

The panel decides. This skill collects, orders and records; it never scores a candidate and never recommends hire or no hire. Check before use: AI systems used to evaluate candidates fall in a high-risk class under the EU AI Act (Annex III); confirm with your legal contact before any tool scores candidates.

## Inputs

- The candidate id (no name in the record), the role and `hiring/rubrics/<role-slug>.json`.
- The scorecards: per interviewer, evidence and a level for each dimension of their stage, with the time each was submitted.
- The facilitator and the decision maker, named before the first interview.

## Steps

1. **Collect the scorecards.** Ask each interviewer for their scorecard: evidence lines and one level per dimension of their stage. Check that each scorecard was submitted before the debrief and before its author saw another score. Mark any scorecard written later as "written after seeing other scores" in the record.
2. **Check the scorecards.** For each dimension: evidence is present, the level is 1 to 4, and the evidence matches the anchor of that level in the rubric. Where evidence and anchor do not match, ask the interviewer before the debrief. A level with no evidence counts as "no evidence" in the evidence round.
3. **Start the record** without overwriting the template:

   ```bash
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/hiring/debrief-template.md" hiring/debrief-template.md
   ```

   Fill a copy of it for this candidate in the place the team keeps candidate records. If the team has no such place, ask the user where it goes. A debrief record never goes into a public repository.
4. **Evidence round.** Go through the dimensions in loop order. Each interviewer reads out the evidence for their dimensions, with no level and no hire or no-hire. The panel asks questions about the evidence only. Record the points raised and the open questions.
5. **Levels.** Show all levels together. Where two levels for related evidence are more than one level apart, ask each interviewer to point to the evidence. A level changes only for a reason tied to evidence, and the record shows the old level, the new level and the reason.
6. **Hire bar.** Compare the final levels with `hire_bar` in the rubric. Record met or not met.
7. **Decision last.** The decision maker states the decision: hire, no hire, or more evidence from a named stage. Each reason names a dimension and the evidence behind it. Record any dissent with the interviewer role and the reason.
8. **Feedback and close.** Draft the feedback to the candidate from the evidence, for the hiring manager to send. List the follow-ups with an owner role each.

## Output

- One filled debrief record in the team's candidate records: scorecards, evidence round, levels with any changes, hire bar result, decision, reasons, dissent and follow-ups.
- A note to the hiring manager when a scorecard was written after seeing other scores, or when the decision differs from the hire bar.

## Rules

- No talk about the candidate among the panel before every scorecard is in.
- Evidence first, levels second, decision last.
- Reasons cite a dimension and its evidence. "Gut feeling", "culture fit" and comparisons to people on the team are not reasons.
- No discussion of age, family, health, origin, religion, gender, sexual orientation or any other protected characteristic. If such a discussion starts, stop it and restart from the evidence.
- The decision maker speaks last in the levels round.
- Candidate data stays in the team's candidate records, under the retention period the company sets.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/hiring" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/hiring/` exists, read its `README.md` first, then the files in `hiring/hiring-debrief/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
