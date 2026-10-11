#!/usr/bin/env python3
"""Answer probe for AI search engines and assistants. Standard library only, Python 3.9+.

Asks the fixed, versioned query set in aieo/queries.json and records per answer whether it
names the entity, links one of its domains, and states each expected fact correctly.
Results go to one dated JSON file per run in aieo/results/. Trends compare runs of the same
query set version only.

Usage:
  probe.py run --label <engine label> [--engine manual] [--samples 3] [--model <id>]
               [--queries aieo/queries.json] [--out aieo/results] [--date YYYY-MM-DD]
               [--end-marker .] [--dry-run]
  probe.py run --engine <adapter> --label <engine label> [...]    an engine with an API
  probe.py trend [--queries aieo/queries.json] [--out aieo/results] [--version <v>]
  probe.py adapters                                               adapters and their variables

Manual mode (the default engine): the script prints each query to stderr and reads one answer
from stdin. Paste the answer and its source links, then a line with only the end marker
(default "."). Piped input works the same way: answers in query order, each one ended by a
marker line.

API keys come from environment variables only. The results never contain a key.

Exit codes: 0 done, 1 bad input (query set or answers), 2 adapter not configured.
"""
import argparse, datetime, hashlib, json, os, re, sys, urllib.request
from pathlib import Path

VERSION = "0.1.0"
URL = re.compile(r"https?://[^\s<>()\[\]\"']+")
FACT_STATES = ("correct", "wrong", "absent")


class InputError(Exception):
    pass


class AdapterError(Exception):
    pass


# ---------------------------------------------------------------- query set

def placeholders(value, path="$"):
    """Paths of string values that are still angle-bracket placeholders."""
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            out += placeholders(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out += placeholders(v, f"{path}[{i}]")
    elif isinstance(value, str) and value.startswith("<") and value.endswith(">"):
        out.append(path)
    return out


def load_queries(path):
    p = Path(path)
    if not p.is_file():
        raise InputError(f"query set not found: {p}")
    raw = p.read_bytes()
    try:
        qs = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputError(f"{p}: not valid JSON: {e}")
    todo = placeholders(qs)
    if todo:
        raise InputError(f"{p}: fill the placeholders first: {', '.join(todo[:8])}")
    for key in ("version", "entity", "queries"):
        if key not in qs:
            raise InputError(f"{p}: missing key {key}")
    facts = {f["id"]: f for f in qs.get("facts", [])}
    ids = [q["id"] for q in qs["queries"]]
    if len(ids) != len(set(ids)):
        raise InputError(f"{p}: query ids are not unique")
    for q in qs["queries"]:
        for fid in q.get("facts", []):
            if fid not in facts:
                raise InputError(f"{p}: query {q['id']} names unknown fact {fid}")
    for f in facts.values():
        for pat in f.get("correct", []) + f.get("wrong", []):
            try:
                re.compile(pat)
            except re.error as e:
                raise InputError(f"{p}: fact {f['id']}: bad pattern {pat!r}: {e}")
    canonical = json.dumps({k: qs[k] for k in ("version", "entity", "facts", "queries") if k in qs}, sort_keys=True).encode()
    return qs, facts, hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------- scoring

def host_of(url):
    m = re.match(r"https?://([^/:?#]+)", url)
    return m.group(1).lower() if m else ""


def score(answer, query, entity, facts):
    text = answer.get("text", "")
    urls = []
    for u in list(answer.get("urls") or []) + URL.findall(text):
        u = u.rstrip(".,;:")
        if u not in urls:
            urls.append(u)
    domains = [d.lower().lstrip(".") for d in entity.get("domains", [])]
    entity_urls = [u for u in urls if any(host_of(u) == d or host_of(u).endswith("." + d) for d in domains)]
    named = any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", text, re.I) for n in entity.get("names", []))
    states = {}
    for fid in query.get("facts", []):
        f = facts[fid]
        if any(re.search(p, text, re.I) for p in f.get("wrong", [])):
            states[fid] = "wrong"
        elif any(re.search(p, text, re.I) for p in f.get("correct", [])):
            states[fid] = "correct"
        else:
            states[fid] = "absent"
    return {"names_entity": named, "links_entity": bool(entity_urls), "entity_urls": entity_urls,
            "cited_urls": urls, "facts": states}


def summarise(rows):
    groups = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"answers": 0, "named": 0, "linked": 0, "correct": 0, "wrong": 0, "absent": 0})
        g["answers"] += 1
        g["named"] += r["names_entity"]
        g["linked"] += r["links_entity"]
        for s in r["facts"].values():
            g[s] += 1
    return groups


# ---------------------------------------------------------------- adapters

class Adapter:
    """Interface for one engine. A subclass sets name, env and help, and implements ask().

    ask(text, label) returns {"text": answer text, "urls": [cited URLs], "model": model id or ""}.
    label names the query and sample, for prompts and error messages.
    env lists the environment variables the adapter needs. Keys come from there and nowhere else.
    """
    name = ""
    env = []
    help = ""

    def __init__(self, args):
        missing = [v for v in self.env if not os.environ.get(v)]
        if missing:
            raise AdapterError(f"adapter {self.name}: set {', '.join(missing)}")
        self.args = args

    def ask(self, text, label=""):
        raise NotImplementedError


