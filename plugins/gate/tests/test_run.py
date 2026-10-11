#!/usr/bin/env python3
"""Tests for the gate runner (templates/.github/actions/gate/run.py).

Each case builds a small repository in a temporary folder, runs the runner as a subprocess
and checks the files it writes. Standard library only, Python 3.9+.

Usage: python3 plugins/gate/tests/test_run.py [-v]
"""
import hashlib, json, subprocess, sys, tempfile, textwrap
from pathlib import Path

sys.dont_write_bytecode = True

GATE = Path(__file__).resolve().parent.parent
RUNNER = GATE / "templates/.github/actions/gate/run.py"
OSCAL = GATE / "templates/.github/actions/gate/reporters/oscal.py"
VERBOSE = "-v" in sys.argv


class Repo:
    def __init__(self, tmp, rules, config, latest=None, files=None):
        self.root = Path(tmp)
        rd = self.root / "rules"
        rd.mkdir()
        for name, src in rules.items():
            (rd / name).write_text(textwrap.dedent(src))
        for name, src in (files or {}).items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(src) if isinstance(src, str) else json.dumps(src))
        self.out = self.root / "gate"
        self.out.mkdir(exist_ok=True)
        (self.out / "gate.json").write_text(json.dumps(dict({"name": "t", "rules_dir": "rules"}, **config)))
        if latest is not None:
            (self.out / "latest.json").write_text(json.dumps(latest))

    def run(self, *extra, sha="c1"):
        p = subprocess.run([sys.executable, str(RUNNER), "--root", str(self.root), "--config", "gate/gate.json", "--sha", sha, *extra],
                           capture_output=True, text=True)
        if VERBOSE:
            print(textwrap.indent((p.stdout + p.stderr).strip(), "     "))
        return p

    def latest(self):
        return json.loads((self.out / "latest.json").read_text())

    def record(self):
        runs = sorted(p for p in (self.out / "runs").glob("*.json") if not p.name.endswith(".oscal.json"))
        return json.loads(runs[-1].read_text())


def rule(rid, body, extra=""):
    return f'ID = "{rid}"\n{extra}\ndef check(ctx):\n' + textwrap.indent(textwrap.dedent(body), "    ")


FLAG = rule("t.flag", """
    hits = [{"file": "a.txt", "snippet": "bad", "rule": "r1"}] if (ctx.root / "bad").exists() else []
    return {"result": "fail" if hits else "pass", "detail": f"{len(hits)} hits", "hits": hits}
""")


def key(check, file, hit_rule, snippet):
    return "F-" + hashlib.sha256(f"{check}|{file}|{hit_rule}|{snippet}".encode()).hexdigest()[:12]


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def partial_and_pending_do_not_fail(tmp):
    r = Repo(tmp, {"p.py": rule("t.partial", "return {'result': 'partial', 'detail': 'half'}"),
                   "q.py": rule("t.pending", "return {'result': 'pending', 'detail': 'no data yet'}")},
             {"rules": {"t.partial": {"tier": "block"}, "t.pending": {"tier": "block"}}})
    p = r.run("--exit-code")
    rec = r.record()
    assert p.returncode == 0, p.stderr
    assert rec["overall"] == "pass"
    assert rec["checks"]["t.partial"]["result"] == "partial" and rec["checks"]["t.pending"]["effective"] == "pending"
    assert r.latest()["findings"] == []


@case
def finding_fields_and_closure(tmp):
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}}, files={"bad": ""})
    assert r.run("--exit-code").returncode == 1
    [f] = r.latest()["findings"]
    assert f["id"] == key("t.flag", "a.txt", "r1", "bad"), f["id"]
    assert (f["check"], f["rule"], f["status"], f["opened_commit"]) == ("t.flag", "r1", "open", "c1")
    (r.root / "bad").unlink()
    assert r.run("--exit-code", sha="c2").returncode == 0
    [f] = r.latest()["findings"]
    assert f["status"] == "closed" and f["closed_commit"] == "c2" and f["closed_by_passing_run"] == f["closed"]


@case
def reopened_finding_drops_closed_fields(tmp):
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}}, files={"bad": ""})
    r.run()
    (r.root / "bad").unlink()
    r.run(sha="c2")
    (r.root / "bad").write_text("")
    r.run(sha="c3")
    [f] = r.latest()["findings"]
    assert f["status"] == "open" and "closed" not in f and "closed_by_passing_run" not in f and f["reopened"], f


