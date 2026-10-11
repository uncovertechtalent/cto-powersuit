---
name: threat-model
description: >
  Write a short threat model for one RFC or one risky change: assets, entry
  points and trust boundaries, threats by category with likelihood and impact,
  mitigations with owners and tickets, and the residual risk someone accepts by
  name. Covers the threats of coding agents and their tools as entry points.
  Linked to the decisions/rfc skill: the RFC links the model, and the model
  feeds the RFC's risks section. Use when an RFC opens for comments, or when a
  change adds an entry point, a data class, a permission, a secret, or a third
  party. Activates on "/threat-model", "threat model this", "what could go
  wrong with this change", "security review of the RFC", "STRIDE".
user-invocable: true
---

# Threat model

One page per RFC or risky change, written before the change ships, short enough that the reviewers read it. It names what the change exposes, what could go wrong at each entry point, what the team does about each threat, and who accepts what is left. Each mitigation becomes a ticket, so the model is done when the tickets are.

## When a change needs one

The change does at least one of these:

- adds or changes an entry point: an endpoint, a webhook, a file upload, a CI trigger, a queue consumer;
- stores or moves a new class of data, such as personal data, payment data, or credentials;
- changes authentication, authorisation, roles, or tokens;
- adds a third party: a service, a package, an action, an agent skill, or an MCP server;
- gives a coding agent or an automation new tools or wider permissions;
- adds a secret.

A change with none of these needs no model. Say so in the RFC's risks section, with the reason.

## Inputs

- **The RFC** (`docs/decisions/rfc-NNNN-*.md`, written by `/decisions:rfc`) or the change: a pull request, an issue or a design note.
- **Owner**: the person who owns the change. Ask if not given.
- **Reviewers**: at least one person who did not design the change.

## Steps

1. **Copy the template** without overwriting:

   ```bash
   mkdir -p docs/security && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/security/_templates/threat-model.md" "docs/security/threat-model-<rfc-NNNN or short-name>.md"
   ```

   Set `rfc` to the RFC id or the change link, `owner`, `status: draft`, `reviewed` today.
2. **Scope.** Two or three sentences from the RFC's proposal. Name what the model leaves out.
3. **Assets.** What the change can leak, change or stop: data, credentials, systems, money, the deploy path. One owner per asset.
4. **Entry points and trust boundaries.** Each place where input crosses from a less trusted side to a more trusted one. For coding agents and automations, count as entry points: every text an agent with tools reads (issues, pull request comments, web pages, documents, tool output), every MCP server and skill it loads, and every token it holds.
5. **Threats.** Walk each entry point through the six categories: spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege. Write one row per real threat, in one sentence, with likelihood and impact (low, medium, high). Skip categories that do not apply; do not pad the table. Threats to check on any change with agents:
   - instructions hidden in text the agent reads lead it to use its tools (prompt injection);
   - the agent's token can do more than its task needs;
   - a skill or MCP server from an unchecked source runs with the agent's rights (run `/security:supply-chain` step 7 on it);
   - the agent writes a secret into a file, a log, a commit, or a chat.
6. **Mitigations.** One per threat, as a concrete change: a check, a permission, a limit, a review step. Each gets an owner and a ticket from `/sdlc:ticket`, with the threat id in the ticket.
7. **Supply chain and secrets.** List each new third party with its row in `docs/security/provenance-log.md`, and each new secret with its rotation runbook from `/security:secrets`.
8. **Residual risk.** The threats left open after the mitigations. One named person accepts them, with the date. A high-likelihood and high-impact threat with no mitigation is a reason to hold the RFC, and the owner says so in the RFC.
9. **Link it to the RFC.** In the RFC's "Risks and open questions" section, add the link to the model and the one-sentence summary of its most serious threat. When `/decisions:rfc` closes the RFC as accepted, set the model's `status: reviewed` and fill its review table.

## Output

- `docs/security/threat-model-<name>.md` with every section filled, linked from the RFC.
- Tickets for the mitigations, each naming its threat id.
- The residual risk, accepted by a named person.

## Rules

- One page. Cut every row that states no specific threat, so the reviewers read all of it.
- Every mitigation has an owner and a ticket, or it is a residual risk.
- No secrets, customer names or exploit code in the model. Each threat is one sentence, without attack steps.
- The model maps to control rows only through `/compliance:control-map`, by number, with the owner's confirmation.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/threat-model/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
