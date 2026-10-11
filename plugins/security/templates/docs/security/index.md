---
title: Security
summary: Where the code and its dependencies come from, who can change the repository, which secrets exist and how they rotate, and how known vulnerabilities reach a fix by a date.
labels: security, supply-chain, secrets, access, vulnerabilities
owner: <person or team that keeps this space true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This space holds the security pages of the repository: the provenance log of every third-party action, agent skill, MCP server, and tool, the key-rotation runbooks, the threat models of risky changes, the access reviews, and the vulnerability policy with its fix-by windows.

## Pages

| Page | What it holds |
|---|---|
| [Provenance log](provenance-log.md) | One row per third-party action, agent skill, MCP server, and tool: source, owner check, install path, pinned version, source risk, data exposure, decision, date, and reviewer |
| [Vulnerability policy](vuln-policy.md) | Severity levels, fix-by windows, exceptions, and who decides |
| `runbook-key-rotation-<secret>.md` | One rotation runbook per secret, from `_templates/` via `/security:secrets` |
| `threat-model-<rfc or change>.md` | One threat model per RFC or risky change, from `_templates/threat-model.md` via `/security:threat-model` |
| `access-review-<YYYY-MM-DD>.md` | The dated access reviews, from `/security:access-review` |

## Records

- Gate checks: `security.secrets` and `security.action-owners` in `gate/gate.json`; `gate.actions-pinned` from the gate module.
- Update config: `.github/dependabot.yml`.
- Vulnerability tickets: the issues labelled `security`, each with a fix-by date.
