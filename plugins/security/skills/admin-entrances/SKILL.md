---
name: admin-entrances
description: >
  List every place an administrator can sign in (cloud consoles and root
  accounts, identity provider and email admin, directory, VPN and remote
  access, source control and CI/CD owners, DNS and registrar, password manager,
  SaaS admin consoles, on-premises servers, device management, backups and
  logs, vendor access) and record for each one the owner, whether
  multi-factor authentication is enforced, the weakest method an admin can
  still use, and any exception with its reason, the person who accepted it and
  its end date. Writes docs/security/admin-entrances.md from a template and
  installs the gate check security.admin-entrances. Use for a security
  baseline, before an audit or a NIS2 or ISO 27001 assessment, when a cloud
  account, a domain or a VPN is added, and with each quarterly access review.
  Activates on "/admin-entrances", "admin entrances", "MFA inventory", "where
  is MFA missing", "is MFA on for admins", "multi-factor audit", "NIS2
  21(2)(j)".
user-invocable: true
---

# Admin entrances

An attacker who needs an admin login tries the entrance with the weakest sign-in. The British Library's own review of its 2023 attack records how a gap like that comes about. Multi-factor authentication was introduced in 2020 for cloud applications, and connectivity to the Library's domain, including access to on-premises servers, was left out of scope for reasons of practicality, cost, and impact on programmes. The lack of it on the domain was identified and raised as a risk at the time, and the review says its consequences were perhaps under-appraised. The terminal server was protected by firewalls and virus software, and access to it was not subject to multi-factor authentication. The review's third lesson asks for multi-factor authentication on all internet-facing endpoints regardless of technical difficulties (British Library, cyber incident review, 8 March 2024, pages 6 and 17).

