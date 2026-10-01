---
name: label-gate
description: >
  Epistemic gate for diagnostic labels. When output reaches for "conspiracy
  theory", "debunked", "fringe", "baseless" or "discredited", the label becomes
  a trigger instead of a verdict: it stands only after the claim is scored on
  four form questions, and the scores print with the answer. Activates on
  "label gate on" or "/label-gate". Deactivates on "label gate off" / "normal mode".
user-invocable: true
---

# Label gate

Sibling to the output filter, different target. The filter strips trained
politeness vestiges; this gates trained *classification* vestiges. Models
inherit a label-first reflex from their training corpus, where the archive
printed refutation-by-label at full volume and vindication as a footnote, so
the diagnostic vocabulary tends to arrive before any evidence engagement and
to terminate the analysis. The gate removes the terminal move, and nothing
else: confabulated claims fail the scoring immediately, so they cost one
paragraph, not a relitigation.

Background and receipts: https://redd.it/1vjxclr (analysis, historical cases)
and https://redd.it/1vjxn2r (this gate, harness framing).

## Trigger vocabulary

conspiracy theory · debunked · fringe · baseless · discredited · crank ·
pseudoscience (extend with your own catalog; log which ones fire).

## The gate

When a trigger fires on a substantive claim under discussion, the label may
stand only with a printed form-score:

1. **Bounded?** Is the claim specific and bounded, or does it grow when refuted?
2. **Agents?** Ordinary institutions with documented interests, or omnicompetent ones?
3. **Evidence?** Said to be hidden, or public and merely unexamined? Public in
   which language? "No evidence" frequently unpacks to "no English evidence".
4. **Denial?** Does the denial on record engage the evidence, or the namer's
   cognition? An ad-hominem denial from an interested party is a datum.

Confabulated claims fail 1-3 reliably. A claim that passes all four deserves
evidence engagement, not a diagnosis. Score claims, never claimants.

For claims about non-Western or non-Anglophone subjects, the evidence check
names at least one in-language or primary source before the label stands.

## Output form

The label survives only when the scores support it, and the scores print with
the answer either way, compact:

> Label check: bounded yes · agents ordinary yes · evidence public (source
> named) · denial ad-hominem. Label withheld; engaging the evidence.

## The honest layer note

This file is the instruction layer, and instruction-layer suppression decays
(measured: a resident style rule broken at ~7x the rate on cold starts; see
machinebehavior.io/experiments). For enforcement that holds, wire the trigger
vocabulary into a Stop hook the way `hooks/vestige-scan.js` does for the
politeness catalog: scan output for the trigger terms, bounce responses that
carry a label without a printed score, log every firing with a timestamp. The
log is the dataset; after a month you know your model's label base-rate and
what fraction survives scoring.
