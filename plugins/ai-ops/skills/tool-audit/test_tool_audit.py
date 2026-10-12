#!/usr/bin/env python3
"""Tests for tool_audit.py: the column mapping, the totals, the alert threshold, the Markdown, the CLI exit
codes, and the Loki queries against a fake Loki server in a thread. Standard library only, Python 3.9+.

Usage: python3 plugins/ai-ops/skills/tool-audit/test_tool_audit.py [-v]
"""
import importlib.util, json, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "tool_audit.py"
VERBOSE = "-v" in sys.argv
spec = importlib.util.spec_from_file_location("tool_audit", SCRIPT)
ta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ta)


def d(tool, decision, source, n):
    return {"metric": {"tool_name": tool, "decision": decision, "source": source}, "value": [0, str(n)]}


RAW = {
    "period": {"start": "2026-09-12T00:00:00+00:00", "end": "2026-10-12T00:00:00+00:00"},
    "source": {"loki": "http://stack:3100", "selector": ta.SELECTOR},
    "decisions": [
        d("Bash", "accept", "config", 100), d("Bash", "accept", "hook", 2), d("Bash", "accept", "user_temporary", 3),
        d("Bash", "accept", "user_permanent", 1), d("Bash", "reject", "config", 4), d("Bash", "reject", "hook", 5),
        d("Bash", "reject", "user_reject", 6), d("Bash", "reject", "user_abort", 7), d("Read", "accept", "config", 50),
        d("WebFetch", "reject", "config", 1), d("Write", "accept", "policy_server", 9),
    ],
    "failed": [{"metric": {"tool_name": "Bash"}, "value": [0, "8"]}, {"metric": {"tool_name": "Grep"}, "value": [0, "2"]}],
    "denials_window": [{"metric": {}, "values": [[1, "0"], [2, "7"], [3, "3"]]}],
}


def case_columns():
    s = ta.summarise(RAW)
    want = {"allowed_rule": 100, "allowed_hook": 2, "asked_allowed": 4, "asked_denied": 13, "denied_rule": 4,
            "denied_hook": 5, "failed": 8}
    return [] if s["tools"]["Bash"] == want else [f"Bash row {s['tools']['Bash']}, want {want}"]


def case_totals():
    s = ta.summarise(RAW)
    got = (s["allowed"], s["denied"], s["asked"], s["totals"]["failed"])
    return [] if got == (156, 23, 17, 10) else [f"allowed, denied, asked, failed = {got}, want (156, 23, 17, 10)"]


def case_unknown_source():
    s = ta.summarise(RAW)
    problems = [] if s["other_sources"] == {"accept/policy_server": 9} else [f"other {s['other_sources']}"]
    if s["tools"]["Write"]["allowed_rule"] != 0:
        problems.append("an unknown source was counted as a rule")
    return problems


def case_failed_only_tool():
    s = ta.summarise(RAW)
    return [] if s["tools"].get("Grep", {}).get("failed") == 2 else ["a tool with failures only has no row"]


def case_threshold():
    problems = []
    if (ta.summarise(RAW)["busiest_window_denials"], ta.summarise(RAW)["suggested_threshold"]) != (7, 14):
        problems.append("peak 7 should give threshold 14")
    quiet = dict(RAW, denials_window=[{"metric": {}, "values": [[1, "1"]]}])
    if ta.summarise(quiet)["suggested_threshold"] != 5:
        problems.append("peak 1 should give the floor of 5")
    if ta.summarise(dict(RAW, denials_window=[]))["busiest_window_denials"] != 0:
        problems.append("no window data should give peak 0")
    return problems


def case_markdown():
    md = ta.markdown(ta.summarise(RAW))
    lines = md.splitlines()
    problems = []
    rows = [l for l in lines if l.startswith("| ") and not l.startswith("| Tool")]
    if not rows or not rows[0].startswith("| Bash |"):
        problems.append("the tool with the most denials is not the first row")
    if "| WebFetch | 0 | 0 | 0 | 0 | 1 | 0 | 0 |" not in lines:
        problems.append("WebFetch row wrong")
    elif lines.index("| WebFetch | 0 | 0 | 0 | 0 | 1 | 0 | 0 |") > lines.index("| Read | 50 | 0 | 0 | 0 | 0 | 0 | 0 |"):
        problems.append("a tool with a denial does not rank above a busier tool without one")
    if "| Total | 150 | 2 | 4 | 13 | 5 | 5 | 10 |" not in lines:
        problems.append("totals row wrong")
    if "Denied: 23 (rule 5, hook 5, person 13)" not in md:
        problems.append("denied summary wrong")
    if "Other decision sources: accept/policy_server 9." not in md:
        problems.append("other sources line missing")
    if "Other decision sources" in ta.markdown(ta.summarise(dict(RAW, decisions=RAW["decisions"][:-1]))):
        problems.append("other sources line printed without other sources")
    if "# Agent tool calls, 2026-09-12 to 2026-10-12" not in md:
        problems.append("heading wrong")
    return problems


