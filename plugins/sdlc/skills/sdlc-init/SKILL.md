---
name: sdlc-init
description: >
  Map the repository's delivery lifecycle and write docs/sdlc.md: a stage table
  with entry and exit criteria, an owner per stage, the record each stage leaves
  and the installed module that serves it, with the uncovered stages listed as
  gaps. Use when a team adopts the suit, or when nobody can say how a change gets
  from request to production. Activates on "/sdlc-init", "map our lifecycle",
  "write the sdlc doc", "how do changes ship here", "set up the sdlc".
user-invocable: true
---

# SDLC init

Writes the lifecycle down once, so every later skill and every agent session can read where a change is and what comes next.

The stages: request, RFC, decision, build, review, test, gate, release, observe, incident, and back to request.

## Steps

1. **Run the audit first** if no `docs/sdlc.md` exists: `/sdlc:sdlc-audit`. Its evidence fills most of the table.
2. **Find the installed modules** from the files they leave in the repository:

   | Module | Signal |
   |---|---|
   | decisions | `docs/decisions/index.md` |
   | docs | `docs/docs.json`, `scripts/build_docs.py` |
   | gate | `gate/gate.json`, `.github/actions/gate/run.py` |
   | reliability | `services/*.yml`, `incidents/` |
   | observability | `observability/docker-compose.yml` |
   | finops | `docs/**/cost-baseline*.md`, `scripts/focus_export.py` |
   | compliance | `compliance/control-map.csv`, `.well-known/security.txt` |

3. **Ask the user** for what the files do not show: the owner of each stage, the ticket system (GitHub Issues by default), the branch model, who may deploy, and the release rhythm.
4. **Copy the templates** without overwriting:

   ```bash
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/" ./
   ```

   This adds `docs/sdlc.md`, `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`, `CHANGELOG.md` and `scripts/changelog_draft.py`. Report copied and skipped files.
5. **Fill `docs/sdlc.md`.** One row per stage with entry, exit, owner, record and the module or skill that serves it. A stage with no module and no practice goes into the Gaps table with the skill that fills it. Fill the front matter (owner, reviewed, review_by).
6. **Offer the traceability check.** With the gate installed, suggest `/gate:add-rule` for `sdlc.traceability` on `warn`, with the option `since` set to today, so commits from before the adoption are not checked.

## Output

`docs/sdlc.md` filled in, the list of gaps with their fixes, and the files copied.

## Rules

- Never overwrite an existing file. If `docs/sdlc.md` exists, update its rows and keep the rest.
- A stage owner is a person or a team the user names. Never invent one.
- Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/sdlc-init/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
