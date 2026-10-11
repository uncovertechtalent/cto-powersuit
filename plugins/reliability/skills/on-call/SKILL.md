---
name: on-call
description: >
  Set up on-call for the services in the catalogue: the rotation, the
  escalation policy, the handover checklist and the paging rules (page only on
  user-facing symptoms, every alert links a runbook), with an audit of the
  existing alert rules, written to docs/sre/on-call.md. Use when a team starts
  on-call, when pages wake people for causes users never see, or when nobody
  can say who answers a page tonight. Activates on "/on-call", "on-call
  rotation", "set up on-call", "escalation policy", "paging rules", "alert
  fatigue", "who gets paged".
user-invocable: true
---

# On-call

Writes the on-call policy in `docs/sre/on-call.md`: who is on call for which services, how a page escalates, what a handover covers, and which alerts may page a person. The skill audits the existing alert rules against the paging rules and proposes changes. The user changes the paging tool and merges the rule changes.

## Inputs

- **Services in scope**: by tier from `services/*.yml`, default tier 1 at any hour and tier 2 in working hours.
- **People**: names, time zones and working hours.
- **Paging tool**: the tool that pages people, and where its settings live.
- **Alert rules**: the files or the system that holds them.
- **Rules for working time**: what the organisation allows and pays for on-call. Check before use: working-time law and on-call pay rules in each country where on-call staff work.

## Steps

1. **Set up.** Copy the policy page without overwriting:

   ```bash
   mkdir -p docs/sre
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/" docs/sre/
   ```

   Without rsync, use `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/docs/sre/." docs/sre/`.
2. **Set the scope.** List the services by tier from the catalogue. Every service in scope must have an owner and a runbook; if the gate runs the rule, run `python3 .github/actions/gate/run.py --only reliability.service-catalog --dry-run`.
3. **Design the rotation.** Shift length, handover day and time, time zone. Compute the load: with N people in a 24/7 weekly rotation, each person is on call one week in N. Show the figure and ask the user whether that load is acceptable. With people in distant time zones, propose shifts that follow working hours.
4. **Write the escalation policy.** Primary, secondary, then a manager or incident lead pool, with the time without acknowledgement before each step. Write the settings to enter in the paging tool. The user enters them.
5. **Audit the alert rules.** List every alert with its severity and whether it has a runbook link. For Prometheus-style rule files:

   ```bash
   python3 - $(grep -rl --include='*.yml' --include='*.yaml' -e '- alert:' . 2>/dev/null) <<'EOF'
   import re, sys
   for path in sys.argv[1:]:
       text = open(path, encoding="utf-8").read()
       for block in re.split(r"\n\s*- alert:", "\n" + text)[1:]:
           name = block.split("\n", 1)[0].strip()
           sev = re.search(r"severity:\s*['\"]?(\w+)", block)
           print(f"{path}: {name}: severity {sev.group(1) if sev else 'none'}, runbook {'yes' if 'runbook_url' in block else 'missing'}")
   EOF
   ```

   For each paging alert, classify it: a symptom users see (errors, latency, unavailability, wrong or late data) or a cause (CPU, memory, disk, one failed instance). Propose: cause alerts move to ticket severity, alerts without a runbook get one (the `docs` module has a `runbook` skill) or stop paging, and services with an SLO page on burn rate (see the `slo` skill).
6. **Adopt the handover checklist.** Agree where the handover happens (a call, a chat thread, a ticket) and keep the checklist on the page.
7. **Set the review.** Monthly: pages per shift, the share that needed action, pages outside working hours, alerts without a runbook, time to acknowledge. Name the owner of the review.
8. **Write the page.** Fill `docs/sre/on-call.md`: front matter, rotation, load limits, escalation, paging rules, handover, review. Replace every `<placeholder>`. Add the page to the table in `docs/sre/index.md`.
9. **Check.** With the `docs` module, run `python3 scripts/build_docs.py --check`.
10. **Report.**

## Output

The page path, the rotation and the load per person, the escalation settings for the paging tool, the alert audit (paging alerts by symptom or cause, alerts without runbook) with the proposed change for each, and the open questions for the user.

## Rules

- A page goes to a person only for a symptom users see, and only with a runbook link.
- The skill changes no paging tool setting and no alert rule by itself. It proposes, and the user applies.
- On-call pay, time off and working-time limits are decisions the user makes with the people concerned. The page records them; the skill does not set them.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/on-call/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
