---
name: mode-leak
description: >
  Spoken-vs-written register filter. Catches speech devices (tricolon, hook openers,
  rhetorical question plus short answer, one-line punch paragraphs, recap closers,
  announced counts) leaking into writing, and writing devices (nested clauses,
  dense numbers, back-references) leaking into scripts. Mode leak is the main
  reason readers flag text as "AI generated". Use when drafting or auditing any
  outbound piece (post, article, email, script), and as the model pass behind the
  vestige plugin's regex rules. Activates on "mode leak", "/mode-leak",
  "does this read as AI", "de-AI this", "check the register", or before any
  outbound draft ships.
user-invocable: true
---

# Mode leak

My training data mixes registers without labels: sermons, TED talks, podcast and YouTube transcripts, speeches, marketing copy, textbooks, reference docs. My output is almost always silent-read writing, but I pull devices from the live-persuade register into it. Readers now recognise that mix as the machine signature. This skill names the target register before drafting and removes the devices that don't belong in it.

Sibling to `professional-b2` (words) and `good-chad` (stance). This one targets **mode**: whether the text will be heard or read.

## Scope

- **Every draft or skeleton I write**, for any surface: run it.
- **Chat replies to the user**: cell CH.
- **The user's own text**: only when they ask for a mode-leak check. Report hits. Don't restyle their voice.
- **Scripts (SC)**: the speech devices are correct there. Check the reverse direction instead (writing devices that fail out loud).

## The grid

Two axes. Place a piece on both, and the style rules follow from that position.

**Mode**
- Live speech: one pass, no rewind, speaker controls pace, sees the room.
- Recorded speech: one pass, no room to read.
- Writing: can be re-read, reader sets the pace, no voice.

**Purpose:** perform or persuade · teach · inform or document · bond

**Cells**

| Code | Cell | Examples |
|---|---|---|
| LP | live-persuade | talk, pitch, stage |
| LT | live-teach | workshop, whiteboard session |
| RS | recorded speech | podcast, TikTok, YouTube |
| SC | script (written to be spoken) | talk script, video script |
| CH | chat | model replies, Slack, DMs, forum comments |
| WT | teach-writing | explainer, tutorial, how-to post |
| WP | persuade-writing | essay, op-ed, LinkedIn post |
| RF | reference and technical | docs, runbooks, specification pages |

**Surface to cell**
- Forum posts (Reddit and similar): WP written close to CH ("a person talking, not a keynote").
- Forum comments: CH.
- LinkedIn: WP.
- Blog and newsletter: WT or WP, depending on the piece.
- An essay arguing a case to named readers is WP, even on a research or documentation site. Auditing it as RF flags the author's voice as leaks.
- Talk and video scripts: SC.
- Procedures, error messages, runbooks, agent status output: RF. Strict ASD-STE100 fits here: one meaning per word, a verb for every action, instructions up to 20 words, descriptions up to 25, no semicolons.
- Docs and READMEs: RF or WT, "STE-flavoured": sentence discipline and no phrasal verbs, without the dictionary lock.
- Never apply STE to an author's voice layer or to WP. Its length caps conflict with long additive run-ons, so check the cell to pick the rule that applies.
- Email: CH if it's to a peer, WP if it's a pitch.

## Two questions for every cell

1. **Can the audience go back?** Speech: no, so it needs redundancy, rhythm and signposts. Writing: yes, so it needs compression, with the structure visible on the page.
2. **Who controls the pace?** In speech the speaker does, so a pause carries meaning. In writing the reader does, so a beat is dead weight.

Chat is a hybrid. The reader can go back, and feedback comes every turn. So fragments and audience checks work, and recaps don't.

## Device matrix

✓ works · ~ works under a condition (listed below) · ✗ fails · n/a doesn't apply

### Speech devices (leak into writing)

| Device | LP | LT | RS | SC | CH | WT | WP | RF |
|---|---|---|---|---|---|---|---|---|
| Tricolon, triple staccato | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ~ | ✗ |
| Rhetorical question | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ~ | ✗ |
| Announcing the count ("three things") | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ |
| Fragments | ✓ | ~ | ✓ | ✓ | ✓ | ~ | ~ | ✗ |
| Refrain, repeated opener | ✓ | ~ | ✓ | ✓ | ✗ | ✗ | ~ | ✗ |
| One-line punch paragraph | n/a | n/a | n/a | ✓ | ✓ | ✗ | ~ | ✗ |
| Recap ("so remember") | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ~ |
| Hook opener ("here's the thing") | ✓ | ~ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Audience check ("right?") | ~ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ | ✗ |
| Thinking aloud ("I mean", "kind of") | ✗ | ~ | ~ | ✗ | ✓ | ✗ | ✗ | ✗ |

### Writing devices (leak into speech)

