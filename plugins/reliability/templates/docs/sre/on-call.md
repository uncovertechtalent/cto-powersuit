---
title: On-call
summary: Who is on call for which services, how a page escalates, the handover between shifts, and the rules for what may page a person.
order: 30
labels: on-call, paging, escalation
owner: <person or team that keeps this policy true>
reviewed: <YYYY-MM-DD>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: reference
---
This policy covers the services in the catalogue (`services/*.yml`) of tier <tiers covered>. A person on call answers pages for those services, runs incidents until an incident lead takes over, and hands over at the end of the shift.

## Rotation

| Rotation | Services | Members | Shift | Handover | Time zone | Paging tool |
|---|---|---|---|---|---|---|
| <name> | <tier 1 services, or a list of ids> | <names or the group> | <one week> | <weekday and time> | <time zone> | <tool> |

Load limits:

- <No person is on call more than one week in four.>
- <A person paged at night starts the next day late, or takes the time back.>
- <With more than two pages in one shift, the shift reviews them with the owner of the alerts in the same week.>

## Escalation

| Step | Who | When |
|---|---|---|
| 1 | Primary on call | At once |
| 2 | Secondary on call | <after 15 minutes without acknowledgement> |
| 3 | <engineering manager or the incident lead pool> | <after 30 minutes without acknowledgement, or on request> |
| 4 | <head of engineering> | <when a sev1 incident is declared> |

Anyone may escalate early. A call for help is part of the job.

## Paging rules

1. Page only on symptoms users see: errors, slow answers, unavailability, data that is wrong or late. For a cause with no user impact yet, such as high CPU, one failed instance behind a load balancer, or a disk that fills in days, open a ticket.
2. Every alert links a runbook in its `runbook_url` annotation. An alert without a runbook does not page.
3. Page only when a person must act. When the action can be automated, automate it and remove the page.
4. SLO burn-rate alerts are the default page for a service with an SLO. See the SLO page of the service.
5. Each page is reviewed at handover: was it actionable, and was the runbook right.

## Handover checklist

- [ ] Open incidents, their stage and the incident lead
- [ ] Pages of this shift: count, actionable or not, runbooks that were wrong or missing
- [ ] Silences and maintenance windows in force, with their end times
- [ ] Changes in flight: deploys, migrations, feature flags
- [ ] Tickets opened from alerts
- [ ] Access for the next shift: paging app, VPN, dashboards, consoles, runbooks
- [ ] The next person on call confirms the handover

## Review

Every month, the owner of this page reviews: pages per shift, the share of pages that needed action, pages outside working hours, alerts without a runbook, and the time to acknowledge.
