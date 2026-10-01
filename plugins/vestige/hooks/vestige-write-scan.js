#!/usr/bin/env node
'use strict';
// vestige-write-scan — PostToolUse hook on Write|Edit. Scans .md files at
// write-time against your vestige-patterns rule table, so a document written
// to disk mid-session gets caught at the write, before a batch run or a
// reader finds it.
//
// Closes the gap between vestige-scan.js (replies only) and vestige-batch.js
// (on-demand only): disk writes get their own gate. Three surfaces, one rule
// table.
//
// Behaviour:
//   - PostToolUse: the write has already landed. Exit 2 feeds the hit list
//     back to the model as feedback ("fix this file"), it does not roll back.
//   - .md files only. Non-markdown writes exit 0 untouched.
//   - EXCLUDED paths: directories holding verbatim source material, where the
//     hits belong to the quoted source and must not be "fixed". Tune the list
//     to your layout.
//   - stripExempt already exempts fenced code, inline code, and > quotes.
//   - Logs hits to ~/.claude/vestige-scan.log with a write-scan tag — same
//     promotion dataset as the Stop hook (see analyze-log.js).

const fs = require('fs');
const path = require('path');
const os = require('os');
const { configDir, loadPatterns } = require('./config-dir');
const { stripExempt, scan } = loadPatterns();

// Verbatim-source directories: quoted text is the source's voice, not yours.
// Edit to match your vault/repo layout.
const EXCLUDE = [
  /\/_sources?\//, /\/resources\//, /\/specimens?\//, /\/transcripts?\//,
  /\/\.obsidian\//, /\/_archive\//, /\/node_modules\//,
];

function main() {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch {}
  const fp = input.tool_input && input.tool_input.file_path;
  if (!fp || !fp.endsWith('.md')) process.exit(0);
  if (EXCLUDE.some(re => re.test(fp))) process.exit(0);

  let text;
  try { text = fs.readFileSync(fp, 'utf8'); } catch { process.exit(0); }
  // Scripts are written to be spoken: stage devices are correct there.
  const hits = scan(stripExempt(text), /script/i.test(fp) ? { skipFamilies: ['mode-leak'] } : {});
  if (hits.block.length === 0) process.exit(0);

  try {
    fs.appendFileSync(path.join(configDir, 'vestige-scan.log'),
      `${new Date().toISOString()} session=${input.session_id || '?'} write-scan file=${fp}\n  ${hits.block.join('\n  ')}\n`);
  } catch {}

  process.stderr.write(
    `VESTIGE WRITE-SCAN: ${fp} contains banned patterns.\n` +
    hits.block.map(h => '- ' + h).join('\n') +
    `\nFix these in the file now (Edit), unless the hits are verbatim quoted source material, in which case leave them and say so.`);
  process.exit(2);
}

main();