@case
def old_findings_are_migrated(tmp):
    old_id = "F-" + hashlib.sha256(b"t.flag|a.txt|bad").hexdigest()[:12]
    old = {"id": old_id, "rule": "t.flag", "tier": "block", "file": "a.txt", "line": None, "snippet": "bad",
           "status": "open", "opened": "2026-01-01T00:00:00Z", "opened_commit": "c0", "last_seen": "2026-01-01T00:00:00Z", "runs_seen": 1}
    noh = rule("t.flag", """
        hits = [{"file": "a.txt", "snippet": "bad"}] if (ctx.root / "bad").exists() else []
        return {"result": "fail" if hits else "pass", "detail": "x", "hits": hits}
    """)
    r = Repo(tmp, {"f.py": noh}, {"rules": {"t.flag": {"tier": "block"}}}, latest={"history": [], "findings": [old]}, files={"bad": ""})
    r.run()
    [f] = r.latest()["findings"]
    assert f["check"] == "t.flag" and f["rule"] is None and f["former_id"] == old_id and f["id"] == key("t.flag", "a.txt", "", "bad")
    assert f["runs_seen"] == 2 and f["opened"] == "2026-01-01T00:00:00Z" and f["status"] == "open"


@case
def shared_is_per_run_and_fixture_runs_get_their_own(tmp):
    scan = rule("t.scan", """
        if "scan" not in ctx.shared:
            ctx.shared["scan"] = ["one", "two"]
            ctx.shared["visitors"] = []
        ctx.shared["visitors"].append(ID)
        sub = ctx.run_rule(PROBE, ctx.root)
        return {"result": "pass", "detail": f"visitors={','.join(ctx.shared['visitors'])} items={len(ctx.shared['scan'])} fixture_shared={sub['detail']}"}
    """, extra='''
class PROBE:
    ID = "t.probe"
    @staticmethod
    def check(ctx):
        return {"result": "pass", "detail": str(sorted(ctx.shared))}
''')
    r = Repo(tmp, {"a.py": scan, "b.py": scan.replace('"t.scan"', '"t.scan2"')},
             {"rules": {"t.scan": {"tier": "block"}, "t.scan2": {"tier": "block"}}})
    r.run()
    c = r.record()["checks"]
    assert c["t.scan"]["detail"] == "visitors=t.scan items=2 fixture_shared=[]", c["t.scan"]["detail"]
    assert c["t.scan2"]["detail"] == "visitors=t.scan,t.scan2 items=2 fixture_shared=[]", c["t.scan2"]["detail"]


@case
def after_phase_sees_findings_opens_none_and_order_follows_config(tmp):
    closure = rule("t.closure", """
        if ctx.findings is None:
            return {"result": "fail", "detail": "no findings in ctx"}
        n = sum(f["status"] == "open" for f in ctx.findings)
        return {"result": "fail" if n else "pass", "detail": f"{n} open", "hits": [{"file": "-", "snippet": "open findings"}] if n else []}
    """, extra='PHASE = "after"')
    r = Repo(tmp, {"c.py": closure, "f.py": FLAG}, {"rules": {"t.closure": {"tier": "block"}, "t.flag": {"tier": "warn"}}}, files={"bad": ""})
    p = r.run("--exit-code")
    rec = r.record()
    assert list(rec["checks"]) == ["t.closure", "t.flag"], list(rec["checks"])
    assert rec["checks"]["t.closure"]["phase"] == "after" and rec["checks"]["t.closure"]["detail"] == "1 open"
    assert p.returncode == 1 and rec["overall"] == "fail"
    assert [f["check"] for f in r.latest()["findings"]] == ["t.flag"]


@case
def requirement_states_and_finding_requirements(tmp):
    reqs = {"requirements": [
        {"id": "R-1", "checks": ["t.flag"], "mark": "M"},
        {"id": "R-2", "checks": ["t.ok", "t.flag"], "mark": "M"},
        {"id": "R-3", "checks": ["t.ok", "t.na"]},
        {"id": "R-4", "checks": ["t.off"], "mark": "H", "self_assessment": {"result": "met"}},
    ]}
    r = Repo(tmp, {"f.py": FLAG, "o.py": rule("t.ok", "return {'result': 'pass', 'detail': ''}"), "n.py": rule("t.na", "return {'result': 'n/a', 'detail': ''}")},
             {"requirements": "gate/requirements.json",
              "rules": {"t.flag": {"tier": "warn"}, "t.ok": {"tier": "block"}, "t.na": {"tier": "block"}, "t.off": {"tier": "off"}}},
             files={"bad": "", "gate/requirements.json": reqs})
    r.run()
    s = r.latest()["requirement_states"]
    assert {k: v["live"] for k, v in s.items()} == {"R-1": "fail", "R-2": "partial", "R-3": "pass", "R-4": None}, s
    assert s["R-4"] == {"live": None, "self": "met", "mark": "H"}
    assert r.record()["requirement_states"] == s
    assert r.latest()["findings"][0]["requirements"] == ["R-1", "R-2"]
    assert "## Requirements" in (r.out / "summary.md").read_text()


@case
def reporter_writes_files_and_latest_keys(tmp):
    rep = '''
ID = "t.page"
def report(r):
    return {"files": {"index.html": f"<p>{r.record['overall']} {r.options['title']} {len(r.findings)}</p>", "sub/x.txt": "x"},
            "latest": {"site": "example.org"}}
'''
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}, "reporters": [{"path": "rep.py", "options": {"title": "T"}}]},
             files={"rep.py": rep})
    p = r.run("--dry-run")
    assert "reporters would write: index.html, sub/x.txt" in p.stdout and not (r.out / "index.html").exists()
    r.run()
    assert (r.out / "index.html").read_text() == "<p>pass T 0</p>" and (r.out / "sub/x.txt").exists()
    assert r.latest()["site"] == "example.org" and "reporters" in r.record()["components"]


