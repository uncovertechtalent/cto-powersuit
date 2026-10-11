# Rule fixtures

One folder per rule id. Each holds two small repository trees:

```text
gate/fixtures/<rule id>/
  pass/   files the rule must pass
  fail/   files the rule must fail
```

`gate.rule-fixtures` runs every blocking rule against both trees on each gate run. The default `exclude` list in `gate.json` keeps the whole `gate/` folder, fixtures included, out of every rule that scans files.
