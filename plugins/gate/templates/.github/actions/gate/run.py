#!/usr/bin/env python3
"""Deploy gate runner. Standard library only, Python 3.9+.

Loads the rules in the rules folder, runs the ones enabled in the gate config,
derives an overall result, keeps findings open until a later run passes them,
and writes a run record, latest.json, summary.md and .result.

Usage:
  run.py [--config gate/gate.json] [--root .] [--out <dir>] [--trigger push|schedule|workflow_dispatch|manual]
         [--sha <commit>] [--runner <label>] [--only <rule id>[,<rule id>]] [--dry-run] [--exit-code]

Exit codes: 0 run complete (overall in <out>/.result, or printed on --dry-run),
1 overall fail with --exit-code, 2 config error, 3 internal error.

The rule contract is in rules/README.md next to this file.
"""
import argparse, datetime, hashlib, importlib.util, json, platform, re, subprocess, sys, traceback, uuid
from pathlib import Path

VERSION = "0.1.0"
HERE = Path(__file__).resolve().parent
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
TS = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
RESULTS = ("pass", "warn", "fail", "n/a")
DEFAULT_EXCLUDE = [".git/", "node_modules/", "/gate/"]


class ConfigError(Exception):
    pass


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_front_matter(text):
    """Return (meta, body, body_line). Accepts a block between two '---' lines at the top of the file,
    or a header of 'key: value' lines ended by a '---' line. Values are strings; a key followed by
    '- item' lines becomes a comma-separated string. Without front matter: ({}, text, 1)."""
    lines = text.split("\n")
    key_line = re.compile(r"^([A-Za-z_][\w-]*)\s*:(.*)$")
    head, start = None, 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                head, start = lines[1:i], i + 1
                break
    elif lines and key_line.match(lines[0]):
        for i, line in enumerate(lines):
            if line.strip() == "---":
                head, start = lines[:i], i + 1
                break
            if line.strip() and not (key_line.match(line) or line.lstrip().startswith("- ")):
                break
    if head is None:
        return {}, text, 1
    meta, last = {}, None
    for line in head:
        m = key_line.match(line)
        if m:
            last = m.group(1)
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if v.startswith("[") and v.endswith("]"):
                v = ", ".join(x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip())
            meta[last] = v
        elif last and line.lstrip().startswith("- "):
            item = line.lstrip()[2:].strip().strip("\"'")
            meta[last] = (meta[last] + ", " + item) if meta[last] else item
    return meta, "\n".join(lines[start:]), start + 1


def load_rules(rules_dir):
    """Every *.py file in rules_dir that does not start with '_' and defines ID and check()."""
    rules = {}
    d = Path(rules_dir)
    if not d.is_dir():
        return rules
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location("gate_rule_" + re.sub(r"\W", "_", str(f.resolve())), f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "ID") or not callable(getattr(mod, "check", None)):
            raise ConfigError(f"{f}: a rule file needs ID and check(ctx)")
        if mod.ID in rules:
            raise ConfigError(f"{f}: rule id {mod.ID} is defined twice")
        mod.__gate_file__ = f
        rules[mod.ID] = mod
    return rules


def normalise(res, rule_id):
    if not isinstance(res, dict) or res.get("result") not in RESULTS:
        return {"result": "fail", "detail": f"rule {rule_id} returned no valid result", "evidence": [repr(res)[:200]], "hits": []}
    out = {"result": res["result"], "detail": str(res.get("detail", "")), "evidence": [str(e) for e in res.get("evidence") or []], "hits": []}
    for h in res.get("hits") or []:
        out["hits"].append({"file": str(h.get("file", "-")), "line": h.get("line"), "snippet": str(h.get("snippet", ""))[:200]})
    return out


