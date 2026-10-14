---
title: Scorecard
summary: Where each area of the CTO job stands after the review, with the checks run, the findings by severity, and a one-line verdict per area.
labels: review, scorecard, fit
owner: <who owns the review>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
<review name>, <YYYY-MM-DD>. Repository: <owner>/<repo>. The findings are GitHub Issues with the labels `area:<area>`, `kind:<kind>`, and `severity:<level>`. `python3 <file-findings skill folder>/file_findings.py scorecard findings.json` fills this page from the same file that filed them.

| Area | Checks run | Critical | High | Medium | Low | Verdict |
|---|---:|---:|---:|---:|---:|---|
| <Area> | <n> | <n> | <n> | <n> | <n> | <one line> |

## <Area>

| Check | Status |
|---|---|
| `/<plugin>:<skill>` | ran |
| `/<plugin>:<skill>` | not run: <why> |

| Severity | Findings |
|---|---:|
| Critical | <n> |
| High | <n> |
| Medium | <n> |
| Low | <n> |

Decisions open: <n>. Actions: <n>. Items: <finding ids>.

Verdict: <one line: where this area stands and the first thing to do>

Severity is the fix-by window of `/security:vuln-intake`: critical 7 days, high 30, medium 90, low 180.
