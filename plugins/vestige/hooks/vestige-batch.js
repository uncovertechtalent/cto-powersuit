#!/usr/bin/env node
'use strict';
// vestige-batch — CLI scanner over files/dirs against your vestige-patterns
// rule table. Same rules as the Stop hook, two more surfaces:
//
//   1. Corpus audit: `node vestige-batch.js <path...>` walks every .md under
//      the paths, reports per-file block hits, exits 1 if any. Run it over a
//      notes vault or a manuscript to catch what per-reply scanning never sees.
//   2. In-loop pre-emit gate: have the model write a candidate draft to a
//      scratch file, run this on it, fix the reported hits, re-run until
//      clean, THEN emit. Moves the check from after generation (Stop hook,
//      full re-send) to before (cheap in-draft fix). Keep the Stop hook as
//      the backstop: an instruction to pre-lint degrades over a long session;
//      the hook does not.
//
// Flags:
//   --warn      include WARN-tier hits in the report (default: block only)
//   --quiet     print only files with hits (default: also prints a clean line)
//   --json      machine-readable output for programmatic loops
//   --script    skip the mode-leak family (drafts written to be spoken)
//
// Exit: 1 if any block-tier hit across all inputs, else 0.

const fs = require('fs');
const path = require('path');
const { loadPatterns } = require('./config-dir');
const { stripExempt, scan } = loadPatterns();

const args = process.argv.slice(2);
const flags = new Set(args.filter(a => a.startsWith('--')));
const inputs = args.filter(a => !a.startsWith('--'));
const showWarn = flags.has('--warn');
const quiet = flags.has('--quiet');
const asJson = flags.has('--json');
const scanOpts = flags.has('--script') ? { skipFamilies: ['mode-leak'] } : {};

if (inputs.length === 0) {
  process.stderr.write('usage: vestige-batch.js [--warn] [--quiet] [--json] [--script] <file-or-dir>...\n');
  process.exit(2);
}

function collect(p, out) {
  let st;
  try { st = fs.statSync(p); } catch { process.stderr.write(`skip (not found): ${p}\n`); return; }
  if (st.isDirectory()) {
    for (const name of fs.readdirSync(p)) {
      if (name.startsWith('.')) continue; // skip .git, .obsidian, dotfiles
      collect(path.join(p, name), out);
    }
  } else if (st.isFile() && p.endsWith('.md')) {
    out.push(p);
  }
}

const files = [];
for (const p of inputs) collect(p, files);
files.sort();

const results = [];
let totalBlock = 0;
for (const f of files) {
  let text;
  try { text = fs.readFileSync(f, 'utf8'); } catch { continue; }
  const hits = scan(stripExempt(text), scanOpts);
  const block = hits.block.length;
  const warn = hits.warn.length;
  totalBlock += block;
  if (block > 0 || (showWarn && warn > 0)) {
    results.push({ file: f, block: hits.block, warn: hits.warn });
  } else if (!quiet) {
    results.push({ file: f, block: [], warn: [] });
  }
}

if (asJson) {
  process.stdout.write(JSON.stringify({ scanned: files.length, totalBlock, results }, null, 2) + '\n');
} else {
  for (const r of results) {
    if (r.block.length === 0 && r.warn.length === 0) {
      process.stdout.write(`clean  ${r.file}\n`);
      continue;
    }
    process.stdout.write(`HITS   ${r.file}\n`);
    for (const h of r.block) process.stdout.write(`         block: ${h}\n`);
    if (showWarn) for (const h of r.warn) process.stdout.write(`         warn:  ${h}\n`);
  }
  process.stdout.write(`\nscanned ${files.length} file(s), ${totalBlock} block-tier hit(s)\n`);
}

process.exitCode = totalBlock > 0 ? 1 : 0; // exitCode, not exit(): exit() truncates large piped stdout
