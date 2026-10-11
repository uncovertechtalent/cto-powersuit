---
name: add-rule
description: >
  Add a rule to the deploy gate: install a check that another module ships, or
  write a new one. Every rule starts in the warn tier, gets a pass fixture and a
  fail fixture, and moves to the block tier only after a recorded false-positive
  test. Activates on "/add-rule", "add a gate rule", "gate this",
  "make the gate check", "install the docs check".
user-invocable: true
---

# Add rule

Adds one rule to the gate in the current repository. Run `/gate:gate-init` first if `gate/gate.json` does not exist.

A gate rule is mechanical: it reads files in the repository and returns pass or fail with no network, no model call and no judgment. A check that needs judgment belongs in a review skill, outside the gate.

## Path A: install a module's check

Modules ship their checks in `checks/<rule>.py`, with fixtures in `checks/fixtures/<rule id>/`. Examples: `decisions.adr-fields` (decisions module) and `docs.review` (docs module).

1. **Find the module's checks folder.** In a local clone of this marketplace it is `plugins/<module>/checks/`; in the plugin cache it sits next to this plugin:

   ```bash
   for d in "${CLAUDE_PLUGIN_ROOT}/../<module>/checks" "${CLAUDE_PLUGIN_ROOT}"/../../<module>/*/checks; do [ -d "$d" ] && echo "$d"; done
   ```

   If nothing prints, ask the user for the path.
2. **Copy without overwriting.** The rule file goes to the rules folder named in `gate/gate.json` (`rules_dir`, default `.github/actions/gate/rules`), the fixtures to `gate/fixtures/<rule id>/`:

   ```bash
   cp -n "<checks>/<rule>.py" .github/actions/gate/rules/
   mkdir -p "gate/fixtures/<rule id>" && cp -Rn "<checks>/fixtures/<rule id>/." "gate/fixtures/<rule id>/"
   ```

3. Continue at step 5 of Path B.

## Path B: write a new rule

1. **State the rule.** One sentence: which files it reads and what counts as a hit. Ask the user for one real example of a hit and one of a clean file.
2. **Name it.** Id `<module or team>.<rule-name>`, file `<rule_name>.py` in the rules folder. Check that no rule file already uses the id.
3. **Write the rule** to the contract in `.github/actions/gate/rules/README.md`: `ID`, `DESCRIPTION`, `DEFAULTS` for globs and patterns, `check(ctx)` returning `result`, `detail`, `hits`. Use `ctx.files`, `ctx.front_matter` and `ctx.rel`. Keep each hit snippet stable (no dates or counts in it), so the same problem keeps the same finding id across runs.
4. **Write the fixtures.** `gate/fixtures/<rule id>/pass/` and `fail/`: the smallest repository trees that show the rule passing and failing, with one file in `fail/` per kind of hit. Git does not track empty folders, so each tree needs at least one file.
5. **Register on warn.** Add the rule to `gate/gate.json` under `rules` with `"tier": "warn"` and any `options` the repository needs.
6. **Run it on the repository.**

   ```bash
   python3 .github/actions/gate/run.py --only <rule id>
   ```

   Read every hit with the user.
7. **Record the false-positive test.** For each hit, decide with the user: a real problem, or legitimate text the rule should not flag. Record the count in `gate/gate.json` under the rule:

   ```json
   "false_positive_test": {"date": "YYYY-MM-DD", "corpus": "what was scanned", "hits": 4, "legitimate": 1, "decision": "warn until the pattern skips quoted text"}
   ```

   If `legitimate` is above zero, tighten the rule or add an exemption, rerun and record again.
8. **Promote to block** only when all three hold: `legitimate` is zero, the repository has no real hits left (fix them first, or the next push blocks the deploy), and the fixtures behave. Set `"tier": "block"`, then run:

   ```bash
   python3 .github/actions/gate/run.py --only gate.rule-fixtures,<rule id> --exit-code
   ```

   Exit code 0 means the rule passes its pass fixture, fails its fail fixture and has a recorded test.
9. **Report** the rule id, tier, fixture paths, the false-positive record and the commands above. Commit when the user says so.

## Rules

- Never overwrite an existing rule file or fixture. Never push.
- A new rule never starts on `block`.
- A rule reads only files under `ctx.root`. No network, no clock-dependent hits except dates the files themselves carry.
- Keep fixture content generic. Fixtures must not contain secrets, customer data or real names.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/gate" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/gate/` exists, read its `README.md` first, then the files in `gate/add-rule/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
