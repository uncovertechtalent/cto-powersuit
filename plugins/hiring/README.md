# hiring

Structured hiring for engineering roles. A loop for a role is built from the outcomes the person must deliver: the outcomes give a short list of signals, and each signal is collected once, in one stage. Each signal has a rubric dimension with fixed questions and four levels, and each level has an anchor that describes observable behaviour. The rubric is written before the first interview. In the debrief, every interviewer submits evidence and a level before seeing other scores, the discussion starts with the evidence, and the decision comes last with its reasons on record.

The module also writes the profile of the next platform owner: the systems in the repository that person will own, the skills each system needs, and where in the loop a candidate shows each skill.

The skills prepare, check and record. Interviewers score and the panel decides; no skill scores a candidate.

Install:

```bash
claude plugin install hiring@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/hiring:interview-loop` | Writes `hiring/loop.md`: outcomes, must-haves, stages, the interviewer role per stage and a signal map in which each signal appears in one stage |
| `/hiring:interview-rubric` | Writes `hiring/rubrics/<role-slug>.json`: one dimension per signal with its stage, fixed questions and levels 1 to 4 with observable anchors, the hire bar, a calibration round and a freeze before the first interview |
| `/hiring:hiring-debrief` | Collects the independent scorecards, runs the evidence round, then the levels, then the decision, and records the reasons and any dissent with the candidate id |
| `/hiring:successor-profile` | Writes `docs/successor-profile.md`: the systems the next platform owner takes over, read from the installed modules and the docs, the skills per system, the stage and rubric dimension for each first-day skill, and the gaps |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/hiring/` (see the root README). The interview programme of a team (its questions, rubrics and calibration samples) belongs in the overlay.

## Templates

The skills copy these files into the client repository. An existing file is never overwritten.

| Lands at | What it is |
|---|---|
| `hiring/loop.md` | The loop page with docs front matter: role, outcomes, stages, signal map, interviewer rules, candidate information, decision rule |
| `hiring/rubrics/example-role.json` | An example rubric: role, hire bar and four dimensions, each with a signal, the stage that collects it, questions and levels `"1"` to `"4"` with anchors |
| `hiring/debrief-template.md` | The debrief record with docs front matter: scorecards, evidence round, levels with reasons for changes, hire bar, decision, dissent and follow-ups |
| `docs/successor-profile.md` | The successor profile with docs front matter: systems to own with their sources, skills per system, skills mapped to the loop, gaps |

A filled debrief holds personal data. The skill writes it to the place the team keeps candidate records and never into the repository. Rubrics and the loop hold no candidate data and can be committed.

## Gate check

`checks/rubric_anchors.py` defines the rule `hiring.rubric-anchors`. For each file that matches `hiring/rubrics/*.json` it reports:

| Snippet | Problem |
|---|---|
| `not valid JSON`, `not a JSON object` | The rubric cannot be read |
| `no dimensions` | `dimensions` is missing or empty |
| `dimension <n>: not an object` | A dimension is not a JSON object |
| `<dimension>: missing name`, `<dimension>: missing signal` | No name or no signal, or an empty one |
| `<dimension>: placeholder name`, `<dimension>: placeholder signal` | The value is still a placeholder in angle brackets |
| `<dimension>: missing levels`, `<dimension>: levels must be an object keyed 1 to N` | No levels, or levels in another shape |
| `<dimension>: level keys not consecutive from 1 (<keys>)` | The level keys do not run 1, 2, 3 and on without a gap |
| `<dimension>: level <k>: empty anchor`, `<dimension>: level <k>: placeholder anchor` | A level with no anchor, or an anchor still in angle brackets |

A level is a string anchor or an object with an `anchor` key. A value counts as a placeholder when no letter or digit is left after removing every `<...>` span, so an anchor such as "kept first replies < 4 hours" passes. The result is `fail` on any hit, `pass` when every rubric is clean and `n/a` when no file matches. Paths with a segment that starts with `_` are skipped, so a draft named `hiring/rubrics/_<role-slug>.json` is not checked. Option: `globs` (default `["hiring/rubrics/*.json"]`).

Enable it with `/gate:add-rule` (path A). By hand, from a clone of this repository:

1. Copy the rule: `cp -n plugins/hiring/checks/rubric_anchors.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -Rn plugins/hiring/checks/fixtures/hiring.rubric-anchors <repo>/gate/fixtures/`.
3. Add the rule to `gate/gate.json` on `warn`:

   ```json
   "hiring.rubric-anchors": {"tier": "warn"}
   ```

4. Move it to `"tier": "block"` once a false-positive test over your own rubrics is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures` checks the fixtures and the record.

Run it on its own with `python3 .github/actions/gate/run.py --only hiring.rubric-anchors --dry-run`.

Demo: no public page yet; the interview programme content stays in the private overlay.
