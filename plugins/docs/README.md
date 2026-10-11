# docs

Documentation as code for one repository. Pages are Markdown files in `docs/<space>/`, each with an owner, a review date, a next review date and a type. A build script turns them into a static site with a page tree, backlinks, decision record and RFC indexes, a search index and a health page that lists the pages past review. A gate check reports missing or malformed review fields on every run.

Demo: [machinebehavior.io/inside/docs/health/](https://machinebehavior.io/inside/docs/health/), the docs health page of the platform behind machinebehavior.io.

## Skills

| Skill | What it does |
|---|---|
| `/docs:docs-init` | Sets up the docs tree in the current repository: asks for the spaces, copies the config, the space pages, the page templates and the build script, fills the front matter and runs the first build. |
| `/docs:runbook` | Writes one runbook page for one symptom or procedure, from an incident, a chat or your notes, and links it from the runbooks index. |
| `/docs:review-sweep` | Finds stale pages, checks each one against the system it describes, updates the review dates only after that check, and reports what still needs the owner. |

## Templates

`docs-init` copies these files into the client repository at the same paths. It never overwrites an existing file.

| Path in the repository | What it is |
|---|---|
| `docs/docs.json` | Site title, output folder, URL prefix, base URL, review interval and the list of spaces |
| `docs/eng/index.md` | Home page of the Engineering space |
| `docs/eng/runbooks.md` | Runbooks index; each runbook is a child page of it |
| `docs/_templates/page.md` | Starting point for a page |
| `docs/_templates/runbook.md` | Starting point for a runbook: Symptom, Checks, Steps, Verify, Roll back or escalate |
| `scripts/build_docs.py` | The build. Python 3.9+, standard library only |

The `decisions` space in `docs.json` belongs to the `decisions` module, which writes the RFCs and ADRs in `docs/decisions/`. The build skips a space whose folder does not exist.

## Front matter

```yaml
---
title: Deploy pipeline
summary: How a commit on main reaches production.
parent: architecture        # slug in the same space; empty = the space home
order: 20
labels: deploy, ci
owner: Platform team
reviewed: 2026-10-01        # or no
review_by: 2026-12-30
type: explanation           # tutorial, how-to, reference or explanation
---
```

`title` and `summary` are required. `created` and `updated` are optional dates; `date` works as `created`. Without them the build uses the git date of the file. Quote a value that contains `": "`. Decision records add `adr`, `status`, `supersedes` and `superseded_by`; RFCs add `rfc`, `status`, `comments_close` and `decision`.

Links: `[text](doc:<space>/<slug>)` links another page. An unknown target stops the build. `<!-- adr-index -->` and `<!-- rfc-index -->`, each on a line of its own, become the index tables of the decision records and the RFCs.

## Build

```bash
python3 scripts/build_docs.py            # writes the site to the "out" folder in docs/docs.json
python3 scripts/build_docs.py --check    # parses, validates and renders in memory; writes nothing; exit 1 on errors
python3 scripts/build_docs.py --stale    # lists the pages that need a review, grouped by owner
```

The build stops, and writes nothing, on a malformed date, an unknown type or status, an unknown `doc:` link, a supersede link that only one of the two records states, or two records with the same number. It prints a warning for a page without an owner, a review date or a type. Output: one `index.html` per page under `out` (default `site/docs/`), served at `url_prefix` (default `/docs/`), plus `health/index.html` and `search.json`. Set `base_url` to write canonical links.

## Gate check

`checks/docs_review.py` is the rule `docs.review` for the deploy gate of the `gate` module. For every file under `docs/**/*.md` (paths with a segment that starts with `_` are skipped) it checks: front matter present, `owner` set, `reviewed` a date or `no`, `review_by` a date (required when `reviewed` is a date), `type` one of the four Diátaxis types. A missing or malformed field fails the rule. A passed `review_by` or `reviewed: no` makes it a warning; with the option `"overdue_fails": true` it fails.

To enable it in a repository that has the gate, run `/gate:add-rule` and install `docs.review` from this module (path A). By hand:

1. Copy `checks/docs_review.py` to `.github/actions/gate/rules/` and `checks/fixtures/docs.review/` to `gate/fixtures/docs.review/`.
2. Add the rule to `gate/gate.json`:

   ```json
   "rules": {
     "docs.review": {"tier": "warn"}
   }
   ```

3. Run `python3 .github/actions/gate/run.py --dry-run`.

Start on `warn`. Move the rule to `block` with `/gate:add-rule`, which adds the false-positive test that blocking rules need.

## Overlay

Each skill reads `$POWERSUIT_OVERLAY/docs/` first when it exists: house rules for pages, the list of spaces and owners, runbook conventions, systems the review sweep must not touch. See the root README.