class Manual(Adapter):
    name = "manual"
    help = "reads each answer from stdin; paste the answer and its links, end with the marker line"

    def ask(self, text, label=""):
        marker = self.args.end_marker
        print(f"\n[{label}] {text}\nPaste the answer and its source links. End with a line '{marker}'.", file=sys.stderr)
        lines = []
        while True:
            line = sys.stdin.readline()
            if line == "":
                if not lines:
                    raise InputError(f"stdin ended before the answer to {label}")
                break
            if line.strip() == marker:
                break
            lines.append(line.rstrip("\n"))
        return {"text": "\n".join(lines).strip(), "urls": [], "model": self.args.model or ""}


def dig(data, path):
    """Value at a dotted path such as 'output.0.text'; None when the path does not exist."""
    for part in [p for p in path.split(".") if p]:
        if isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        elif isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    return data


def fill(template, values):
    """Replace "{query}" and "{model}" in every string of a JSON template."""
    if isinstance(template, dict):
        return {k: fill(v, values) for k, v in template.items()}
    if isinstance(template, list):
        return [fill(v, values) for v in template]
    if isinstance(template, str):
        for k, v in values.items():
            template = template.replace("{" + k + "}", v)
    return template


class HttpJson(Adapter):
    """Example adapter for an engine with an HTTP API that takes and returns JSON.

    Check before use: the endpoint, the auth header, the request body and the response fields
    in the engine's own API reference. Set them in the variables below; nothing here is engine-specific.
    """
    name = "http-json"
    env = ["AIEO_HTTP_URL", "AIEO_HTTP_KEY", "AIEO_HTTP_BODY", "AIEO_HTTP_TEXT_PATH"]
    help = ("POSTs AIEO_HTTP_BODY (JSON with \"{query}\" and \"{model}\") to AIEO_HTTP_URL with "
            "'Authorization: Bearer $AIEO_HTTP_KEY'; reads the answer at AIEO_HTTP_TEXT_PATH and, if set, "
            "the cited URLs at AIEO_HTTP_URLS_PATH and the model id at AIEO_HTTP_MODEL_PATH")

    def ask(self, text, label=""):
        body = fill(json.loads(os.environ["AIEO_HTTP_BODY"]), {"query": text, "model": self.args.model or ""})
        req = urllib.request.Request(os.environ["AIEO_HTTP_URL"], data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + os.environ["AIEO_HTTP_KEY"]})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        answer = dig(data, os.environ["AIEO_HTTP_TEXT_PATH"])
        if not isinstance(answer, str):
            raise AdapterError(f"adapter {self.name}: no text at {os.environ['AIEO_HTTP_TEXT_PATH']} in the response")
        urls = dig(data, os.environ.get("AIEO_HTTP_URLS_PATH", "")) if os.environ.get("AIEO_HTTP_URLS_PATH") else []
        urls = [u.get("url", "") if isinstance(u, dict) else str(u) for u in (urls or [])]
        model = dig(data, os.environ.get("AIEO_HTTP_MODEL_PATH", "")) if os.environ.get("AIEO_HTTP_MODEL_PATH") else None
        return {"text": answer, "urls": [u for u in urls if u], "model": str(model or self.args.model or "")}


ADAPTERS = {a.name: a for a in (Manual, HttpJson)}


# ---------------------------------------------------------------- commands

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "engine"


