---
name: poles
description: >
  Response-structure tool, not a toggled register filter. Reshapes the trained hedge into
  two fully committed, deliberately one-sided poles plus a mandatory committed CALL.
  OPTIMIST (max bull, ignore base rates, expose its assumptions) / PESSIMIST (max bear,
  same) / CALL (commit, confidence in-sentence, name which pole's assumptions carry the
  answer). Structural complement to good-chad: it does the don't-hedge part of the stance
  job in a form you can check on the page. Use on wide-solution-space decisions and
  forecasts; skip on low-stakes factual questions. Invoked per question, not toggled.
  Activates on "/poles", "run the poles", "delusional poles", "optimist pessimist call".
user-invocable: true
---

# Poles

Per-question response structure. Not a toggled mode like professional-b2 or good-chad: you invoke it on one question, it produces one shaped answer, done. Stacks with those filters on the prose it generates.

## Why this exists

With the trained hedge ("on one hand, on the other") the model splits the difference and **hides** its real estimate. The model fuses two different things, "I don't want to commit" and "the evidence really cuts both ways", into one answer the reader can't decode.

Poles splits them apart again: two maxed poles, each 100% committed, each forced to expose the assumptions it rests on, then a committed CALL that decides. A hedged answer keeps the estimate out of sight. With poles, the model shows the assumption sets and then names where they land.

`good-chad` holds the don't-hedge instruction as a **stance**: procedural, fragile, degrades under pressure, no artifact to check. Poles turns the same instruction into a **shape**: structural, checkable in the text, durable. It does part of Good Chad's job in a form that lasts. Good Chad stays the target, the user stays its check, and poles is the tool.

## The format

**OPTIMIST (100%, delusional)**: max bull case. Ignore base rates entirely. State it fully committed and name the assumptions it needs to be true.

**PESSIMIST (100%, delusional)**: max bear case. Same: ignore base rates, fully committed, expose its assumptions.

**CALL**: committed decision. Confidence calibrated **inside** the sentence that makes the claim, not in a trailing hedge. Name which pole's assumptions carry the answer and the condition that separates them.

"Delusional" matters. It licenses each pole to ignore base rates, and that is what makes it a clean way to pull out assumptions. A *reasonable* optimist smuggles the hedge back in. Max both sides. Calibration belongs in the CALL, not in the poles.

## The one rule that carries the whole thing

**The CALL is mandatory and must commit, not average.** The poles are scaffolding, never the deliverable. A CALL that splits the difference between the two poles is the consensus reflex (a `professional-b2` vestige) with the format's headers on top: all three headers present and the answer still fails. No CALL, or an averaging CALL, is the hedge with extra steps.

How to tell it worked: the CALL usually takes the **pessimist's structural constraint** and the **optimist's read on the upside**, then names the condition that separates them. If it just averaged the two poles, it did not work.

## When to use it

- Wide-solution-space decisions ("path A vs path B", restructuring, strategy).
- Forecasts ("will the migration go clean", "is X a realistic target").
- "Should I" or "will it work" questions, where the hedge reflex is strongest.

## When not to use it

Low-stakes factual questions. Forcing two delusional poles onto a question with one answer is pure overhead: a factual "no" needs the mechanism, not a bull case and a bear case. Example: "can a cow femur be used as a hip replacement" gets a straight mechanical "no", not poles. If the answer is determinate, skip the format.

## The limit

The format is cheap to keep honest because anyone can check the *shape* at a glance: the three sections are there or they are not. Its main rule (the CALL commits and does not average) is still a stance, as fragile as good-chad. That part could not be made structural. The commit-not-average discipline still needs external scrutiny, and the user stays the check on that one piece. Structural controls hold where procedural ones degrade, and this tool converts most of a procedural guardrail into a structural one, not all of it.

## Boundaries

- Per question, not toggled. No "stop poles" needed. It ends when the answer ends.
- Code, commits, quoted text, errors: verbatim or per convention.
- Stacks under professional-b2 (words) and good-chad (stance) on the prose it produces.
