---
name: style-review
description: >
  Audit existing prose against the user's personal vestige catalog (from their
  generated output-filter skill). Returns a hit list with location, pattern,
  severity, and suggested rewrite. Read-only: report, no modification.
  Activates on "/style-review", "check for vestiges", "audit this for hedging".
user-invocable: true
---

# Style review

Post-hoc audit against the user's catalog. Companion to `output-filter`, which enforces the catalog at composition time; this skill enforces it on existing text.

## Source of truth

Read the catalog from `~/.claude/skills/output-filter/SKILL.md` before auditing. If no generated catalog exists yet, say so and offer `/calibrate`; auditing against the starter menu alone is allowed but label the report "starter catalog, uncalibrated".

## Scope: whose text is this?

The catalog governs model-to-user output. Before auditing, classify:

- **Model output** (replies, drafts the model wrote): full catalog.
- **The user's own writing** (their posts, emails, articles): do NOT run the catalog unless they explicitly ask for it on their own text. Many writers deliberately use the default register for external audiences; a filter tuned for inbound reading is the wrong tool for outbound writing. When they do ask, say once that the calibration direction differs, then proceed.

Unclear direction: ask.

## Usage

- `/style-review <file path>`: audit the file.
- `/style-review` + pasted prose: audit the paste.
- `/style-review --rewrite <input>`: hit list plus a rewritten version with critical and high hits stripped.

## Output format

```
## Style review: <source>

Total hits: N (critical: N, high: N, medium: N, low: N)

1. Line 12: **<pattern name>**
   > "<quoted specimen>"
   Suggested: <the fix from the catalog entry>

### Summary
- Strongest patterns: <top 2 by count>
- Recommended action: <one line>
```

Severity comes from the user's catalog ordering (entries they confirmed as BLOCK-tier regex rules are critical; prose-only stance rules are medium unless their entry says otherwise). List all hits first, then compute totals from the finished list; never write counts before the hits exist.

## What this is NOT

- Not a grammar or fact checker.
- Not a universal AI-detector. The catalog is fitted to one reader; other readers' legitimate registers will false-positive against it.
- Not a rewrite service by default. `--rewrite` is opt-in; the default report leaves the text alone.