class Ctx:
    """What a rule sees. See rules/README.md for the contract."""

    def __init__(self, root, options, config, history, trigger, git_dir):
        self.root = Path(root).resolve()
        self.options = options
        self.config = config
        self.history = history
        self.trigger = trigger
        self.now = NOW
        self.today = NOW.date()
        self._git_dir = git_dir
        self._exclude = list(config.get("exclude", DEFAULT_EXCLUDE))

    def rel(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def excluded(self, relpath):
        """A pattern ending in '/' is a folder, any other pattern a file. A leading '/' anchors the
        pattern at root; without it the folder or file name matches at any depth."""
        for x in self._exclude:
            anchored, pat = x.startswith("/"), x.lstrip("/")
            if pat.endswith("/"):
                if relpath.startswith(pat) or (not anchored and ("/" + pat) in ("/" + relpath)):
                    return True
            elif relpath == pat or (not anchored and relpath.endswith("/" + pat)):
                return True
        return False

    def files(self, globs, exclude=()):
        """Files under root matching any of the glob patterns ('**' recurses), minus the config's exclude
        list and the extra exclude patterns; sorted, no duplicates."""
        if isinstance(globs, str):
            globs = [globs]
        seen, out = set(), []
        for g in globs:
            for p in self.root.glob(g):
                if not p.is_file():
                    continue
                r = p.relative_to(self.root).as_posix()
                if r in seen or self.excluded(r) or any(Path(r).match(x) or r.startswith(x) for x in exclude):
                    continue
                seen.add(r)
                out.append(p)
        return sorted(out)

    def read(self, path):
        return Path(path).read_text(encoding="utf-8", errors="replace")

    def front_matter(self, path):
        return parse_front_matter(self.read(path))

    def git(self, *args):
        try:
            return subprocess.run(["git", *args], cwd=self._git_dir or self.root, capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            return ""

    def load_rules(self, rules_dir):
        return load_rules(rules_dir)

    def run_rule(self, rule, root, options=None):
        """Run a rule module against another root (a fixture tree, for example) and return its result."""
        opts = dict(getattr(rule, "DEFAULTS", {}))
        opts.update(options or {})
        sub = Ctx(root, opts, self.config, self.history, self.trigger, None)
        try:
            return normalise(rule.check(sub), rule.ID)
        except Exception as e:
            return {"result": "fail", "detail": f"rule {rule.ID} raised {type(e).__name__}: {e}", "evidence": traceback.format_exc().splitlines()[-3:], "hits": []}


def finding_key(rule_id, hit):
    return hashlib.sha256(f"{rule_id}|{hit.get('file')}|{hit.get('snippet', '')}".encode()).hexdigest()[:12]


def build_findings(prev, checks, sha):
    """A finding opens for each hit of a failing rule, in either tier, and closes only when a later run of
    that rule no longer sees the hit. Turning a rule off or moving it to warn closes nothing."""
    found = {}
    for rid, c in checks.items():
        if c["result"] != "fail":
            continue
        for h in c["hits"] or [{"file": "-", "snippet": c["detail"]}]:
            k = finding_key(rid, h)
            found[k] = {"id": f"F-{k}", "rule": rid, "tier": c["tier"], "file": h.get("file"), "line": h.get("line"), "snippet": h.get("snippet")}
    out, seen = [], set()
    for f in prev:
        k = f["id"][2:]
        seen.add(k)
        if k in found:
            f.update(status="open", last_seen=TS, runs_seen=f.get("runs_seen", 1) + 1, line=found[k].get("line"), tier=found[k]["tier"])
        elif f.get("status") == "open" and f.get("rule") in checks:
            f.update(status="closed", closed=TS, closed_commit=sha)
        out.append(f)
    for k, f in found.items():
        if k not in seen:
            out.append(dict(f, status="open", opened=TS, opened_commit=sha, last_seen=TS, runs_seen=1))
    return out


def summary_md(gate_name, overall, checks, findings, history):
    open_f = [f for f in findings if f["status"] == "open"]
    closed_f = sorted((f for f in findings if f["status"] == "closed"), key=lambda f: f.get("closed", ""), reverse=True)[:10]
    blocking = sum(f.get("tier") == "block" for f in open_f)
    lines = [f"# Gate: {gate_name}", "", f"Last run {TS}, overall **{overall}**. Open findings: {len(open_f)}, of which {blocking} in the block tier.", "",
             "## Checks", "", "| Rule | Tier | Result | Detail |", "|---|---|---|---|"]
    for rid, c in checks.items():
        lines.append(f"| `{rid}` | {c['tier']} | {c['effective']} | {c['detail'].replace('|', '/')} |")
    lines += ["", "## Open findings", ""]
    lines += [f"- `{f['id']}` `{f['rule']}` ({f.get('tier', 'block')}) {f.get('file') or ''}{(':' + str(f['line'])) if f.get('line') else ''} {f.get('snippet') or ''} (opened {f.get('opened', '')[:10]}, seen in {f.get('runs_seen', 1)} runs)" for f in open_f] or ["None."]
    lines += ["", "## Recently closed", ""]
    lines += [f"- `{f['id']}` `{f['rule']}` {f.get('file') or ''}, closed {f.get('closed', '')[:10]} by commit {str(f.get('closed_commit', ''))[:12]}" for f in closed_f] or ["None."]
    lines += ["", "## History", "", "| Run (UTC) | Trigger | Commit | Overall | Open |", "|---|---|---|---|---|"]
    for h in reversed(history[-10:]):
        lines.append(f"| {h['ts']} | {h['trigger']} | `{str(h['sha'])[:12]}` | {h['overall']} | {h['findings_open']} |")
    lines += ["", "Written by run.py. Full run records are in `runs/` or the CI artifacts.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Deploy gate runner")
    ap.add_argument("--config", default="gate/gate.json")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None, help="directory for latest.json, summary.md, runs/ and .result; default: the config's directory")
    ap.add_argument("--git-dir", default=None, help="repository for commit metadata when --root is not the repository")
    ap.add_argument("--trigger", default="manual")
    ap.add_argument("--sha", default=None)
    ap.add_argument("--runner", default=platform.platform())
    ap.add_argument("--only", default=None, help="comma-separated rule ids; run only these")
    ap.add_argument("--dry-run", action="store_true", help="print the results, write nothing")
    ap.add_argument("--exit-code", action="store_true", help="exit 1 when the overall result is fail")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cfg_path = Path(args.config) if Path(args.config).is_absolute() else root / args.config
    if not cfg_path.exists():
        raise ConfigError(f"gate config not found: {cfg_path}")
    config = json.loads(cfg_path.read_text())
    out = Path(args.out).resolve() if args.out else cfg_path.parent.resolve()
    rules_dir = root / config.get("rules_dir", ".github/actions/gate/rules")
    rules = load_rules(rules_dir)
    latest_path = out / "latest.json"
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else {"history": [], "findings": []}
    only = set(args.only.split(",")) if args.only else None

    checks = {}
    for rid, rc in config.get("rules", {}).items():
        tier = rc.get("tier", "block")
        if tier == "off" or (only and rid not in only):
            continue
        if tier not in ("block", "warn"):
            raise ConfigError(f"rule {rid}: tier must be block, warn or off")
        if rid not in rules:
            res = {"result": "fail", "detail": f"enabled in the gate config, but no rule file in {rules_dir.relative_to(root) if rules_dir.is_relative_to(root) else rules_dir} defines this id", "evidence": [], "hits": []}
        else:
            ctx = Ctx(root, {}, config, latest["history"], args.trigger, args.git_dir)
            res = ctx.run_rule(rules[rid], root, rc.get("options"))
        eff = "warn" if (tier == "warn" and res["result"] == "fail") else res["result"]
        checks[rid] = dict(res, tier=tier, effective=eff)
    if only and not checks:
        raise ConfigError(f"--only {args.only}: no enabled rule with that id")

    git = Ctx(root, {}, config, [], args.trigger, args.git_dir).git
    sha = args.sha or git("rev-parse", "HEAD") or "unknown"
    overall = "fail" if any(c["effective"] == "fail" for c in checks.values()) else "pass"
    findings = build_findings([dict(f) for f in latest["findings"]], checks, sha) if not only else latest["findings"]
    components = {
        "run_py": sha256(__file__),
        "config": sha256(cfg_path),
        "rules": {rid: {"file": m.__gate_file__.name, "sha256": sha256(m.__gate_file__)} for rid, m in rules.items()},
        "runtime": {"python": platform.python_version(), "runner": args.runner},
    }
    record = {
        "tool": "cto-powersuit gate run.py", "version": VERSION, "uuid": str(uuid.uuid4()),
        "gate": config.get("name", root.name), "timestamp": TS, "trigger": args.trigger, "commit": sha,
        "commit_date": git("log", "-1", "--format=%cI") or "unknown", "components": components,
        "checks": {rid: {k: c[k] for k in ("tier", "result", "effective", "detail", "evidence", "hits")} for rid, c in checks.items()},
        "findings_open": [f for f in findings if f["status"] == "open"],
        "overall": overall, "partial_run": bool(only),
    }
    summary = f"run.py: gate={record['gate']} trigger={args.trigger} sha={sha[:12]} overall={overall} findings_open={len(record['findings_open'])} checks=" + ", ".join(f"{k}:{v['effective']}" for k, v in checks.items())

    if args.dry_run or only:
        print(summary)
        for rid, c in checks.items():
            if c["effective"] in ("fail", "warn"):
                print(f"  {c['effective'].upper()} {rid}: {c['detail']}")
                for e in (c["evidence"] or [f"{h['file']}{(':' + str(h['line'])) if h.get('line') else ''} {h['snippet']}" for h in c["hits"]])[:30]:
                    print(f"       {e}")
        print("dry run: nothing written" if args.dry_run else "partial run (--only): nothing written")
    else:
        latest["findings"] = findings
        latest["history"] = (latest["history"] + [{"ts": TS, "trigger": args.trigger, "sha": sha, "overall": overall,
                                                    "findings_open": len(record["findings_open"]),
                                                    "warnings": sum(c["effective"] == "warn" for c in checks.values())}])[-100:]
        latest.update(last_run=TS, overall=overall, gate=record["gate"])
        (out / "runs").mkdir(parents=True, exist_ok=True)
        (out / "runs" / f"{TS.replace(':', '')}-{record['uuid'][:8]}.json").write_text(json.dumps(record, indent=1))
        latest_path.write_text(json.dumps(latest, indent=1))
        (out / "summary.md").write_text(summary_md(record["gate"], overall, checks, findings, latest["history"]))
        (out / ".result").write_text(overall + "\n")
        print(summary)
    if args.exit_code and overall == "fail":
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except (ConfigError, json.JSONDecodeError) as e:
        print(f"run.py: config error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        traceback.print_exc()
        print(f"run.py: internal error: {e}", file=sys.stderr)
        sys.exit(3)
