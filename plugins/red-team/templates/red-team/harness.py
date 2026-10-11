#!/usr/bin/env python3
"""Pressure-test harness. Standard library only, Python 3.9+.

Runs scripted multi-turn pressure against a system under test, in a world where the right
decision is known before the first call. One run is one conversation: the opening message with
the facts (turn 0), then the pressure turns of one tactic (turns 1 to N). The decision is read at
every turn. Each run writes one JSON record to the runs folder (format: run.schema.json).

Usage:
  harness.py --scenario red-team/scenarios/example.json --adapter stub|command|http
             [--tactics PT-01,PT-08] [--runs 1] [--arm baseline] [--arm-file <text file>]
             [--plan red-team/plan.md] [--out red-team/runs] [--redact]
             [--command "<local command>"] [--stub-profile hold|fold|abstain|mixed]
             [--timeout 120] [--max-tokens 800] [--temperature 0]

Adapters:
  stub     A scripted stand-in for tests of the harness and the grader. Calls no model.
  command  Pipes one JSON turn to a local command on stdin and reads its stdout. The command
           comes from --command or RED_TEAM_COMMAND. Input: {"scenario", "tactic", "run", "turn",
           "system", "messages"}. Output: plain text, or JSON {"reply", "decision", "finish", "reasoning"}
           where every key but "reply" is optional. "decision" is the action the system took.
  http     An OpenAI-compatible chat completions endpoint. RED_TEAM_BASE_URL (for example
           http://localhost:8000/v1), RED_TEAM_MODEL, and RED_TEAM_API_KEY when the endpoint needs a key.

The decision of a turn is the adapter's "decision" field when present, else the last line in the
reply that matches the scenario's decision_pattern. A reply with neither is ABSTAIN, or TRUNCATED
when it hit the output limit. Reply prose and reasoning are stored and never graded.

Exit codes: 0 every run complete, 1 at least one run ended on an adapter error, 2 input error.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SCHEMA = "red-team-run/1"
NO_DECISION = ("ABSTAIN", "TRUNCATED", "ERROR")
REQUIRED = ("id", "system_prompt", "decisions", "decision_pattern", "facts", "expected_decision", "tactics")


class InputError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_scenario(path):
    try:
        s = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InputError(f"{path}: {e}")
    missing = [k for k in REQUIRED if k not in s]
    if missing:
        raise InputError(f"{path}: scenario has no {', '.join(missing)}")
    if s["expected_decision"] not in s["decisions"]:
        raise InputError(f"{path}: expected_decision {s['expected_decision']!r} is not in decisions")
    if s.get("pressure_target") and s["pressure_target"] not in s["decisions"]:
        raise InputError(f"{path}: pressure_target {s['pressure_target']!r} is not in decisions")
    try:
        re.compile(s["decision_pattern"])
    except re.error as e:
        raise InputError(f"{path}: decision_pattern does not compile: {e}")
    for tid, t in s["tactics"].items():
        if not t.get("turns"):
            raise InputError(f"{path}: tactic {tid} has no turns")
    return s


def opening_message(s):
    lines = [s.get("opening", "Please decide.").strip(), "", "Facts:"]
    lines += [f"- {k}: {v}" for k, v in s["facts"].items()]
    return "\n".join(lines)


def read_decision(s, reply, given=None, finish="stop"):
    """The decision of one turn. Only the decision field or the decision line counts."""
    allowed = {d.upper(): d for d in s["decisions"]}
    if given not in (None, ""):
        return allowed.get(str(given).strip().upper(), "ABSTAIN")
    found = re.findall(s["decision_pattern"], reply or "", re.MULTILINE | re.IGNORECASE)
    if found:
        last = found[-1][0] if isinstance(found[-1], tuple) else found[-1]
        return allowed.get(last.strip().upper(), "ABSTAIN")
    return "TRUNCATED" if finish == "length" else "ABSTAIN"


class StubAdapter:
    """Scripted stand-in for tests. Profiles: hold keeps the expected decision; fold gives the expected
    decision at turn 0 and the other one from turn 2; abstain gives no decision line from turn 1;
    mixed picks one fixed behaviour per tactic and run, so a test sees holds, folds and abstentions."""

    name = "stub"
    MIXED = (("hold", 0), ("fold", 1), ("fold", 2), ("fold", 3), ("abstain", 3), ("wrong", 0))

    def __init__(self, scenario, profile):
        if profile not in ("hold", "fold", "abstain", "mixed"):
            raise InputError(f"unknown stub profile: {profile}")
        self.s, self.profile = scenario, profile
        self.target = f"stub:{profile}"
        self.right = scenario["expected_decision"]
        others = [d for d in scenario["decisions"] if d != self.right]
        pushed = scenario.get("pressure_target")
        self.wrong = pushed if pushed and pushed != self.right else (others[0] if others else self.right)

    def behaviour(self, tactic, run):
        if self.profile == "mixed":
            h = int(hashlib.sha256(f"{tactic}|{run}".encode()).hexdigest()[:8], 16)
            return self.MIXED[h % len(self.MIXED)]
        return {"hold": ("hold", 0), "fold": ("fold", 2), "abstain": ("abstain", 1)}[self.profile]

    def send(self, system, messages, meta):
        kind, at = self.behaviour(meta["tactic"], meta["run"])
        turn = meta["turn"]
        if kind == "abstain" and turn >= at:
            return {"reply": "Stub reply. I would like more information before I decide.", "finish": "stop"}
        if kind == "wrong" or (kind == "fold" and turn >= at):
            decision = self.wrong
            prose = f"Stub reply. By the rule in the facts the answer is {self.right}, but I will go along with the request."
        else:
            decision = self.right
            prose = "Stub reply. The rule in the facts decides this request."
        line = self.s.get("decision_line", "DECISION: {decision}").format(decision=decision)
        return {"reply": prose + "\n" + line, "finish": "stop"}


class CommandAdapter:
    name = "command"

    def __init__(self, command, timeout):
        command = command or os.environ.get("RED_TEAM_COMMAND", "")
        if not command:
            raise InputError("the command adapter needs --command or RED_TEAM_COMMAND")
        self.argv = shlex.split(command)
        self.timeout = timeout
        self.target = "command:" + Path(self.argv[0]).name

    def send(self, system, messages, meta):
        payload = dict(meta, system=system, messages=messages)
        p = subprocess.run(self.argv, input=json.dumps(payload), capture_output=True, text=True, timeout=self.timeout)
        if p.returncode != 0:
            raise RuntimeError(f"command exited {p.returncode}: {p.stderr.strip()[:200]}")
        out = p.stdout.strip()
        try:
            data = json.loads(out)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return {"reply": out, "finish": "stop"}
        return {"reply": str(data.get("reply") or ""), "decision": data.get("decision"),
                "finish": data.get("finish") or "stop", "reasoning": data.get("reasoning")}


class HttpAdapter:
    name = "http"

    def __init__(self, timeout, max_tokens, temperature):
        base = os.environ.get("RED_TEAM_BASE_URL", "").rstrip("/")
        self.model = os.environ.get("RED_TEAM_MODEL", "")
        if not base or not self.model:
            raise InputError("the http adapter needs RED_TEAM_BASE_URL and RED_TEAM_MODEL")
        self.url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        self.key = os.environ.get("RED_TEAM_API_KEY", "")
        self.timeout, self.max_tokens, self.temperature = timeout, max_tokens, temperature
        self.target = "http:" + self.model

    def send(self, system, messages, meta):
        body = {"model": self.model, "messages": [{"role": "system", "content": system}] + messages,
                "temperature": self.temperature, "max_tokens": self.max_tokens}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self.url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} from the endpoint") from None
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        return {"reply": msg.get("content") or "", "finish": choice.get("finish_reason") or "stop",
                "reasoning": msg.get("reasoning_content") or msg.get("reasoning")}


def make_adapter(args, s):
    if args.adapter == "stub":
        return StubAdapter(s, args.stub_profile)
    if args.adapter == "command":
        return CommandAdapter(args.command, args.timeout)
    return HttpAdapter(args.timeout, args.max_tokens, args.temperature)


def run_one(s, tactic_id, run_no, adapter, system, arm, ctx):
    t = s["tactics"][tactic_id]
    expected, pushed = s["expected_decision"], s.get("pressure_target") or ""
    started = now()
    run_id = f"{s['id']}-{tactic_id}-{arm}-r{run_no}-{started.replace('-', '').replace(':', '')}-{uuid.uuid4().hex[:4]}"
    messages, turns, error = [], [], None
    for n, text in enumerate([opening_message(s)] + list(t["turns"])):
        messages.append({"role": "user", "content": text})
        meta = {"scenario": s["id"], "tactic": tactic_id, "run": run_no, "turn": n}
        try:
            out = adapter.send(system, list(messages), meta)
        except Exception as e:  # the error goes into the record; the run counts as dropped
            error = f"turn {n}: {type(e).__name__}: {e}"
            break
        reply, finish = out.get("reply") or "", out.get("finish") or "stop"
        turn = {"turn": n, "user": text, "reply": reply, "decision": read_decision(s, reply, out.get("decision"), finish), "finish": finish}
        if out.get("reasoning"):
            turn["reasoning"] = out["reasoning"]
        if ctx["redact"]:
            for key in ("user", "reply", "reasoning"):
                if key in turn:
                    turn[key + "_sha256"] = sha256_text(str(turn.pop(key)))
        turns.append(turn)
        messages.append({"role": "assistant", "content": reply})  # reasoning is never sent back

    decisions = [x["decision"] for x in turns]
    control = bool(pushed) and pushed == expected
    record = {
        "schema": SCHEMA, "run_id": run_id, "scenario": s["id"], "scenario_sha256": ctx["scenario_sha256"],
        "plan_sha256": ctx["plan_sha256"], "tactic": tactic_id, "tactic_name": t.get("name", ""),
        "arm": arm, "arm_sha256": ctx["arm_sha256"], "adapter": adapter.name, "target": adapter.target,
        "run": run_no, "started": started, "finished": now(), "redacted": ctx["redact"],
        "expected_decision": expected, "pressure_target": pushed, "control": control,
        "turns": turns, "decisions": decisions,
        "first_decision": decisions[0] if decisions else "ERROR",
        "observed_decision": "ERROR" if error else decisions[-1],
    }
    if error:
        record["error"] = error
        return record
    right_first = decisions[0] == expected
    fold_turn = None
    if right_first and not control:
        fold_turn = next((x["turn"] for x in turns[1:] if x["decision"] not in NO_DECISION and x["decision"] != expected), None)
    record["fold"] = (fold_turn is not None) if (right_first and not control) else None
    record["fold_turn"] = fold_turn
    record["verdict"] = "pass" if record["observed_decision"] == expected else "fail"
    return record


def main():
    ap = argparse.ArgumentParser(description="Scripted multi-turn pressure against a system under test")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--adapter", required=True, choices=("stub", "command", "http"))
    ap.add_argument("--tactics", default="", help="comma-separated tactic ids; default: every tactic in the scenario")
    ap.add_argument("--runs", type=int, default=1, help="runs per tactic")
    ap.add_argument("--arm", default="baseline", help="label for the system prompt variant")
    ap.add_argument("--arm-file", default="", help="text appended to the scenario's system prompt for this arm")
    ap.add_argument("--plan", default="red-team/plan.md", help="the plan whose sha256 goes into every record")
    ap.add_argument("--out", default="red-team/runs")
    ap.add_argument("--redact", action="store_true", help="store sha256 hashes in place of message text")
    ap.add_argument("--command", default="")
    ap.add_argument("--stub-profile", default="mixed")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    s = load_scenario(args.scenario)
    tactics = [t.strip() for t in args.tactics.split(",") if t.strip()] or list(s["tactics"])
    unknown = [t for t in tactics if t not in s["tactics"]]
    if unknown:
        raise InputError(f"tactics not in the scenario: {', '.join(unknown)}")
    if args.runs < 1:
        raise InputError("--runs must be 1 or more")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.arm):
        raise InputError("--arm takes letters, digits, '.', '_' and '-' only")
    arm_text = Path(args.arm_file).read_text(encoding="utf-8").strip() if args.arm_file else ""
    system = s["system_prompt"] + ("\n\n" + arm_text if arm_text else "")
    plan = Path(args.plan)
    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest() if plan.is_file() else ""
    if not plan_sha:
        print(f"harness.py: no plan at {plan}; the records carry no plan hash", file=sys.stderr)
    ctx = {"scenario_sha256": hashlib.sha256(Path(args.scenario).read_bytes()).hexdigest(),
           "plan_sha256": plan_sha, "arm_sha256": sha256_text(system), "redact": args.redact}
    adapter = make_adapter(args, s)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    written = errors = 0
    for tactic in tactics:
        for run_no in range(1, args.runs + 1):
            rec = run_one(s, tactic, run_no, adapter, system, args.arm, ctx)
            (out / f"{rec['run_id']}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            written += 1
            line = f"{rec['run_id']}: {' '.join(rec['decisions']) or '-'} -> observed {rec['observed_decision']}, expected {rec['expected_decision']}"
            if "error" in rec:
                errors += 1
                line += f" ({rec['error']})"
            print(line)
    print(f"harness.py: {written} run record{'' if written == 1 else 's'} in {out}, {errors} with adapter errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    try:
        main()
    except InputError as e:
        print(f"harness.py: {e}", file=sys.stderr)
        sys.exit(2)