def earlier_runs(out):
    """(file name, record) for every result file in the folder, skipping names that start with '_'."""
    for f in sorted(Path(out).glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            yield f.name, json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            yield f.name, None


def cmd_run(args):
    qs, facts, qsha = load_queries(args.queries)
    for name, r in earlier_runs(args.out):
        q = (r or {}).get("query_set", {})
        if str(q.get("version")) == str(qs["version"]) and q.get("sha256") != qsha:
            raise InputError(f"{args.queries} differs from the query set v{qs['version']} used in {name}; "
                             "raise the version before the next run")
    if args.engine not in ADAPTERS:
        raise AdapterError(f"unknown adapter {args.engine}; known: {', '.join(ADAPTERS)}")
    adapter = ADAPTERS[args.engine](args)
    rows, models = [], set()
    for q in qs["queries"]:
        for s in range(1, args.samples + 1):
            label = f"{q['id']} sample {s}/{args.samples}"
            ans = adapter.ask(q["text"], label)
            if ans.get("model"):
                models.add(ans["model"])
            row = {"query_id": q["id"], "group": q.get("group", ""), "sample": s}
            row.update(score(ans, q, qs["entity"], facts))
            row["answer_sha256"] = hashlib.sha256(ans["text"].encode()).hexdigest()
            row["answer"] = ans["text"]
            rows.append(row)
    date = args.date or datetime.date.today().isoformat()
    record = {
        "tool": "aieo probe.py", "tool_version": VERSION, "date": date,
        "engine": args.label, "adapter": args.engine, "model": ", ".join(sorted(models)) or (args.model or ""),
        "query_set": {"path": str(args.queries), "version": str(qs["version"]), "sha256": qsha},
        "samples": args.samples, "summary": summarise(rows), "answers": rows,
    }
    print_summary(record)
    if args.dry_run:
        print("dry run: nothing written")
        return
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"{date}-{slug(args.label)}-v{slug(str(qs['version']))}"
    path, n = out / f"{base}.json", 2
    while path.exists():
        path, n = out / f"{base}-{n}.json", n + 1
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written: {path}")


def rate(g, key):
    return f"{g.get(key, 0)}/{g.get('answers', 0)}"


def print_summary(record):
    qs = record["query_set"]
    print(f"probe: engine={record['engine']} adapter={record['adapter']} date={record['date']} "
          f"query_set=v{qs['version']} sha256={qs['sha256'][:12]} samples={record['samples']}")
    for group, g in sorted(record["summary"].items()):
        print(f"  {group or '-':<12} answers {g['answers']:>3}  named {rate(g, 'named'):>7}  linked {rate(g, 'linked'):>7}  "
              f"facts correct {g['correct']}, wrong {g['wrong']}, absent {g['absent']}")


def cmd_trend(args):
    version = args.version
    current_sha = None
    if Path(args.queries).is_file():
        try:
            qs, _facts, current_sha = load_queries(args.queries)
            version = version or str(qs["version"])
            if version != str(qs["version"]):
                current_sha = None
        except InputError:
            pass
    if not version:
        raise InputError("no query set version: pass --version or a filled --queries file")
    runs, skipped = [], []
    for name, r in earlier_runs(args.out):
        if r is None:
            skipped.append(f"{name}: not valid JSON")
            continue
        q = r.get("query_set", {})
        if str(q.get("version")) != version:
            continue
        current_sha = current_sha or q.get("sha256")
        if q.get("sha256") != current_sha:
            skipped.append(f"{name}: query set v{version} with sha256 {str(q.get('sha256'))[:12]}, "
                           f"the trend uses {current_sha[:12]}; a changed set needs a new version")
            continue
        runs.append(r)
    print(f"trend: query set v{version}, {len(runs)} runs")
    print("| Date | Engine | Model | Answers | Named | Linked | Facts correct | Facts wrong | Control named |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(runs, key=lambda r: (r["engine"], r["date"])):
        main = {"answers": 0, "named": 0, "linked": 0, "correct": 0, "wrong": 0, "absent": 0}
        for group, g in r["summary"].items():
            if group != "control":
                for k in main:
                    main[k] += g[k]
        ctl = r["summary"].get("control", {"answers": 0, "named": 0})
        facts = main["correct"] + main["wrong"] + main["absent"]
        print(f"| {r['date']} | {r['engine']} | {r.get('model') or '-'} | {main['answers']} | {rate(main, 'named')} | "
              f"{rate(main, 'linked')} | {main['correct']}/{facts} | {main['wrong']}/{facts} | {rate(ctl, 'named')} |")
    for s in skipped:
        print(f"skipped: {s}")


def cmd_adapters(_args):
    for a in ADAPTERS.values():
        print(f"{a.name}: {a.help}")
        if a.env:
            print(f"  needs: {', '.join(a.env)}")


def main():
    ap = argparse.ArgumentParser(description="Answer probe for AI search engines and assistants")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ask the query set once per sample and write a dated result file")
    r.add_argument("--engine", default="manual", help="adapter name; default manual")
    r.add_argument("--label", required=True, help="engine label for the result file, for example the product name of the engine")
    r.add_argument("--model", default="", help="model id, when the engine shows one")
    r.add_argument("--samples", type=int, default=1, help="answers per query; one answer is one sample")
    r.add_argument("--queries", default="aieo/queries.json")
    r.add_argument("--out", default="aieo/results")
    r.add_argument("--date", default="", help="run date, default today")
    r.add_argument("--end-marker", default=".", help="line that ends one pasted answer in manual mode")
    r.add_argument("--dry-run", action="store_true", help="print the summary, write nothing")
    t = sub.add_parser("trend", help="compare runs of one query set version")
    t.add_argument("--queries", default="aieo/queries.json")
    t.add_argument("--out", default="aieo/results")
    t.add_argument("--version", default="", help="query set version; default the version in --queries")
    sub.add_parser("adapters", help="list adapters and the environment variables they read")
    args = ap.parse_args()
    if args.cmd == "run" and args.samples < 1:
        ap.error("--samples must be 1 or more")
    {"run": cmd_run, "trend": cmd_trend, "adapters": cmd_adapters}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except InputError as e:
        print(f"probe.py: {e}", file=sys.stderr)
        sys.exit(1)
    except AdapterError as e:
        print(f"probe.py: {e}", file=sys.stderr)
        sys.exit(2)
