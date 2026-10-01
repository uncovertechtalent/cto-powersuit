#!/usr/bin/env node
// guess-scan — Stop hook. Deterministic verification of checkable references
// in the last assistant message: the rung-1 guess gate.
//
// Rationale: hallucinated references (paths, commands, usernames) are not a
// capability failure, they are trained suppression of an available uncertainty
// signal: approval training rewards an answer-shaped answer over an abstention.
// You cannot prompt that away, but a reference class with a ground truth can
// be checked mechanically. This hook checks what is checkable and bounces the
// reply until every failed reference is corrected or labelled unverified.
//
// What it checks (v1, local ground truth only, near-zero false positives):
//   - Absolute and ~ file paths      -> existence on this filesystem
//   - `command ...` in prose         -> binary resolvable on PATH (opt-in)
//   - @usernames / u/usernames       -> membership in a roster file (opt-in)
// Placeholders (/path/to, foo, your-*, <angle>, $VARS, ...) are exempt, as is
// anything inside quoted (>) lines. Paths the reply itself marks as planned,
// proposed, to-be-created, or unverified are exempt: the gate forces the
// label, not omniscience.
//
// Optional config at ~/.claude/guess-gate.json:
//   { "roster": ["stefan", "..."], "checkCommands": true }
//
// Log: ~/.claude/guess-scan.log — every hit, timestamped. The log is the
// dataset: after a month you know your model's reference-guess base rate.

'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');
const { configDir } = require('./config-dir');

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

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(path.join(configDir, 'guess-gate.json'), 'utf8'));
  } catch { return {}; }
}

// Placeholder shapes: illustrative, not claims. Never flag these.
const PLACEHOLDER = /(\/path\/to|\byour[-_]|\bexample\b|\bfoo\b|\bbar\b|<[^>]+>|\{\{?[^}]*\}\}?|\$[A-Z_]+|\bplaceholder\b|\bsome[-_])/i;
// Exemption labels: the reply already carries the uncertainty. The gate's job
// is to force one of these, so their presence near a reference clears it.
const LABELLED = /(unverified|not verified|planned|proposed|to be created|will create|hypothetical|does not exist yet|example only)/i;

function stripQuoted(text) {
  // fenced code, inline code, and quoted (>) lines are exempt: test commands,
  // hypothetical examples and quoted speech name paths without asserting them
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`\n]*`/g, ' ')
    .replace(/"[^"\n]{0,120}"/g, ' ')
    .split('\n').filter(l => !/^\s*>/.test(l)).join('\n');
}

function sentences(text) {
  // sentence = the exemption scope: a label clears only references it shares a
  // sentence (or list line) with. Newlines end sentences too.
  return text.split(/(?<=[.!?])\s+|\n/);
}

function checkPaths(text, hits) {
  const re = /(?:^|[\s("'`])((?:~|\/)[A-Za-z0-9._\-/]{3,})/gm;
  const seen = new Set();
  for (const sent of sentences(text)) {
    if (LABELLED.test(sent)) continue;
    let m;
    while ((m = re.exec(sent)) !== null) {
      let p = m[1].replace(/[.,;:)\]'"`]+$/, '');
      if (seen.has(p) || PLACEHOLDER.test(p)) continue;
      seen.add(p);
      const expanded = p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p;
      // only judge paths under home or /tmp: elsewhere existence is not our ground truth
      if (!expanded.startsWith(os.homedir()) && !expanded.startsWith('/tmp') && !expanded.startsWith('/private/tmp')) continue;
      if (!fs.existsSync(expanded)) hits.push(`path-not-found: ${p} -> correct it, or label it (planned / unverified)`);
    }
  }
}

function checkCommands(text, hits) {
  const re = /`([a-z][a-z0-9._+-]{1,30})(?: [^`]*)?`/g;
  let m;
  const seen = new Set();
  while ((m = re.exec(text)) !== null) {
    const cmd = m[1];
    if (seen.has(cmd)) continue;
    seen.add(cmd);
    try { execFileSync('which', [cmd], { stdio: 'ignore' }); }
    catch { hits.push(`command-not-on-path: \`${cmd}\` -> correct it, or label it unverified`); }
  }
}

function checkUsernames(text, roster, hits) {
  const re = /(?:^|\s)(?:@|u\/)([A-Za-z0-9_\-.]{2,30})/gm;
  let m;
  const seen = new Set();
  const known = new Set(roster.map(r => r.toLowerCase()));
  while ((m = re.exec(text)) !== null) {
    const u = m[1];
    if (seen.has(u)) continue;
    seen.add(u);
    if (!known.has(u.toLowerCase())) hits.push(`username-not-in-roster: ${u} -> only name accounts present in the conversation or roster; otherwise describe, don't name`);
  }
}

function main() {
  let input = {};
  try { input = JSON.parse(readStdin() || '{}'); } catch {}
  if (input.stop_hook_active) process.exit(0); // one correction pass max
  const text = input.transcript_path ? lastAssistantText(input.transcript_path) : null;
  if (!text) process.exit(0);
  const cfg = loadConfig();
  const proseText = stripQuoted(text); // code/quotes exempt for path + username checks
  const hits = [];
  checkPaths(proseText, hits);
  // commands are extracted FROM inline backticks, so they scan the raw text
  // (minus fenced blocks, which are transcripts/scripts rather than claims)
  if (cfg.checkCommands) checkCommands(text.replace(/```[\s\S]*?```/g, ' '), hits);
  if (Array.isArray(cfg.roster) && cfg.roster.length > 0) checkUsernames(proseText, hits);

  if (hits.length > 0) {
    try {
      fs.appendFileSync(path.join(configDir, 'guess-scan.log'),
        `${new Date().toISOString()} session=${input.session_id || '?'}\n  ${hits.join('\n  ')}\n`);
    } catch {}
    process.stdout.write(JSON.stringify({
      decision: 'block',
      reason: `GUESS SCAN (mechanical, reference verification): last reply contains unverifiable references.\n${hits.map(h => '- ' + h).join('\n')}\nFor each: correct the reference against ground truth, or keep it with an explicit label (unverified / planned / hypothetical). Do not delete the claim to dodge the check; label it. Do not narrate the correction.`,
    }));
    return;
  }
  process.exit(0);
}

main();
