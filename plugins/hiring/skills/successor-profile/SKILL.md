---
name: successor-profile
description: >
  Write docs/successor-profile.md, the profile of the person who takes over the
  platform: the systems they will own, read from the installed modules and the
  docs in the repository, the skills each system needs, and the interview stage
  and rubric dimension where a candidate shows each skill. Use when the current
  platform owner plans a handover, when a team hires the next platform lead, or
  when nobody can list what the platform owner owns. Activates on
  "/successor-profile", "successor profile", "who takes over the platform",
  "hire my replacement", "what does the platform owner own".
user-invocable: true
---

# Successor profile

Builds the profile of the next platform owner from the repository. The systems come from the modules and docs that are present; each system gets the skills it needs; each skill needed on the first day maps to one stage of the interview loop and one rubric dimension. The gaps list shows systems with no docs and skills no stage tests.

## Inputs

- The repository root (default: the current directory).
- `hiring/loop.md` and `hiring/rubrics/*.json`, if they exist.
- The current owner of the platform, for what the files do not show.

## Steps

1. **Find the installed modules** from the files they leave in the repository. If `docs/fit.md` exists, read its module table first.

   | Module | Signal |
   |---|---|
   | sdlc | `docs/sdlc.md` |
   | decisions | `docs/decisions/index.md` |
   | docs | `docs/docs.json` |
   | gate | `gate/gate.json` |
   | reliability | `services/*.yml` or `incidents/incidents.json` |
   | observability | `observability/docker-compose.yml` |
   | finops | `docs/fin/index.md` or `scripts/focus_export.py` |
   | compliance | `compliance/control-map.csv` or `.well-known/security.txt` |
   | ai-ops | `docs/agents.md` |
   | red-team | `red-team/plan.md` |
   | hiring | `hiring/loop.md` |

   For a module not in this table, read its README for its signal file.
2. **List the systems.** Read, with the command or file as the source of each row:
   - the service catalogue (`services/*.yml`) and the runbooks it links;
   - `docs/sdlc.md` for the delivery pipeline, `gate/gate.json` for the gate rules;
   - CI workflows (`.github/workflows/`), infrastructure code (Terraform, Kubernetes manifests, compose files);
   - `docs/decisions/` for decisions the owner has to keep or revisit;
   - `docs/handover.md` if it exists;
   - the README and the docs tree.

   One row per system the owner runs, changes, is on call for or decides on. Mark each system as documented, partly documented or not documented, with the page that documents it.
3. **Ask the current owner** what the files do not show: systems outside the repository, vendor relationships, recurring tasks, pending decisions, people who rely on the platform. Add each answer as a row with the source "owner interview, <date>".
4. **Name the skills.** For each system, the skills that owning it needs, stated as things a person does: "runs a database failover from the runbook", "reads a cost report and finds the top three drivers". Mark each skill as needed on the first day or learnable after joining.
5. **Map skills to the loop.** For each first-day skill, find the stage and the rubric dimension that collect it. If `hiring/loop.md` does not exist, run `/hiring:interview-loop` first with these skills as input. A skill with no stage goes to the gaps list with the fix: a new dimension in an existing stage, through `/hiring:interview-rubric`.
6. **Write `docs/successor-profile.md`.** Copy the template without overwriting, then fill every table:

   ```bash
   mkdir -p docs && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/successor-profile.md" docs/successor-profile.md
   ```

   If the file exists, update the rows and keep the rest. Fill the front matter (owner, reviewed, review_by).
7. **List the gaps:** systems with no docs, systems with no current owner, first-day skills with no stage. Each gap gets the fix: a page to write (`/docs:runbook` and the docs module), a stage or dimension to add, or a person to ask.

## Output

- `docs/successor-profile.md` with the systems, the skills, the loop mapping and the gaps.
- A short list for the current owner: the pages to write before the handover, ordered by risk.

## Rules

- Every system row names its source: a file, a command or the owner interview.
- The profile describes systems and skills. It names no candidate and no current employee; owners appear by role.
- A skill is stated as an action a person takes on a system. Years of experience and tool names on their own are not skills.
- Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/hiring" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/hiring/` exists, read its `README.md` first, then the files in `hiring/successor-profile/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
