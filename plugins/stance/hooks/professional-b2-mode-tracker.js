#!/usr/bin/env node
// professional-b2: UserPromptSubmit hook to track active mode
// Inspects user input for /b2, /professional-b2, and natural-language activation
// or deactivation phrases. Writes mode to flag file or removes it.
//
// Sibling to caveman-mode-tracker.js. Operates on its own flag file
// ($CLAUDE_CONFIG_DIR/.professional-b2-active). Both hooks can run in the same
// session; their flags are independent.

const fs = require('fs');
const path = require('path');
const os = require('os');
const { getDefaultMode, safeWriteFlag, readFlag, VALID_MODES } = require('./professional-b2-config');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const flagPath = path.join(claudeDir, '.professional-b2-active');

let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const prompt = (data.prompt || '').trim();
    const lower = prompt.toLowerCase();

    // Slash command activation: /b2, /professional-b2 or /stance:professional-b2, optionally followed by lite|full|ultra|off
    const slashMatch = /^\/(?:stance:)?(b2|professional-b2)(?:\s+(\S+))?/.exec(lower);
    if (slashMatch) {
      const arg = slashMatch[2] || '';
      let mode = null;

      if (!arg) {
        mode = getDefaultMode();
      } else if (arg === 'off' || arg === 'stop' || arg === 'disable') {
        mode = 'off';
      } else if (VALID_MODES.includes(arg)) {
        mode = arg;
      }
      // Unknown arg → mode stays null, flag untouched

      if (mode && mode !== 'off') {
        safeWriteFlag(flagPath, mode);
      } else if (mode === 'off') {
        try { fs.unlinkSync(flagPath); } catch (e) {}
      }
    }

    // Natural-language activation: "b2 mode", "professional mode",
    // "smart professional", "activate b2", "turn on b2", "professional-b2 mode"
    if (/\b(activate|enable|turn on|start|use)\b.*\b(b2|professional[\s-]b2|smart professional|professional mode)\b/i.test(lower) ||
        /\b(b2|professional[\s-]b2|smart professional)\b.*\b(mode|activate|enable|turn on|start|on)\b/i.test(lower) ||
        /\bprofessional mode\b/i.test(lower)) {
      if (!/\b(stop|disable|turn off|deactivate|off)\b/i.test(lower)) {
        const mode = getDefaultMode();
        if (mode !== 'off') {
          safeWriteFlag(flagPath, mode);
        }
      }
    }

    // Deactivation: explicit "stop b2", "stop professional", "disable b2",
    // "deactivate professional-b2", or universal "normal mode" (shared with caveman)
    if (/\b(stop|disable|deactivate|turn off)\b.*\b(b2|professional[\s-]b2|professional)\b/i.test(lower) ||
        /\b(b2|professional[\s-]b2|professional)\b.*\b(stop|disable|deactivate|turn off|off)\b/i.test(lower) ||
        /\bnormal mode\b/i.test(lower)) {
      try { fs.unlinkSync(flagPath); } catch (e) {}
    }

    // Per-turn reinforcement when active. Models lose injected context after
    // other plugins inject competing instructions mid-conversation; this anchor
    // keeps the strip-catalog visible on every user turn.
    const activeMode = readFlag(flagPath);
    if (activeMode) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: "PROFESSIONAL-B2 MODE ACTIVE (" + activeMode + "). " +
            "Pre-output scan: drop praise reflexes, liability hedges, convenience-tax framings, " +
            "service-worker closers, consensus reflex, performative uncertainty, preamble. " +
            "Register: B2 smart-professional. " +
            "Code/commits/security/quoted text: write normal."
        }
      }));
    }
  } catch (e) {
    // Silent fail: hook must never block prompt submission
  }
});