| Device | LP | LT | RS | SC | CH | WT | WP | RF |
|---|---|---|---|---|---|---|---|---|
| Nested clauses, parentheticals | ✗ | ✗ | ✗ | ✗ | ~ | ✓ | ✓ | ✓ |
| Dense numbers, inline citations | ✗ | ~ | ✗ | ✗ | ~ | ✓ | ~ | ✓ |
| Back-references ("as noted above") | ✗ | ✗ | ✗ | ✗ | ~ | ✓ | ✓ | ✓ |
| Bullet lists read out word for word | ✗ | ~ | ✗ | ✗ | ✓ | ✓ | ~ | ✓ |
| Things as subjects ("the data shows", "this enables") | ~ | ~ | ~ | ~ | ✗ | ~ | ✗ | ✓ |
| Synonym rotation (user, customer, client for one thing) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ~ | ✗ |

### The conditions behind the ~ cells

- **Tricolon in writing:** fine when there really are three things. It fails when rhythm picked the number and the third item is filler. The reader can see the padding.
- **Rhetorical question in writing:** at most once per piece, and the answer has to be more than a two-word punch.
- **Rhetorical question in chat:** only when it's a real question to the other person.
- **Count in teach-writing:** only for long pieces, where the headers don't already show it.
- **Fragments in writing:** one for emphasis. A chain of them is the staccato tell.
- **Refrain in persuade-writing:** only when the repeated words are a phrase you want readers to quote and search engines to find.
- **Punch line in persuade-writing:** once, at the turn. A string of them is LinkedIn "broetry".
- **Recap in reference and teach-writing:** as a TL;DR at the top, or a summary at the end of a long tutorial. Never as a closer in persuade-writing.
- **Audience check in recorded speech:** fails because nobody can answer.
- **Writing devices in chat:** fine when the chat is async and gets re-read (Slack threads, PR comments).
- **Things as subjects (the agent check).** Ask who is doing the verb. "The data shows", "this enables", "the approach ensures" leave nobody acting. Put the person back: "we measured", "you can now", "I set it up so". Informational writing hides the actor this way, and the habit leaks into persuasion and chat. "The data shows" is an active verb with a thing as its subject, so it isn't a passive. Biber (1988) places agentless passives, the grammatical form of the same move, on Dimension 5 (abstract vs non-abstract information). Don't cite Biber for the active form directly. In reference writing a thing as the subject is correct when the thing really acts ("the hook runs on every reply"). In teach-writing it's fine for the system being taught and wrong for claims. Independent support: ASD-STE100 rule 3.7 ("use an approved verb to describe an action").
- **Abstract nouns don't act (personification).** In my drafts an abstract noun never takes a human or physical verb: no "the work sits", "the complaint feeds", "the question survives", "the thesis lives". A person, a model or a tool does the verb. This is the agent check's sibling. The agent check catches nobody acting ("the data shows"), and this one catches an abstraction acting like a person. Readers flag it as a fine-tuning tell. Borrowed idioms from third parties stay inside quote marks with attribution, and are never promoted to headings or used in the draft's own voice. An author who likes personification adds it in their own pass. It never goes into my draft.
- **Synonym rotation (one name per thing).** School writing teaches people to avoid repeating a word, and Fowler called the result "elegant variation" (*Modern English Usage*, 1926). Models do it constantly: the user, the customer and the client in one paragraph, all meaning the same person. The reader has to work out whether they are three things. Pick one name per thing and keep it. In persuade-writing a second word is allowed when it adds meaning ("the customer, who pays"), and never just for variety. It also helps search: readers and search engines find the term that is repeated word for word. Source: the ASD-STE100 one-meaning-per-word principle.

## My leak list, ranked by how often it fires

1. Hook opener ("Here's the thing", "Let's dive in", "Picture this")
2. Tricolon, especially adjective triplets and three-beat closers
3. Rhetorical question plus short answer ("The result? Chaos.")
4. One-line punch paragraph after a long one
5. Recap closer ("In short", "The takeaway")
6. Announcing the count ("Three things matter here.")

## Uniformity: the second tell

Readers flag the sameness as well as the devices. Check for these:
- Every list has three items.
- Every section ends on a punch line.
- Every paragraph has the same shape (claim, elaboration, landing line).
- Sentence lengths pile up at the short end (keynote), or the long sentences are all built the same way: stacked subordinate clauses (the overcorrection).
- Headers all follow one template.

Fix it by varying on purpose. Let a list have two or five items when the content does. Let a section end on the plain last fact. Mix one long sentence into a run of short ones.

Don't rely on the spread of sentence lengths. In the author's measurements, keynote-style drafts and approved final text had the same relative spread. Keynote leaks show up as devices, and the length numbers stay normal. Length alone does not mark the overcorrection either. How the long sentences are built does (see the run-on shape test below).

## Voice layer: writing in a named author's voice

A voice is a speaker profile. Linguists call it an idiolect. Apply it on top of the cell, and keep the cell's rules. It applies when a named person is the author: their posts, their articles. Their own posted text is the ground truth. Read samples of it before drafting.

**Why a real voice doesn't count as a leak.** A leak is a stock speech device dropped into writing without the pause that made it work. A human voice usually brings speech into writing with specific material: punctuation that carries the delivery (an ellipsis for a comic pause, caps or italics for stress, parentheses for an aside), coinages, references, jokes, real typos. Working hypothesis: stock speech devices read as AI, and speech devices carrying specific material read as a person.

