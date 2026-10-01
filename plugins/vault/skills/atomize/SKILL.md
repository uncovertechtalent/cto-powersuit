---
name: atomize
description: >
  Turn a document, chat log, braindump, or the _inbox into linked one-idea
  atoms plus index links, following the vault's conventions. Activates on
  "/atomize", "atomize this", "sweep the inbox", "file this into the vault".
user-invocable: true
---

# Atomize

Input: a file path, pasted text, or (no argument) the vault's `_inbox/`. Output: atoms filed in domain folders, links between them, source handled.

## Procedure

1. **Read the vault's CLAUDE.md first.** Its conventions, folder list, and private boundary override anything here.
2. **Extract ideas, not sections.** An atom is one claim, decision, fact-cluster, or reusable reference, stated in its first line. Headings in the source are formatting, not atom boundaries; a single section can hold three ideas and three sections can hold one.
3. **Search before creating.** For each candidate atom, run `vault_search` for existing coverage. Update or extend an existing atom rather than writing a near-duplicate. Genuinely new ones get new files.
4. **Name for the future reader.** Filename = the idea, sentence-cased. Not the source ("Meeting 2026-08-03 part 2"), the content ("Vendor X owns the schema migration").
5. **Link as you go.** Atoms from the same source usually relate; link them. Also link into existing atoms surfaced by the searches in step 3. Unresolved links to atoms worth writing later are encouraged.
6. **Handle the source.** Inbox items: delete after atomization (their content now lives in atoms). External files: leave in place, add a one-line pointer at the top of the source noting it was atomized and where, if the file will be seen again.
7. **Update MOCs.** If a domain crossed the ~7-atom threshold, create its `_MOC.md`; if a MOC exists, add the new atoms with one-line summaries.
8. **Reindex and report.** Run `vault_reindex`, then report: atoms created (with paths), atoms updated, links added, inbox items cleared. Counts come from the finished work, not the plan.

## Judgment calls

- Boring operational text (logistics, scheduling) usually doesn't earn atoms. When most of a source is noise, say so and extract the two things that weren't.
- Long verbatim material worth keeping (a quoted email, a spec) can live as an atom-with-a-body; the first line still states why it's kept.
- Anything touching the CLAUDE.md private boundary: file it inside the boundary and never quote it outside the vault.
