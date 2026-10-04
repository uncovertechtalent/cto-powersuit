# man pages status

DONE

Date: 2026-10-04
Bead: vault-l6fd.10 (left open: packaging and tap)
Source: machinebehavior.io/man (live copy at ~/code/machinebehavior.io/man.html, published 2026-10-03)
Check: `mandoc -T lint` gives no errors and no warnings on any page; `mandoc -T utf8` renders every page.
The only lint output is the STYLE note "referenced manual not found" for cross-references, because the pages are not installed.

## Final page list

- man1/stance.1
- man1/register.1
- man5/trap-file.5
- man5/instruction-file.5
- man5/llms.txt.5
- man5/lesson.5
- man7/llm-intro.7
- man7/knowledge-infrastructure.7
- man7/codec.7
- man7/golem.7
- man7/claudish.7
- man7/compaction.7
- man7/llm-user.7
- man8/operations.8
- man8/engine.8
- man8/track.8
- man8/chaos.8
- man8/toil.8

Also: README.md, homebrew/llm-man.rb.draft

## Open

- Page names follow the hub (golem, trap-file, chaos). The series plan names llm-golem(7), trapfile(5), llm-chaos(8). Only llm-intro(7) carries the prefix, because intro(7) exists on most systems.
- The hub entry cheating-moved has no section number. It is in EXAMPLES of llm-intro(7) and has no page of its own.
- Unprefixed names (stance, register, engine, track, operations) may collide with other packages once installed.
- Formula url, sha256 and version are TODO.