This skill turns a known gap into a row with a named person and an end date, and it turns a whole class of entrances that is out of scope into a row that has to say so. NIS2 Art 21(2)(j) names multi-factor or continuous authentication as a measure, and Art 21(1) lists the cost of implementation among the factors for proportionate measures ([Directive (EU) 2022/2555](https://eur-lex.europa.eu/eli/dir/2022/2555/oj)). A cost reason can be recorded. It needs a named person and an end date, and for an internet-facing entrance it also needs a restriction that limits who can reach it.

The skill records and checks. A recorded exception stops no attack by itself: it makes the gap visible and ends it on a date.

## Inputs

- **Repository root** of a private repository that holds the team's docs.
- **The team's systems**: ask the user, system by system. The repository shows only part of them.
- **Optional**: `gh` logged in as an owner of the GitHub organisation, for the source control row.

## The bar

- **Enforced** means the system refuses an admin sign-in without a second factor, for every account that holds admin rights, including an account on the day it is created. A user who has it turned on, or a rule that people were asked to turn it on, is `no` or `partial`.
- **Method** is the weakest way an admin can still sign in or recover access, because that is the one an attacker picks.

  | Method | Reading |
  |---|---|
  | `passkey`, `security-key`, `certificate` | Resists phishing. A security key or a device-bound passkey is the target for admin accounts. `certificate` means a key held in hardware that cannot be exported (smart card, TPM, security key). A certificate file, a client certificate in a kubeconfig, or an SSH key file alone is one stealable factor: record `none`. |
  | `push`, `totp` | A proxy that relays the code or the approval can phish them. `push` here means a prompt with number matching, which stops blind approval and does not stop a relay. |
  | `push-no-match`, `sms`, `voice`, `email` | Can be intercepted, redirected, or approved blindly: a SIM swap, a mailbox takeover, or a flood of prompts until someone taps yes. |
  | `none` | No second factor. |

  Recovery counts. Record `sms` or `email` when an admin can reset the factor by SMS, or by email to an account that has no phishing-resistant factor itself, and when a helpdesk can reset an admin's factor without verifying the caller.
  CISA's fact sheet "Implementing Phishing-Resistant MFA" names FIDO/WebAuthn and certificate-based sign-in as the phishing-resistant ones.
- **Break-glass accounts**: an emergency account kept outside the policies that could lock it out counts as enforced when it has its own phishing-resistant factor, an alert on every use, and a test at least every 90 days. A break-glass account with a password alone makes the row `partial`.
- The check reports `push-no-match`, `sms`, `voice`, and `email` as below the bar. With `phishing_resistant_only` set, it reports `push` and `totp` too. CISA urges administrators and other high-value targets to move to phishing-resistant methods, so set the option as soon as admins hold keys. A row below the bar needs an exception.

## Steps

1. **Pick the home of the page.** Run `gh repo view --json visibility` (read only). Go on only when the answer is `PRIVATE`, or `INTERNAL` with the user's agreement. When the repository is public, or the command fails (no `gh`, another host, no remote), stop and ask the user to name a private repository: the page lists where multi-factor authentication is missing and when each exception ends. Then copy the template without overwriting:

   ```bash
   mkdir -p docs/security
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/docs/security/admin-entrances.md" docs/security/
   ```

   If the page exists, work in it. Set `owner`, `reviewed` and `review_by` in the front matter after the walk, so `docs.review` passes.
2. **Walk the kinds, one at a time.** For each kind, ask what exists, then write a row per entrance. Ask about the items in the third column; they are the usual holes.

   | Kind | Entrances to look for | Often missed |
   |---|---|---|
   | `cloud` | Cloud consoles, root or owner accounts, organisation management accounts, accounts that can grant admin, the Kubernetes API, database master logins, key management services | The root account used once at setup; command-line and API access with long-lived keys, and CI/CD roles that can assume admin, which a second factor does not cover |
   | `identity` | Identity provider admin roles, email and productivity suite super admins, who can reset an admin's factor | Break-glass accounts excluded from the policy; legacy protocols and app passwords that skip modern sign-in; policies that skip the second factor for trusted locations or remembered devices; account recovery by SMS or email; helpdesk resets |
   | `directory` | Domain controllers, directory admin groups, privileged access tools | Server logins (remote desktop, SSH) that do not go through the identity provider |
   | `remote-access` | VPN, remote desktop gateways, terminal servers, bastions and jump hosts, remote support and monitoring tools | Any internet-facing login that takes a password alone, the case in the British Library review; the appliance's local admin login |
   | `source-ci` | Source control organisation owners, CI/CD admins, package and container registry publish rights | Organisations without a two-factor requirement; deploy tokens; pipelines that can assume a cloud admin role |
   | `dns-registrar` | Registrar account, DNS provider, certificate authority account | Recovery email on a domain the account itself controls; a shared mailbox as the account owner |
   | `password-manager` | Vault admins, whoever can reset members or recover accounts | The recovery path; a shared admin account whose one-time-password seed sits in the same vault as its password, so one compromise yields both factors |
   | `saas` | Each SaaS admin console: payments, payroll, CRM, support, analytics, AI provider consoles, app store developer accounts | A local admin login beside single sign-on |
   | `on-prem` | Servers, hypervisors, storage, network gear, out-of-band management (BMC), secrets managers and HSMs | Default accounts; management interfaces on the office network; root tokens of a secrets manager |
   | `endpoint` | Device management and endpoint security consoles | They push software and wipe devices |
   | `backup-monitoring` | Backup console, log and alert administration | Whoever can delete backups or switch off logging can hide an intrusion |
   | `vendor` | Managed service providers, contractors and vendors with admin access into your systems | Their accounts and their sign-in policy; the British Library review notes MFA on end-user technologies and not on certain supplier endpoints |

   The check requires a row of every kind above. A kind the organisation does not have gets one row with MFA enforced `n/a`, an owner, no admin holders, and the reason. A kind that has an entrance is never `n/a`. `other` is free for anything the table misses.
3. **Fill the row.** Fields in this order:
   - **Owner**: the person who answers for the entrance.
   - **Admin holders**: roles or groups and the number of accounts. No email addresses.
   - **MFA enforced**: `yes`, `partial`, `no`, or `n/a`, from the system's policy. Ask which accounts the policy skips. Legacy protocols, local logins beside single sign-on, trusted-location skips, a shared seed, and a break-glass account that fails the bar above make a row `partial`.
   - **Method**: the weakest method, from the table above, recovery included.
   - **Evidence**: where the setting can be seen (policy name, console path, ticket, a file in the repository). A location, never a value.
   - **Last checked**: the date someone read the setting in the system.

   Service accounts, API keys, and CI tokens that carry admin rights cannot answer a second factor, so a `yes` row does not cover them. Give each class its own row: MFA enforced `no`, method `none`, and an exception that names the compensating controls (scope, rotation, a network restriction). [`/security:secrets`](../secrets/SKILL.md) and [`/security:access-review`](../access-review/SKILL.md) cover the credentials themselves.
4. **Read what a tool can read, without new credentials.** For the GitHub organisation, run the access review as an organisation owner:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/access-review/access_review.py" <owner/repo> --days 30
   ```

   Its `mfa:` line says whether the organisation requires two-factor authentication and how many members and outside collaborators have it off, or that the caller could not read it. GitHub shows the organisation's full record to an organisation owner, and a classic token needs the `admin:org` scope for it. That scope also allows writes: add it for the run and remove it afterwards. Read the method in the organisation's authentication settings. With "Only allow secure two-factor methods" on, SMS is refused and the weakest allowed methods are authenticator apps and the GitHub mobile app: record `totp`. With it off, SMS is allowed: record `sms`. Name the setting and the date you read it in Evidence. If the organisation is an Enterprise Managed Users organisation, the identity provider handles sign-in: take the method from its policy, and ignore the GitHub two-factor flags. For any other provider, the user reads the setting in the console and tells you the answer. If the user names a read-only call on a session that is already signed in, run it only when it returns a setting or metadata. Never run a call that creates, prints, or reads a credential: an access token, a session token, a key, or a secret value.
5. **Record each exception.** An entrance below the bar (MFA enforced `no` or `partial`, or a method of `push-no-match`, `sms`, `voice`, or `email`) gets all three:
   - **Reason**: why, and what limits the risk meanwhile (a network range, a hardware-only path, an alert on every sign-in, short-lived access). An internet-facing entrance gets no exception without a restriction that limits who can reach it; cost or effort alone is not a reason there.
   - **Accepted by**: the person with the authority to accept the risk, and where the team has one, a different person from the owner.
   - **Expires**: the date someone decides again, at most 180 days after Last checked. Ask for a ticket that closes the gap before that date (`/sdlc:ticket`). An exception with no end date is not recorded.
6. **Run the check and read every hit** with the user:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/checks/admin_entrances.py" .
   ```

   | Hit | Meaning |
   |---|---|
   | `no-table` | The page has no inventory table, or the table lacks a column |
   | `kind-missing` | A required kind has no row. Add the entrance, or a row with MFA enforced `n/a`, no admin holders, and a reason |
   | `row-incomplete` | A row lacks its owner, admin holders, evidence, or last checked date, holds a value outside the lists, or is `n/a` and lists admin holders |
   | `row-stale` | The row's last checked date lies more than 120 days before the page's `reviewed` date: the page was reviewed and the row was not read again |
   | `mfa-not-enforced` | MFA enforced is `no` or `partial` and the exception lacks a reason, a person, or a date |
   | `weak-method` | The weakest method is below the bar and the exception lacks a reason, a person, or a date |
   | `exception-expired` | The exception ended on its date and nobody decided again |
   | `exception-too-long` | The exception ends more than 180 days after the last check |

   A hit names the entrance and the field. It never prints a reason, an owner, admin holders, or evidence.
7. **Install the gate check on `warn`.** With the gate in place, use `/gate:add-rule` (path A: install a module's check), or by hand:

   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/checks/admin_entrances.py" .github/actions/gate/rules/
   mkdir -p gate/fixtures && cp -R "${CLAUDE_PLUGIN_ROOT}/checks/fixtures/security.admin-entrances" gate/fixtures/
   ```

   Add `"security.admin-entrances": {"tier": "warn"}` to `gate/gate.json`. Options: `required_kinds`, `phishing_resistant_only`, `max_exception_days` (180), `max_check_age_days` (120), `page`. Move it to `block` once the page has no hit, the fixtures are in place, and the false-positive test is recorded under the rule.
8. **Map the control.** With `/compliance:control-map`, name `docs/security/admin-entrances.md` as the evidence for NIS2 Art 21(2)(j). The proposed ISO/IEC 27001:2022 Annex A numbers are A.5.17, A.8.2, and A.8.5, to confirm with the control owner. Mark the row `implemented` only when the check passes with no exception, and `partial` when exceptions remain, with the earliest end date in the gap column.
9. **Set the rhythm.** Re-read the page with each quarterly access review, when a cloud account, domain, VPN, or SaaS tool is added, and on the earliest exception end date. Update Last checked only for a row someone read in the system on that day.

## Output

- `docs/security/admin-entrances.md` with one row per entrance.
- A short report: entrances by kind and MFA state, the exceptions with their end dates, the check's hits, and what could not be read.

## Rules

- Never ask for, read, print, or store a password, token, API key, recovery code, or secret seed. Evidence is a location.
- Read only. Do not change an MFA policy, enrol or reset a factor, or touch an account. Propose each change with the setting, the current value, the new value, and the reason; the owner makes it.
- Do not sign in to a console for the user, and do not drive an admin console in a browser.
- Mark `yes` only when the setting was read in the system. A statement that people use it counts as `partial`.
- Keep the page in a private repository. No email addresses and no secrets on it.
- Do not commit or push. The user does.

## Check the script

`python3 "${CLAUDE_PLUGIN_ROOT}/tests/test_security.py"` runs the check against its fixtures and against rows for each rule, the options, the template, and the access review's MFA section on recorded organisation answers. Every line must read `ok`.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/admin-entrances/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