@case
def reporter_refusal_writes_nothing(tmp):
    rep = 'def report(r):\n    return {"files": {"index.html": "TODO"}, "refuse": {"code": 4, "reason": "placeholder in page"}}\n'
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}, "reporters": ["rep.py"]}, files={"rep.py": rep})
    for extra in ((), ("--dry-run",)):
        p = r.run(*extra)
        assert p.returncode == 4 and "placeholder in page" in p.stderr, (p.returncode, p.stderr)
    assert sorted(x.name for x in r.out.iterdir()) == ["gate.json"]


@case
def reporter_limits_are_config_errors(tmp):
    bad = {
        "low.py": 'def report(r):\n    return {"refuse": {"code": 1, "reason": "x"}}\n',
        "key.py": 'def report(r):\n    return {"latest": {"overall": "pass"}}\n',
        "esc.py": 'def report(r):\n    return {"files": {"../x.txt": "x"}}\n',
        "own.py": 'def report(r):\n    return {"files": {"latest.json": "{}"}}\n',
    }
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}}, files=bad)
    for name in bad:
        cfg = json.loads((r.out / "gate.json").read_text())
        cfg["reporters"] = [name]
        (r.out / "gate.json").write_text(json.dumps(cfg))
        p = r.run()
        assert p.returncode == 2, (name, p.returncode, p.stderr)
    assert not (r.root / "x.txt").exists()


@case
def write_summary_false(tmp):
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}, "write_summary": False})
    r.run()
    assert not (r.out / "summary.md").exists() and (r.out / "latest.json").exists()


@case
def warnings_count_hits_of_checks_that_did_not_fail(tmp):
    many = rule("t.many", "return {'result': 'pass', 'detail': '3 logged', 'hits': [{'file': 'x', 'snippet': str(i)} for i in range(3)]}")
    warnfail = rule("t.warnfail", "return {'result': 'fail', 'detail': '2', 'hits': [{'file': 'y', 'snippet': str(i)} for i in range(2)]}")
    blockfail = rule("t.blockfail", "return {'result': 'fail', 'detail': '4', 'hits': [{'file': 'z', 'snippet': str(i)} for i in range(4)]}")
    quiet = rule("t.quiet", "return {'result': 'warn', 'detail': 'no hits'}")
    r = Repo(tmp, {"a.py": many, "b.py": warnfail, "c.py": blockfail, "d.py": quiet},
             {"rules": {"t.many": {"tier": "block"}, "t.warnfail": {"tier": "warn"}, "t.blockfail": {"tier": "block"}, "t.quiet": {"tier": "block"}}})
    p = r.run()
    assert r.latest()["history"][-1]["warnings"] == 5, r.latest()["history"]
    assert " warnings=5 " in p.stdout


@case
def oscal_reporter(tmp):
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}, "reporters": [str(OSCAL)]}, files={"bad": ""})
    r.run()
    [o] = list((r.out / "runs").glob("*.oscal.json"))
    doc = json.loads(o.read_text())
    res = doc["assessment-results"]["results"][0]
    assert [x["title"] for x in res["observations"]] == ["t.flag"] and len(res["findings"]) == 1
    assert doc["x-gate"]["run_record"] == r.record()["uuid"]


@case
def only_runs_write_nothing_and_skip_reporters(tmp):
    rep = 'def report(r):\n    return {"refuse": {"code": 4, "reason": "should not run"}}\n'
    r = Repo(tmp, {"f.py": FLAG}, {"rules": {"t.flag": {"tier": "block"}}, "reporters": ["rep.py"]}, files={"rep.py": rep})
    p = r.run("--only", "t.flag")
    assert p.returncode == 0 and "partial run" in p.stdout and not (r.out / "latest.json").exists()


@case
def rules_import_helpers_from_their_folder(tmp):
    r = Repo(tmp, {"_t_helper.py": "def answer():\n    return 42\n",
                   "h.py": rule("t.helper", "return {'result': 'pass', 'detail': str(answer())}", extra="from _t_helper import answer")},
             {"rules": {"t.helper": {"tier": "block"}}})
    r.run()
    assert r.record()["checks"]["t.helper"]["detail"] == "42", r.record()["checks"]["t.helper"]


@case
def unknown_phase_is_a_config_error(tmp):
    r = Repo(tmp, {"x.py": rule("t.x", "return {'result': 'pass', 'detail': ''}", extra='PHASE = "later"')}, {"rules": {"t.x": {}}})
    assert r.run().returncode == 2


def main():
    failures = 0
    for fn in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn(tmp)
                print(f"ok   {fn.__name__}")
            except Exception as e:
                failures += 1
                print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(CASES)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
