---
title: Admin entrances
summary: Every place an administrator can sign in, who owns it, whether multi-factor authentication is enforced there and with which method, and the dated exceptions.
parent: security
labels: security, access, mfa, nis2
owner: <person or team that keeps this page true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
One row per entrance. An entrance is any place where an account with admin rights can sign in and change systems, data, or other people's access. Keep this page in a private repository: it lists where multi-factor authentication is missing and when each exception ends. Never write a password, token, recovery code, or seed value on this page.

Gate check: `security.admin-entrances`. Evidence for NIS2 Art 21(2)(j) in `compliance/control-map.csv`.

## Columns

| Column | What to write |
|---|---|
| Entrance | The system and the admin path, for example `<cloud provider> console, root account`. |
| Kind | One of `cloud`, `identity`, `directory`, `remote-access`, `source-ci`, `dns-registrar`, `password-manager`, `saas`, `on-prem`, `endpoint`, `backup-monitoring`, `vendor`, `other`. |
| Admin holders | The roles or groups that hold admin, and how many accounts. No email addresses. `none` only on an `n/a` row. |
| Owner | The person who answers for this entrance. |
| MFA enforced | `yes` when the system refuses an admin sign-in without a second factor, for every admin account, including a new account on its first day. `partial` when some accounts are exempt: legacy protocols, local logins beside single sign-on, a policy that skips the second factor for trusted locations or remembered devices, a shared admin account whose one-time-password seed sits in the same vault as its password, or a break-glass account without its own phishing-resistant factor, an alert on every use, and regular tests. `no`. `n/a` when the organisation has no entrance of this kind. |
| Method | The weakest method an admin can still sign in or recover with, because that is the one an attacker picks. `passkey`, `security-key`, and `certificate` resist phishing; `certificate` means a key held in hardware that cannot be exported (smart card, TPM, security key), and a certificate file, a kubeconfig client certificate, or an SSH key file alone is one stealable factor, so record `none`. `push` (with number matching) and `totp` can be phished. `push-no-match`, `sms`, `voice`, and `email` can be intercepted, redirected, or approved blindly. `none`. Recovery counts: record `sms` or `email` when an admin can reset the factor by SMS or by email to an account that has no phishing-resistant factor itself, and when a helpdesk can reset an admin's factor without verifying the caller. Several methods are separated by a comma. |
| Reason | Why MFA is not enforced or the method is below the bar, with the compensating controls. An internet-facing entrance needs a network restriction here; cost alone is not a reason. For `n/a`, why the kind does not exist. |
| Accepted by | The person with the authority to accept the risk, and where the team has one, a different person from the Owner. |
| Expires | The date the exception ends and someone decides again (`YYYY-MM-DD`, at most 180 days after Last checked). |
| Last checked | The date someone read the setting in the system (`YYYY-MM-DD`). |
| Evidence | Where to see the setting: a policy name, a console path, a ticket, or a file in the repository. A location, never a secret. |

An entrance with `no` or `partial`, or with a method of `push-no-match`, `sms`, `voice`, or `email`, needs a Reason, an Accepted by, and an Expires date. The check reports an exception past its Expires date or longer than 180 days. A long-lived admin credential (an API key, a service account, a CI role that can assume admin) cannot answer a second factor: give it its own row with MFA enforced `no`, method `none`, and an exception that names the compensating controls (scope, rotation, network restriction).

An `n/a` row is for a kind of entrance the organisation does not have, with no admin holders. A live entrance without MFA is a `no` or `partial` row with an exception.

## Inventory

| Entrance | Kind | Admin holders | Owner | MFA enforced | Method | Reason | Accepted by | Expires | Last checked | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `<cloud console, root or owner account, organisation management account>` | cloud | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<identity provider and email suite admin>` | identity | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<domain controller or directory>` | directory | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<VPN, remote desktop gateway, bastion, remote support tool>` | remote-access | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<source control organisation owners, CI/CD admin, package and image registries>` | source-ci | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<domain registrar, DNS provider, certificate authority account>` | dns-registrar | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<password manager admin>` | password-manager | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<SaaS admin console>` | saas | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<on-premises servers, hypervisors, network gear, out-of-band management>` | on-prem | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<device management and endpoint security consoles>` | endpoint | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<backup console, log and alert administration>` | backup-monitoring | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |
| `<managed service providers, contractors, vendors with admin access>` | vendor | `<roles or groups, count>` | `<name>` | `<yes, partial, no, or n/a>` | `<method>` | `<reason>` | `<name>` | `<YYYY-MM-DD>` | `<YYYY-MM-DD>` | `<where to see the setting>` |

## Change log

| Date | Change | By |
|---|---|---|
| `<YYYY-MM-DD>` | `<row added, exception accepted, exception ended, MFA enforced>` | `<name>` |
