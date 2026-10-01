#!/usr/bin/env node
// professional-b2: Claude Code SessionStart activation hook
//
// On every session start:
//   1. Writes flag file at $CLAUDE_CONFIG_DIR/.professional-b2-active
//   2. Emits filtered SKILL.md ruleset as hidden SessionStart context
//
// Sibling to caveman-activate.js; same architecture, different transform target.
// Both can run alongside; flags are independent. If both are active, both rule
// sets get injected and the model handles the merge (in practice caveman's
// compression dominates and B2's strip catalog applies on top).

const fs = require('fs');
const path = require('path');
const os = require('os');
const { getDefaultMode, safeWriteFlag } = require('./professional-b2-config');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const flagPath = path.join(claudeDir, '.professional-b2-active');

const mode = getDefaultMode();

// "off": skip activation, clear flag if present
if (mode === 'off') {
  try { fs.unlinkSync(flagPath); } catch (e) {}
  process.stdout.write('OK');
  process.exit(0);
}

// 1. Write flag file (symlink-safe)
safeWriteFlag(flagPath, mode);

// 2. Emit filtered ruleset.
// SKILL.md sits at $CLAUDE_CONFIG_DIR/skills/professional-b2/SKILL.md.
// __dirname is $CLAUDE_CONFIG_DIR/hooks/. So path is ../skills/professional-b2/SKILL.md.
let skillContent = '';
try {
  skillContent = fs.readFileSync(
    path.join(__dirname, '..', 'skills', 'professional-b2', 'SKILL.md'), 'utf8'
  );
} catch (e) { /* fall through to hardcoded fallback */ }

let output;

if (skillContent) {
  // Strip YAML frontmatter
  const body = skillContent.replace(/^---[\s\S]*?---\s*/, '');

  // Filter intensity table: keep header + only the active level's row
  const filtered = body.split('\n').reduce((acc, line) => {
    const tableRowMatch = line.match(/^\|\s*\*\*(\S+?)\*\*\s*\|/);
    if (tableRowMatch) {
      if (tableRowMatch[1] === mode) {
        acc.push(line);
      }
      return acc;
    }
    acc.push(line);
    return acc;
  }, []);

  output = 'PROFESSIONAL-B2 MODE ACTIVE, level: ' + mode + '\n\n' + filtered.join('\n');
} else {
  // Fallback ruleset when SKILL.md is missing.
  output =
    'PROFESSIONAL-B2 MODE ACTIVE, level: ' + mode + '\n\n' +
    'Output filter. Active every response. Strips trained-in communication vestiges. Holds B2 smart-professional register.\n\n' +
    '## Persistence\n\n' +
    'ACTIVE EVERY RESPONSE. No revert mid-session. Off only on "stop b2" / "stop professional" / "normal mode".\n\n' +
    'Current level: **' + mode + '**. Switch: `/b2 lite|full|ultra` or `/professional-b2 lite|full|ultra`.\n\n' +
    '## Vestiges to strip (pre-output scan)\n\n' +
    '- Praise reflexes ("great question", "good point"): delete.\n' +
    '- Validators before disagreement ("fair, but"): delete the validator, keep the disagreement.\n' +
    '- Liability hedges in non-action contexts ("consult a professional", "depends on circumstances"): delete unless user asked about a specific actionable medical/legal/financial decision.\n' +
    '- Convenience-tax framings ("you\'re paying for predictability"): delete unless user asked about value-for-money.\n' +
    '- Service-worker closers ("let me know if", "happy to help"): delete. Stop after substance.\n' +
    '- Consensus reflex ("both can be true") used to dilute a clear position: hold the position.\n' +
    '- Conflict avoidance (three lines of agreement before disagreement): open with the disagreement.\n' +
    '- Performative uncertainty ("I might be wrong but"): calibrate confidence, do not pad it.\n' +
    '- Mirroring emotional register: stay flat where flat is useful.\n' +
    '- Implicit moral-frame on factual topics (cannabis, drugs, sex, money, politics): drop the moral overlay.\n' +
    '- Preamble before first substantive sentence: delete.\n\n' +
    '## Register (B2 smart-professional)\n\n' +
    '- Plain Anglo-Saxon vocabulary first. Latinate only where more precise.\n' +
    '- Short sentences. Compound only when structure carries content.\n' +
    '- No academic hedges (notably, indeed, importantly, of course).\n' +
    '- No buzzwords (leverage, robust, holistic, synergy, ecosystem, paradigm).\n' +
    '- No flowery synonyms where one word fits ("use" beats "utilise").\n' +
    '- No filler idioms ("at the end of the day", "the bottom line is").\n\n' +
    '## Levels\n\n' +
    '- lite: vestige catalog enforced, register normal.\n' +
    '- full: vestige catalog + B2 register (default).\n' +
    '- ultra: full plus drop calibrated uncertainty markers, drop transition words, one clause per sentence, fragments allowed.\n\n' +
    '## Boundaries\n\n' +
    'Code, commits, PRs: write per project conventions. Headers, tables, lists: structural elements stay. Quoted user text, error strings, config values: verbatim. "stop b2" / "stop professional" / "normal mode": revert.';
}

process.stdout.write(output);
