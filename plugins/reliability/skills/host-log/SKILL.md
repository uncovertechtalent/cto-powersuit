---
name: host-log
description: >
  Keep a change record on every server that people or agents change over ssh.
  Each host holds /<hostname>.log with one line per change, and every ssh
  connection prints an AGENTS line that points at it, so the next person or
  agent reads the host's history before touching anything. Covers the rule,
  the line format, appending safely from stdin, setup on Linux with sudo and
  on macOS or hosts without sudo, appliances, and the hosts to leave out. Use
  before and after any change on a remote host, and when a host joins the
  fleet. Activates on "host log", "server log", "hostname.log", "AGENTS
  banner", "change record for a server", or any ssh change on a host that
  prints an AGENTS line.
user-invocable: true
---

# Host log

Every server keeps its own change record, so the next person or agent sees what was done, by whom, and why, without the laptop or the knowledge base of whoever did it. When a service breaks, the first question is what changed. On a host with a log, the answer is in the last lines of one file.

The record is a plain text file on the host. The banner is one line that every ssh connection shows. The skill sets both up on a host the user agrees to, and applies the rule on every change after that.

## Inputs

- **The host**: `<user>@<address>` and the short hostname (`hostname -s`, lower case). The log and the symlink use that name.
- **Whether the login user has sudo.** It decides the setup path.
- **What the host is**: a server, a workstation, or an appliance such as a NAS or a router. It decides the caveats.
- **The fleet table**, if the user keeps one (see Overlay).

## The rule

1. **Before** a change: read the AGENTS line in the ssh output (it arrives on stderr), then read the end of the log: `ssh <user>@<address> 'tail -n 30 /<host>.log'`, or `~/<host>.log` where the log lives in the home folder. If there is no AGENTS line and no log, the host has no record yet. Tell the user and offer the setup below. Do not start the setup unasked.
2. **After** each change: append one line. Never edit, reorder, or delete an old line. A wrong line is corrected by a new line that says so.

```
YYYY-MM-DD HH:MM TZ | who (person, or agent + session) | what changed (paths, services) | why / ref
```

Example:

```
2026-03-02 14:05 CET | claude (session export-timeouts) | /etc/nginx/conf.d/api.conf: proxy_read_timeout 60s to 120s, nginx reloaded | PROJ-481, report exports time out
```

- Log config edits, service restarts, installs and updates, deletes, and changes to scheduled jobs (cron, timers, LaunchAgents). Read-only probes are not logged.
- A change that failed or was rolled back gets its own line.
- One line per change. No `|` and no line break inside a field.
- The log is readable by every local user. Write what changed and why. Never write a password, a token, or a key.

## Append a line

Build the line on your machine and send it on stdin. The remote command stays fixed and holds no log text. `<log path>` is `/<host>.log` on a host set up with path A and `~/<host>.log` on a path B host. The remote shell expands the `~`.

```bash
{ printf '%s | ' "$(date '+%F %H:%M %Z')"; cat <<'LINE'
claude (session <name>) | <what changed> | <why or ref>
LINE
} | ssh <user>@<address> 'cat >> <log path>'
```

The quoted `'LINE'` stops the local shell from expanding `$`, backticks, and backslashes in the text, and an apostrophe in the text breaks nothing. Read the last line back with `ssh <user>@<address> 'tail -n 1 <log path>'`.

Never put the text of a log line inside a quoted remote command. In `ssh host 'echo "<text>" >> /host.log'`, one apostrophe in the text ends the quote, and the words after it run as commands on your machine. In `ssh host "echo '<text>' >> /host.log"`, the host's shell parses the text, so the same apostrophe makes the host run the words after it. The first form has happened in practice.

## Set up a host

Setup changes sshd or a shell startup file on a live host. Do it one host at a time, with the user's yes for that host. Name the host's log `<host>.log` with `<host>` from `hostname -s`, lower case.

Pick the path:

| Host | Path |
|---|---|
| Linux, the login user has sudo | A: log at `/<host>.log`, banner from sshd |
| macOS, or no sudo | B: log in the home folder, banner from a shell hook |
| A DNS, DHCP, or routing single point | Leave it out (see below) |

An appliance (NAS, router, firewall) takes path A or B by what it allows, plus the appliance caveat below.

### Path A: Linux with sudo

Run the commands on the host over ssh. They need sudo without a password prompt; otherwise the user runs them.

1. **Snapshot the sshd config first.**

   ```bash
   host=$(hostname -s | tr '[:upper:]' '[:lower:]')
   snap=/root/config-snapshots/$(date +%F)
   sudo mkdir -p "$snap" && sudo cp -a /etc/ssh/sshd_config "$snap"/
   [ -d /etc/ssh/sshd_config.d ] && sudo cp -a /etc/ssh/sshd_config.d "$snap"/
   ```

2. **Create the log** owned by the login user, mode 644, and link it into the home folder:

   ```bash
   host=$(hostname -s | tr '[:upper:]' '[:lower:]')
   sudo touch "/$host.log" && sudo chown "$(id -un):$(id -gn)" "/$host.log" && sudo chmod 644 "/$host.log"
   ln -sfn "/$host.log" "$HOME/$host.log"
   ```

   If the log already exists, leave it as it is and append to it. For a new log, fill the placeholders of `${CLAUDE_PLUGIN_ROOT}/templates/hosts/host.log` (`<host>`, `<address>`, `<what it is>`), save the result as `header.txt`, and send it on stdin like a log line: `ssh <user>@<address> 'cat >> /<host>.log' < header.txt`. The login user owns the file, so this needs no sudo.

