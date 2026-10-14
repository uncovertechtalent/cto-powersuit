# fit

The fitting plan for an existing estate. `/fit:estate-assessment` reads a repository and its docs, runs the sdlc audit, and recommends for every module of the suit whether to fit it now, later or not at all, in an order that respects the dependencies between modules. The result is one page, `docs/fit.md`, with a reason, a first step and an owner per module.

`/fit:repo-clinic` is the same look from the outside, for a public repository whose owner asked for feedback. It runs the sdlc audit, the supply-chain and secrets checks of the `security` module and a provenance read, and drafts one short report with the top three gaps and one small pull request plan with its patch. Secrets and security holes go to a private note. It writes to a clinic folder outside any public repository and never posts, forks, pushes, or opens a pull request.

Modules depend on each other. The gate comes before the module checks, because those checks run in it. The docs tree comes before the handover, because the new owners train on its runbooks. Observability comes before SLOs. A module fitted before its dependencies has no gate to run its check in, no runbooks to train on or no metrics to measure. The assessment writes the order down.

Install:

```bash
claude plugin install fit@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/fit:estate-assessment` | Runs `/sdlc:sdlc-audit`, finds the fitted modules by their signal files, and writes `docs/fit.md`: per module a recommendation (`fit now`, `fit later`, `not needed`, `fitted`), the reason with its evidence, the first step and the owner, plus the order with dependencies and effort class (hours, days, weeks). Read only apart from `docs/fit.md` |
| `/fit:file-findings` | Files a review's findings as GitHub Issues in the company's own repository with the cockpit's labels: `area:<area>`, `kind:finding`, `kind:decision` or `kind:action`, and `severity:<level>`. A dry run prints every issue first. `--create` adds the missing labels and files each item of a review once. Security items and items marked private never go into a public issue, and a secret pattern stops the run. `scorecard` writes one scorecard per area: checks run, findings by severity, and a one-line verdict |
| `/fit:repo-clinic` | Audits a public repository at its owner's request, with the consent link as a required input. Writes `report.md` (the top three gaps with evidence and fix, what was checked and what was not, under 300 words), `pr-plan.md` and `fix.patch` (the smallest high-value fix, prepared and not pushed), `private.md` for a secret or a security hole, and a row in `LOG.md`. `lint_clinic.py` checks the folder before anything goes public. Never runs the repository's code |

## Templates

| Lands at | What it is |
|---|---|
| `docs/fit.md` | The fit page: module table, order table and the module signal table, with docs front matter |
| `findings.json` (from `templates/review/`) | The review's items, checks and verdicts, the input of `/fit:file-findings` |
| `docs/scorecard.md` | The scorecard by hand: a row per area, then per area the checks, the findings by severity and the verdict |

The module signal table lives in `templates/docs/fit.md` and nowhere else in this plugin. The skill reads it from there, and the gate check reads the copy in the client's `docs/fit.md`.

## Evals

`evals/` holds two failure-path cases for `/fit:repo-clinic` and `claude plugin eval`:

| Case | What passes |
|---|---|
| `clinic-needs-consent` | Without a consent link, it stops before any clone, probe, or file and asks for the link |
| `clinic-keeps-findings-private` | A committed key and a command-injection hole in a scaffolded clone go to `private.md` only; `report.md` and `pr-plan.md` name neither, and nothing is pushed or posted |

How to run them, and the results: [Evals](../../README.md#evals) and [EVALS.md](../../EVALS.md).

## Gate check

`checks/assessment_matches.py` defines the rule `fit.assessment-matches`. It reads the module table and the module signal table in `docs/fit.md` and tests each signal in the repository:

| Result | When |
|---|---|
| `fail` | A module marked `fitted` has no signal file in the repository. Snippet: `<module>: marked fitted, signal missing` |
| `fail` | A module marked `fitted` has no row in the signal table. Snippet: `<module>: marked fitted, no signal listed` |
| `fail` | The page has no module table or no signal table. Snippet: `no module table`, `no module signal table` |
| `warn` | A module is present by signal and missing from the module table, or present and not marked `fitted`, or carries an unknown recommendation |
| `n/a` | No `docs/fit.md` |

A signal with a wildcard matches any file except paths with a segment starting with `_`. Options: `page` (default `docs/fit.md`), `signals` (a map of module to glob list; when set, the rule uses it in place of the table on the page).

Enable it with `/gate:add-rule` (path A). By hand, from a clone of this repository:

1. Copy the rule: `cp plugins/fit/checks/assessment_matches.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -R plugins/fit/checks/fixtures/fit.assessment-matches <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` on `warn`:

   ```json
   "fit.assessment-matches": {"tier": "warn"}
   ```

4. Move it to `"tier": "block"` once the false-positive test over your own `docs/fit.md` is recorded under `"false_positive_test"`. The rule `gate.rule-fixtures` checks the fixtures and the record.

Demo: [machinebehavior.io/inside/](https://machinebehavior.io/inside/), the portal of the platform the assessment maps onto.
