---
name: answer-probe
description: >
  Ask AI search engines and assistants a fixed, versioned query set and record
  per answer whether it names the entity, links it and states the expected
  facts correctly, with dated JSON results and a trend over runs of the same
  query set version. Use when a team wants to know whether AI answers name and
  cite its site, before and after a change, without third-party tracking tools.
  Activates on "/answer-probe", "probe the AI engines", "do AI answers cite
  us", "run the answer probe", "AI search visibility".
user-invocable: true
---

# Answer probe

Runs a fixed query set against AI search engines and assistants and scores each answer on three questions: does it name the entity, does it link one of the entity's domains, and does it state each expected fact correctly. The script `aieo/probe.py` writes one dated JSON file per run. A trend compares runs of the same query set version only, because results from a changed query set are not comparable.

The probe records what one engine answered on one day. The cause of a citation is not in the data.

## Inputs

- The entity: the names the pages use, and its domains.
- The facts an answer should state, each with a pattern for a correct statement and, where known, a pattern for a wrong one.
- The engines to probe. Manual mode works for any engine with a chat or search page. The adapter mode needs an engine with an API and a key.

## Steps

1. **Copy the templates** without overwriting:

   ```bash
   mkdir -p aieo/results
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/aieo/probe.py" "${CLAUDE_PLUGIN_ROOT}/templates/aieo/queries.json" aieo/
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/aieo/results/README.md" aieo/results/
   ```

2. **Write the query set** in `aieo/queries.json` with the user. Ten to twenty queries in four groups:

   | Group | What it asks |
   |---|---|
   | `definition` | A term the pages define, in the words a user would type |
   | `entity` | The entity by name |
   | `problem` | A problem one of the pages answers, without naming the entity |
   | `control` | A contested query where the entity is not expected to appear. A named entity here is a result to explain |

   Fill `entity.names`, `entity.domains` and the `facts`. Patterns are Python regular expressions, matched without case. The script exits with an error while a value is still an angle-bracket placeholder.
3. **Freeze the version.** Set `frozen` to today and keep `version` at `1`. From now on, any change to a query, a fact or the entity raises the version. Optional: copy the set to `predictions/aieo-query-set-v1-<YYYY-MM-DD>.txt` and hash it with `/aieo:prediction-hash`, so the set is fixed in public before the first run.
4. **Set up the engines.**
   - Manual mode: a fresh session per run, logged out or on a measurement account with no history. Note language and country in the label, for example `--label <engine>-en-de`.
   - Adapter mode: list the adapters with `python3 aieo/probe.py adapters`. The example adapter `http-json` reads its endpoint, key, request body and response paths from environment variables. Check before use: the engine's API reference and its terms on automated queries. To add an engine, subclass `Adapter` in `probe.py`, set `name` and `env`, implement `ask()` and add it to `ADAPTERS`.
   - Keys go in environment variables only. Never write a key into a file, a command line in the transcript or a result.
5. **Run.** Three samples per query, because one answer is one sample:

   ```bash
   python3 aieo/probe.py run --label <engine label> --samples 3
   python3 aieo/probe.py run --engine http-json --label <engine label> --samples 3
   ```

   In manual mode the script prints each query. The user asks the engine, pastes the answer with its source links, and ends it with a line holding only `.`. Answers can also come from a file in query order, each ended by a `.` line: `python3 aieo/probe.py run --label <engine label> < answers.txt`.
6. **Read the rows** where a fact is `absent` or `wrong`, with the user. If a pattern scored a correct answer as absent, fix the pattern, raise the version and run again. Keep the old result file.
7. **Show the trend:**

   ```bash
   python3 aieo/probe.py trend
   ```

   It prints one row per run of the current version, per engine: answers, named, linked, facts correct and wrong, and control queries that named the entity. It skips runs of other versions and runs whose query set changed without a new version.
8. **Keep a rhythm.** The same query set, the same engines and the same sample count, on a fixed weekday. Commit each result file.

## Output

One result file per run in `aieo/results/`, the trend table, and a short report: what changed since the last run of the same version, the rows the user checked by hand, and what the probe leaves out (answers in the engine's own app can differ from its API; other engines are not covered).

## Rules

- Never write an answer yourself. In manual mode every answer is pasted by the user from the engine, as shown.
- Compare runs of one query set version only. A changed query is a new version.
- No baseline claim before a run exists. No claim that a change on the site caused a citation.
- Keys come from environment variables only and never appear in results, files or the transcript.
- Never edit a result file. A rescored run is a new run.
- Never overwrite an existing file with a template. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/aieo" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/aieo/` exists, read its `README.md` first, then the files in `aieo/answer-probe/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
