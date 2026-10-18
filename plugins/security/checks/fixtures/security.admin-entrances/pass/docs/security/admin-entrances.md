---
title: Admin entrances
summary: Every place an administrator can sign in, with the owner, the MFA setting and the dated exceptions.
parent: security
labels: security, access, mfa
owner: Dana Example
reviewed: 2026-10-01
review_by: 2099-01-01
type: reference
---
Fixture: every kind has a row, an exception has a reason, a person and a future date, and a kind the organisation does not have says so.

## Inventory

| Entrance | Kind | Admin holders | Owner | MFA enforced | Method | Reason | Accepted by | Expires | Last checked | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Cloud console and root account | cloud | 2 roles, 3 accounts | Dana Example | yes | security-key | | | | 2026-10-01 | Sign-in policy admins-require-key |
| Identity provider and email suite admin | identity | 1 group, 4 accounts | Dana Example | yes | passkey, security-key | | | | 2026-10-01 | Authentication policy for admin roles |
| Domain controller | directory | none | Dana Example | n/a | none | The company has no directory server; staff identities live in the identity provider row. | | | 2026-10-01 | Architecture page, section identity |
| VPN | remote-access | 1 group, 2 accounts | Sam Example | partial | totp | The VPN appliance accepts one time passwords only; sign-in is limited to the office network range and every sign-in alerts the owner. | Sam Example, CTO | 2099-12-31 | 2026-10-01 | Ticket SEC-14 |
| Source control organisation and CI/CD | source-ci | 1 role, 2 accounts | Dana Example | yes | security-key, passkey | | | | 2026-10-01 | Organisation setting: require two-factor authentication |
| Domain registrar and DNS | dns-registrar | 1 account | Dana Example | yes | security-key | | | | 2026-10-01 | Registrar security page |
| Password manager | password-manager | 1 group, 2 accounts | Sam Example | yes | passkey | | | | 2026-10-01 | Admin console, policy page |
| Payroll admin console | saas | 1 account | Sam Example | no | none | The vendor offers no second factor on the admin login; the console is reachable from the office range only. | Sam Example, CTO | 2099-12-31 | 2026-10-01 | Ticket SEC-15 |
| On-premises servers | on-prem | none | Dana Example | n/a | none | The company runs no on-premises server. | | | 2026-10-01 | Asset list, 2026-10-01 |
