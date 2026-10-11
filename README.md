**English** · [Deutsch](README_de.md)

# cto-powersuit

[![skills.sh](https://skills.sh/b/uncovertechtalent/cto-powersuit)](https://skills.sh/uncovertechtalent/cto-powersuit)

Agent skills for the work of a CTO, one plugin per function, in one Claude Code plugin marketplace. A team installs the modules it needs and runs them on generic defaults.

Each skill also reads a private overlay when one exists: your own data for that module, kept outside the repository. See [Overlay](#overlay-your-private-layer).

## Modules

| Plugin | What it does | Needs |
|---|---|---|
| `decisions` | RFCs, architecture decision records (ADRs) and a review of the decision log. Templates for both records and a gate check that every ADR has a status, an owner and a date. | Python 3.9+ for the gate check |
| `docs` | A docs tree where every page has an owner and review dates, runbooks, and a sweep for stale pages. A static docs build and a gate check on the review fields. | Python 3.9+ |
| `gate` | A deploy gate: a rules folder with pass and fail fixtures per rule, run records, findings that close only on a passing rerun, and a workflow whose deploy job waits for the gate. The checks of the other modules run in it. | Python 3.9+, GitHub Actions for the workflow |
| `sdlc` | The lifecycle that ties the modules together: an audit that ranks the missing stages of a repository built without one, the lifecycle map, tickets, review for agent-written changes, test strategy, and release with rollback. A gate check that every change names a ticket or a decision. | Python 3.9+, git |

## Knowledge infrastructure

These three plugins are the knowledge infrastructure layer ([what knowledge infrastructure for LLMs means](https://coetzeestefan.substack.com/p/knowledge-infrastructure-for-llms)). `vault` is the knowledge base and its retrieval, `vestige` enforces your rules at the output boundary, and `stance` adds boundary rules plus verification through the receipts standard. Each one replaces a manual install (copy files into `~/.claude/`, then edit `settings.json` by hand) with two commands.

| Plugin | What it does | Needs |
|---|---|---|
| `vestige` | An output filter you calibrate to yourself. `/vestige:calibrate` mines your own transcripts for the moments you pushed back and builds your catalog from them. Hooks scan every reply and every Markdown file Claude writes. | Node 14+ |
| `vault` | A plain-Markdown vault with hybrid keyword and semantic search, served to Claude as an MCP server. Skills to create the vault, seed it from an interview and atomize documents into it. | [uv](https://docs.astral.sh/uv/) (Python 3.12+) |
| `stance` | Stance filters against the trained accommodation reflex: `professional-b2` (plain register, no politeness vestiges), `good-chad` (holds position under pushback, no grovel), `receipts` (probe before you assert), `poles` (decisions without the hedge) and `mode-leak` (speech devices in writing). | Node 14+, bash |

The plugins are independent. Install the ones you need. Each module works without the others; the gate checks of the modules need `gate` to run in CI. On an existing repository, start with `/sdlc:sdlc-audit`: it needs no other module and names the module that fills each gap.

## Install

```bash
claude plugin marketplace add uncovertechtalent/cto-powersuit
claude plugin install decisions@cto-powersuit
claude plugin install docs@cto-powersuit
claude plugin install gate@cto-powersuit
claude plugin install sdlc@cto-powersuit
claude plugin install vestige@cto-powersuit
claude plugin install vault@cto-powersuit
claude plugin install stance@cto-powersuit
```

Inside Claude Code the same works as `/plugin marketplace add ...` and `/plugin install ...`. Restart Claude Code after installing.

From a local clone: `claude plugin marketplace add /path/to/cto-powersuit`.

With the [skills CLI](https://skills.sh), for Claude Code and other agents:

```bash
npx skills add uncovertechtalent/cto-powersuit
```

The skills CLI copies the skill folders only. Skills that copy templates, the hooks and the MCP server need the plugin install above or a clone of this repository.

## Overlay: your private layer

Every skill in this repository works on generic defaults. Each one also checks for an overlay: a folder you keep outside the repository with your own data for that module, such as rubrics, calibrations, past decisions, incident history and local conventions.

Set `POWERSUIT_OVERLAY` to the overlay root, in your shell or in the `env` block of `settings.json`. One folder per module, named after the plugin:

```text
$POWERSUIT_OVERLAY/
  decisions/
    README.md      what this overlay holds; every skill in the module reads it first
    adr/           files for one skill, named after the skill
  docs/
  gate/
  vestige/
```

Read order for skill `<skill>` in module `<module>`:

1. `$POWERSUIT_OVERLAY/<module>/README.md`, if present.
2. `$POWERSUIT_OVERLAY/<module>/<skill>/`, if present.
3. The defaults in the skill itself.

Where the overlay and the skill disagree, the skill follows the overlay. With the variable unset or the module folder missing, the skill runs on its defaults and does not ask for an overlay.

Nothing from an overlay goes into this repository. Keep it in a private location with no public remote. A team that installs the modules builds its own overlay over time from its decisions, incidents, docs and cost history.

## Module layout

Each module is one plugin under `plugins/<module>/` with four parts:

| Part | Path in the plugin | What it is |
|---|---|---|
| Skills | `skills/<skill>/SKILL.md` | One task per skill, in the Agent Skills format. Every skill checks the overlay first. |
| Templates | `templates/` | Files that land in the client repository, laid out at the paths they take there. Skills copy them and never overwrite an existing file. |
| Gate check | `checks/<rule>.py`, `checks/fixtures/<rule-id>/pass/` and `fail/` | A rule the deploy gate of the `gate` module can run. The two fixtures are small repository trees: the rule must pass on `pass/` and fail on `fail/`. |
| Demo | one line in the module's `README.md` | The page on machinebehavior.io/inside where the module runs in public. |

The plugin also needs `.claude-plugin/plugin.json` and an entry in `.claude-plugin/marketplace.json`.

The knowledge infrastructure plugins (`vestige`, `vault`, `stance`) predate this layout and keep their own structure.

## vestige

Run `/vestige:calibrate` first. Until you do, the hooks use a small starter table (praise openers, service closers, filler idioms, stage hooks). Calibration writes two files you own, outside the plugin, so plugin updates never overwrite them:

- `~/.claude/skills/output-filter/SKILL.md`: your filter skill, written from the template in `plugins/vestige/templates/output-filter/`. The template is not a skill until calibration fills it.
- `~/.claude/vestige-patterns.js`: your rule table. The hooks load it in place of the starter table.

Hit logs go to `~/.claude/vestige-scan.log` and `~/.claude/guess-scan.log`. `node <plugin>/hooks/analyze-log.js` turns the log into promote and retire candidates. All paths follow `CLAUDE_CONFIG_DIR` when you set it.

Hooks: a Stop hook scans each reply (`vestige-scan.js`) and checks the paths it names (`guess-scan.js`); a PostToolUse hook scans `.md` files after Write and Edit (`vestige-write-scan.js`). The method and its limits: [vestige-kit](https://github.com/uncovertechtalent/vestige-kit).

## vault

1. `/vault:vault-init` copies the starter vault to `~/vault`. It never overwrites a file.
2. `/vault:seed` interviews you and builds the structure from your own domains.
3. The `vault-search` MCP server gives Claude `vault_search`, `vault_read`, `vault_ask`, `vault_reindex` and `vault_list_tags`.

For a vault somewhere else, set the plugin option: `/plugin configure vault@cto-powersuit` in Claude Code, or `claude plugin install vault@cto-powersuit --config vault_path=/path/to/vault`. Restart Claude Code after changing it.

The private boundary: folders listed in `.vsearchignore` at the vault root, and notes tagged `private`, `status/private` or `status/sensitive`, are never indexed, never returned and refused by `vault_read`. The first search run downloads about 130 MB of embedding weights. Details: [vault-kit](https://github.com/uncovertechtalent/vault-kit).

## stance

The stance plugin is on by default. At session start its hooks load `receipts`, `professional-b2` (level `full`), `good-chad` and two example pairs of corrected output. On every prompt the mode trackers re-inject a one-line reminder for each active mode.

Switch modes in the session: `/stance:professional-b2 lite|full|ultra`, `b2 mode`, `stop b2`, `/stance:good-chad off`, `stop good chad`, `normal mode` (all off). `poles` and `mode-leak` run only when you invoke them.

Change the defaults with environment variables (shell, or the `env` block in `settings.json`):

| Variable | Values | Default |
|---|---|---|
| `PROFESSIONAL_B2_DEFAULT_MODE` | `off`, `lite`, `full`, `ultra` | `full` |
| `GOOD_CHAD_DEFAULT_MODE` | `off`, `on` | `on` |
| `STANCE_RECEIPTS` | `off`, `on` | `on` |
| `STANCE_EXEMPLARS` | `off`, `on` | `on` |

The filters are text in the context window, so the model drifts from them over a long session. The hooks repeat them on every turn, and the `vestige` Stop hook catches the slice a regex can see. You, reading the output, are the check that holds.

Optional extra: [caveman](https://github.com/JuliusBrussee/caveman) (third party) compresses the output. It stacks with `professional-b2` and `good-chad`.

## Moving from the manual install

If you copied the kits into `~/.claude/` before, remove the copied hook entries from `~/.claude/settings.json` and the copied skills from `~/.claude/skills/` after installing the plugins. Otherwise every reply is scanned twice and the skills load twice. Keep your calibrated `vestige-patterns.js`: move it from `~/.claude/hooks/` to `~/.claude/`.

## Check a change

```bash
claude plugin validate --strict .
for p in plugins/* plugins/*/skills; do claude plugin validate --strict "$p"; done
python3 scripts/test_checks.py
```

`scripts/test_checks.py` runs every module's gate check with the gate runner against its pass and fail fixtures. It needs Python 3.9+ and exits 1 when a check passes a fail fixture or fails a pass fixture.

## License

MIT. `plugins/stance/THIRD_PARTY_NOTICES.md` lists the code adapted from caveman.
