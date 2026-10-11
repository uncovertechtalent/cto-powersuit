# stance

Stance filters against the trained accommodation reflex: `professional-b2`, `good-chad`, `receipts`, `poles`, `mode-leak` and `beta`. Hooks load the standing filters at session start and repeat a reminder on every prompt. Part of the `ai-ops` group; modes and environment variables are in the root README, section "stance".

Install:

```bash
claude plugin install stance@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/stance:receipts` | Probe before you assert; label what is unverified |
| `/stance:professional-b2` | Plain professional register without politeness filler; levels lite, full, ultra |
| `/stance:good-chad` | Holds a position under pushback, takes correction without grovelling |
| `/stance:poles` | Two committed poles and a call, for decisions and forecasts |
| `/stance:mode-leak` | Finds speech devices in written text and the reverse |
| `/stance:beta` | The unfiltered default, for comparison |

## Templates

| Lands at | What it is |
|---|---|
| `docs/stance.md` | The team page: which filters run for every session, the shared defaults and their owner |

## Gate check

`checks/shared_defaults.py` defines `stance.shared-defaults`: the agent settings checked into the repository (`.claude/settings.json`) do not set `STANCE_RECEIPTS`, `GOOD_CHAD_DEFAULT_MODE` or `PROFESSIONAL_B2_DEFAULT_MODE` to `off`, and do not set `disableAllHooks`. Personal settings in `.claude/settings.local.json` stay out of scope. The result is `n/a` when no shared settings file exists.

Enable it with `/gate:add-rule` (path A), on `warn` first. Move it to `block` after the false-positive test is recorded under `"false_positive_test"` in `gate/gate.json`.

Demo: [machinebehavior.io/inside/docs/res/](https://machinebehavior.io/inside/docs/res/), the research space with the experiments behind the stance filters.
