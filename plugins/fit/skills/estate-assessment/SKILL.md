---
name: estate-assessment
description: >
  Assess a repository and its docs, build on the ranked gap list of the sdlc
  audit, and recommend which modules of the suit to fit, in which order and
  why, with the first skill, the effort class, the dependencies and an owner
  per module, written to docs/fit.md. Use when a team or an incoming CTO wants
  a fitting plan for an existing estate, or wants to know which modules are
  already fitted. Activates on "/estate-assessment", "which modules do we
  need", "assess our estate", "fitting plan", "where should the suit start".
user-invocable: true
---

# Estate assessment

Reads one repository and its docs and turns the sdlc audit into a fitting plan: for every module of the suit, one recommendation (`fit now`, `fit later`, `not needed` or `fitted`), the reason, the first step, the effort class and the owner, in an order that respects the dependencies between modules.

The skill is read only. The one file it writes is `docs/fit.md`.

## Inputs

- The repository root (default: the current directory) and its docs.
- The ranked gap list of `/sdlc:sdlc-audit`, from this run.
- From the user: goals with dates (a customer audit, a certification, a launch, a hire, a handover date), the people who can own a module, AI features in the product, and whether the repository serves a public site.

## Steps

1. **Run the sdlc audit first:** `/sdlc:sdlc-audit`. If the sdlc plugin is not installed, look for its copy next to this plugin and follow the audit steps from there:

   ```bash
   find "${CLAUDE_PLUGIN_ROOT}/../.." -maxdepth 5 -path "*/skills/sdlc-audit/SKILL.md" 2>/dev/null | head -1
   ```

   If nothing prints, ask the user to install it (`claude plugin install sdlc@cto-powersuit`) or for the path. Give the audit the repository's purpose (`users`, `grader` or `nothing`) and the user's commit author; its ranking depends on both. Keep the audit's ranked gap list, its history basis and its evidence. Modules for stages the audit marks out of scope go to "not needed" with that reason.
2. **Find the fitted modules.** The signal table is in `${CLAUDE_PLUGIN_ROOT}/templates/docs/fit.md`, section "Module signals". Test each signal in the repository:

   ```bash
   python3 - "${CLAUDE_PLUGIN_ROOT}/templates/docs/fit.md" <<'EOF'
   import re, sys
   from pathlib import Path
   table = Path(sys.argv[1]).read_text().split("## Module signals", 1)[1]
   for line in table.splitlines():
       cells = [c.strip() for c in line.strip().strip("|").split("|")]
       if not line.startswith("|") or len(cells) != 2 or cells[0] in ("Module", "---"):
           continue
       found = [str(p) for g in re.findall(r"`([^`]+)`", cells[1]) for p in sorted(Path(".").glob(g))
                if p.is_file() and not any(s.startswith("_") for s in p.parts)]
       print(f"{cells[0]:<14} {'present' if found else 'absent':<8} {', '.join(found[:3])}")
   EOF
   ```

   A present signal shows that the module's files are there. Check that they are in use (filled, current, run in CI) before you mark the module `fitted`.
3. **Ask the user** for what the files do not show: the goals and dates, who can own each module, the AI features, the public site.
4. **Map each gap to a module.** Use the "Fills it" column of the audit. Add the needs the audit does not cover: a public site (`aieo`, `compliance`), AI features (`ai-ops`, `red-team`), open roles (`hiring`), cost questions (`finops`), a person who built the platform and will leave (`handover`).
5. **Decide per module:**

   | Recommendation | When |
   |---|---|
   | `fitted` | The signal is present and the files are in use |
   | `fit now` | The module closes one of the top-ranked gaps, or a `fit now` module depends on it |
   | `fit later` | The need is real, and it waits for a dependency, a date or an owner |
   | `not needed` | No gap and no goal points to it. Say why in one line |

   Each reason cites its evidence: the audit rank, a file, a command output or the user's goal.
6. **Order the modules.** A module starts after the modules it depends on. Defaults:

   | Module | Depends on | Why | Effort | First skill |
   |---|---|---|---|---|
   | sdlc | none | The lifecycle page lists the stages the other modules serve | hours | `/sdlc:sdlc-init` |
   | gate | none | Every module's gate check runs in the gate, so the gate comes before the checks | hours | `/gate:gate-init` |
   | docs | none | Runbooks, owned pages and the handover live in the docs tree | days | `/docs:docs-init` |
   | decisions | none | Records the choices made during the fitting | hours | `/decisions:adr` |
   | observability | none | Metrics and logs come before SLOs, alerts and agent metering | days | `/observability:stack-init` |
   | reliability | observability, docs | SLOs need metrics; runbooks are docs pages | weeks | `/reliability:nines-per-service` |
   | finops | none | Needs billing exports and invoices | days | `/finops:cost-baseline` |
   | compliance | docs | Evidence links to owned pages | weeks | `/compliance:control-map` |
   | ai-ops | observability | Metering sends agent telemetry to the stack | days | `/ai-ops:agent-harness` |
   | hiring | none | Needs an open role | days | `/hiring:interview-loop` |
   | red-team | an AI feature | Tests a decision the feature makes | days | `/red-team:pressure-plan` |
   | aieo | a public site | Works on the pages a site serves | days | `/aieo:llms-txt` |
   | handover | docs and every module it hands over | New owners train on the runbooks and the docs | weeks | `/handover:owner-training` |

   Effort is one class per module: hours, days or weeks. Move a module up a class when the evidence shows a large estate, for example many services or many providers. Skill names can change between versions; confirm each first skill in the module's README.
7. **Write `docs/fit.md`.** Copy the template without overwriting:

   ```bash
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/fit.md" docs/fit.md
   ```

   Fill the front matter, the opening paragraph, one row per module in the module table and the order table. Keep the "Module signals" table as copied. If `docs/fit.md` exists, update its rows and keep the rest.
8. **Offer the gate check.** With the gate installed, suggest `/gate:add-rule` for `fit.assessment-matches` on `warn`. It checks that every `fitted` row has its signal in the repository.

## Output

`docs/fit.md`, and in the chat: the fitted modules, the ordered list with one reason per module, and the first command to run.

## Rules

- Read only. The one file this skill writes is `docs/fit.md`. It installs nothing and copies no other module's files.
- Every recommendation cites its evidence. A module with no probe result is "not checked".
- `not needed` is a valid answer. Recommend a module only for a gap or a goal the user confirmed.
- An owner is a person or team the user names. Never invent one; leave `<owner>` in place.
- Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/fit" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/fit/` exists, read its `README.md` first, then the files in `fit/estate-assessment/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
