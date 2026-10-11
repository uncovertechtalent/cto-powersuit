# aieo

AI engine optimisation (AIEO): the work of getting a site's pages retrieved, named and cited when an AI search engine or assistant answers a question. The same work is also called answer engine optimisation (AEO) and generative engine optimisation (GEO). This module covers the parts a team can do and check on its own site: a plain index for agents (`llms.txt`), structured data that matches the visible page, a probe that measures what the engines answer, and predictions fixed by hash before a page goes live.

The foundation comes first: pages that crawlers can reach, that are indexed, and that say clearly what they hold. The skills here assume that foundation. None of them replaces it. Check before use: what each engine you target documents about retrieval and citation, at `<URL of each engine's documentation for site owners>`.

Install:

```bash
claude plugin install aieo@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/aieo:llms-txt` | Writes `llms.txt` from the site's pages (title, summary, sections of links with one line each) and checks it against `sitemap.xml` |
| `/aieo:structured-data` | Writes one JSON-LD graph per page from one source (Organization or Person, WebSite, Article, BreadcrumbList, FAQPage where the page shows real questions) and checks each block against the visible page |
| `/aieo:answer-probe` | Asks engines a fixed, versioned query set and records per answer whether it names the entity, links it and states the facts correctly; dated results and a trend per query set version |
| `/aieo:prediction-hash` | Writes a dated prediction file before a page goes live, adds its sha256 to `predictions/HASHES.txt` and commits both; a correction is a new file |

## Templates

| Lands at | What it is |
|---|---|
| `llms.txt` | Index skeleton: title, summary, sections with one line per page |
| `aieo/queries.json` | The versioned query set: entity names and domains, facts with patterns, queries in four groups (definition, entity, problem, control) |
| `aieo/probe.py` | The answer probe. Manual mode reads pasted answers from stdin; adapters call engines with an API, with keys from environment variables. Subcommands `run`, `trend`, `adapters`. Python 3.9+, standard library only |
| `aieo/results/README.md` | Folder note for the dated result files |
| `aieo/jsonld-example.json` | A JSON-LD graph with Organization, WebSite, Article and BreadcrumbList, for reference |
| `predictions/HASHES.txt` | Hash list with its format in a comment line |
| `predictions/README.md` | The rules for prediction files and their layout |

## Gate check

`checks/prediction_hashes.py` defines the rule `aieo.prediction-hashes`. It reads `predictions/HASHES.txt` and the `*.txt` files next to it and reports:

| Result | When |
|---|---|
| `fail` | A listed file is missing. Snippet: `<file>: file missing` |
| `fail` | A listed file does not match its sha256. Snippet: `<file>: sha256 differs from HASHES.txt` |
| `fail` | A prediction file is not listed. Snippet: `<file>: not listed in HASHES.txt` |
| `fail` | A line starts like an entry and breaks the format. Snippet: `<file>: malformed line in HASHES.txt` |
| `n/a` | No `predictions/` folder or no `HASHES.txt`, or neither a listed file nor a prediction file |

An entry line is `<file name>  sha256 <64 hex digits>`. Lines starting with `#` are comments; other lines are notes. Files whose name starts with `_` are drafts and are skipped. Options: `dir` (default `predictions`), `hashes_file` (default `HASHES.txt`).

Enable it with `/gate:add-rule` (path A). By hand, from a clone of this repository:

1. Copy the rule: `cp plugins/aieo/checks/prediction_hashes.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/aieo/checks/fixtures/aieo.prediction-hashes <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` on `warn`:

   ```json
   "aieo.prediction-hashes": {"tier": "warn"}
   ```

4. Move it to `"tier": "block"` once the false-positive test over your own `predictions/` folder is recorded under `"false_positive_test"`. The rule `gate.rule-fixtures` checks the fixtures and the record.

Demo: [machinebehavior.io/aieo/](https://machinebehavior.io/aieo/), the AI search measurement pages of machinebehavior.io.
