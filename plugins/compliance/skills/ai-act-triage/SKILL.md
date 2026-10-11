---
name: ai-act-triage
description: >
  Triage every AI use in a register under the EU AI Act: classify each one as a
  prohibited practice (Art 5), high-risk (Annex III use case or Annex I product
  safety), transparency obligations (Art 50) or minimal, record provider
  obligations for general-purpose AI models, and note the date from which each
  obligation applies. Prepares the question for legal review. Use when a team
  builds, buys or ships an AI feature, or before a customer or auditor asks for
  the AI inventory. Activates on "/ai-act-triage", "AI Act", "is this high
  risk", "classify our AI", "AI register", "AI inventory", "do we fall under the
  AI Act".
user-invocable: true
---

# AI Act triage

Keeps `compliance/ai-register.md`: one row per AI use, with the team's role, the risk class under Regulation (EU) 2024/1689 (AI Act) as amended, the article or annex point it rests on, the date the obligations apply and the state of the legal review.

This triage prepares the question for legal review. A lawyer confirms the classification.

## Sources

- The AI Act on EUR-Lex: <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>. Read the consolidated version, which includes the amendments by Regulation (EU) 2026/1744.
- Cite article, paragraph, point and annex numbers. Do not paste the text of the regulation into the register or any other file.
- Check before use: confirm the dates against the consolidated text on EUR-Lex.
- Check before use: confirm the article, paragraph and annex numbers in this skill against the same text.

## Inputs

- The AI uses: features the team builds that use a model, AI tools the team buys or uses internally, models the team trains or fine-tunes and releases.
- Per use: what it does, who uses its output, which people it affects, where it is offered (EU market or not) and the model and supplier.
- The team's role per use: provider (develops it, or has it developed, and places it on the market under its own name), deployer (uses it under its own authority), importer or distributor. Art 3 defines the roles.

## Steps

1. **Set up the register.** Copy without overwriting:

   ```bash
   mkdir -p compliance
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/compliance/ai-register.md" compliance/
   ```

   Fill `owner` and keep `reviewed: no` until a person checks the register against the systems in use.
2. **Find the AI uses.** Search the repository for model clients and inference code (`grep -rniE 'llm|inference|embedding|completion|model_id|model_name' --include='*.py' --include='*.ts' --include='*.js' .`), check the dependency files for client libraries of model providers, and ask the user for bought tools and internal uses (support, recruiting, monitoring of staff). One row per AI system per purpose, ids `AI-001` onwards.
3. **Set the role.** Record provider, deployer, importer or distributor. A team that changes the intended purpose of a system, or makes a substantial change to it, can become its provider (Art 25); flag such rows for the lawyer.
4. **Classify each use, in this order.** The first class that applies is the class. Read each referenced article on EUR-Lex for the use at hand, and record the point that applies in `Basis`.
   1. **Prohibited practice.** Compare the use with each point of Art 5(1), and with the points that Regulation (EU) 2026/1744 added to Art 5. A match: class `prohibited`, stop the use and escalate to the lawyer the same day.
   2. **High-risk, Annex I.** The system is a safety component of a product, or is itself a product, under the Union harmonisation law listed in Annex I, and that product needs a third-party conformity assessment (Art 6(1)). Class `high-risk (Annex I)`.
   3. **High-risk, Annex III.** The use falls under a point of Annex III (Art 6(2)). Record the point and sub-point. If the team relies on the exception in Art 6(3), record the reason and the documentation that Art 6(4) asks for, and flag the row for the lawyer. Class `high-risk (Annex III)`.
   4. **Transparency.** The use falls under Art 50(1), (2), (3) or (4). Record the paragraph. Class `transparency`. A high-risk system can carry Art 50 obligations too; record both in `Obligations`.
   5. **Minimal.** None of the above. Class `minimal`. Art 4 still applies to providers and deployers.
5. **General-purpose AI models.** Only when the team places a general-purpose AI model on the market, or modifies one and releases it: add a row to the second table with the obligations of Art 53, and Art 55 when the model has systemic risk under Art 51. Using a model through an API is a deployer row in the first table.
6. **Record the date and the obligations.** `Applies from` takes the date from the Dates table below. `Obligations` lists article numbers only, for example the provider obligations for high-risk systems in Chapter III Section 2 and Art 16, or the deployer obligations in Art 26 and Art 27.
7. **Prepare the legal review.** For each row with class `prohibited` or `high-risk`, each row that relies on Art 6(3), each role change under Art 25 and each row the user is unsure about: write the question for the lawyer in one or two sentences, with the facts of the use and the article numbers. Set `Legal review` to `open`. Only the lawyer's answer changes it to a date and a name.
8. **Check.** Every row has a role, a class, a basis (or `none` for minimal), a date and a legal review state. No row holds text copied from the regulation.
9. **Report.**

## Dates

As amended by Regulation (EU) 2026/1744:

| Date | What applies |
|---|---|
| 2025-02-02 | Art 4 and Art 5 as first adopted |
| 2025-08-02 | Obligations for providers of general-purpose AI models |
| 2026-08-02 | Art 50 and the general date of application |
| 2026-12-02 | The points that Regulation (EU) 2026/1744 added to Art 5 |
| 2027-12-02 | High-risk systems under Art 6(2) and Annex III |
| 2028-08-02 | High-risk systems under Art 6(1) and Annex I |

Check before use: confirm the dates against the consolidated text on EUR-Lex.

## Output

- `compliance/ai-register.md` with one row per AI use and, if any, one row per general-purpose AI model the team provides.
- A short report: uses per class, the rows that need legal review with their questions, the next date from the table that applies to a row, and uses the user still has to describe.

## Rules

- The triage is preparation for a lawyer. Never state a classification as final; the `Legal review` column shows who confirmed it.
- Article and annex numbers only. No text from the regulation in any file.
- Never overwrite or delete the register. A use that ends keeps its row with status `stopped` and the date.
- No personal data in the register. Name groups of people (`applicants`, `customers`), never individuals.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/compliance" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/compliance/` exists, read its `README.md` first, then the files in `compliance/ai-act-triage/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
