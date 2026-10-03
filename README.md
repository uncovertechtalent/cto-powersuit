# utt-kits

Knowledge infrastructure for LLMs.

These plugins are its tools layer. `vault` is the knowledge base and its retrieval, `vestige` enforces your rules at the output boundary, and `stance` adds boundary rules plus verification through the receipts standard.

Three Claude Code plugins in one marketplace. Each one replaces a manual install (copy files into `~/.claude/`, then edit `settings.json` by hand) with two commands.

| Plugin | What it does | Needs |
|---|---|---|
| `vestige` | An output filter you calibrate to yourself. `/vestige:calibrate` mines your own transcripts for the moments you pushed back and builds your catalog from them. Hooks scan every reply and every Markdown file Claude writes. | Node 14+ |
| `vault` | A plain-Markdown vault with hybrid keyword and semantic search, served to Claude as an MCP server. Skills to create the vault, seed it from an interview and atomize documents into it. | [uv](https://docs.astral.sh/uv/) (Python 3.12+) |
| `stance` | Stance filters against the trained accommodation reflex: `professional-b2` (plain register, no politeness vestiges), `good-chad` (holds position under pushback, no grovel), `receipts` (probe before you assert), `poles` (decisions without the hedge) and `mode-leak` (speech devices in writing). | Node 14+, bash |

The plugins are independent. Install one, two or all three.

## Install

```bash
claude plugin marketplace add uncovertechtalent/utt-kits
claude plugin install vestige@utt-kits
claude plugin install vault@utt-kits
claude plugin install stance@utt-kits
```

Inside Claude Code the same works as `/plugin marketplace add ...` and `/plugin install ...`. Restart Claude Code after installing.

From a local clone: `claude plugin marketplace add /path/to/utt-kits`.

## vestige

Run `/vestige:calibrate` first. Until you do, the hooks use a small starter table (praise openers, service closers, filler idioms, stage hooks). Calibration writes two files you own, outside the plugin, so plugin updates never overwrite them:

- `~/.claude/skills/output-filter/SKILL.md`: your filter skill.
- `~/.claude/vestige-patterns.js`: your rule table. The hooks load it in place of the starter table.

Hit logs go to `~/.claude/vestige-scan.log` and `~/.claude/guess-scan.log`. `node <plugin>/hooks/analyze-log.js` turns the log into promote and retire candidates. All paths follow `CLAUDE_CONFIG_DIR` when you set it.

Hooks: a Stop hook scans each reply (`vestige-scan.js`) and checks the paths it names (`guess-scan.js`); a PostToolUse hook scans `.md` files after Write and Edit (`vestige-write-scan.js`). The method and its limits: [vestige-kit](https://github.com/uncovertechtalent/vestige-kit).

## vault

1. `/vault:vault-init` copies the starter vault to `~/vault`. It never overwrites a file.
2. `/vault:seed` interviews you and builds the structure from your own domains.
3. The `vault-search` MCP server gives Claude `vault_search`, `vault_read`, `vault_ask`, `vault_reindex` and `vault_list_tags`.

For a vault somewhere else, set the plugin option: `/plugin configure vault@utt-kits` in Claude Code, or `claude plugin install vault@utt-kits --config vault_path=/path/to/vault`. Restart Claude Code after changing it.

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
claude plugin validate --strict plugins/vestige
```

## License

MIT. `plugins/stance/THIRD_PARTY_NOTICES.md` lists the code adapted from caveman.
