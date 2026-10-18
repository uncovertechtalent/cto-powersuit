#!/usr/bin/env python3
"""Tests for the append snippet of /reliability:host-log, the one place where a log line crosses a shell.

The skill sends a log line to a host on stdin and keeps the remote command fixed. These cases take the snippet
from skills/host-log/SKILL.md (so the test follows the text) and run it against a fake `ssh`.

- The fake ssh models the two sides of a real one: it drops the destination, joins the remaining words with
  spaces, and hands them to a shell on "the host", which has its own working folder and its own HOME. A
  marker file shows which side ran a command, and a stray file in the local home shows a leak.
- The snippet: the heredoc delimiter is quoted and the remote command holds no log text.
- Text that is hostile to a shell (apostrophes, quotes, backslashes, `$`, command substitution, separators,
  redirects, `%` codes, globs, tilde, non-ASCII) arrives byte for byte on one line, with an absolute log path and
  with a `~` path, from bash and zsh to a host whose shell is sh, dash, bash, or zsh. Nothing runs on either side and
  no file appears on either side.
- Two appends give two lines, in order, and the read-back command of the skill returns the last one.
- The forbidden forms still break, on the side the skill names: the single-quoted form runs the text on the
  local machine and the double-quoted form on the host. The test fails if the fake stops modelling the trap.

zsh is skipped with a note when it is not installed. Standard library only, Python 3.9+.
Usage: python3 plugins/reliability/tests/test_host_log.py [-v]
"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

MODULE = Path(__file__).resolve().parent.parent
SKILL = MODULE / "skills/host-log/SKILL.md"
VERBOSE = "-v" in sys.argv
WHO, WHY = "s1", "PROJ-1"
TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} \S+"
PLACEHOLDERS = re.compile(r"<(?:name|what changed|why or ref|user>@<address|log path|text)>")

# Each text is one line. The shell of the sender or of the host must neither run nor change any of it.
TEXTS = [
    ("apostrophes", "it's reloaded and we don't retry"),
    ("quotes and backslashes", 'set "timeout" to 120s in C:\\temp\\x, and \\n stays two characters'),
    ("dollar and backtick", "$HOME ${PATH} $(touch SUBST) `touch TICK` $((1+1))"),
    ("separators and redirects", "a; touch SEMI && touch AND || touch OR > REDIR < /dev/null &"),
    ("pipes and format codes", "50% done %s %d | still one line for the shell"),
    ("delimiter word", "the word LINE inside a line, and EOF too"),
    ("glob and tilde", "* ? [a-z] ~ ~root {a,b} !! !$"),
    ("non-ASCII", "Größe → 3 µs, 日本語"),
    ("spaces and dashes", "   -n  -e \\t  trailing   "),
]
TRAP_TEXT = "it's reloaded; touch MARK; we don't retry"

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def section(title):
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise AssertionError(f"SKILL.md has no section '## {title}'")
    return m.group(1)


def snippet():
    """The bash block of '## Append a line', split into the block, the heredoc body, and the remote command."""
    m = re.search(r"```bash\n(.*?)\n```", section("Append a line"), re.S)
    if not m:
        raise AssertionError("no bash block under '## Append a line'")
    block = m.group(1)
    h = re.search(r"<<(\S+)\n(.*?)\n(\S+)\n", block, re.S)
    ssh = re.search(r"\| ssh (\S+) '([^']*)'", block)
    if not h or not ssh:
        raise AssertionError(f"cannot find the heredoc and the ssh call in the block: {block!r}")
    return {"block": block, "delimiter": h.group(1), "closer": h.group(3), "body": h.group(2),
            "destination": ssh.group(1), "remote": ssh.group(2)}


def readback():
    spans = re.findall(r"`(ssh <user>@<address> 'tail -n 1 <log path>')`", section("Append a line"))
    if len(spans) != 1:
        raise AssertionError(f"want one read-back command in the Append section, found {len(spans)}")
    return spans[0]


def forbidden_forms():
    """The two inline commands the skill forbids: the single-quoted form, then the double-quoted form."""
    spans = re.findall(r"`(ssh host [^`]*<text>[^`]*)`", section("Append a line"))
    if len(spans) != 2 or not spans[0].startswith("ssh host '") or not spans[1].startswith('ssh host "'):
        raise AssertionError(f"want the single-quoted and the double-quoted form, found {spans}")
    return spans


def fill(template, text="plain text", log="/tmp/host.log"):
    out = (template.replace("<name>", WHO).replace("<what changed>", text).replace("<why or ref>", WHY)
           .replace("<user>@<address>", "deploy@host.test").replace("<log path>", log).replace("<text>", text))
    return out


class World:
    """Two sides: the local machine (a working folder and a HOME) and the host (the same)."""

    def __init__(self, root):
        self.root = Path(root)
        self.local, self.local_home = self.root / "local/cwd", self.root / "local/home"
        self.remote, self.remote_home = self.root / "remote/cwd", self.root / "remote/home"
        self.logs, self.bin = self.root / "remote/logs", self.root / "bin"
        for d in (self.local, self.local_home, self.remote, self.remote_home, self.logs, self.bin):
            d.mkdir(parents=True)
        fake = self.bin / "ssh"
        fake.write_text('#!/bin/sh\n'
                        '# Models ssh: drop the destination, join the other words with spaces, run them in a shell on the host.\n'
                        'shift\n'
                        'cd "$FAKE_REMOTE_CWD" || exit 97\n'
                        'HOME="$FAKE_REMOTE_HOME" exec "$FAKE_REMOTE_SHELL" -c "$*"\n')
        fake.chmod(0o755)

    def env(self, remote_shell):
        env = dict(os.environ)
        env.update(PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", HOME=str(self.local_home),
                   FAKE_REMOTE_CWD=str(self.remote), FAKE_REMOTE_HOME=str(self.remote_home),
                   FAKE_REMOTE_SHELL=remote_shell)
        return env

    def run(self, shell, script, remote_shell):
        return subprocess.run([shell, "-c", script], cwd=self.local, env=self.env(remote_shell), capture_output=True,
                              text=True, encoding="utf-8", stdin=subprocess.DEVNULL)

    def leaks(self):
        """Files outside the log: anything in either working folder or in the local home."""
        found = []
        for label, d in (("local folder", self.local), ("local home", self.local_home), ("host folder", self.remote)):
            found += [f"{label}: {p.name}" for p in d.iterdir()]
        return found


def shells():
    found = [(n, shutil.which(n)) for n in ("bash", "zsh")]
    skipped = [n for n, p in found if not p]
    if skipped and VERBOSE:
        print(f"     skipped, not installed: {', '.join(skipped)}")
    return [(n, p) for n, p in found if p]


def with_world(fn):
    with tempfile.TemporaryDirectory() as tmp:
        return fn(World(tmp))


@test
def snippet_is_the_documented_one():
    s, bad = snippet(), []
    if s["delimiter"] != "'LINE'":
        bad.append(f"the heredoc delimiter is {s['delimiter']}, want 'LINE' (quoted, so the local shell expands nothing)")
    if s["closer"] != "LINE":
        bad.append(f"the heredoc closes with {s['closer']}, want LINE")
    if s["remote"] != "cat >> <log path>":
        bad.append(f"the remote command is {s['remote']!r}, want a fixed 'cat >> <log path>' with no log text")
    for ph in ("<name>", "<what changed>", "<why or ref>"):
        if ph not in s["body"]:
            bad.append(f"the line template lost the placeholder {ph}")
    left = PLACEHOLDERS.findall(fill(s["block"]))
    if left:
        bad.append(f"placeholders left after filling: {left}; update the test with the skill")
    return bad


@test
def fake_ssh_models_two_sides():
    bad = []

    def go(w):
        for name, path in shells():
            for remote_shell in ("sh", "bash"):
                p = w.run(path, "ssh h 'pwd -P; echo $HOME'", remote_shell)
                want = f"{w.remote.resolve()}\n{w.remote_home}\n"
                if p.stdout != want:
                    bad.append(f"{name} -> {remote_shell}: the host side ran in {p.stdout!r}, want {want!r}")
            p = w.run(path, "pwd -P; echo $HOME", "sh")
            want = f"{w.local.resolve()}\n{w.local_home}\n"
            if p.stdout != want:
                bad.append(f"{name}: the local side ran in {p.stdout!r}, want {want!r}")
    with_world(go)
    return bad


def append_case(w, shell, remote_shell, text, log_arg, log_file):
    s = snippet()
    script = fill(s["block"], text, log_arg)
    p = w.run(shell, script, remote_shell)
    body = fill(s["body"], text)
    bad = []
    if p.returncode != 0:
        bad.append(f"exit {p.returncode}, stderr {p.stderr.strip()!r}")
    try:
        got = log_file.read_bytes().decode("utf-8")
    except FileNotFoundError:
        got = None
    if got is None:
        bad.append("no log file")
    elif not re.fullmatch(rf"{TIMESTAMP} \| {re.escape(body)}\n", got):
        bad.append(f"log holds {got!r}, want a timestamp, then {body!r}")
    bad += [f"stray {x}" for x in w.leaks()]
    return bad


@test
def append_keeps_hostile_text_verbatim():
    bad = []
    runs = 0
    for name, path in shells():
        for remote_shell in ("sh", "dash", "bash", "zsh"):
            if not shutil.which(remote_shell):
                continue
            for label, text in TEXTS:
                for form in ("absolute path", "tilde path"):
                    def go(w):
                        if form == "absolute path":
                            log = w.logs / "host.log"
                            return append_case(w, path, remote_shell, text, str(log), log)
                        return append_case(w, path, remote_shell, text, "~/host.log", w.remote_home / "host.log")
                    runs += 1
                    for b in with_world(go):
                        bad.append(f"{name} -> {remote_shell}, {label}, {form}: {b}")
    if VERBOSE:
        print(f"     {runs} runs")
    return bad


@test
def two_appends_give_two_lines_and_the_readback_returns_the_last():
    bad = []

    def go(w):
        s = snippet()
        log = w.logs / "host.log"
        for name, path in shells():
            if log.exists():
                log.unlink()
            for text in ("first change", "second change, it's the last"):
                p = w.run(path, fill(s["block"], text, str(log)), "sh")
                if p.returncode != 0:
                    bad.append(f"{name}: append exit {p.returncode}: {p.stderr.strip()!r}")
            lines = log.read_text(encoding="utf-8").split("\n")
            if len(lines) != 3 or lines[2] != "" or not lines[0].endswith("| first change | " + WHY) \
                    or not lines[1].endswith("| second change, it's the last | " + WHY):
                bad.append(f"{name}: log lines {lines!r}")
            p = w.run(path, fill(readback(), log=str(log)), "sh")
            if p.stdout != lines[1] + "\n":
                bad.append(f"{name}: read-back printed {p.stdout!r}, want the second line")
        bad.extend(f"stray {x}" for x in w.leaks())
    with_world(go)
    return bad


@test
def quoted_remote_command_forms_still_break_on_the_named_side():
    single, double = forbidden_forms()
    bad = []
    for name, path in shells():
        for label, form, runs_on in (("single-quoted", single, "local"), ("double-quoted", double, "host")):
            def go(w):
                log = w.logs / "host.log"
                script = fill(form, TRAP_TEXT).replace("/host.log", str(log))
                w.run(path, script, "sh")
                local, host = (w.local / "MARK").exists(), (w.remote / "MARK").exists()
                found = []
                if runs_on == "local" and not (local and not host):
                    found.append(f"the text must run on the local machine only; local {local}, host {host}")
                if runs_on == "host" and not (host and not local):
                    found.append(f"the text must run on the host only; local {local}, host {host}")
                intact = log.exists() and TRAP_TEXT in log.read_text(encoding="utf-8")
                if intact:
                    found.append("the line arrived intact; the trap is not modelled")
                return found
            bad += [f"{name}, {label} form: {b}" for b in with_world(go)]
    return bad


def main():
    failures = 0
    for fn in TESTS:
        try:
            bad = fn()
        except Exception as e:  # a crash is a failure of that case
            bad = [f"raised {type(e).__name__}: {e}"]
        print(f"{'ok  ' if not bad else 'FAIL'} {fn.__name__}")
        for b in bad[:12]:
            print(f"     {b}")
        if len(bad) > 12:
            print(f"     ... and {len(bad) - 12} more")
        failures += bool(bad)
    print(f"{len(TESTS)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
