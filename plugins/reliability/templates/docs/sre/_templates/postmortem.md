---
title: "Postmortem: <what users saw, in one line>"
summary: <one sentence: what happened, for how long, and how many users saw it>
parent: <slug of the parent page; leave empty for the space home>
order: <whole number; a lower number sorts first among siblings>
labels: postmortem, incident
owner: <the incident lead>
reviewed: <YYYY-MM-DD, the day the review meeting agreed the text, or no>
review_by: <YYYY-MM-DD, the due date of the last open action item>
type: explanation
date: <YYYY-MM-DD, the day the incident started>
incident: <incident id from incidents/incidents.json>
severity: <sev1, sev2, sev3 or sev4>
---
This postmortem is blameless. It describes what the systems did and what information the people had at each point. Names appear only as owners of action items.

## Summary

<One paragraph: what users saw, from when to when, the cause in one sentence, and the fix.>

## Impact

| Measure | Value | Source |
|---|---|---|
| Start and end (UTC) | <YYYY-MM-DD HH:MM to HH:MM> | <alert, log line or deploy record> |
| Minutes of user impact | <minutes> | <how they were counted> |
| Users affected | <number or share> | <query or report> |
| Requests failed | <number and share of valid requests> | <query> |
| Error budget used | <share of the window's budget> | <SLO page> |
| Data lost or wrong | <none, or what> | <check that confirmed it> |

## Timeline

All times UTC. A time appears only when a record backs it.

| Time | Event | Source |
|---|---|---|
| <HH:MM> | <the change or the condition that started it> | <deploy, commit, log> |
| <HH:MM> | <first alert or first user report> | <alert or ticket> |
| <HH:MM> | <incident declared, severity, incident lead> | <incident log> |
| <HH:MM> | <mitigation> | <command, deploy> |
| <HH:MM> | <resolved> | <graph or check> |

Time to detect: <minutes from start to first alert>. Time to mitigate: <minutes from start to mitigation>.

## Contributing factors

<Numbered list of mechanisms, each in one or two sentences: the conditions in the system and the process that made this incident possible, made it last, or made it larger. A factor names a system, a signal, a tool or a process, never a person.>

1. <factor>

## What went well

- <detection, response, communication or tooling that worked>

## What went poorly

- <what slowed detection, diagnosis or recovery, stated as mechanism>

## Action items

| Action | Kind | Owner | Due | Ticket | Status |
|---|---|---|---|---|---|
| <one change, specific enough to close> | <prevent, detect, mitigate or process> | <one named person> | <YYYY-MM-DD> | <link> | <open or done> |

The owner of this page checks the action items at `review_by` and moves the date until the last item is done.
