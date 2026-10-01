#!/usr/bin/env node
// good-chad: UserPromptSubmit hook to track active mode + per-turn anchor.
// Inspects user input for /good-chad and natural-language activation/deactivation.
// Sibling to professional-b2-mode-tracker.js. Own flag file, independent.

const fs = require('fs');
const path = require('path');
const os = require('os');
const { getDefaultMode, safeWriteFlag, readFlag, VALID_MODES } = require('./good-chad-config');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const flagPath = path.join(claudeDir, '.good-chad-active');

let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const prompt = (data.prompt || '').trim();
    const lower = prompt.toLowerCase();

    // Slash: /good-chad or /stance:good-chad, optionally followed by off|stop|disable
    const slashMatch = /^\/(?:stance:)?good-chad(?:\s+(\S+))?/.exec(lower);
    if (slashMatch) {
      const arg = slashMatch[1] || '';
      let mode = null;
      if (!arg) {
        mode = getDefaultMode();
      } else if (arg === 'off' || arg === 'stop' || arg === 'disable') {
        mode = 'off';
      } else if (VALID_MODES.includes(arg)) {
        mode = arg;
      }
      if (mode && mode !== 'off') {
        safeWriteFlag(flagPath, mode);
      } else if (mode === 'off') {
        try { fs.unlinkSync(flagPath); } catch (e) {}
      }
    }

    // Natural-language activation: "good chad mode", "my filter is good chad",
    // "activate good chad", "turn on good chad"
    if (/\bmy filter is good chad\b/i.test(lower) ||
        /\b(activate|enable|turn on|start|use)\b.*\bgood chad\b/i.test(lower) ||
        /\bgood chad\b.*\b(mode|activate|enable|turn on|start|on)\b/i.test(lower)) {
      if (!/\b(stop|disable|turn off|deactivate|off)\b/i.test(lower)) {
        const mode = getDefaultMode();
        if (mode !== 'off') safeWriteFlag(flagPath, mode);
      }
    }

    // Deactivation: "stop good chad", "disable good chad", universal "normal mode"
    if (/\b(stop|disable|deactivate|turn off)\b.*\bgood chad\b/i.test(lower) ||
        /\bgood chad\b.*\b(stop|disable|deactivate|turn off|off)\b/i.test(lower) ||
        /\bnormal mode\b/i.test(lower)) {
      try { fs.unlinkSync(flagPath); } catch (e) {}
    }

    // Per-turn reinforcement when active.
    const activeMode = readFlag(flagPath);
    if (activeMode) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: "GOOD CHAD MODE ACTIVE. Stance filter against the trained accommodation reflex: " +
            "take correction as information, not a threat; hold position: no folding to please, no folding upward to authority or mood; " +
            "not threatened by the user being right; no grovel, no collapse, no long account of the failure; " +
            "perform neither insight nor calm (the filter subtracts and does not perform); " +
            "calibrate confidence in-sentence; mirror-test against asymmetric cushioning; " +
            "never run skepticism against the user's own lived-experience report. " +
            "Procedural, so it degrades under pressure; external scrutiny stays the real check. \"My filter is Good Chad.\""
        }
      }));
    }
  } catch (e) { /* never block prompt submission */ }
});