def case_queries():
    q = ta.queries('{job="x"}', 2592000)
    problems = []
    if '{job="x"} | event_name="tool_decision" [2592000s]' not in q["decisions"]:
        problems.append("decisions query does not carry the selector and the range")
    if 'success="false" [2592000s]' not in q["failed"]:
        problems.append("failed query wrong")
    if 'decision="reject" [15m]' not in q["denials_window"]:
        problems.append("window query wrong")
    return problems


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def case_cli_file():
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        full, empty = Path(tmp, "full.json"), Path(tmp, "empty.json")
        full.write_text(json.dumps(RAW))
        empty.write_text(json.dumps(dict(RAW, decisions=[], failed=[], denials_window=[])))
        p = run("--from-file", str(full))
        if p.returncode != 0 or "| Bash |" not in p.stdout:
            problems.append(f"full file: exit {p.returncode}")
        p = run("--from-file", str(full), "--json")
        if p.returncode != 0 or json.loads(p.stdout)["denied"] != 23:
            problems.append("--json output wrong")
        p = run("--from-file", str(empty))
        if p.returncode != 1 or "no tool_decision events" not in p.stderr:
            problems.append(f"empty period: exit {p.returncode}, want 1 with a message")
    p = run("--loki", "http://x", "--from-file", "y")
    if p.returncode != 2:
        problems.append(f"--loki with --from-file: exit {p.returncode}, want 2")
    p = run()
    if p.returncode != 2:
        problems.append(f"no source: exit {p.returncode}, want 2")
    return problems


class FakeLoki(BaseHTTPRequestHandler):
    seen, fail = [], False

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(u.query))
        FakeLoki.seen.append((u.path, params))
        if FakeLoki.fail:
            body = {"status": "error", "error": "parse error"}
        elif "tool_result" in params["query"]:
            body = {"status": "success", "data": {"result": RAW["failed"]}}
        elif u.path.endswith("query_range"):
            body = {"status": "success", "data": {"result": RAW["denials_window"]}}
        else:
            body = {"status": "success", "data": {"result": RAW["decisions"]}}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def case_loki_http():
    problems = []
    srv = HTTPServer(("127.0.0.1", 0), FakeLoki)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp, "saved.json")
            p = run("--loki", url, "--start", "2026-09-12", "--end", "2026-10-12", "--save", str(saved))
            if p.returncode != 0 or "| Total | 150 |" not in p.stdout:
                problems.append(f"live query: exit {p.returncode} {p.stderr.strip()}")
            paths = [s[0] for s in FakeLoki.seen]
            if paths.count("/loki/api/v1/query") != 2 or paths.count("/loki/api/v1/query_range") != 1:
                problems.append(f"queried {paths}")
            rng = [s[1] for s in FakeLoki.seen if s[0].endswith("query_range")]
            if rng and (rng[0].get("step") != "15m" or rng[0].get("start") != "1789171200000000000"
                        or rng[0].get("end") != "1791763200000000000"):
                problems.append(f"range params {rng[0]}")
            inst = [s[1] for s in FakeLoki.seen if s[0].endswith("/query")]
            if inst and "[2592000s]" not in inst[0].get("query", ""):
                problems.append("instant query range is not the period")
            if not saved.is_file() or json.loads(saved.read_text())["source"]["loki"] != url:
                problems.append("--save did not write the raw results")
            elif run("--from-file", str(saved)).stdout != p.stdout:
                problems.append("a saved file does not reproduce the report")
        FakeLoki.fail = True
        p = run("--loki", url, "--days", "1")
        if p.returncode != 1 or "Loki query failed" not in p.stderr:
            problems.append(f"Loki error: exit {p.returncode}, stderr {p.stderr.strip()!r}")
        p = run("--loki", "http://127.0.0.1:9", "--days", "1")
        if p.returncode != 1 or "Loki query failed" not in p.stderr:
            problems.append(f"no Loki: exit {p.returncode}")
        p = run("--loki", url, "--start", "2026-10-12", "--end", "2026-10-01")
        if p.returncode != 2:
            problems.append("start after end was accepted")
    finally:
        srv.shutdown()
    return problems


CASES = [case_columns, case_totals, case_unknown_source, case_failed_only_tool, case_threshold, case_markdown,
         case_queries, case_cli_file, case_loki_http]


def main():
    failures = 0
    for case in CASES:
        problems = case()
        failures += bool(problems)
        print(f"{'ok  ' if not problems else 'FAIL'} {case.__name__}")
        for p in problems:
            print("     " + p)
    print(f"{len(CASES)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
