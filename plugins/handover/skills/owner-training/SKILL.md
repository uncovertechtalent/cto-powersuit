---
name: owner-training
description: >
  Write a training checklist for each installed module of the platform, found
  by its signal file, that the new owner works through: what to read, what to
  run, one change made under supervision and how to know the module works,
  with the progress recorded in docs/handover.md. Use when a platform moves
  from the person who built it to named owners inside the team, or when a new
  owner or backup takes over a module. Activates on "/owner-training", "train
  the new owner", "handover checklist", "onboard the platform owner", "who
  learns what before the handover".
user-invocable: true
---

# Owner training

Gives the new owner of each module one checklist with four steps: read, run, change once under supervision, and know it works. The new owner does every step. The person handing over watches and answers questions. Progress goes into `docs/handover.md`, so `/handover:exit-criteria` and the gate check use the same page.

## Inputs

- The repository with its installed modules.
- From the user: the person handing over, the new owner and the backup per module, the start date and the planned exit date.

## Steps

1. **Find the installed modules.** The signal table is in `${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md`, section "Module signals". Test each signal in the repository:

   ```bash
   python3 - "${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md" <<'EOF'
   import re, sys
   from pathlib import Path
   table = Path(sys.argv[1]).read_text().split("## Module signals", 1)[1]
   for line in table.splitlines():
       cells = [c.strip() for c in line.strip().strip("|").split("|")]
       if not line.startswith("|") or len(cells) != 2 or cells[0] in ("Module", "---"):
           continue
       found = [str(p) for g in re.findall(r"`([^`]+)`", cells[1]) for p in sorted(Path(".").glob(g))
                if p.is_file() and not any(s.startswith("_") for s in p.parts)]
       print(f"{cells[0]:<14} {'installed' if found else 'absent':<10} {', '.join(found[:3])}")
   EOF
   ```

2. **Copy the template** without overwriting:

   ```bash
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/handover.md" docs/handover.md
   ```

   Keep the "Module signals" table as copied. The gate check reads it.
3. **Fill the owners table.** One row per installed module, with the owner and the backup the user names. Leave `<owner>` in place where the user names nobody yet, and list those modules in the report.
4. **Write one checklist per installed module** under "Training", from the defaults below. Replace each entry with the real pages, commands and checks of this repository. Confirm each command in the module's README.

   | Module | Read | Run | Change once, supervised | Know it works |
   |---|---|---|---|---|
   | sdlc | `docs/sdlc.md` | `/sdlc:work-item` for one real change | One row of the stage table or the label scheme | The next pull request names its ticket and passes review |
   | decisions | `docs/decisions/index.md`, the last three ADRs | `/decisions:decision-log-review` | Record one ADR with `/decisions:adr` | The ADR is in the index and passes `decisions.adr-fields` |
   | docs | `docs/docs.json`, the space home pages | The docs build | Review one stale page with `/docs:review-sweep` | The build passes and the owner has no overdue page |
   | gate | `gate/gate.json`, `gate/summary.md`, the rules README | `python3 .github/actions/gate/run.py --dry-run` | Add or tune one rule on `warn` with `/gate:add-rule` | The next push runs the gate and the deploy waits for it |
   | reliability | `services/*.yml`, the runbooks, the on-call policy | One runbook in a drill | One SLO target or alert threshold | The status page builds; the drill leaves a record in `incidents/incidents.json` |
   | observability | `observability/docker-compose.yml`, the dashboard specs, the alert routes | Start the stack and check that each component answers | One dashboard panel through `/observability:dashboards-as-code` | A test alert reaches the right receiver |
   | finops | `docs/fin/index.md`, the cost baseline | The monthly baseline or FOCUS export | Allocate one service in the showback | The month reconciles with the invoices and passes `finops.cost-provenance` |
   | compliance | `compliance/control-map.csv`, `.well-known/security.txt` | The gap report of `/compliance:control-map` | Update the evidence of one control | Every control has an owner; security.txt is valid and not expired |
   | security | `docs/security/index.md`, the provenance log, the rotation runbooks | `/security:access-review` | Approve one new action owner or skill after a provenance check | One secret rotated from its runbook; `security.secrets` passes |
   | ai-ops | `docs/agents.md`, the shared agent settings | The metering dashboard and the budget alert | One permission or plugin, reviewed | Agents run with the shared settings; the budget alert evaluates |
   | hiring | `hiring/loop.md` | One loop for one candidate, with the person handing over present | One stage or rubric line | The next loop leaves a complete debrief |
   | red-team | `red-team/plan.md` | `/red-team:pressure-run` with the stub adapter | One plan change, as a new plan version | `/red-team:pressure-grade` scores the run |
   | aieo | `llms.txt`, `predictions/README.md`, `aieo/queries.json` | `python3 aieo/probe.py trend` | Hash one prediction or bring `llms.txt` in step with the sitemap | `aieo.prediction-hashes` passes; the llms.txt sync exits 0 |
   | fit | `docs/fit.md` | `/fit:estate-assessment` | Update one row | `fit.assessment-matches` passes |
   | handover | `docs/handover.md` | `/handover:runs-without-me` for one scenario | Update the owners table | `handover.module-owners` passes |

5. **Work through the checklists** with the new owner. Write the date into "Done on" and a link into "Evidence" for each step: the pull request, the run record, the check output. The supervised change goes through review like any other change.
6. **Close a module's training** when all four steps carry a date and evidence. Write that date into "Trained on" in the owners table.
7. **Check the owners.** With the gate installed, run `python3 .github/actions/gate/run.py --only handover.module-owners`, or suggest `/gate:add-rule` for the rule on `warn`.

## Output

`docs/handover.md` with the owners table and one checklist per installed module, and a report: modules with no named owner or backup, steps done and open per owner, and the next step for each owner.

## Rules

- The new owner does each step. The person handing over watches, answers and reviews.
- A step is done only with a date and evidence. Never mark a step done for the owner.
- Owner and backup are people the user names, and two different people. Never invent a name.
- Write only `docs/handover.md`. Never overwrite an existing file with the template; update its rows and keep the rest. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/handover" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/handover/` exists, read its `README.md` first, then the files in `handover/owner-training/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
