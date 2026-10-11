---
title: Engineering
summary: "How the systems are built, deployed and run: architecture, pipelines and runbooks."
owner: <owner>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD>
type: reference
labels: engineering
---
This space documents the systems of <team or product>: how each one is built, how it reaches production and what to do when it fails.

## Systems

| System | What it does | Source | Page |
|---|---|---|---|
| <system> | <one line> | `<path or repository>` | <link to its page, once the page exists> |

## Start here

- [Runbooks](doc:eng/runbooks): one page per symptom, with checks, steps, how to verify the fix and when to escalate.

## Write a page

Copy `docs/_templates/page.md` to `docs/eng/<slug>.md`, fill the front matter and build with `python3 scripts/build_docs.py --check`. Link other pages with `[text](doc:<space>/<slug>)`.
