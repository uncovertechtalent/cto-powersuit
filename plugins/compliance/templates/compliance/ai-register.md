---
title: AI register
summary: Every AI system the team builds, buys or uses, its role and risk class under the EU AI Act, and the state of its legal review.
labels: compliance, ai-act
owner: <person or team that keeps this register current>
reviewed: <YYYY-MM-DD, the day the register was checked against the systems in use, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
One row per AI use. A use is one AI system in one purpose: the same model in two products is two rows. The `ai-act-triage` skill fills and updates this page.

References are article and annex numbers of Regulation (EU) 2024/1689 (AI Act) as amended. Read the text on EUR-Lex: <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>. This page holds no text of the regulation.

This triage prepares the question for legal review. A lawyer confirms the classification.

## AI uses

| ID | AI system and use | Our role | Model and supplier | Purpose | People affected | Class | Basis | Applies from | Obligations | Legal review | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AI-001 | <system: what it does, where it runs> | <provider, deployer, importer or distributor> | <model, supplier> | <one sentence> | <customers, employees, applicants, the public> | <prohibited, high-risk (Annex III), high-risk (Annex I), transparency, minimal> | <Art 5(1)(x), Art 6(2) with Annex III point n, Art 6(1) with Annex I, Art 50(n), none> | <YYYY-MM-DD> | <article numbers> | <open, or YYYY-MM-DD and reviewer> | <in use, planned, stopped> |

Class values:

- `prohibited`: a practice listed in Art 5. Stop the use and escalate.
- `high-risk (Annex III)`: a use case in Annex III, under Art 6(2), with no Art 6(3) exception documented.
- `high-risk (Annex I)`: a safety component of a product, or a product, under the Union harmonisation law in Annex I, under Art 6(1).
- `transparency`: a use under Art 50.
- `minimal`: none of the above. Art 4 applies to every provider and deployer.

## General-purpose AI models we provide

Fill this table only when the team places a general-purpose AI model on the market. Using a model through an API is a deployer row above.

| Model | Release | Systemic risk (Art 51) | Obligations | Legal review | Status |
|---|---|---|---|---|---|
| <model name> | <YYYY-MM-DD> | <yes or no, with the reason> | <Art 53; Art 55 when systemic risk> | <open, or YYYY-MM-DD and reviewer> | <status> |

## Dates

| Date | What applies |
|---|---|
| 2025-02-02 | Art 4 and Art 5 as first adopted |
| 2025-08-02 | Obligations for providers of general-purpose AI models |
| 2026-08-02 | Art 50 and the general date of application |
| 2026-12-02 | The points that Regulation (EU) 2026/1744 added to Art 5 |
| 2027-12-02 | High-risk systems under Art 6(2) and Annex III |
| 2028-08-02 | High-risk systems under Art 6(1) and Annex I |

Check before use: confirm the dates against the consolidated text on EUR-Lex.

## Changes

| Date | Change | By |
|---|---|---|
| <YYYY-MM-DD> | <row added, class changed, legal review done> | <name> |
