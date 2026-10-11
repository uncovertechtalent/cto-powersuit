# decisions

A decision log for a repository. Larger changes start as a request for comments (RFC) with a fixed comment window. Each decision ends up as a numbered architecture decision record (ADR) with its context, the decision and its consequences. Records are never deleted: a replaced record gets the status `superseded` and names its successor, and the successor names it back. A gate check reports ADRs whose front matter breaks this format.

Install:

```bash
claude plugin install decisions@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/decisions:rfc` | Writes an RFC from a problem statement, opens it for comments until `comments_close`, collects the outcome from the owner, and hands an accepted or rejected RFC to `adr`. The next number is the highest RFC number plus one. |
| `/decisions:adr` | Records one decision as an ADR, from a decided RFC or directly for a small decision. Sets the supersede fields on both records and keeps the tables in `docs/decisions/index.md` current. |
| `/decisions:decision-log-review` | Sweeps the log and writes a report: missing status, owner or date, proposed ADRs older than 30 days, RFCs past `comments_close`, broken supersede links, duplicate numbers, records past `review_by`, and a spot check of accepted decisions against the code. Changes files only after you approve a fix. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/decisions/` (see the root README). Use it for your own comment window, reviewers, folder or review rules.

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/docs/decisions/index.md` | `docs/decisions/index.md` | The decision log page: status table, the index markers and the steps to add a record |
| `templates/docs/decisions/_templates/adr.md` | `docs/decisions/_templates/adr.md` | ADR template: front matter, Context, Decision, Consequences |
| `templates/docs/decisions/_templates/rfc.md` | `docs/decisions/_templates/rfc.md` | RFC template: front matter, Summary, Problem, Proposal, Alternatives considered, Risks and open questions, Rollout and rollback, Decision |

Records are named `docs/decisions/adr-NNNN-short-name.md` and `docs/decisions/rfc-NNNN-short-name.md`. The slug of a record is its file name without `.md`; links between records use slugs.

The index page holds two marker lines, `<!-- rfc-index -->` and `<!-- adr-index -->`. With the `docs` module installed, its build fills both tables at build time. Without a docs build, the `adr` skill keeps each table by hand on the lines below its marker. The docs build and the gate checks skip any path with a segment that starts with `_`, so `_templates/` is never published or checked.

## Gate check

`checks/adr_fields.py` defines the rule `decisions.adr-fields` for the deploy gate of the `gate` module. For each file that matches `docs/decisions/adr-[0-9]*.md` it reports:

| Snippet | Problem |
|---|---|
| `missing status`, `unknown status: <value>` | Status absent or outside `proposed`, `accepted`, `rejected`, `deprecated`, `superseded` |
| `missing owner` | No owner, or an empty one |
| `missing date`, `malformed <field>` | No `date` (or `created`), or a value that is not an ISO date `YYYY-MM-DD` |
| `superseded without superseded_by`, `superseded_by names no record: <slug>` | A superseded record with no successor, or a successor file that does not exist in the same folder |
| `duplicate adr number NNNN` | Two records with the same number |

The result is `fail` on any hit, `pass` when all records are clean and `n/a` when no file matches. The rule accepts `created` as a second date field, so records in the older header format (`key: value` lines ended by `---`) pass too.

Enable it with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rule into the gate's rules folder: `cp plugins/decisions/checks/adr_fields.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/decisions/checks/fixtures/decisions.adr-fields <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` in the `warn` tier first:

   ```json
   "decisions.adr-fields": {"tier": "warn"}
   ```

   For another folder, add `"options": {"globs": ["<folder>/adr-[0-9]*.md"]}`.
4. Move it to `"tier": "block"` once the fixtures are in place and a false-positive test over your own records is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run it on its own with `python3 .github/actions/gate/run.py --only decisions.adr-fields --dry-run`.

Demo: [machinebehavior.io/inside/docs/eng/decision-log/](https://machinebehavior.io/inside/docs/eng/decision-log/), the decision log of the platform behind machinebehavior.io.
