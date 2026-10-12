#!/usr/bin/env python3
"""Count the tool calls of coding agents by tool and by who decided, from Claude Code's events in Loki.

Per tool, over one period:
- allowed by rule (tool_decision accept, source config), by hook (accept, hook), after asking
  (accept, user_temporary or user_permanent);
- denied by rule (reject, config), by hook (reject, hook), after asking (reject, user_reject or user_abort);
- failed: the call ran and failed (tool_result success false).
Asked = allowed after asking + denied after asking. A prompt nobody answered writes no event.
Also prints the busiest 15 minutes of denials, which sets the threshold of the AgentToolDenialsSpike alert.

An empty period exits 1: no events means no audit trail (telemetry off, or the pipeline is broken).
Reads Loki over HTTP, or a file written earlier with --save. Prints Markdown, or JSON with --json.
Standard library only, Python 3.9+.

Usage: python3 tool_audit.py --loki http://<stack-host>:3100 [--days 30 | --start YYYY-MM-DD --end YYYY-MM-DD]
                             [--selector '{service_name=~"claude-code.*"}'] [--save file.json] [--json]
       python3 tool_audit.py --from-file file.json [--json]
"""
import argparse, datetime, json, sys, urllib.parse, urllib.request

sys.dont_write_bytecode = True
SELECTOR = '{service_name=~"claude-code.*"}'
COLUMNS = [  # (key, heading, decision, sources)
    ("allowed_rule", "Allowed by rule", "accept", {"config"}),
    ("allowed_hook", "Allowed by hook", "accept", {"hook"}),
    ("asked_allowed", "Asked, allowed", "accept", {"user_temporary", "user_permanent"}),
    ("asked_denied", "Asked, denied", "reject", {"user_reject", "user_abort"}),
    ("denied_rule", "Denied by rule", "reject", {"config"}),
    ("denied_hook", "Denied by hook", "reject", {"hook"}),
]
WINDOW = "15m"


def queries(selector, seconds):
    r = f"[{seconds}s]"
    return {
        "decisions": f'sum by (tool_name, decision, source) (count_over_time({selector} | event_name="tool_decision" {r}))',
        "failed": f'sum by (tool_name) (count_over_time({selector} | event_name="tool_result" | success="false" {r}))',
        "denials_window": f'sum(count_over_time({selector} | event_name="tool_decision" | decision="reject" [{WINDOW}]))',
    }


def fetch(loki, path, params):
    url = loki.rstrip("/") + "/loki/api/v1/" + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as resp:
        body = json.load(resp)
    if body.get("status") != "success":
        raise RuntimeError(f"Loki answered {body.get('status')}: {body.get('error', '')}")
    return body["data"]["result"]


def collect(loki, selector, start, end):
    seconds = int((end - start).total_seconds())
    q = queries(selector, seconds)
    at = int(end.timestamp()) * 10**9
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "source": {"loki": loki, "selector": selector},
        "decisions": fetch(loki, "query", {"query": q["decisions"], "time": at}),
        "failed": fetch(loki, "query", {"query": q["failed"], "time": at}),
        "denials_window": fetch(loki, "query_range", {"query": q["denials_window"], "start": int(start.timestamp()) * 10**9,
                                                       "end": at, "step": WINDOW}),
    }


def summarise(raw):
    tools, other = {}, {}
    for series in raw.get("decisions", []):
        m, n = series["metric"], int(float(series["value"][1]))
        tool, decision, source = m.get("tool_name", "<none>"), m.get("decision", ""), m.get("source", "")
        row = tools.setdefault(tool, {k: 0 for k, *_ in COLUMNS} | {"failed": 0})
        for key, _, dec, sources in COLUMNS:
            if decision == dec and source in sources:
                row[key] += n
                break
        else:
            other[f"{decision}/{source or '<none>'}"] = other.get(f"{decision}/{source or '<none>'}", 0) + n
    for series in raw.get("failed", []):
        tool = series["metric"].get("tool_name", "<none>")
        row = tools.setdefault(tool, {k: 0 for k, *_ in COLUMNS} | {"failed": 0})
        row["failed"] += int(float(series["value"][1]))
    totals = {k: sum(r[k] for r in tools.values()) for k in [c[0] for c in COLUMNS] + ["failed"]}
    peak = max((float(v) for s in raw.get("denials_window", []) for _, v in s.get("values", [])), default=0.0)
    allowed = totals["allowed_rule"] + totals["allowed_hook"] + totals["asked_allowed"]
    denied = totals["denied_rule"] + totals["denied_hook"] + totals["asked_denied"]
    return {
        "period": raw.get("period", {}), "source": raw.get("source", {}), "tools": tools, "totals": totals,
        "allowed": allowed, "denied": denied, "asked": totals["asked_allowed"] + totals["asked_denied"],
        "other_sources": other, "busiest_window_denials": int(peak), "window": WINDOW,
        "suggested_threshold": max(5, 2 * int(peak)),
    }


