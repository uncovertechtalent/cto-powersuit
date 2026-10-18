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
| Admin holders | The roles or groups that hold admin, and how many accounts. No email addresses. |
| Owner | The person who answers for this entrance. |
| MFA enforced | `yes` when the system refuses an admin sign-in without a second factor, for every admin account. `partial` when some accounts are exempt (break-glass accounts, legacy protocols, local logins beside single sign-on). `no`. `n/a` when the organisation has no entrance of this kind. |
| Method | The weakest method an admin can still sign in with, because that is the one an attacker picks. `passkey`, `security-key`, or `certificate` resist phishing. `push` and `totp` can be phished. `sms`, `voice`, and `email` can be intercepted or redirected. `none`. Several methods are separated by a comma. |
| Reason | Why MFA is not enforced or the method is below the bar, with the compensating controls. For `n/a`, why the kind does not exist. |
| Accepted by | The person with the authority to accept the risk. |
| Expires | The date the exception ends and someone decides again (`YYYY-MM-DD`, at most 180 days ahead). |
| Last checked | The date someone read the setting in the system (`YYYY-MM-DD`). |
| Evidence | Where to see the setting: a policy name, a console path, a ticket, or a file in the repository. A location, never a secret. |

An entrance with `no` or `partial`, or with a method of `sms`, `voice`, or `email`, needs a Reason, an Accepted by, and an Expires date. The check reports an exception past its Expires date.

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

## Change log

| Date | Change | By |
|---|---|---|
| `<YYYY-MM-DD>` | `<row added, exception accepted, exception ended, MFA enforced>` | `<name>` |
