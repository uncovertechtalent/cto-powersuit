---
title: Provenance log
summary: Every third-party action, agent skill and MCP server this repository or its agents run, with the provenance check that let it in.
parent: security
labels: security, supply-chain, provenance
owner: <person or team that approves new sources>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
Add a row before anything new is installed or referenced. A row with verdict `stop` stays in the log, so the same source is not checked twice. Remove a row only when the source is removed from the repository and from every agent configuration.

| Source | Kind | Expected owner and where it is named | Pinned to | Verdict | Signals | Date | Reviewer |
|---|---|---|---|---|---|---|---|
| `<owner/repo>` | action, skill or MCP server | `<owner>`, from `<registry entry or vendor docs URL>` | `<40-character commit SHA or package version>` | proceed, check or stop | `<signal ids from provenance.py, or none>` | YYYY-MM-DD | `<name>` |
