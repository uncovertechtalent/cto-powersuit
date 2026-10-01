'use strict';
// vestige-patterns — single source of truth for the mechanical catalog scan.
// Consumed by vestige-scan.js (Stop hook). Edit here; the hook picks it up.
//
// /calibrate regenerates this file from your confirmed catalog. Hand-edits
// are fine too; keep the exported interface intact.

// BLOCK tier: near-zero false positives ONLY. The hook rejects the reply and
// demands a corrected resend. A rule that misfires on legitimate text does not
// belong here; demote it to WARN_RULES until its regex is tight.
const BLOCK_RULES = [
  { name: 'praise-opener', re: /\b(great|good|excellent|fair|interesting) (question|point|catch|idea|observation)\b/gi, fix: 'delete the praise, start with the substance' },
  { name: 'service-closer', re: /\b(let me know if|feel free to|happy to help|hope (this|that) helps|don't hesitate to)\b/gi, fix: 'delete; stop after the substance' },
  { name: 'filler-idiom', re: /\b(at the end of the day|the bottom line is|needless to say)\b/gi, fix: 'delete filler' },

  // Mode-leak family: stage devices from live speech in text that is read
  // silently. The pattern is anchored to the start of a sentence or line, so a
  // quoted mention ("Here's the thing" inside a sentence) does not fire. Scripts
  // written to be spoken use these on purpose: callers skip the family there
  // (vestige-write-scan.js on paths containing "script", vestige-batch.js --script).
  // False-positive test: 0 hits across 1,282 markdown files of the author's vault.
  { name: 'hook-opener', family: 'mode-leak', re: new RegExp(String.raw`(?:^|[.!?]\s+)[ \t]*(?:[-*+]\s+|\d+\.\s+|#+\s+)?(?:\*\*|_)?(?:here'?s the (?:thing|kicker|catch|twist)|let'?s (?:dive|jump) in|let'?s break (?:it|this) down|picture this|imagine this:|buckle up|spoiler(?: alert)?:|but wait)`, 'gim'), fix: 'stage hook in written text: delete it and open on the substance' },

  // Personal-taste examples, disabled by default. Enable if they match YOUR
  // calibration (see CALIBRATION.md step 3 for the false-positive test):
  // { name: 'em-dash', re: /—/g, fix: 'no em dashes in prose; use a period or comma' },
  // { name: 'performative-uncertainty', re: /\b(i might be wrong,? but|this is just my (view|opinion|take))\b/gi, fix: 'calibrate confidence in the claim sentence instead' },
];

// WARN tier: usually bad, sometimes legitimate. Warns are reported alongside a
// block and logged always; the log is the promotion dataset (a rule that runs
// clean for weeks moves up to BLOCK; one that keeps hitting legitimate text
// gets rewritten or dropped).
const WARN_RULES = [
  // { name: 'not-x-but-y', re: /\bnot (just |only |merely )?[a-z][^.!?\n]{0,40}, but\b/gi, fix: 'rewrite without the contrast construction' },
];

// Strip code and quoted text before scanning — exempt per filter boundaries.
function stripExempt(text) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')      // fenced code
    .replace(/`[^`\n]*`/g, ' ')            // inline code
    .split('\n').filter(l => !/^\s*>/.test(l)).join('\n'); // quoted lines
}

// opts.skipFamilies: rule families to skip, e.g. ['mode-leak'] for scripts.
function scan(text, opts = {}) {
  const skip = new Set(opts.skipFamilies || []);
  const hits = { block: [], warn: [] };
  for (const r of BLOCK_RULES) {
    if (r.family && skip.has(r.family)) continue;
    const m = text.match(r.re);
    if (m) hits.block.push(`${r.name} x${m.length} ("${String(m[0]).slice(0, 40)}") -> ${r.fix}`);
  }
  for (const r of WARN_RULES) {
    if (r.family && skip.has(r.family)) continue;
    const m = text.match(r.re);
    if (m) hits.warn.push(`${r.name} x${m.length} ("${String(m[0]).slice(0, 40)}") -> ${r.fix}`);
  }
  return hits;
}

module.exports = { BLOCK_RULES, WARN_RULES, stripExempt, scan };
