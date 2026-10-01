# Calibration: deriving your own catalog

The `/calibrate` skill automates this procedure. This document is the manual version, and the rationale, so you can run it by hand or audit what the skill did.

## Premise

A filter is a fit between two registers: the model's trained output style and your tolerance. Both vary. Some people want zero warmth, some want warmth but no hedging, some only want the fake questions gone. There is no universal catalog, only a universal derivation:

1. Collect specimens of output that grated on you.
2. Name the pattern in each specimen.
3. Sort patterns into layers (lexical / register / stance).
4. Write the rules, each with its fix.
5. Install the mechanical backstop for the lexical slice.
6. Iterate on catch, forever.

## Step 1: specimens

You need 10 to 20 real examples of model output that irritated you. Sources, best first:

- **Your own transcripts.** Claude Code keeps session logs under `~/.claude/projects/`. Grep them for your own pushback: messages where you said "stop", "why are you", "don't do that", "just answer". The assistant message right before each of those is a specimen, pre-validated by your own past irritation.
- **Live collection.** Work normally for a week with a note open. Paste anything that grates, verbatim, the moment it grates.
- Memory alone is the worst source. You will remember the caricature ("it says great question a lot") and miss your actual top irritant, which is usually structural.

## Step 2: name the pattern

For each specimen, ask: what exactly is the offending unit? A word? A phrase shape? A sentence position (opener, closer)? A behavior (agreeing before disagreeing)? Write one line per specimen: the quoted text, the pattern name you give it, and what the model should have done.

Patterns that recur across 3+ specimens are catalog candidates. Singletons are noise; leave them out on the first pass.

## Step 3: sort into layers

| Layer | Test | Enforcement |
|---|---|---|
| Lexical | Can a regex catch it with near-zero false positives? | Stop hook (`vestige-patterns.js`), BLOCK tier |
| Register | Is it about vocabulary level, sentence length, structure? | Skill prose, plus hook WARN tier if partially regex-able |
| Stance | Is it about behavior under disagreement, correction, emotion? | Skill prose only, plus your own attention |

Be strict about the lexical test. "Great question" is regex-safe. "Hedging" is not: the same words are legitimate calibration in one sentence and cushioning in the next. Rules that cannot pass the false-positive test go in the skill as prose, not in the hook. A hook that cries wolf gets disabled within a week.

## Step 4: write the rules

Each catalog entry needs three parts, in the skill file:

- **The pattern**, with 2 or 3 example phrases.
- **The fix**, stated as an action ("delete the validator, keep the disagreement"), never as "avoid X".
- **The documented exemption**, if any. When a rule has legitimate uses, list them in the entry (quoting someone, rubric criteria, teaching contexts). Undocumented exemptions turn into arguments with the model later; documented ones settle instantly.

Date your entries. A catalog is a lab notebook, and "added 2026-08-03 after the fake-enthusiasm incident" is what lets future-you audit whether a rule still earns its place.

## Step 5: the mechanical backstop

Prose instructions degrade over a long session; a regex that runs on every Stop does not. Move your regex-safe rules into `hooks/vestige-patterns.js`:

- **BLOCK tier**: near-zero false positives only. The hook blocks the reply once and demands a corrected resend. One block per turn max, no loops.
- **WARN tier**: patterns that are usually bad but sometimes legitimate. Warns ride along when a block fires and are logged either way. The log (`~/.claude/vestige-scan.log`) is your promotion dataset: a warn rule that runs clean for weeks gets promoted to block; one that keeps hitting legitimate text gets rewritten or dropped.

## Step 4b: state rules positively where you can

A ban list ("don't open with praise") and a register description ("open with the substance; pattern: [thing] [action] [reason]") can encode the same catalog. Prefer the register form for the skill prose: the model follows an instruction better than it polices a checklist, and the positive form survives longer sessions. Keep the ban form for the hook, where a regex needs a concrete pattern to match. Rule of thumb: hook entries are negative (patterns to catch), skill prose is positive (how to write), and they describe the same behavior from two sides.

## Step 5b: embed the baseline, keep the toggle

A skill activates when invoked; your CLAUDE.md loads every session from turn 1. For maximum durability, put the core catalog + register rules into your CLAUDE.md (or project equivalent) as a persistent section, and keep the generated skill for level switching and the "add to catalog" workflow. `/calibrate` offers this as the embed option. Always-on baseline, toggleable intensity.

## Step 6: iterate on catch

The loop that keeps the filter fitted:

- Output grates and no rule fired: add the pattern, dated, with the specimen.
- A rule fires on legitimate text: add the documented exemption, or demote block to warn.
- You stop noticing a pattern in raw output: the base model may have improved; retire the rule and note the date.

## The maintenance loop is the product

The initial calibration is the setup; this loop is what you actually bought. First-class workflow, verbatim:

1. Output grates.
2. You: `add to catalog` + paste the specimen.
3. Model drafts the entry: pattern name, the fix as an action, exemptions.
4. You confirm or adjust.
5. Model appends it, dated, to the skill file (and CLAUDE.md section if embedded).
6. If the pattern is regex-safe, model proposes the `vestige-patterns.js` rule for the hook.

Example exchange:

> **You:** add to catalog: "That's a really thoughtful approach, and I can see why you'd want to..."
> **Model:** Entry draft — pattern: `validator-preamble` (agreement padding before the actual answer). Fix: start with the answer. Exemption: genuine agreement that IS the answer. Regex-safe: no (legitimate agreement matches the same shapes). Goes in skill prose only. Confirm?
> **You:** yes
> **Model:** Appended, dated 2026-08-04.

## Measure it once

After calibrating, ask the model to answer five representative questions from your actual work, with the filter off and then on. Compare output lengths. A fitted filter typically cuts 30-60% of output tokens; your number gives you a reason to maintain the catalog beyond taste. People maintain what they can measure. The hook log (`~/.claude/vestige-scan.log`) is the ongoing version of the same measurement; `hooks/analyze-log.js` summarizes it.

## Bootstrapping from rules you already have

If your CLAUDE.md already carries informal style rules ("be direct", "no filler", "don't apologize", "stop hedging"), those are pre-specimens: each one marks a fight you already had with the model. `/calibrate` reads them and offers to formalize each into a proper catalog entry (pattern + fix + exemption) instead of leaving them as vibes the model half-follows.

## The limits, so you don't oversell this to yourself

The stance layer does not stay fixed by any of this. Instructions asking the model to hold a posture lose force as sessions grow long and as pressure mounts, and the disposition re-expresses in whatever layer you did not patch. The hook is durable because it is not the model complying, it is code. Everything else is a fit that drifts, and the maintenance loop in step 6 is not optional. You are the check that does not degrade. Budget for that, and the kit does the rest.
