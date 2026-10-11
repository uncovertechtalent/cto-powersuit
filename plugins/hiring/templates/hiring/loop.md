---
title: Interview loop for <role>
summary: The stages of the interview loop for <role>, the interviewer role in each stage and the signal each stage collects, with each signal collected once.
labels: hiring, interview-loop
owner: <hiring manager>
reviewed: <YYYY-MM-DD, the day the loop was agreed with the panel>
review_by: <YYYY-MM-DD, 90 days after reviewed, or the end of this hiring round>
type: reference
---
Every candidate for <role> goes through the stages below, in this order, with the same questions per stage. Each signal is collected in one stage only. The rubric in `hiring/rubrics/<role-slug>.json` holds the anchored levels for every signal and is written before the first interview.

## Role

| Field | Value |
|---|---|
| Role | <title and level> |
| Team | <team the person joins> |
| Why the role exists | <the problem this hire solves, in one sentence> |
| Outcomes in the first year | <two to four outcomes a reviewer can check> |
| Must-haves at the screen | <criteria checked as yes or no, each tied to an outcome> |
| Learnable after joining | <skills the loop does not test> |

## Stages

| # | Stage | Interviewer role | Length | Format | Signals collected |
|---|---|---|---|---|---|
| 1 | Screen | <hiring manager or recruiter> | <minutes> | <call> | Must-haves only, as yes or no |
| 2 | <stage name> | <role, for example senior engineer on the team> | <minutes> | <work sample, design discussion, structured interview> | <signal> |
| 3 | <stage name> | <role> | <minutes> | <format> | <signal> |
| 4 | <stage name> | <role> | <minutes> | <format> | <signal> |
| 5 | Debrief | Panel, led by <facilitator role> | <minutes> | Evidence first, decision last (`hiring/debrief-template.md`) | None |

## Signal map

One row per signal. A signal that shows up in two stages is collected twice and counted twice: move it to one stage.

| Signal | Stage | Interviewer role | Rubric dimension |
|---|---|---|---|
| <what the stage observes, in one line> | <stage #> | <role> | <dimension name in the rubric> |

## Interviewer rules

- Ask the questions in the rubric for your stage. Follow-up questions stay on the topic of the question and ask for detail on the candidate's answer.
- Score only the dimensions of your stage. Write the evidence first: what the candidate said or did, close to their words. Then pick the level whose anchor matches the evidence.
- Submit the scorecard before you see any other score and before you talk about the candidate with anyone on the panel.
- Interviewers take the rubric training for this loop before their first interview: <how and when>.

## Candidate information

- What the candidate gets before each stage: <format, length, tools allowed, who they meet by role>.
- Total time asked of the candidate: <hours>. A take-home task has a stated time limit of <hours>.
- Adjustments: ask every candidate the same question about adjustments they need, and record the answer outside the scorecards.

## Decision rule

<The hire bar from the rubric, for example: no dimension at level 1, and at least <number> dimensions at level 3 or above. Who makes the decision: <role>.>
