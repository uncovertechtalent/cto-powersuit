---
title: Predictions
summary: Dated prediction files, written and hashed before the page they belong to goes live, with their sha256 in HASHES.txt.
owner: <person or team that publishes the predictions>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
A prediction file states what you expect to happen after a page goes live, in terms a third party can check: the query, the engines, the date of the reading and the result that refutes the prediction. It is written and hashed before the page goes live, so nobody can adjust it to the result.

## Files

| File | What it is |
|---|---|
| `<slug>-<YYYY-MM-DD>.txt` | One prediction, dated the day it was written. Plain text |
| `HASHES.txt` | One line per prediction file: `<file name>  sha256 <64 hex digits>`, with a note line above it on the page and the date of hashing |
| `_<name>.txt` | A draft. Files whose name starts with `_` are not hashed and the gate check skips them |

## Rules

1. Write the file, compute its sha256, add the line to `HASHES.txt`, and commit both files in one commit before the page goes live. The commit date is the public timestamp.
2. Never edit a file after it is hashed. A correction is a new file with a new date or a `-v2` suffix that names the file it corrects.
3. Publish the result next to the prediction whichever way it lands.

Compute the hash with `shasum -a 256 <file>` (macOS) or `sha256sum <file>` (Linux). The gate check `aieo.prediction-hashes` fails when a listed file is missing or changed, or when a prediction file is not listed.

## Prediction file layout

```text
Prediction record: <what is predicted>
Page: <URL of the page the prediction belongs to>
Written and hashed on <YYYY-MM-DD>, before the page went live.

THE PROBE
<engines, queries, runs per query, what counts as naming and as citing>

THE PREDICTIONS
P1. On <YYYY-MM-DD>, <a result a third party can check>.

WHAT REFUTES IT
<the result that refutes each prediction>
```
