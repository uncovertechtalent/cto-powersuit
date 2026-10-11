---
title: Threat model, <RFC number or change in a few words>
summary: <one sentence: the change, the most serious threat found, and what the team does about it>
parent: security
labels: security, threat-model, <system>
owner: <person who owns the change>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, the day the change ships plus 180 days>
type: reference
rfc: <rfc-NNNN, an issue link or a pull request link>
status: draft
---
## Scope

<The change in two or three sentences, with a link to the RFC or the pull request. What this model leaves out, and why.>

## Assets

| Asset | What it is | Owner | Harm if it leaks, changes or stops |
|---|---|---|---|
| <customer records> | <table, bucket or service> | <team> | <one sentence> |
| <deploy credentials> | <secret name and where it lives> | <team> | <one sentence> |

## Entry points and trust boundaries

<Every place where input crosses from a less trusted side to a more trusted one: public endpoints, file uploads, webhooks, CI triggers on pull requests from forks, third-party actions and packages, agent skills and MCP servers, text an agent with tools reads (issues, web pages, documents).>

| Entry point | From | To | Who can send input |
|---|---|---|---|
| <POST /api/import> | <internet> | <import worker> | <any signed-in user> |

## Threats

One row per threat. Category: S spoofing, T tampering, R repudiation, I information disclosure, D denial of service, E elevation of privilege. Likelihood and impact: low, medium or high.

| Id | Category | Threat | Entry point | Likelihood | Impact | Mitigation | Owner | Ticket | Status |
|---|---|---|---|---|---|---|---|---|---|
| T1 | <E> | <An agent with write access follows instructions hidden in an issue it reads> | <issue text> | <medium> | <high> | <read-only token for the triage agent; writes need a human approval> | <name> | <#123> | open |

## Supply chain and secrets

- New third-party actions, packages, agent skills or MCP servers: <list, each with its row in the provenance log, or none>.
- New secrets: <list, each with its rotation runbook, or none>.
- New permissions: <tokens, roles, deploy keys, or bypass rights the change adds, or none>.

## Residual risk

<The threats left open after the mitigations, and who accepted them on which date. An accepted threat names one person.>

## Review

| Date | Reviewer | Result |
|---|---|---|
| YYYY-MM-DD | <name> | <approved, or the changes asked for> |
