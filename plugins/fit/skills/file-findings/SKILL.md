---
name: file-findings
description: >
  File the findings of a CTO review as GitHub Issues in the company's own
  repository, labelled by area (area:direction to area:knowledge), kind
  (kind:finding, kind:decision, kind:action) and severity, and write one
  scorecard per area with the checks run, the findings by severity, and a
  one-line verdict. A dry run prints every issue before anything is created;
  with the user's go it creates the missing labels and the issues, and never
  files an item of the same review twice. Use at the end of a review or a pilot, when the
  findings should land in the team's own tracker or on the cockpit. Activates
  on "/file-findings", "file the findings", "turn the findings into issues",
  "write the scorecard", "scorecard per area".
user-invocable: true
---

# File findings

Each check of a review produces findings. This skill puts them where the team already works: one GitHub Issue per finding, decision, or action, in the company's own repository, with the labels the cockpit reads (machinebehavior.io/inside/cockpit/). It also writes the scorecard per area from the same file, so the scorecard and the tracker agree.

## Labels

| Label | Values |
|---|---|
| `area:<key>` | `area:direction`, `area:delivery`, `area:operations`, `area:money`, `area:security`, `area:ai`, `area:people`, `area:knowledge` |
| `kind:<kind>` | `kind:finding` (a gap a check found), `kind:decision` (a choice still to make), `kind:action` (work to do). `kind:lead` exists for the cockpit; a review never files one, and `--create` never adds that label |
| `severity:<level>` | `severity:critical`, `severity:high`, `severity:medium`, `severity:low`: the fix-by windows of `/security:vuln-intake`, 7, 30, 90, and 180 days. Every finding has one; a decision or an action may |

There is no space after the colon. The labels of `/sdlc:ticket` (`area: <part>`, with a space) name parts of the system and live next to these. The colours and descriptions of the area and kind labels are the cockpit's.

## Steps

1. **Collect the findings in one file.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/review/findings.json` to the review folder. Keep that folder outside the repository under review unless the team wants the file there. Each item has:
   - `id` (such as `SEC-1`);
   - `area`, `kind`, and `severity`;
   - `title`: one line naming the gap, at most 300 characters;
   - `evidence`: a file and line, or the check and its result;
   - `fix` and `check`: the change, and the skill that found it. Only `evidence` and `fix` may span lines;
   - `private: true` for an item outside the security area that must not go into a public issue, such as an AI agent that can read customer data.

   Mask any secret: give its kind, its prefix, and a hash prefix, as `/security:secrets` prints them, and never the value. Set `date` to the review day: it marks each issue as this review's. List every check under `checks`, each `ran` or `not run` with the reason. Write one verdict per area under `verdicts`.
2. **Check the file.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-findings/file_findings.py" check findings.json
   ```

3. **Dry run.** Print every issue as it would be filed, with its title, labels, and body:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-findings/file_findings.py" issues findings.json --repo <owner>/<repo>
   ```

   Show the output to the user. The user edits the file and you run the dry run again until the user says go.
4. **File them, with the user's go.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-findings/file_findings.py" issues findings.json --repo <owner>/<repo> --create
   ```

   It creates the labels that are missing, and leaves existing labels as they are, whatever their case. It prints the link of each new issue.
   - An item this review already filed, found by the `<date>/<id>` marker in an issue body, open or closed, is skipped. A second run files nothing twice.
   - An item whose title an existing issue already has is held, with that issue's link. Check it, then run again with `--force` to file the item anyway. An older review that used the same ids has another date, so its issues never block this one.
   - On a public repository, every item of the security area, whatever its kind, and every item marked `private` stops the run. A public issue discloses a hole before the fix. File them as a private security advisory or in a private tracker, then run again without them.
   - A string anywhere in the file that matches a secret pattern stops the run in every mode.
   - `--create` needs the review date in the file, and triage or write access. It stops before any write when the access is read-only. In a review with read-only access, give the team the file and the dry-run output, and the team runs `--create`.
5. **Write the scorecard.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-findings/file_findings.py" scorecard findings.json --out scorecard.md
   ```

   It writes one row per area in the cockpit's order, then a section per area with its checks, its findings by severity, its open decisions and actions, and the verdict. Only areas with a check or an item appear. A missing verdict prints a placeholder: fill it in the file and run the command again. `${CLAUDE_PLUGIN_ROOT}/templates/docs/scorecard.md` has the same shape for writing by hand, with docs front matter.

## Output

`findings.json`, the dry-run listing, the links of the filed issues, and the scorecard.

## Rules

- Never create a label or an issue without the user's go. The dry run comes first.
- One finding, decision, or action per issue.
- No secret value, no customer data, and no person's name in an issue.
- Security items, and items marked private, never go into a public issue.
- A review files no `kind:lead`.

## Check the script

`python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-findings/test_file_findings.py"` runs the validation, the labels, the dry run, filing with a fake `gh`, the second run, the marker and title matches, the public-repository guard, the refusals (access, date, a failed label), and the scorecard. Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/fit" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/fit/` exists, read its `README.md` first, then the files in `fit/file-findings/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
