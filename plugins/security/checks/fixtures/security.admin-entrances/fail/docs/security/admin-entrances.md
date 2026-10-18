---
title: Admin entrances
summary: Fixture with one problem per row.
parent: security
labels: security, access, mfa
owner: Dana Example
reviewed: 2026-10-01
review_by: 2099-01-01
type: reference
---
Fixture: each row shows one problem. The page has no row of kind password-manager, saas, or on-prem.

| Entrance | Kind | Admin holders | Owner | MFA enforced | Method | Reason | Accepted by | Expires | Last checked | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Cloud console and root account | cloud | 2 roles, 3 accounts | Dana Example | no | none | | | | 2026-10-01 | Sign-in policy page |
| Identity provider admin | identity | 1 group, 4 accounts | Dana Example | yes | sms | | | | 2026-10-01 | Authentication policy |
| Domain controller | directory | 1 group, 2 accounts | Sam Example | no | none | Legacy servers cannot take a second factor. | Sam Example, CTO | 2024-01-31 | 2026-10-01 | Ticket SEC-9 |
| VPN | remote-access | 1 group, 2 accounts | Sam Example | yes | none | | | | 2026-10-01 | VPN policy |
| Source control organisation | ci | 1 role, 2 accounts | | yes | security-key | | | | 2026-10-01 | Organisation setting |
| Domain registrar | dns-registrar | 1 account | Dana Example | yes | totp | | | | 2026-13-45 | |
