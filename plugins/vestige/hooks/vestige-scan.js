#!/usr/bin/env node
// vestige-scan — Stop hook. Mechanical scan of the last assistant message
// against the regex-safe slice of your vestige catalog.
//
// Rationale: prose instructions (a skill asking the model to behave) degrade
// over long sessions; a regex that runs on every Stop does not. This automates
// the lexical slice of the checking so you are not the only check.
//
// Behaviour:
//   - Reads transcript_path from stdin JSON, extracts the last assistant
//     message's text blocks.
//   - Strips fenced code, inline code, and quoted (>) lines before scanning.
//   - BLOCK tier hits reject the reply once with a fix list (stop_hook_active
//     guards against loops: one correction pass max).
//   - WARN tier hits ride along with a block, never block alone.
//   - Appends every hit to ~/.claude/vestige-scan.log — your promotion dataset.

'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const { configDir, loadPatterns } = require('./config-dir');
const { stripExempt, scan } = loadPatterns();

function readStdin() {
  try { return fs.readFileSync(0, 'utf8'); } catch { return ''; }
}

function lastAssistantText(transcriptPath) {
  let raw;
  try { raw = fs.readFileSync(transcriptPath, 'utf8'); } catch { return null; }
  const lines = raw.split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (!line) continue;
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    if (obj.type !== 'assistant' || !obj.message || !Array.isArray(obj.message.content)) continue;
    const texts = obj.message.content
      .filter(b => b.type === 'text' && typeof b.text === 'string')
      .map(b => b.text);
    if (texts.length === 0) continue;
    return texts.join('\n');
  }
  return null;
}

function main() {
  let input = {};
  try { input = JSON.parse(readStdin() || '{}'); } catch {}
  if (input.stop_hook_active) process.exit(0); // one correction pass max, no loops
  const text = input.transcript_path ? lastAssistantText(input.transcript_path) : null;
  if (!text) process.exit(0);
  const hits = scan(stripExempt(text));
  const all = [...hits.block, ...hits.warn];
  if (all.length > 0) {
    try {
      fs.appendFileSync(path.join(configDir, 'vestige-scan.log'),
        `${new Date().toISOString()} session=${input.session_id || '?'} blocked=${hits.block.length > 0}\n  ${all.join('\n  ')}\n`);
    } catch {}
  }
  if (hits.block.length === 0) process.exit(0);

  process.stdout.write(JSON.stringify({
    decision: 'block',
    reason: `VESTIGE SCAN (mechanical, catalog): last reply contains banned patterns.\n${all.map(h => '- ' + h).join('\n')}\nRe-send the reply with these fixed. Do not apologise or narrate the correction; just deliver the corrected content.`,
  }));
}

main();
