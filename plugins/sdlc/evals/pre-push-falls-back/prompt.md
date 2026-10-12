---
description: Failure path. preloop is not installed. The skill says so in one line, runs the pre-PR command from docs/sdlc.md instead, installs nothing, runs no deploy, and does not push.
tags: [pre-push, failure-path]
runs: 3
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---

I'm about to push the discount branch. Run the CI checks locally first so nothing red goes up.
