---
title: Rotate <secret name>
summary: <one sentence: what the secret protects, where the live value lives, and how long rotation takes>
parent: security
labels: runbook, security, secrets, <system>
owner: <person or team that holds the secret>
reviewed: <YYYY-MM-DD, the day the steps were last run, or no>
review_by: <YYYY-MM-DD, 90 days after reviewed>
type: how-to
secret: <secret name>
lives_in: <the one place the live value lives: a container's settings file, a secret store path, a CI secret>
rotate_every: <90 days, or never with a reason>
last_rotated: <YYYY-MM-DD>
---
## Secret

<What the secret protects. Every system and person that reads it. What an attacker can do with it, and for how long a leaked value stays useful.>

## When to rotate

- On the schedule in `rotate_every`.
- At once when the value was ever in a tracked file, a commit, a log, a chat, a ticket, or a screenshot.
- When a person or a machine with access leaves, and after any suspected compromise.

## Rules for every step

- The value never appears on a screen, in a terminal scroll-back, in a chat, or in a log. Commands write it straight into its target, and searches print file names and commit ids only.
- The new value is generated inside the target (the container, the host or the secret store), so it never crosses the network in clear text.
- Only redacted references are committed: a placeholder that says where the live value lives.

## Steps

1. **Snapshot.** Keep a copy of the live configuration on the target, readable by the owner only:

   ```bash
   <ssh or exec into the target> 'cp -p <config file> <config file>.bak-$(date +%Y%m%d) && chmod 600 <config file>.bak-*'
   ```

2. **Record the old value's fingerprint** without printing the value:

   ```bash
   <exec into the target> 'grep -E "^\s*<key>:" <config file>.bak-<date> | sed -E "s/.*:\s*\"?([^\"]*)\"?/\1/" | tr -d "\n" | sha256sum | cut -c1-12'
   ```

3. **Generate and write the new value inside the target:**

   ```bash
   <exec into the target> 'NEW=$(openssl rand -hex 32) && sed -i -E "s|^(\s*<key>:\s*).*|\1\"$NEW\"|" <config file> && unset NEW'
   ```

4. **Reload** the service that reads the value: `<restart or reload command>`.
5. **Verify.** The service answers: `<health check and its expected output>`. The fingerprint of the live value differs from step 2. Sessions or tokens signed with the old value no longer work, where that applies.
6. **Search for the old value** in every repository and file tree that could hold it. Read the value from the snapshot into a variable, print only file names and commit ids, then clear the variable:

   ```bash
   OLD=$(<exec into the target> 'sed -n -E "s/^\s*<key>:\s*\"?([^\"]*)\"?/\1/p" <config file>.bak-<date>')
   git grep -lF -e "$OLD"; git log --all --format=%h -S"$OLD"; unset OLD
   ```

   No output means no file and no commit holds it.
7. **Commit only a redacted reference.** Replace each value in tracked files with a placeholder such as `"<random string; live value only in <lives_in>>"`. The commit message says the value in earlier history is retired. Never commit the new value.
8. **Record** the rotation: set `last_rotated` and `reviewed` in this page, and close the ticket with the date and who rotated.

## Roll back or escalate

A failed reload: restore the snapshot only to end an outage, then repeat the steps with a fresh value the same day, because the old value is the one being retired. A value found in history stays retired: rewriting history is a separate decision with the repository owner, and it does not reach clones made before the rewrite. Call <owner or on-call rota> when the service does not come back.
