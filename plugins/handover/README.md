# handover

The handover of a platform from the person who built it to named owners inside the team. Each installed module gets an owner and a backup, the owners work through a training checklist, the person handing over leaves when written exit criteria are met, and a test plan shows that the new owners run the platform from the docs alone.

Without evidence, a handover ends on a calendar date, and the knowledge goes with the person who leaves. This module ties the exit date to evidence in the repository: training steps with links, runbooks run by their new owners, the gate and the status page operated without help for a set period, and scenarios run from the docs with every gap ticketed.

Install:

```bash
claude plugin install handover@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/handover:owner-training` | Finds the installed modules by their signal files and writes one checklist per module for its new owner: what to read, what to run, one change made under supervision and how to know it works. Records progress and the owners table in `docs/handover.md` |
| `/handover:exit-criteria` | Sets the conditions for the exit of the person handing over (owner and backup per module, every runbook run by its new owner, gate and status page operated without help for a set period, open decisions recorded, access moved, scenarios passed), checks each against evidence and sets the exit date |
| `/handover:runs-without-me` | Plans and logs scenarios the new owner runs with no help (a deploy, a blocked gate, an incident, a restore, a cost spike, a docs review, a new decision), with time taken, docs used, and gaps found; every gap becomes a ticket |

## Templates

| Lands at | What it is |
|---|---|
| `docs/handover.md` | The handover page with docs front matter: owners table (module, owner, backup, trained on, exit criteria), training checklists, exit criteria, the runs-without-me log and the module signal table |

The module signal table lives in `templates/docs/handover.md` and nowhere else in this plugin. The skills read it from there, and the gate check reads the copy in the client's `docs/handover.md`. The table is the same as the one in the `fit` module.

## Gate check

`checks/module_owners.py` defines the rule `handover.module-owners`. It finds the installed modules from the signal table in `docs/handover.md` and reads the owners table on the same page:

| Result | When |
|---|---|
| `fail` | An installed module has no row in the owners table. Snippet: `<module>: no row in the owners table` |
| `fail` | An installed module's row has no named owner: empty, `-`, `none` or an angle-bracket placeholder. Snippet: `<module>: no named owner` |
| `fail` | The page has no module signal table or no owners table. Snippet: `no module signal table`, `no owners table` |
| `n/a` | No `docs/handover.md`, or no installed module found by signal |

A signal with a wildcard matches any file except paths with a segment starting with `_`. Rows for modules that are not installed are not checked. Options: `page` (default `docs/handover.md`), `signals` (a map of module to glob list; when set, the rule uses it in place of the table on the page).

Enable it with `/gate:add-rule` (path A). By hand, from a clone of this repository:

1. Copy the rule: `cp plugins/handover/checks/module_owners.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/handover/checks/fixtures/handover.module-owners <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` on `warn`:

   ```json
   "handover.module-owners": {"tier": "warn"}
   ```

4. Move it to `"tier": "block"` once the false-positive test over your own `docs/handover.md` is recorded under `"false_positive_test"`. The rule `gate.rule-fixtures` checks the fixtures and the record.

Demo: [machinebehavior.io/inside/tour/](https://machinebehavior.io/inside/tour/), the five-minute tour of the platform behind machinebehavior.io.
