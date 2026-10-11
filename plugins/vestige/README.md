# vestige

An output filter you calibrate to yourself. `/vestige:calibrate` mines your own transcripts for the moments you pushed back and builds your catalog from them. Hooks scan every reply and every Markdown file Claude writes. Part of the `ai-ops` group; setup and logs are in the root README, section "vestige".

Install:

```bash
claude plugin install vestige@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/vestige:calibrate` | Builds your catalog from your own pushback and writes your filter skill and rule table |
| `/vestige:style-review` | Audits a draft against your catalog and lists the hits with fixes |
| `/vestige:guess-gate` | Checks paths, commands, names and citations in a reply against ground truth |
| `/vestige:label-gate` | Holds back labels such as "debunked" until the claim is scored on four questions |

## Templates

| Path in the plugin | Lands at | What it is |
|---|---|---|
| `templates/output-filter/SKILL.md` | `~/.claude/skills/output-filter/SKILL.md` | The filter skill template that `/vestige:calibrate` fills in |

## Gate check

`checks/catalog_scan.py` defines `vestige.catalog-scan`: published Markdown (`docs/**/*.md` and `README.md`) carries none of the blocking-tier patterns of the starter catalog: `praise-opener`, `service-closer`, `filler-idiom` and `hook-opener`. Fenced code, inline code, quoted lines, front matter and double-quoted spans are exempt, because a mention is not a use. Snippet: `<rule>: <matched text>`. For a calibrated catalog, set the option `patterns_file` to a JSON list of `{"name", "pattern", "flags"}`.

Enable it with `/gate:add-rule` (path A), on `warn` first. Move it to `block` after the false-positive test over your own pages is recorded under `"false_positive_test"` in `gate/gate.json`.

Demo: [machinebehavior.io/inside/docs/eng/conformity-gate/](https://machinebehavior.io/inside/docs/eng/conformity-gate/), the gate whose rule table scans every published page of machinebehavior.io.
