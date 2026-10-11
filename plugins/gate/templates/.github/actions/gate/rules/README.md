# Gate rules

Each `*.py` file in this folder is one rule. `run.py` loads every file that does not start with `_` and runs the rules that `gate/gate.json` enables. Standard library only.

## Contract

```python
ID = "module.rule-name"          # required, unique; the key in gate.json
DESCRIPTION = "One sentence."    # optional; shown by the add-rule skill
DEFAULTS = {"globs": ["**/*.md"]} # optional; gate.json "options" override these keys

def check(ctx):
    return {
        "result": "pass",        # pass, warn, fail or n/a
        "detail": "one line with counts",
        "evidence": [],          # optional lines for the summary
        "hits": [{"file": "docs/a.md", "line": 3, "snippet": "missing owner"}],
    }
```

`ctx` gives the rule:

| Name | What it is |
|---|---|
| `ctx.root` | Repository root as a `Path` (a fixture tree during fixture tests) |
| `ctx.options` | `DEFAULTS` merged with the rule's `options` from `gate.json` |
| `ctx.config` | The whole gate config |
| `ctx.history` | Earlier runs from `latest.json`, oldest first |
| `ctx.trigger` | `push`, `schedule`, `workflow_dispatch` or `manual` |
| `ctx.now`, `ctx.today` | UTC time of the run and its date |
| `ctx.files(globs, exclude=())` | Matching files under root, minus the config's `exclude` list (default `.git/`, `node_modules/` and `/gate/`; a leading `/` anchors a pattern at root) |
| `ctx.rel(path)` | Path relative to root, with `/` separators |
| `ctx.read(path)` | File text |
| `ctx.front_matter(path)` | `(meta, body, body_line)`; accepts `---` blocks and header blocks ended by `---` |
| `ctx.git(*args)` | Output of a git command, or an empty string |
| `ctx.load_rules(dir)`, `ctx.run_rule(rule, root, options)` | Load rule files from a folder and run one against another root |

## Results and tiers

- `fail` with tier `block` fails the run and blocks the deploy.
- `fail` with tier `warn` is recorded as `warn` and blocks nothing.
- A `fail` in either tier opens one finding per hit. A finding closes only when a later full run of the same rule no longer sees that hit. Turning a rule off or moving it to `warn` closes nothing.
- Keep snippets stable (no timestamps or counts in them), so the same problem keeps the same finding id across runs.

## Fixtures

Every rule in the `block` tier has two fixture trees in `gate/fixtures/<rule id>/`: the rule must pass on `pass/` and fail on `fail/`. The rule `gate.rule-fixtures` checks this on every run, together with a recorded false-positive test in `gate.json`.
