---
name: prediction-hash
description: >
  Write a dated prediction file before a page goes live, compute its sha256, add
  the line to predictions/HASHES.txt and commit both, so a third party can check
  that the prediction was not changed after the result came in. Use when a page
  makes a claim about a future result (an answer engine experiment, a probe
  reading, an evaluation) and the claim must be fixed in public before the page
  goes live. Activates on "/prediction-hash", "hash a prediction", "preregister
  this", "freeze the prediction", "add to HASHES.txt".
user-invocable: true
---

# Prediction hash

Fixes a prediction before the page it belongs to goes live. The file is plain text with a date in its name; its sha256 goes into `predictions/HASHES.txt`; both land in one commit. From then on the hash shows whether the text changed. The gate check `aieo.prediction-hashes` fails a deploy when a listed file is missing or changed, or when a prediction file is not listed.

## Inputs

- The page the prediction belongs to, and its URL.
- The prediction: what is measured, how (engines, queries, runs, what counts as a hit), the reading date, and the result that refutes it.

## Steps

1. **Copy the templates** without overwriting:

   ```bash
   mkdir -p predictions
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/predictions/HASHES.txt" "${CLAUDE_PLUGIN_ROOT}/templates/predictions/README.md" predictions/
   ```

2. **Write the file** `predictions/<slug>-<YYYY-MM-DD>.txt` with the layout in `predictions/README.md`: what is predicted, the page, the date of writing, the probe, numbered predictions with a reading date, and what refutes each one. Plain UTF-8 text with a final newline. If the file name exists, stop: a hashed file is never replaced.
3. **Read it back to the user** in full and get a clear yes. After the next step the text is fixed.
4. **Compute the hash:**

   ```bash
   shasum -a 256 predictions/<file>     # macOS
   sha256sum predictions/<file>         # Linux
   ```

5. **Append to `predictions/HASHES.txt`**, below the existing lines: one note line (what the prediction covers, the page, "hashed <YYYY-MM-DD> before the page went live"), then the entry line:

   ```text
   <file name>  sha256 <64 hex digits>
   ```

   Never change an existing line.
6. **Verify.** Recompute the hash and compare it with the entry. With the gate installed:

   ```bash
   python3 .github/actions/gate/run.py --only aieo.prediction-hashes
   ```

7. **Commit both files in one commit** before the page goes live, when the user says so:

   ```bash
   git add predictions/<file> predictions/HASHES.txt
   git commit -m "Hash prediction <slug> before publication"
   ```

   The commit date comes from the committer's clock. A push to a public remote before the page goes live gives a date a third party can check.
8. **Corrections.** A wrong prediction file stays as it is. Write a new file (`<slug>-<YYYY-MM-DD>-v2.txt` or a new date) that names the file it corrects and why, hash it with the same steps, and publish both.

## Output

The prediction file, its line in `HASHES.txt`, the sha256, the verify result and the commit command.

## Rules

- Never edit, rename or delete a hashed file. Never change a line in `HASHES.txt`.
- Hash before the page goes live and before any reading of the result.
- Files whose name starts with `_` are drafts. They are not hashed and the gate check skips them.
- If git converts line endings in the repository, add `predictions/*.txt -text` to `.gitattributes` with the user, so the bytes on disk match the hash on every checkout.
- Publish the result next to the prediction whichever way it lands.
- Never push without the user.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/aieo" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/aieo/` exists, read its `README.md` first, then the files in `aieo/prediction-hash/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
