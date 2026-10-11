---
title: Vulnerability policy
summary: Severity levels, the fix-by window of each, how an exception is granted, and who decides.
parent: security
labels: security, vulnerabilities, policy
owner: <person who decides on exceptions>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 180 days after reviewed>
type: reference
---
A known vulnerability in code this repository ships becomes a ticket with a fix-by date. The window starts on the day the alert or advisory appeared in the alert list, whatever day someone first read it.

## Fix-by windows

| Severity | Fix-by window | Priority label |
|---|---|---|
| critical | 7 days | `P0` |
| high | 30 days | `P1` |
| medium | 90 days | `P2` |
| low | 180 days | `P3` |
| unknown | the high window until the owner sets a level, within 2 working days | `P1` |

The severity is the advisory's own level. The team raises it when the vulnerable code is reachable from the internet or handles credentials, and lowers it only with a written reason in the ticket (for example: the vulnerable function is never called, with the search that shows it).

## Fixes

- Upgrade to the first fixed version, or to the newest version on the same major line.
- Without a fix: remove the dependency, disable the feature that reaches it, or block the input at the edge. Record which one in the ticket.
- A fix is done when the alert closes, the scan of the default branch no longer lists the vulnerability, and the deploy that carries it is live.

## Exceptions

An exception names the vulnerability id, the reason, the compensating control, the new date, and the person who approved it. The policy owner approves; the person who asks cannot approve their own exception. An exception lasts at most 90 days and is renewed in writing.

## Review

Each month, the owner lists the open security tickets past their fix-by date and the exceptions that end within 30 days.
