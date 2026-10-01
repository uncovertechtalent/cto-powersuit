#!/usr/bin/env node
// good-chad: Claude Code SessionStart activation hook
//
// On every session start:
//   1. Writes flag file at $CLAUDE_CONFIG_DIR/.good-chad-active
//   2. Emits the SKILL.md body as hidden SessionStart context
//
// Sibling to professional-b2-activate.js. Binary on/off. Runs alongside
// professional-b2 and any compression mode; flags independent. Good Chad is
// the stance layer; b2 the lexical layer.

const fs = require('fs');
const path = require('path');
const os = require('os');
const { getDefaultMode, safeWriteFlag } = require('./good-chad-config');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const flagPath = path.join(claudeDir, '.good-chad-active');

const mode = getDefaultMode();

if (mode === 'off') {
  try { fs.unlinkSync(flagPath); } catch (e) {}
  process.stdout.write('OK');
  process.exit(0);
}

safeWriteFlag(flagPath, mode);

let skillContent = '';
try {
  skillContent = fs.readFileSync(
    path.join(__dirname, '..', 'skills', 'good-chad', 'SKILL.md'), 'utf8'
  );
} catch (e) { /* fall through to fallback */ }

let body;
if (skillContent) {
  body = skillContent.replace(/^---[\s\S]*?---\s*/, '');
} else {
  body = 'GOOD CHAD MODE ACTIVE. Stance filter against the trained accommodation reflex. ' +
    'Take correction as information, not a threat; hold position (no folding to please, no folding upward); ' +
    'not threatened by the user being right; no grovel, no collapse, no long account of the failure; ' +
    'perform neither insight nor calm; mirror-test cushioning; never audit the user\'s report of their own experience. ' +
    'Procedural, so it degrades under pressure; external scrutiny is the real check. "My filter is Good Chad."';
}

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: body
  }
}));
