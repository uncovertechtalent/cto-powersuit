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
Fixture: every required kind has a row, several methods in one cell are read as the weakest, and a kind the organisation does not have says so with no admin holders and a reason. The fixture holds no exception, because an exception carries a date that ends. The exception cases run in `plugins/security/tests/test_security.py` with a fixed date.

## Inventory

| Entrance | Kind | Admin holders | Owner | MFA enforced | Method | Reason | Accepted by | Expires | Last checked | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Cloud console and root account | cloud | 2 roles, 3 accounts | Dana Example | yes | security-key | | | | 2026-10-01 | Sign-in policy admins-require-key |
| Identity provider and email suite admin | identity | 1 group, 4 accounts | Dana Example | yes | passkey, security-key | | | | 2026-10-01 | Authentication policy for admin roles |
| Domain controller | directory | none | Dana Example | n/a | none | The company has no directory server; staff identities live in the identity provider row. | | | | Architecture page, section identity |
| VPN | remote-access | 1 group, 2 accounts | Sam Example | yes | totp | | | | 2026-10-01 | VPN sign-in policy |
| Source control organisation and CI/CD | source-ci | 1 role, 2 accounts | Dana Example | yes | totp | | | | 2026-10-01 | Organisation setting: only allow secure two-factor methods |
| Domain registrar and DNS | dns-registrar | 1 account | Dana Example | yes | security-key | | | | 2026-10-01 | Registrar security page |
| Password manager | password-manager | 1 group, 2 accounts | Sam Example | yes | passkey | | | | 2026-10-01 | Admin console, policy page |
| Payroll admin console | saas | 1 account | Sam Example | yes | security-key | | | | 2026-10-01 | Admin console, security page |
| On-premises servers | on-prem | none | Dana Example | n/a | none | The company runs no on-premises server. | | | | Asset list, 2026-10-01 |
| Device management console | endpoint | 1 group, 2 accounts | Dana Example | yes | security-key | | | | 2026-10-01 | Console sign-in policy |
| Backup console and log administration | backup-monitoring | 1 group, 2 accounts | Sam Example | yes | passkey | | | | 2026-10-01 | Console sign-in policy |
| Vendors with admin access | vendor | none | Sam Example | n/a | none | No vendor holds admin access; the vendor list was read on 2026-10-01. | | | | Vendor register |
