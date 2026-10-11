---
name: nines-per-service
description: >
  Pick an availability target per service from user impact, tier and serial
  dependencies, check it against the allowed downtime per 30 days, quarter and
  year and against the product of its dependencies' availabilities, and write
  it into the service catalogue. Use when a service has no target yet, when a
  target looks arbitrary, or before a tier change or a customer commitment.
  Activates on "/nines-per-service", "how many nines", "availability target",
  "pick an SLO target", "99.9 or 99.99", "allowed downtime", "dependency
  ceiling".
user-invocable: true
---

# Nines per service

Sets one availability target per service in `services/<id>.yml`. The target follows from three things: what users lose when the service is down, the tier, and the serial dependencies. A service fails when one of its serial dependencies fails, so its availability cannot exceed the product of their availabilities. The skill computes that ceiling, shows the allowed downtime for the candidate targets, and writes the chosen target into the catalogue after the owner agrees.

## Inputs

- **Service** (required): the catalogue id. Without an entry, start one from `services/_template.yml`.
- **User impact**: who notices an outage, how fast, and what an hour down costs them.
- **Tier**: from the catalogue, or decided now.
- **Dependencies**: the serial ones (`depends_on`) and the ones the service survives (`soft_depends_on`). For an external dependency, the availability the provider commits to. Check before use: each provider's commitment, in its current SLA document.
- **Measured availability**: the last 30 and 90 days, if a metric or probe exists.

## Allowed downtime

Allowed downtime = (1 - target) × window, with the target as a fraction. Windows: 30 days (43,200 min), a quarter of 90 days (129,600 min), a year of 365 days (525,600 min).

| Target | 30 days | Quarter (90 days) | Year (365 days) |
|---|---|---|---|
| 99% | 432 min (7 h 12 min) | 1,296 min (21 h 36 min) | 5,256 min (3 d 15 h 36 min) |
| 99.5% | 216 min (3 h 36 min) | 648 min (10 h 48 min) | 2,628 min (1 d 19 h 48 min) |
| 99.9% | 43.2 min (43 min 12 s) | 129.6 min (2 h 9 min 36 s) | 525.6 min (8 h 45 min 36 s) |
| 99.95% | 21.6 min (21 min 36 s) | 64.8 min (1 h 4 min 48 s) | 262.8 min (4 h 22 min 48 s) |
| 99.99% | 4.32 min (4 min 19.2 s) | 12.96 min (12 min 57.6 s) | 52.56 min (52 min 33.6 s) |

Compute it again for another target or window:

```bash
python3 -c 'import sys; t = float(sys.argv[1]); print(*(f"{d} d: {(1 - t / 100) * d * 1440:.2f} min" for d in (30, 90, 365)), sep="\n")' 99.9
```

## Steps

1. **Set up.** Copy the catalogue template and the status script without overwriting:

   ```bash
   mkdir -p services scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/services/_template.yml" services/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/build_status.py" scripts/
   ```

   Without rsync, use `cp -n` for both files. `build_status.py` also needs `incidents/incidents.json`; copy it from `${CLAUDE_PLUGIN_ROOT}/templates/incidents/` the same way.
2. **Read the entry and its dependencies.** Read `services/<id>.yml` and the entries it names in `depends_on`. Ask the owner, for each dependency, whether the service fails when it fails. Move the ones it survives (a cache, a fallback, a queue, a degraded mode) to `soft_depends_on`. Give every serial dependency its own catalogue entry with a target, also an external one (`lifecycle: external`).
3. **Describe the user impact.** In two or three sentences: who notices, after how long, and what they lose. Tier 1 is a service users meet directly or that revenue or data depends on.
4. **Look at the data.** If a metric or probe exists, compute the availability of the last 30 and 90 days. A first target sits at or a little below what the service already delivers, unless users need more.
5. **Propose a target.** Starting points by tier: tier 1 99.9%, tier 2 99.5%, tier 3 99%. Move up only when users need more and the team can fix a failure within the allowed downtime. At 99.95%, one incident of 25 minutes uses more than the whole 30-day budget.
6. **Check the dependency ceiling.** The ceiling is the product of the targets of the serial dependencies:

   ```bash
   python3 scripts/build_status.py --check
   ```

   Example: serial dependencies at 99.95% and 99.99% give 0.9995 × 0.9999 = 0.99940005, a ceiling of 99.94%. A target of 99.95% is above it. If the proposal is above the ceiling, lower the target, or take a dependency off the serial path (a cache, a fallback, a second provider) and record that design change as a decision.
7. **Agree with the owner.** Show the target, the allowed downtime for 30 days, the quarter and the year, the ceiling, and the measured availability. The owner decides.
8. **Write the target.** In `services/<id>.yml`, set `slo.target` (a number in percent, below 100) and `slo.window` (default `30d`). Change no other field without asking. Show the diff.
9. **Check.** Run `python3 scripts/build_status.py --check`: the service reads `ok`. If the gate runs the rule, also run `python3 .github/actions/gate/run.py --only reliability.service-catalog --dry-run`.
10. **Report** and hand over to the `slo` skill, which defines the indicator, the error budget and the alerts.

## Output

Per service: the target, the window, the allowed downtime per 30 days, quarter and year, the serial dependencies with their targets, the ceiling, the measured availability, and the diff of the catalogue entry.

## Rules

- A target is a number below 100. 100% leaves no error budget.
- A target never exceeds the ceiling of its serial dependencies.
- The owner of the service decides the target. The skill proposes and computes.
- A customer commitment (SLA) is a contract the user makes. It is set looser than the internal target.
- Every downtime figure is computed from the formula above, and the table is checked against the snippet before it is shown.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/nines-per-service/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