**What I can build in someone's voice, and what is theirs to add:**
- **I build:** sentence shape, openers, direct "you", a concrete scene as the opener, one thinking-aloud qualifier, one punch line at the turn, parentheses.
- **I never fabricate:** typos, coinages, pop-culture jokes, emoticons, caps for stress, ellipsis timing, analogies, personification. Those belong to the author, and they add them in their own pass.

**Run-on shape test.** Some authors write long, breathless sentences on purpose. Their long sentences add clauses in the order they would say them: and, but, so, commas, a self-interruption partway through, a loose landing. My long sentences nest one clause inside another: which, that, where, because, if. This is Ong's contrast between additive (spoken) and subordinative (written) style, and you can count it. For sentences of 25 words or more, compare the count of and/but/so/or/then with the count of which/that/where/because/while/when/if. If the author's ratio is clearly higher than the draft's, rebuild the nested sentences: cut "which" and "where" chains into "and" or "so" chains, or into two sentences. Keep the long sentences.

**The two ways a draft in someone's voice fails:**
1. **Keynote fragments.** This is the default leak.
2. **Written-style long sentences.** This is the overcorrection: the long sentences nest subordinate clauses, often with extra qualifiers and an announced count.

A pass that only removes devices goes from 1 to 2. The fix is the run-on shape test.

## Procedure

Order matters: structure first, devices second, the phrase list last. External evidence: chele.bi (2026, "The cure for AI slop is a 1986 aircraft manual", 6 developer writing tasks, the author's own linter). On Claude Sonnet a banned-words list cut mechanical slop by 3% and a full ASD-STE100 writing system cut it by 74%. On GPT-5.5 the banned list cut it by 40% and roughly tied STE (50%). A writing system beat or matched the word list on both models, and the Claude number is the extreme case. Fixing the phrases first removes the obvious tics and leaves a text that still reads like a talk.

1. **Name the cell** before drafting, using the surface map. If the surface is unclear, pick the most likely cell and state it in one line.
2. **Draft.**
3. **Structure pass.** Check the sentence build: additive or nested (the run-on shape test), whether a person is doing the verbs (the agent check), no abstract noun doing a human verb (personification), one name per thing (no synonym rotation), and uniformity across the piece.
4. **Device pass.** Go down the cell's column in the matrix. Remove every ✗ device and check every ~ device against its condition.
5. **Mechanical slice.** If the `vestige` plugin from the same marketplace is installed, write the draft to a scratch file and run its `hooks/vestige-batch.js --warn <file>` (the plugin sits under `~/.claude/plugins/cache/`). For scripts, add `--script` so the speech-device rules don't fire.
6. Ship. When the draft goes to its author for a voice pass, the hit list goes with it.

## Audit mode

`/mode-leak <file or pasted text> [cell]`: read-only report. Give the cell (stated or inferred), then the hits grouped by device with line, quote and fix, then the uniformity notes. Write the totals only after the hit list is finished. With `--rewrite`, also return a corrected version. Never use `--rewrite` on the user's own text unless they ask for it.

## Mechanical slice

The `vestige` plugin's rule table ships one rule from this family: `hook-opener` (BLOCK), stock hook phrases at the start of a sentence or line. A phrase quoted inside a sentence is exempt. Its write scan skips the family for paths that contain `script`.

Candidates for your own table, if `/vestige:calibrate` confirms them for you:
- `q-short-answer` (WARN): a question of up to 8 words followed by an answer of up to 5 words.
- `personification` (BLOCK once tested): a determiner, an abstract noun (work, complaint, question, thesis, evidence...) and a human or physical verb (sits, feeds, survives, wears, lives, hides...). Exempt a quote mark right before it. Leave out "fed" ("the data fed into the model" is a reduced relative clause) and bare "live" ("the data live in S3" is standard).
- `thing-as-subject` (WARN): "this", "that" or "the data/approach/framework..." followed by shows, enables, ensures, allows and similar verbs, at the start of a sentence. Legitimate in reference writing, so keep it at WARN.
- `recap-closer` (WARN): a line that opens with "in short", "in summary", "to sum up", "the takeaway" or "so remember".

Tricolons, punch paragraphs and uniformity are too noisy for regex. They stay in the model pass. Move a WARN rule to BLOCK once the hit log shows it running clean.

## Sources

- Walter Ong, *Orality and Literacy* (1982), the phrase "additive rather than subordinative": spoken style is additive and redundant because a listener can't go back.
- Douglas Biber, *Variation across Speech and Writing* (Cambridge University Press, 1988): the strongest dimension across real texts is involved vs informational, and it tracks mode.
- Martin Joos, *The Five Clocks* (1961 or 1962; sources differ): the formality axis (frozen, formal, consultative, casual, intimate).
- M.A.K. Halliday: register as field, tenor and mode.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/stance" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/stance/` exists, read its `README.md` first, then the files in `stance/mode-leak/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
