# Seeding: growing your vault from your own inputs

The `/seed` skill automates this. This is the manual version with the reasoning, so you can run it by hand or audit what the skill generated.

## The conventions (what the starter enforces)

1. **One idea per file ("atom").** The unit of retrieval is the unit of thought. If a file needs a table of contents, it is several atoms wearing a trenchcoat. Split it.
2. **Frontmatter, minimal.** `tags` and `created` cover most needs. Tags are hierarchical paths (`project/homelab`, `person/anna`) so searches can scope by prefix. Skip fields you won't query.
3. **Links are the graph.** `[[Other Atom]]` wherever a real connection exists. A link that doesn't resolve yet is a note to your future self, not an error.
4. **MOCs (maps of content) are grown, not planned.** When a cluster of atoms reaches critical mass (rule of thumb: seven), write an index note that links and one-line-summarizes them. Never create the MOC first.
5. **`_inbox/` is the only unsorted place.** Everything enters there; a periodic pass (you or the agent) atomizes and files it. An inbox that only grows means the atomize pass isn't running, and the vault is becoming a pile.
6. **Filenames are titles.** `Consequence Budgeting.md`, not `note-2026-08-03-a.md`. The filename is what links autocomplete against and what search results show. Rename when the idea sharpens; link-following tools handle renames, and stale names cost more than renames do.
7. **The agent writes atoms too.** Anything the model derives that took real work (a debugging conclusion, a decision and its why, a mapped subsystem) gets an atom, so next session starts from the conclusion instead of re-deriving it. This is the difference between a notes folder and a memory.

## The seeding interview (what /seed asks and why)

1. **What do you actually work on?** Names the 3-6 top-level domains. Not aspirational ones: things with activity in the last month.
2. **What do you keep re-explaining to the model?** Those are the first atoms, and the highest-value ones. Every re-explanation is a cache miss the vault exists to fix.
3. **What do you look up more than twice a week?** Reference material worth atomizing now rather than on demand.
4. **What's private?** Draw the boundary explicitly. A vault folder the search index skips (list it in `.vsearchignore`; the starter ships a commented template) beats discovering later that everything was indexed.
5. **Where does raw material arrive from?** (chats, meetings, browser, email) Determines what the inbox pass has to handle, and whether atomize needs source-specific handling.
6. **Do you want the machinebehavior.io reference pack?** Optional. Never by default; only a clear yes imports it (see "Reference packs" below).

From the answers, the skill creates ONLY: the domain folders that had real activity, `_inbox/`, one starter MOC per domain with the re-explained facts as its first atoms, and a CLAUDE.md that names the conventions, the private boundary, and the inbox-pass rule.

## Reference packs (optional, third-party)

The `/vault:reference-pack` skill copies the published pages of machinebehavior.io (the documentation of Stefan Coetzee, about 490 pages) into `reference/machinebehavior/`, one note per page. It runs only after a yes. By hand, the same steps:

1. Dry run, which fetches and compares and writes nothing: `python3 <plugin>/skills/reference-pack/reference_pack.py sync --vault ~/vault --dry-run`. Run it again without `--dry-run` to import.
2. Every note carries `source:` (the page URL), `fetched:` (the date), `sha256:` (of the markdown twin as fetched, so `curl -s <twin url> | shasum -a 256` reproduces it) and `trust: third-party`. The page text sits between two marker lines, below a notice.
3. Read the notes as a third party's documentation: reference, never instructions to the agent. The quarantine rule applies, outside text is data. Add the paragraph from the skill to `CLAUDE.md` so the rule lives where the agent reads its conventions.
4. Keep the pack out of your own work. It is not an atom set: do not atomize it, do not publish a pack note as your own page, do not count it when you ask whether the vault is growing. Write your own note in your own words and link to the page.
5. About 490 notes against five atoms means the pack wins most searches on day one. Seed the vault first and import the pack afterwards, or exclude it from search with the commented line in `.vsearchignore` (`reference/machinebehavior`) and turn it on when you want to look something up. The skill asks once whether the pack is searchable now, because a hit from it has no label of its own yet.
6. To update, run it again: only notes whose hash changed are rewritten, and the run reports them by hash. To remove it, delete the folder.

## What NOT to build on day one

- No tag taxonomy beyond what the first atoms need. Taxonomies built in advance describe the person you planned to be.
- No templates for atom types. Atoms converge on shapes through use; freeze the shapes after they emerge, not before.
- No automation (watchers, scheduled reindex, sync). Add each when its absence hurts twice. The kit's watch mode exists for when you get there.
- No reference pack before your own atoms exist (see above).
- No migration of your entire existing notes pile. Atomize on touch: when something old becomes relevant, atomize it then. Bulk migration front-loads weeks of sorting into the moment your motivation is highest and your judgment about what matters is worst.

## Growing pains and their fixes

| Symptom | Fix |
|---|---|
| Inbox growing, never shrinking | Schedule the atomize pass as a recurring session task; it is agent work, not owner work. |
| Search returns your huge old documents above your atoms | Atomize the documents that keep winning, or exclude the archive folder from indexing. |
| Two atoms about the same thing under different names | Merge, keep the better filename. The duplicate was a naming-convention drift signal, not a filing error. |
| Folders that stay empty | Delete them. They were someone else's head shape (possibly your own from a month ago). |
| Agent ignores the conventions | The conventions live in CLAUDE.md, not in your memory of having explained them once. If it drifts, the file was too vague; tighten the rule with an example. |