def markdown(s):
    p, src = s["period"], s["source"]
    start, end = p.get("start", "?")[:10], p.get("end", "?")[:10]
    out = [f"# Agent tool calls, {start} to {end}", "",
           f"Source: Claude Code `tool_decision` and `tool_result` events in Loki ({src.get('loki', 'saved file')}), "
           f"selector `{src.get('selector', SELECTOR)}`.", ""]
    heads = [h for _, h, *_ in COLUMNS] + ["Failed"]
    out += ["| Tool | " + " | ".join(heads) + " |", "|---|" + "---:|" * len(heads)]
    keys = [k for k, *_ in COLUMNS] + ["failed"]
    order = sorted(s["tools"].items(), key=lambda kv: (-(kv[1]["denied_rule"] + kv[1]["denied_hook"] + kv[1]["asked_denied"]),
                                                         -sum(kv[1].values()), kv[0]))
    for tool, row in order:
        out.append(f"| {tool} | " + " | ".join(str(row[k]) for k in keys) + " |")
    out.append("| Total | " + " | ".join(str(s["totals"][k]) for k in keys) + " |")
    t = s["totals"]
    out += ["", f"Allowed: {s['allowed']}. Denied: {s['denied']} (rule {t['denied_rule']}, hook {t['denied_hook']}, "
            f"person {t['asked_denied']}). Asked: {s['asked']} (allowed {t['asked_allowed']}, denied {t['asked_denied']}).",
            f"Busiest {s['window']} of denials: {s['busiest_window_denials']}. "
            f"Threshold for AgentToolDenialsSpike at twice that, at least 5: {s['suggested_threshold']}."]
    if s["other_sources"]:
        out.append("Other decision sources: " + ", ".join(f"{k} {v}" for k, v in sorted(s["other_sources"].items())) + ".")
    out += ["", "Not in this record: prompts nobody answered, and sessions that send no telemetry. "
            "Calls to MCP tools count under `mcp_tool`; the event names the server only in its parameters."]
    return "\n".join(out)


def day(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


def main():
    ap = argparse.ArgumentParser(description="Count agent tool calls by tool and by who decided, from Claude Code events in Loki")
    ap.add_argument("--loki", help="Loki base URL, such as http://localhost:3100")
    ap.add_argument("--from-file", help="a file written earlier with --save")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--start", help="YYYY-MM-DD, UTC; default: --days before --end")
    ap.add_argument("--end", help="YYYY-MM-DD, UTC, exclusive; default: now")
    ap.add_argument("--selector", default=SELECTOR)
    ap.add_argument("--save", help="write the raw query results to this file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if bool(args.loki) == bool(args.from_file):
        ap.error("give --loki or --from-file")
    if args.from_file:
        with open(args.from_file) as f:
            raw = json.load(f)
    else:
        end = day(args.end) if args.end else datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        start = day(args.start) if args.start else end - datetime.timedelta(days=args.days)
        if start >= end:
            ap.error("--start must be before --end")
        try:
            raw = collect(args.loki, args.selector, start, end)
        except (OSError, RuntimeError, ValueError) as e:
            sys.exit(f"tool_audit: Loki query failed: {e}")
    if args.save:
        with open(args.save, "w") as f:
            json.dump(raw, f, indent=1)
    s = summarise(raw)
    print(json.dumps(s, indent=2) if args.json else markdown(s))
    if not s["tools"]:
        print("tool_audit: no tool_decision events in the period: telemetry is off or does not reach Loki", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