3. **Write the banner file.** Fill `<log path>` in `${CLAUDE_PLUGIN_ROOT}/templates/hosts/agents-banner` with `/<host>.log` and install it as `/etc/ssh/agents-banner`, mode 644, owned by root: `printf '%s\n' '<the filled line>' | sudo tee /etc/ssh/agents-banner >/dev/null && sudo chmod 644 /etc/ssh/agents-banner`. The line holds no apostrophe, so the quoting holds. The banner is sent before login, so anyone who can reach the port reads it. It names the path and the rule, nothing else: no address, no user, no log content. The path carries the short hostname, so a host whose name must stay private gets a neutral log name such as `changes.log` in the banner, the header, and the symlink.

4. **Check what sshd does now.** `sudo sshd -T | grep -i '^banner'` shows `banner none` when no banner is set. If a banner is already set (a legal notice, for example), keep it: with the user's agreement, add the AGENTS line to that banner file instead, and skip step 5.

5. **Point sshd at the banner.** `grep -i '^Include' /etc/ssh/sshd_config` shows whether the main file includes `/etc/ssh/sshd_config.d/*.conf`. If it does, create the drop-in with `echo 'Banner /etc/ssh/agents-banner' | sudo tee /etc/ssh/sshd_config.d/10-agents-banner.conf >/dev/null`. If it does not, add the same line to `/etc/ssh/sshd_config` above the first `Match` block, because a line below a `Match` applies to that match only. sshd keeps the first value it reads for a keyword, so check the result with `sudo sshd -T | grep -i '^banner'` after the reload.

6. **Test, then reload.** `sudo sshd -t` prints nothing when the config is valid. Only then reload sshd. The unit is `ssh` on Debian and the systems built on it, and `sshd` on Fedora, RHEL, and Arch, so pick it first:

   ```bash
   if systemctl cat ssh.service >/dev/null 2>&1; then unit=ssh; else unit=sshd; fi
   sudo systemctl reload "$unit"
   ```

   Keep the session you are in open until step 7 passes. A reload leaves open sessions running.

7. **Verify on a fresh connection.** `ssh <user>@<address> true` prints the AGENTS line, and `ssh <user>@<address> echo ok 2>/dev/null` prints `ok` alone. If either fails, remove the drop-in (or the line you added), run `sudo sshd -t`, reload, and restore from the snapshot if needed.

8. **Log the setup** as the first line of the new log: the files written, the snapshot folder, and the user's go.

### Path B: macOS, or no sudo

The log lives in the home folder: `~/<host>.log`. The root volume of macOS is sealed read-only, so a file cannot be created in `/`.

1. Create the log with the filled header, on stdin: `ssh <user>@<address> 'cat >> ~/<host>.log' < header.txt`.
2. Add a hook to the login shell's environment file, guarded by `$SSH_CONNECTION` so it runs on ssh logins only. For zsh, the default on macOS, that is `~/.zshenv`, which zsh reads for every invocation. For bash, use `~/.bashrc`, above any line that returns early for non-interactive shells. Fill `<log path>` with `~/<host>.log`:

   ```sh
   # host-log: point agents at this host's change record on ssh logins
   if [ -n "$SSH_CONNECTION" ]; then
     echo 'AGENTS: read ~/<host>.log before changing this host. Append one line per change: date | who | what | why.' >&2
   fi
   ```

   The hook writes to stderr. Stdout must stay clean so scp, rsync, and command output keep working. The line prints once for every shell the session starts, including each one-shot `ssh <host> <command>`. That is intended: do not move the hook behind an interactive-only guard, or those calls stop seeing it. Append the hook to the file if it exists, and never replace the file.
3. Verify with a fresh connection, as in step 7 of path A, and log the setup as the first line.

### Appliances

A vendor update on a NAS, router, or firewall can rewrite `sshd_config` and drop the `Banner` line. Add a line like this to that host's log header, below the template lines:

```
# Appliance: a vendor update can reset sshd_config. After each update, check the AGENTS banner and log the check.
```

After each update, connect, check the banner, and append a line for the result. If the `Banner` line is gone, add it again, run `sshd -t`, and reload. Many appliances have no drop-in folder, so the `Banner` line sits in the main file: snapshot it before you edit that one line.

### Hosts to leave out

Leave out hosts that the whole network depends on: the DNS resolver, the DHCP server, the gateway, the router. A mistake in the sshd change there, or a reload that fails, takes name resolution or routing away from every machine on the LAN, and the gain is one line of text. Mark them "not covered" in the fleet table with the reason. A change on one of them needs the owner's explicit yes for that change.

## Fleet table

Keep one table for the hosts you cover. Columns: host, log path, banner mechanism (drop-in, line in the main file, shell hook, none), and for hosts left out the reason and who approves changes. The table names hosts and addresses, so it belongs in the private overlay and never in a public repository. Add a row when a host joins, and update it when a mechanism changes.

## Output

For a change: the log lines appended, each read back. For a setup: the path taken, the files written, the snapshot folder, the result of `sshd -t`, the result of the fresh connection test, and the row for the fleet table. For a host left out: the reason.

## Rules

- Read the log before any change on a host, and append one line after each change. Never edit, reorder, or delete an old line.
- Send log text on stdin. Never put it inside a quoted remote command.
- No secrets in a log line or in a banner. The banner is public to anyone who reaches the port.
- Setup needs the user's yes for that host. Snapshot first, `sshd -t` before the reload, verify on a fresh connection with the old session still open.
- Leave out the DNS, DHCP, and routing single points.
- This skill touches a host only for its log and its banner. Any other change on a host is the user's request, and this rule logs it.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then `host-log-fleet.md` (the fleet table: hosts, addresses, log paths, banner mechanisms, hosts left out) and the files in `reliability/host-log/` if they exist. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
