# Gate rules

Each `*.py` file in this folder is one rule. `run.py` loads every file that does not start with `_` and runs the rules that `gate/gate.json` enables, in the order `gate.json` lists them. Standard library only. A file that starts with `_` is a helper that rules can import; it is never run as a rule.

## Contract

```python
ID = "module.rule-name"          # required, unique; the key in gate.json
DESCRIPTION = "One sentence."    # optional; shown by the add-rule skill
DEFAULTS = {"globs": ["**/*.md"]} # optional; gate.json "options" override these keys
PHASE = "before"                 # optional; "after" runs the rule once the findings are built

def check(ctx):
    return {
        "result": "pass",        # pass, warn, fail, partial, pending or n/a
        "detail": "one line with counts",
        "evidence": [],          # optional lines for the summary
        "hits": [{"file": "docs/a.md", "line": 3, "snippet": "missing owner", "rule": "owner"}],
    }
```

A hit's `rule` is optional. Use it when one check reports hits of several sub-rules (a scanner with a rule table, for example); it becomes part of the finding id.

`ctx` gives the rule:

| Name | What it is |
|---|---|
| `ctx.root` | Repository root as a `Path` (a fixture tree during fixture tests) |
| `ctx.options` | `DEFAULTS` merged with the rule's `options` from `gate.json` |
| `ctx.config` | The whole gate config |
| `ctx.history` | Earlier runs from `latest.json`, oldest first |
| `ctx.trigger` | `push`, `schedule`, `workflow_dispatch` or `manual` |
| `ctx.now`, `ctx.today` | UTC time of the run and its date |
| `ctx.shared` | A dict shared by every rule in one run. Run an expensive scan once, keep it here, and let several rules read it. Fixture runs get an empty one |
| `ctx.findings` | After-phase rules only: every finding after this run, open and closed. `None` in the before phase |
| `ctx.files(globs, exclude=())` | Matching files under root, minus the config's `exclude` list (default `.git/`, `node_modules/` and `/gate/`; a leading `/` anchors a pattern at root) |
| `ctx.rel(path)` | Path relative to root, with `/` separators |
| `ctx.read(path)` | File text |
| `ctx.front_matter(path)` | `(meta, body, body_line)`; accepts `---` blocks and header blocks ended by `---` |
| `ctx.git(*args)` | Output of a git command, or an empty string |
| `ctx.load_rules(dir)`, `ctx.run_rule(rule, root, options)` | Load rule files from a folder and run one against another root |

## Results and tiers

- `fail` with tier `block` fails the run and blocks the deploy.
- `fail` with tier `warn` is recorded as `warn` and blocks nothing.
- `warn`, `partial`, `pending` and `n/a` never fail the run and open no finding. Use `partial` when a check sees part of what it needs, and `pending` when the evidence does not exist yet (no scheduled run so far, for example).
- A `fail` in either tier opens one finding per hit. A finding closes only when a later full run of the same rule no longer sees that hit. Turning a rule off or moving it to `warn` closes nothing.
- The finding id is `F-` plus the first 12 hex digits of `sha256("<rule id>|<file>|<hit rule>|<snippet>")`. Keep snippets stable (no timestamps or counts in them), so the same problem keeps the same id across runs.
- The run's `warnings` count in the history is the number of hits of checks that did not fail. A check that warns without hits counts zero, so give warnings hits.

## After-phase rules

A rule with `PHASE = "after"` runs once the findings of this run are built and reads them in `ctx.findings`. It counts towards the overall result like any rule, but its hits open no finding. Use it for checks on the findings themselves, such as "no finding closed without a passing run".

## Requirements

With `"requirements": "gate/requirements.json"` in `gate.json` (or `--requirements`), each requirement names the checks that give evidence for it:

```json
{"requirements": [{"id": "REQ-1", "title": "Published pages carry no placeholder text", "checks": ["gate.placeholders"], "mark": "M"}]}
```

The run then writes `requirement_states` into the run record and `latest.json`: per requirement, `live` is `pass` when every mapped check that ran passed or was `n/a`, `fail` when every one failed, `partial` otherwise, and `null` when none ran. `self` copies `self_assessment.result` and `mark` copies `mark`, when present. The state uses the raw result, so a failing `warn`-tier check still shows `fail` here. Findings carry the ids of the requirements their check maps to.

## Reporters

A reporter turns a finished run into more output: a page, extra keys in `latest.json`, a record in another format. List them in `gate.json`:

```json
"reporters": [".github/actions/gate/reporters/oscal.py", {"path": "gate/page.py", "options": {"title": "Gate"}}]
```

```python
ID = "gate.oscal"                 # optional; the file name otherwise

def report(r):
    return {
        "files": {"index.html": "<!doctype html>..."},   # paths under the out directory
        "latest": {"site": "example.org"},                # extra keys for latest.json
        "refuse": {"code": 4, "reason": "placeholder text in the rendered page"},  # optional
    }
```

`r` holds `record` (the run record), `latest` (the new `latest.json` content), `checks`, `findings`, `requirements`, `requirement_states`, `config`, `options`, `root`, `out`, `shared` (the rules' `ctx.shared`), `dry_run`, `trigger`, `sha`, `now`, `ts` and `git`. Reporters run in the order listed, on dry runs too, and not on `--only` runs. Files are written only on a full run that no reporter refused. A reporter cannot write `latest.json`, `.result` or `summary.md` (unless `write_summary` is `false`), cannot write outside the out directory, and cannot set the runner's own keys in `latest.json` (`history`, `findings`, `last_run`, `overall`, `gate`, `requirement_states`).

A refusal stops the run before anything is written, and `run.py` exits with the reporter's code (4 to 125). Use it for a last check on the output itself, such as a rendered page that would publish placeholder text.

`reporters/oscal.py` ships with the gate: it writes an OSCAL-shaped assessment-results record next to each run record (`runs/<timestamp>-<id>.oscal.json`, not validated against the OSCAL schema).

Set `"write_summary": false` in `gate.json` when a reporter renders its own summary.

## Fixtures

Every rule in the `block` tier has two fixture trees in `gate/fixtures/<rule id>/`: the rule must pass on `pass/` and fail on `fail/`. The rule `gate.rule-fixtures` checks this on every run, together with a recorded false-positive test in `gate.json`.
