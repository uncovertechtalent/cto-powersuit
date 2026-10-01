---
name: calibrate
description: >
  Derive the user's personal vestige catalog and write their fitted output-filter
  skill plus hook rule table. Interviews the user, mines their own session
  transcripts for pushback moments, drafts catalog entries from real specimens,
  and generates ~/.claude/skills/output-filter/SKILL.md and
  ~/.claude/vestige-patterns.js. Activates on "/calibrate",
  "calibrate my filter", "build my output filter".
user-invocable: true
---

# Calibrate

You are fitting an output filter to THIS user. Their tolerance for warmth, praise, hedging, and scaffolding is not yours to assume. Everything below produces evidence first, rules second.

## Phase 1: mine the transcripts

Session logs live under `~/.claude/projects/<project-dirs>/*.jsonl`. Search user messages for pushback markers:

```bash
grep -l . ~/.claude/projects/*/*.jsonl 2>/dev/null | head -50
```

Then scan for user turns containing (case-insensitive): "stop ", "don't ", "why are you", "just answer", "no fluff", "get to the point", "stop apologizing", "you don't need to", "skip the". For each hit, extract the assistant message immediately before it. That pair (assistant output + user reaction) is a specimen: the user's own past irritation, on the record.

Cap the mining at 20 specimens. If the logs yield fewer than 5, say so and lean on Phase 2.

## Phase 1b: bootstrap from existing rules

Before interviewing, read the user's existing CLAUDE.md / global config for informal style rules ("be direct", "no filler", "don't apologize", "terse", "stop hedging"). Each is a pre-specimen: a fight they already had with the model. Present them: "You already have these preferences; formalize them into catalog entries?" Formalized entries get the full pattern + fix + exemption treatment; the informal originals can then be removed to avoid double-instruction drift.

## Phase 2: interview

Ask these, one block, wait for answers:

1. Which of these bother you? (praise openers / closers offering more help / hedge padding / agreement before disagreement / emotional mirroring / long preamble / moralizing on factual questions / buzzwords / stage hooks such as "here's the thing" or "let's dive in" / none of these reliably)
2. What do you want KEPT? (some people want warmth kept, or hedges kept when uncertainty is real. The filter must not strip what you value.)
3. Paste 1 to 3 replies from any AI that grated on you, if you have them at hand.
4. Vocabulary band: plain and short, or normal, or technical-dense?
5. Pet bans: specific words or punctuation you never want in prose aimed at you?
6. When should the filter step aside? (code reviews, security warnings, commit messages, documentation, multi-step instructions, when you ask for clarification). Answers go verbatim into the generated skill's Auto-clarity and Boundaries sections; a compressed security warning is the classic failure this prevents.

## Phase 3: draft the catalog

From specimens + answers, draft entries. Each entry:

- Pattern name, 2-3 example phrases (from THEIR specimens where possible, generic otherwise)
- The fix, as an action
- Documented exemptions
- Evidence line: which specimens support it (or "interview only", flagged lower-confidence)

Sort into layers per `${CLAUDE_PLUGIN_ROOT}/CALIBRATION.md`: regex-safe with near-zero false positives goes to the hook BLOCK tier; regex-able but sometimes-legitimate goes to WARN; everything else stays prose. Present the draft catalog as a table and get explicit confirmation per entry. Entries they hesitate on go in as WARN or prose, never BLOCK.

## Phase 4: generate the artifacts

1. Write `~/.claude/skills/output-filter/SKILL.md` from the template in this plugin (`${CLAUDE_PLUGIN_ROOT}/skills/output-filter/SKILL.md`), replacing every `{{PLACEHOLDER}}` with their confirmed content. Let them pick the activation phrase and the default level (lite / full / ultra).
1b. Offer the embed option: additionally write the core rules (catalog + register, NOT the levels/recovery machinery) into their CLAUDE.md as a clearly-marked persistent section. Embedded rules are active from turn 1 of every session and survive long sessions better than any toggle; the skill remains the surface for level switching and "add to catalog". If they accept, keep the two in sync whenever the catalog changes.
2. Write `~/.claude/vestige-patterns.js` (or `$CLAUDE_CONFIG_DIR/vestige-patterns.js` when that variable is set) with their BLOCK and WARN rules. Start from the starter table at `${CLAUDE_PLUGIN_ROOT}/hooks/vestige-patterns.js`. The plugin's hooks load the user's table when it exists, and it survives plugin updates. Keep the file's exported interface intact (`BLOCK_RULES`, `WARN_RULES`, `stripExempt`, `scan`). Keep the `family` field on rules that carry one and the `opts.skipFamilies` parameter of `scan`: the write scan and `vestige-batch.js --script` use them to exempt scripts from the `mode-leak` family.
3. Test each regex against their own specimens AND against 3 legitimate sentences that should NOT match. Show the test results.
4. The plugin wires the hooks itself (Stop: vestige-scan and guess-scan; PostToolUse on Write and Edit: vestige-write-scan). Do not add them to `settings.json` as well, or every reply is scanned twice. To confirm the user's table is live, run `node ${CLAUDE_PLUGIN_ROOT}/hooks/vestige-batch.js` on a file that holds one of their specimens.

## Phase 5: schedule the refit

Tell them the maintenance loop from `${CLAUDE_PLUGIN_ROOT}/CALIBRATION.md` step 6 (add on grate, exempt on false positive, retire on model improvement), and suggest a re-run of `/calibrate` after 2 weeks of use, mining only transcripts newer than today.

## Rules for you, the calibrating model

- Do not import the repo author's taste. The starter entries in the template are worked examples, opt-in only.
- Do not pad the catalog to look thorough. Five rules that fire correctly beat twenty that argue.
- If their specimens contradict their interview answers (they SAY praise is fine, but three specimens show them snapping at praise), show them the contradiction and let them decide. Specimens outrank self-report as evidence, but the user outranks both.
- The generated skill governs model-to-user output only. Never apply it to the user's own writing unless they ask.
