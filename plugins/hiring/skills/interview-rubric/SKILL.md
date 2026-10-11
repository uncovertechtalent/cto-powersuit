---
name: interview-rubric
description: >
  Write the structured scoring rubric for a role in hiring/rubrics/<role>.json:
  one dimension per signal in the loop, each with its stage, fixed questions
  and levels 1 to 4 whose anchors describe observable behaviour, plus the hire
  bar, all written and frozen before the first interview. Use after the loop is
  designed, when interviewers score the same answer far apart, or when panel
  members argue from impressions in the debrief. Activates on "/interview-rubric", "write the
  rubric", "scoring guide for interviews", "anchor the levels", "how do we score
  candidates".
user-invocable: true
---

# Interview rubric

Writes the rubric for one role. Each signal in `hiring/loop.md` becomes one dimension with fixed questions and four levels. Each level has an anchor: a description of what the interviewer saw or heard at that level. An interviewer writes the evidence first, then picks the level whose anchor the evidence matches. The rubric is frozen before the first interview, so every candidate is scored on the same scale.

## Inputs

- `hiring/loop.md` with its signal map. Without it, run `/hiring:interview-loop` first.
- The interviewers for each stage, for the calibration round.

## Steps

1. **Read the signal map** in `hiring/loop.md`. One dimension per signal, with the same stage.
2. **Start the file** from the example without overwriting:

   ```bash
   mkdir -p hiring/rubrics && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/hiring/rubrics/example-role.json" "hiring/rubrics/<role-slug>.json"
   ```

   Replace the example dimensions with the role's own. Keep the keys: `role`, `level`, `owner`, `written`, `loop`, `scale`, `hire_bar`, `dimensions` (each with `name`, `signal`, `stage`, `questions`, `levels`) and `changes`.
3. **Write the questions.** Two or three fixed questions or tasks per dimension, asked of every candidate. Questions about past work ask for one real case ("Tell me about a time ..."). Follow-up questions ask for detail on that case.
4. **Write the anchors.** Levels `"1"` to `"4"`:

   | Level | Meaning |
   |---|---|
   | 1 | No evidence of the signal, or evidence against it |
   | 2 | Part of the signal, with help or with prompts |
   | 3 | The signal as the role needs it on day one |
   | 4 | Beyond what the role needs, shown with an example |

   Each anchor states what the candidate said or did: "Named how the design fails and how it recovers." Leave out words that need a judgement to apply, such as "strong", "good", "senior" or "confident". Two levels must differ in something an interviewer can observe. An anchor never refers to the candidate's background, school or past employer.
5. **Set the hire bar** in `hire_bar`, in terms of levels, for example "No dimension at level 1. At least two dimensions at level 3 or above." Name the dimensions that are must-haves, if any.
6. **Calibrate.** Give the interviewers two written sample answers per dimension, invented for this purpose. Each interviewer scores them alone, then the scores are compared. Where two interviewers are more than one level apart, rewrite the anchor that allowed it and repeat.
7. **Freeze.** Set `written` to today's date and ask the user to commit the rubric before the first interview. A change after the first interview applies to candidates who have not started the loop; add it to `changes` with the date and the reason.
8. **Offer the gate check.** With the gate installed, suggest `/gate:add-rule` for `hiring.rubric-anchors` on `warn`.

## Output

- `hiring/rubrics/<role-slug>.json` with one dimension per signal, anchored levels 1 to 4, the questions and the hire bar.
- The calibration result: the anchors rewritten and the remaining spread between interviewers.

## Rules

- The rubric exists before the first interview.
- Every anchor describes observable behaviour. A level with no anchor, or an anchor still in angle brackets, is not ready.
- The same questions and the same rubric for every candidate of the role.
- No dimension, question or anchor on a protected characteristic.
- Scores come from interviewers. This skill writes the rubric and never scores a candidate.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/hiring" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/hiring/` exists, read its `README.md` first, then the files in `hiring/interview-rubric/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
