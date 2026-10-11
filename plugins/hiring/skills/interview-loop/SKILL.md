---
name: interview-loop
description: >
  Design the interview loop for one role and write hiring/loop.md: the outcomes
  the role must deliver, the signals that predict them, the stages, the
  interviewer role in each stage and the signal each stage collects, with each
  signal collected once, in one stage. Use when a team opens a role, when
  interviewers in several stages ask about the same thing, or when interviewers
  cannot say what their stage is for. Activates on "/interview-loop", "design the
  interview loop", "set up interviews for this role", "what should each
  interview test", "our interviews overlap".
user-invocable: true
---

# Interview loop

Designs the interview loop for one role. This skill starts from what the person must deliver, turns that into a short list of signals, and gives each signal to exactly one stage. Every candidate gets the same stages and the same questions. The rubric for the signals comes next, with `/hiring:interview-rubric`, and is written before the first interview.

## Inputs

- The role: title, level, team, and why the role exists.
- The outcomes the person must deliver in the first year, from the hiring manager.
- The people available to interview, by role, and their time.

## Steps

1. **Write the outcomes.** Two to four outcomes a reviewer can check after a year, for example "the deploy pipeline runs without manual steps". Ask the hiring manager. A role with no checkable outcome is not ready for a loop: stop and say so.
2. **Split must-haves from learnable skills.** A must-have is needed on the first day and is tied to an outcome. Everything else is learnable after joining and stays out of the loop.
3. **Name the signals.** Four to six signals, each a thing a candidate can show in an interview: a behaviour, a piece of work, an account of past work with facts. Each signal ties to an outcome. Drop proxies that do not show the skill: school names, past employer names, years of experience on their own, and "fit" without a defined behaviour.
4. **Pick the stages.** One stage per kind of evidence. Common stages:

   | Stage | Evidence it gives | Fits signals like |
   |---|---|---|
   | Screen | Must-haves as yes or no | Work authorisation, availability, a hard requirement of the role |
   | Work sample | The candidate does a small piece of the real work | Writing or changing code, reviewing a change, debugging |
   | Design or case | The candidate reasons through an open problem aloud | System design, planning, trade-offs |
   | Structured experience interview | Facts about past work, with the same questions for every candidate | Running production systems, leading work, handling disagreement |
   | Debrief | Evidence from all stages, decision last | None |

   Give each signal to one stage. A stage can collect two or three signals. A signal in two stages gets counted twice and outweighs the others: move it to the stage with the best evidence for it.
5. **Assign interviewer roles.** One owner per stage, named by role. An interviewer scores only the signals of their stage. Add a second interviewer only to train them, and they score apart from the owner.
6. **Set the candidate's side.** Total time asked of the candidate, what they get before each stage, the time limit on any take-home task, and the same question to every candidate about adjustments they need.
7. **Write `hiring/loop.md`.** Copy the template without overwriting, then fill it:

   ```bash
   mkdir -p hiring && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/hiring/loop.md" hiring/loop.md
   ```

   If `hiring/loop.md` exists for another role, write `hiring/loop-<role-slug>.md` from the same template and name it in the report. Fill the Signal map with one row per signal.
8. **Check the map.** Every signal appears in exactly one row. Every stage after the screen collects at least one signal. Every signal ties to an outcome or a must-have. Report any row that breaks this.
9. **Hand over** to `/hiring:interview-rubric` to write the anchored levels for each signal.

## Output

- `hiring/loop.md` (or `hiring/loop-<role-slug>.md`) with outcomes, stages, interviewer roles and the signal map.
- The list of signals for the rubric, each with its stage.

## Rules

- Each signal is collected once, in one stage.
- The same stages and the same questions for every candidate of the role.
- Interviewers are named by role in the loop. Names of people go into the scheduling tool.
- No signal on age, family, health, origin, religion, gender, sexual orientation or any other protected characteristic. No question that invites the candidate to disclose one.
- Never copy interview questions or rubrics from another company's materials.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/hiring" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/hiring/` exists, read its `README.md` first, then the files in `hiring/interview-loop/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
