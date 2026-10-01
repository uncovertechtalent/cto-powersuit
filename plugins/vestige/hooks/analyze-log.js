#!/usr/bin/env node
// analyze-log — summarize ~/.claude/vestige-scan.log into actionable counts.
//
// Reports per rule: total hits, blocked vs warn-only occurrences, first/last
// seen. Interpretation guide printed with the numbers:
//   - High hit count on a BLOCK rule: the skill prose isn't holding that
//     pattern; the hook is earning its keep (or the rule over-fires — check
//     samples).
//   - Zero hits for weeks: candidate for retirement (base model improved, or
//     the rule is too narrow to matter).
//   - WARN rules with a long clean streak: promotion candidates to BLOCK.
//
// Usage: node analyze-log.js [path-to-log]   (default ~/.claude/vestige-scan.log)

'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const { configDir } = require('./config-dir');
const logPath = process.argv[2] || path.join(configDir, 'vestige-scan.log');
let raw;
try { raw = fs.readFileSync(logPath, 'utf8'); } catch {
  console.error(`no log at ${logPath} — either the hook isn't wired or nothing has ever fired (which is the goal).`);
  process.exit(0);
}

const rules = new Map(); // name -> {hits, blockedEntries, first, last}
let entries = 0, blockedEntries = 0;
let currentTs = null, currentBlocked = false;

for (const line of raw.split('\n')) {
  const head = line.match(/^(\d{4}-\d{2}-\d{2}T[\d:.]+Z) session=\S* blocked=(true|false)/);
  if (head) {
    entries++;
    currentTs = head[1];
    currentBlocked = head[2] === 'true';
    if (currentBlocked) blockedEntries++;
    continue;
  }
  const hit = line.match(/^\s+([a-z0-9-]+) x(\d+) /);
  if (hit && currentTs) {
    const [, name, countStr] = hit;
    const r = rules.get(name) || { hits: 0, blockedEntries: 0, first: currentTs, last: currentTs };
    r.hits += parseInt(countStr, 10);
    if (currentBlocked) r.blockedEntries++;
    r.last = currentTs;
    rules.set(name, r);
  }
}

console.log(`log: ${logPath}`);
console.log(`entries: ${entries} (${blockedEntries} blocked, ${entries - blockedEntries} warn-only)\n`);
const sorted = [...rules.entries()].sort((a, b) => b[1].hits - a[1].hits);
if (sorted.length === 0) { console.log('no rule hits recorded.'); process.exit(0); }
console.log('rule                        hits  in-blocked  first-seen    last-seen');
for (const [name, r] of sorted) {
  console.log(
    name.padEnd(26),
    String(r.hits).padStart(5),
    String(r.blockedEntries).padStart(10),
    ' ', r.first.slice(0, 10), '  ', r.last.slice(0, 10)
  );
}
console.log('\ntop rules: skill prose not holding those patterns (hook earning its keep) — or over-firing; check samples.');
console.log('zero-hit rules over weeks: retirement candidates. clean WARN streaks: promote to BLOCK.');
