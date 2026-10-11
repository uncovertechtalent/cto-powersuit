---
title: Answer probe results
summary: One JSON file per probe run of aieo/probe.py, named by date, engine label and query set version.
owner: <person or team that runs the probe>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This folder holds the results of `aieo/probe.py run`. One file per run: `<YYYY-MM-DD>-<engine label>-v<query set version>.json`. A second run on the same day gets a `-2` suffix. No file here is overwritten.

Each file records the query set version and its sha256, the engine label, the model id where the engine shows one, and one row per answer: query id, group, sample number, whether the answer names the entity, whether it links one of the entity's domains, the cited URLs, the state of each expected fact (`correct`, `wrong` or `absent`) and the answer text.

Compare runs with `python3 aieo/probe.py trend`. The trend reads only runs of one query set version and skips a run whose query set sha256 differs from the others of that version.

Keep raw answers here as they came. Correct a scoring error with a new run or a note in the run's commit message, and leave the file as written.
