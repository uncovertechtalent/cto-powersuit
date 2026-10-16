# direction

The direction area of a company that runs its work in a tracker. Once a week, `/direction:review` reads every item in `bd` across all areas and writes one memo: what moved per area in the period, what is blocked and by what, a proposed allocation of the coming week, and the decisions the owner must take. The memo is a proposal. A decision counts once the owner states it: the skill then records it as a tracker item with `area:direction` and `kind:decision`, closed with the decision as its reason, and the memo line names the record. A gate check reports memos that lack a date or a period, miss one of the four sections, or leave a decision without a status.

The module reads the same labels as the cockpit of the CTO powersuit (`area:` for the eight areas, `kind:` for finding, decision, action and lead) and needs nothing else from it. Items without an `area:` label stay under "no area label" in every table; the skill never guesses an area.

Install:

```bash
claude plugin install direction@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/direction:review` | Reads `bd list --json --all --limit 0`, `bd ready --json` and `bd blocked --json`, writes the memo (what moved per area, blocked items with their blockers, the allocation of five working days with a reason per area, the decisions needed), walks the decisions with the owner, and records each confirmed decision as a tracker item with `area:direction` and `kind:decision`. Read-only until the owner confirms. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/direction/` (see the root README). Use it for your area list, your memo path, your allocation rules and your owner.

## Where the memo goes

Under the tracker root (the folder with `.beads/`): `_inbox/Direction review <YYYY-MM-DD>.md` when that root has an `_inbox/` folder, as a vault made by `/vault:vault-init` has; otherwise `docs/direction/review-<YYYY-MM-DD>.md`. The gate check reads the repository form.

## Templates

The skill copies these files into a repository on first use. An existing file is never overwritten. In a vault it reads the memo template from the plugin and copies nothing.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/docs/direction/index.md` | `docs/direction/index.md` | The direction page: the reviews, how a review runs |
| `templates/docs/direction/_templates/review.md` | `docs/direction/_templates/review.md` | Memo template: front matter, What moved, Blocked, Proposed allocation, Decisions needed |

The page templates carry the front matter of the `docs` module (`owner`, `reviewed`, `review_by`, `type`) plus `date`, `period` and `areas`, so a filled memo passes `docs.review` and `direction.review-memo`.

## Gate check

`checks/review_memo.py` defines the rule `direction.review-memo` for the deploy gate of the `gate` module. For each file that matches `docs/direction/review-*.md`, skipping any path with a segment that starts with `_`, it reports:

| Snippet | Problem |
|---|---|
| `missing date`, `malformed date: <value>` | No `date` in the front matter, or a value that is not an ISO date `YYYY-MM-DD` |
| `missing period`, `malformed period: <value>` | No `period`, or a value that is not `YYYY-MM-DD/YYYY-MM-DD` with real dates and the start not after the end |
| `missing section: <name>` | One of the headings What moved, Blocked, Proposed allocation, Decisions needed is absent |
| `decision without status: <text>` | A list item under Decisions needed that does not end with `(open)`, `(recorded: <id>)` or `(dropped: <reason>)` |

The result is `fail` on any hit, `pass` when every memo is clean and `n/a` when no file matches. Headings match by their text, at any level. Options: `globs` for another folder, `sections` for other heading names (the last one is the decisions section).

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp plugins/direction/checks/review_memo.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/direction/checks/fixtures/direction.review-memo <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first:

   ```json
   "direction.review-memo": {"tier": "warn"}
   ```

   For another folder, add `"options": {"globs": ["<folder>/review-*.md"]}`.
4. Move it to `"tier": "block"` once the fixtures are in place and a false-positive test over your own memos is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run it on its own with `python3 .github/actions/gate/run.py --only direction.review-memo --dry-run`.

Demo: [machinebehavior.io/inside/cockpit/#direction](https://machinebehavior.io/inside/cockpit/#direction), the direction area of the cockpit on the public work behind machinebehavior.io.
