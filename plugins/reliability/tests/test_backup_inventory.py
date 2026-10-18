#!/usr/bin/env python3
"""Tests for the reliability gate check reliability.backup-inventory, beyond its pass and fail fixture runs.

- The fixtures: the pass page passes, the fail page gives exactly one hit per kind, the stale page warns.
- Each flag on its own, on a copy of the pass page with one field changed: no copy outside production admin
  reach (none, missing, unknown value), a production administrator who can delete the out-of-reach copy, no restore
  test, a restore test older than the interval (the boundary day, the option, stale_fails), a failed restore test,
  a measured restore time above the target (units), and the fields a verdict depends on.
- Stable hit snippets: the same problems on another day give the same snippets.
- Parsing: fenced code, bold field names, folders that start with an underscore, a page with no store.
- The unfilled template fails, and carries every field the rule reads.
- Through the gate runner: on the warn tier the fail page blocks nothing, on the block tier it does.

Standard library only, Python 3.9+. Usage: python3 plugins/reliability/tests/test_backup_inventory.py [-v]
"""
import datetime, importlib.util, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

MODULE = Path(__file__).resolve().parent.parent
REPO = MODULE.parent.parent
VERBOSE = "-v" in sys.argv
TODAY = datetime.date(2026, 10, 18)
RUNNER = REPO / "plugins/gate/templates/.github/actions/gate/run.py"
FIXTURES = MODULE / "checks/fixtures/reliability.backup-inventory"
TEMPLATE = MODULE / "templates/docs/sre/backups.md"
PAGE = "docs/sre/backups.md"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load(RUNNER, "gate_run")
rule = load(MODULE / "checks/backup_inventory.py", "rule_backup_inventory")
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def check_rule(root, today=TODAY, **options):
    opts = json.loads(json.dumps(rule.DEFAULTS))
    opts.update(options)
    ctx = run.Ctx(root, opts, {}, [], "manual", None)
    ctx.today = today
    return run.run_one(rule, ctx)


def snippets(res):
    return sorted(h["snippet"] for h in res["hits"])


def fixture_text(kind):
    return (FIXTURES / kind / PAGE).read_text()


def set_field(text, store, field, value):
    """Change one row of a store's table in a page; value None removes the row."""
    out, in_store = [], False
    for line in text.split("\n"):
        if line.startswith("### "):
            in_store = line[4:].strip() == store
        elif in_store and line.startswith(f"| {field} |"):
            if value is None:
                continue
            line = f"| {field} | {value} |"
        out.append(line)
    return "\n".join(out)


def variant(edit=None, today=TODAY, page=PAGE, **options):
    """Run the rule on the pass page after edit(text), in a temporary tree."""
    text = fixture_text("pass")
    if edit:
        text = edit(text)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / page
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        return check_rule(Path(tmp), today=today, **options)


def expect(label, res, result, snips):
    bad = []
    if res["result"] != result:
        bad.append(f"{label}: result {res['result']}, want {result}: {snippets(res)}")
    elif snippets(res) != sorted(snips):
        bad.append(f"{label}: hits {snippets(res)}, want {sorted(snips)}")
    elif VERBOSE:
        print(f"     {label}: {result} {snippets(res)}")
    return bad


@test
def fixtures_behave():
    bad = []
    bad += expect("pass page", check_rule(FIXTURES / "pass"), "pass", [])
    bad += expect("fail page", check_rule(FIXTURES / "fail"), "fail", [
        "orders-database: no copy outside production admin reach",
        "search-index: out-of-reach copy can be deleted by production administrator platform-admin",
        "uploads-bucket: no restore test",
        "analytics-warehouse: last restore test failed",
        "billing-database: measured restore time 95 min is above the target 60 min",
    ])
    bad += expect("stale page", check_rule(FIXTURES / "stale"), "warn", ["orders-database: restore test older than 90 days"])
    bad += expect("stale page, stale_fails", check_rule(FIXTURES / "stale", stale_fails=True), "fail",
                  ["orders-database: restore test older than 90 days"])
    bad += expect("stale page, max_age_days 600", check_rule(FIXTURES / "stale", max_age_days=600), "pass", [])
    bad += expect("pass page, max_age_days 20", check_rule(FIXTURES / "pass", max_age_days=20), "warn",
                  ["uploads-bucket: restore test older than 20 days"])
    return bad


@test
def fail_page_hits_carry_file_and_line():
    res = check_rule(FIXTURES / "fail")
    text = fixture_text("fail").split("\n")
    bad = []
    for h in res["hits"]:
        if h["file"] != PAGE or not isinstance(h["line"], int) or not 1 <= h["line"] <= len(text):
            bad.append(f"hit without file and line: {h}")
        elif not text[h["line"] - 1].startswith("|"):
            bad.append(f"{h['snippet']}: line {h['line']} is not a table row: {text[h['line'] - 1]!r}")
    return bad


@test
def no_copy_outside_reach():
    bad = []
    for label, value, want in (
        ("none", "none", "no copy outside production admin reach"),
        ("placeholder", "<separate-account, immutable, offline, or none>", "no copy outside production admin reach recorded"),
        ("empty", "", "no copy outside production admin reach recorded"),
        ("unknown value", "yes", "copy outside production admin reach has an unknown value: yes"),
        ("none with another kind", "none, offline", "copy outside production admin reach has an unknown value: none, offline"),
    ):
        res = variant(lambda t, v=value: set_field(t, "orders-database", "Out-of-reach copy", v))
        bad += expect(label, res, "fail", ["orders-database: " + want])
    res = variant(lambda t: set_field(t, "orders-database", "Out-of-reach copy", None))
    bad += expect("row removed", res, "fail", ["orders-database: no copy outside production admin reach recorded"])
    for kind in ("separate-account", "immutable", "offline", "Offline, Separate-Account", "immutable; offline"):
        res = variant(lambda t, v=kind: set_field(t, "orders-database", "Out-of-reach copy", v))
        bad += expect(kind, res, "pass", [])
    return bad


@test
def production_administrator_can_delete_the_copy():
    bad = []
    for label, value in (
        ("same name", "platform-admin"),
        ("other case and a note", "Platform-Admin (SRE lead)"),
        ("among others", "backup-admin; prod-root"),
    ):
        res = variant(lambda t, v=value: set_field(t, "orders-database", "Out-of-reach deletable by", v))
        who = "prod-root" if "prod-root" in value else "platform-admin"
        bad += expect(label, res, "fail", [f"orders-database: out-of-reach copy can be deleted by production administrator {who}"])
    for label, value in (("not recorded", None), ("placeholder", "<identities>")):
        res = variant(lambda t, v=value: set_field(t, "orders-database", "Out-of-reach deletable by", v))
        bad += expect(label, res, "fail", ["orders-database: identities that can delete or overwrite the out-of-reach copy not recorded"])
    res = variant(lambda t: set_field(t, "orders-database", "Out-of-reach deletable by", "nobody until retention ends"))
    bad += expect("nobody", res, "pass", [])
    # The main backup may be deletable by a production administrator; only the out-of-reach copy counts.
    res = variant(lambda t: set_field(t, "orders-database", "Can delete or overwrite", "platform-admin, prod-root"))
    bad += expect("main backup deletable", res, "pass", [])
    res = variant(lambda t: re.sub(r"\| Production administrators \|.*\|\n", "", t))
    bad += expect("no administrators listed", res, "fail", ["no production administrators listed"])
    res = variant(lambda t: re.sub(r"\| Production administrators \|.*\|\n", "| Production administrators | <roles> |\n", t))
    bad += expect("administrators placeholder", res, "fail", ["no production administrators listed"])
    # Without a claim of an out-of-reach copy there is nothing to compare, and the missing copy is the hit.
    def no_claims(t):
        t = re.sub(r"\| Production administrators \|.*\|\n", "", t)
        for store in ("orders-database", "uploads-bucket", "ledger-archive"):
            t = set_field(t, store, "Out-of-reach copy", "none")
        return t
    res = variant(no_claims)
    bad += expect("no store claims a copy", res, "fail", [f"{s}: no copy outside production admin reach" for s in ("orders-database", "uploads-bucket", "ledger-archive")])
    return bad


@test
def restore_test_date():
    bad = []
    for label, value, want in (
        ("never", "never", "no restore test"),
        ("Never", "Never", "no restore test"),
        ("placeholder", "<YYYY-MM-DD or never>", "no restore test"),
        ("empty", "", "no restore test"),
        ("not ISO", "18/10/2026", "restore test date is not a YYYY-MM-DD date: 18/10/2026"),
        ("impossible day", "2026-02-30", "restore test date is not a YYYY-MM-DD date: 2026-02-30"),
        ("compact", "20261012", "restore test date is not a YYYY-MM-DD date: 20261012"),
        ("future", "2026-10-19", "restore test date is in the future: 2026-10-19"),
    ):
        res = variant(lambda t, v=value: set_field(t, "orders-database", "Last restore test", v))
        bad += expect(label, res, "fail", ["orders-database: " + want])
    res = variant(lambda t: set_field(t, "orders-database", "Last restore test", None))
    bad += expect("row removed", res, "fail", ["orders-database: no restore test"])
    res = variant(lambda t: set_field(t, "orders-database", "Last restore test", "2026-10-18"))
    bad += expect("today", res, "pass", [])
    return bad


@test
def restore_test_age_boundary():
    bad = []
    day = lambda days: (TODAY - datetime.timedelta(days=days)).isoformat()
    for days, result, snips in (
        (90, "pass", []),
        (91, "warn", ["orders-database: restore test older than 90 days"]),
    ):
        res = variant(lambda t, d=days: set_field(t, "orders-database", "Last restore test", day(d)))
        bad += expect(f"{days} days old", res, result, snips)
    res = variant(lambda t: set_field(t, "orders-database", "Last restore test", day(400)), max_age_days=365)
    bad += expect("365 days option", res, "warn", ["orders-database: restore test older than 365 days"])
    res = variant(lambda t: set_field(t, "orders-database", "Last restore test", day(300)), max_age_days=365)
    bad += expect("300 days old, 365 days option", res, "pass", [])
    # A stale test and a hard problem on different stores: the page fails on the hard problem only, until stale_fails.
    def both(t):
        t = set_field(t, "orders-database", "Last restore test", day(200))
        return set_field(t, "uploads-bucket", "Out-of-reach copy", "none")
    bad += expect("stale and hard", variant(both), "fail", ["uploads-bucket: no copy outside production admin reach"])
    bad += expect("stale and hard, stale_fails", variant(both, stale_fails=True), "fail", [
        "uploads-bucket: no copy outside production admin reach", "orders-database: restore test older than 90 days"])
    return bad


@test
def restore_result_and_times():
    bad = []
    s = "orders-database"
    cases = (
        ("failed", [("Restore result", "fail")], "fail", [f"{s}: last restore test failed"]),
        ("failed with a time above target", [("Restore result", "FAIL"), ("Restore time measured", "999 min")], "fail",
         [f"{s}: last restore test failed"]),
        ("no result", [("Restore result", None)], "fail", [f"{s}: restore test has no result"]),
        ("result placeholder", [("Restore result", "<pass or fail>")], "fail", [f"{s}: restore test has no result"]),
        ("partial result", [("Restore result", "partial")], "fail", [f"{s}: restore result is not pass or fail: partial"]),
        ("no measured time", [("Restore time measured", None)], "fail", [f"{s}: no measured restore time"]),
        ("no target", [("Restore time target", None)], "fail", [f"{s}: no restore time target"]),
        ("neither", [("Restore time measured", "<duration>"), ("Restore time target", "")], "fail",
         [f"{s}: no measured restore time", f"{s}: no restore time target"]),
        ("measured not a duration", [("Restore time measured", "quick")], "fail", [f"{s}: measured restore time is not a duration: quick"]),
        ("target not a duration", [("Restore time target", "an hour")], "fail", [f"{s}: restore time target is not a duration: an hour"]),
        ("above target", [("Restore time measured", "61 min")], "fail", [f"{s}: measured restore time 61 min is above the target 60 min"]),
        ("at target", [("Restore time measured", "60 min")], "pass", []),
        ("hours above minutes", [("Restore time measured", "2 h"), ("Restore time target", "90 min")], "fail",
         [f"{s}: measured restore time 120 min is above the target 90 min"]),
        ("hours equal minutes", [("Restore time measured", "1.5 h"), ("Restore time target", "90 min")], "pass", []),
        ("days", [("Restore time measured", "2 days"), ("Restore time target", "3 days")], "pass", []),
        ("unit-less is minutes", [("Restore time measured", "45"), ("Restore time target", "60")], "pass", []),
        ("unit-less above", [("Restore time measured", "61"), ("Restore time target", "1 h")], "fail",
         [f"{s}: measured restore time 61 min is above the target 60 min"]),
    )
    for label, edits, result, snips in cases:
        def edit(t, edits=edits):
            for field, value in edits:
                t = set_field(t, s, field, value)
            return t
        bad += expect(label, variant(edit), result, snips)
    return bad


@test
def snippets_do_not_change_with_the_day():
    a = check_rule(FIXTURES / "fail", today=TODAY)
    b = check_rule(FIXTURES / "fail", today=TODAY + datetime.timedelta(days=200))
    bad = []
    if snippets(a) != snippets(b):
        bad.append(f"snippets differ between two days: {snippets(a)} / {snippets(b)}")
    for h in a["hits"] + check_rule(FIXTURES / "stale")["hits"]:
        if re.search(r"\b\d+ days? (ago|old)\b", h["snippet"]):
            bad.append(f"a hit shows an age that changes every day: {h['snippet']}")
    return bad


@test
def parsing():
    bad = []
    fenced = lambda t: t + "\n```\n### example-store\n\n| Field | Value |\n|---|---|\n| Out-of-reach copy | none |\n```\n"
    bad += expect("heading inside fenced code", variant(fenced), "pass", [])
    bold = lambda t: set_field(t, "orders-database", "Out-of-reach copy", "none").replace("| Out-of-reach copy |", "| **Out-of-reach copy** |")
    bad += expect("bold field name", variant(bold), "fail", ["orders-database: no copy outside production admin reach"])
    spaced = lambda t: t.replace("| Last restore test |", "|   last  restore TEST   |").replace("2026-10-12 |", "never |", 1)
    res = variant(spaced)
    if "orders-database: no restore test" not in snippets(res):
        bad.append(f"field name case and spacing: {snippets(res)}")
    twice = lambda t: t.replace("### orders-database", "### orders-database\n\n| Field | Value |\n|---|---|\n| Out-of-reach copy | none |\n", 1)
    bad += expect("first row of a field wins", variant(twice), "fail", ["orders-database: no copy outside production admin reach"])
    nostore = lambda t: t[:t.index("## Data stores")] + "## Data stores\n\nNone yet.\n"
    bad += expect("no data store", variant(nostore), "fail", ["no data store listed"])
    bad += expect("no front matter", variant(lambda t: t[t.index("This page is a fixture."):]), "pass", [])
    bad += expect("folder with an underscore skipped", variant(page="docs/sre/_templates/backups.md", globs=["docs/**/*.md"]), "n/a", [])
    bad += expect("no page", variant(page="docs/sre/other.md"), "n/a", [])
    res = variant(page="ops/backups.md", globs=["ops/backups.md"])
    bad += expect("globs option", res, "pass", [])
    return bad


@test
def several_pages_are_all_read():
    with tempfile.TemporaryDirectory() as tmp:
        for name, kind in (("backups.md", "pass"), ("backups-eu.md", "fail")):
            f = Path(tmp) / "docs/sre" / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(fixture_text(kind))
        res = check_rule(Path(tmp), globs=["docs/sre/backups*.md"])
    bad = []
    files = {h["file"] for h in res["hits"]}
    if res["result"] != "fail" or files != {"docs/sre/backups-eu.md"}:
        bad.append(f"result {res['result']}, hits in {sorted(files)}")
    if not res["detail"].startswith("8 data stores"):
        bad.append(f"detail {res['detail']!r}")
    return bad


@test
def unfilled_template_fails_and_has_every_field():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / PAGE
        f.parent.mkdir(parents=True)
        shutil.copy(TEMPLATE, f)
        res = check_rule(Path(tmp))
    wanted = {"no copy outside production admin reach recorded", "no restore test"}
    got = {h["snippet"].split(": ", 1)[1] for h in res["hits"] if ": " in h["snippet"]}
    if res["result"] != "fail" or not wanted <= got:
        bad.append(f"unfilled template: result {res['result']}, hits {snippets(res)}")
    text = TEMPLATE.read_text().lower()
    for name in (rule.COPY, rule.DELETERS, rule.TESTED, rule.RESULT, rule.MEASURED, rule.TARGET, rule.ADMINS):
        if not re.search(rf"^\| {re.escape(name)} \|", text, re.M):
            bad.append(f"the template has no row {name!r}")
    # A template store filled in with the fixture's values passes.
    fixture = fixture_text("pass")
    for name in ("Policy", "Data stores"):
        if f"## {name}" not in TEMPLATE.read_text() or f"## {name}" not in fixture:
            bad.append(f"template or fixture lacks the section {name}")
    t_fields = re.findall(r"^\| ([^|]+?) \|", TEMPLATE.read_text().split("### ", 1)[1].split("\n## ", 1)[0], re.M)
    f_fields = re.findall(r"^\| ([^|]+?) \|", fixture.split("### ", 1)[1].split("\n### ", 1)[0], re.M)
    if t_fields != f_fields:
        bad.append(f"template store fields {t_fields} differ from the fixture's {f_fields}")
    return bad


@test
def gate_runner_tiers():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rules = tmp / "rules"
        rules.mkdir()
        shutil.copy(MODULE / "checks/backup_inventory.py", rules)
        root = tmp / "repo"
        shutil.copytree(FIXTURES / "fail", root)
        for tier, want in (("warn", 0), ("block", 1)):
            cfg = tmp / f"{tier}.json"
            cfg.write_text(json.dumps({"name": "test", "rules_dir": str(rules), "rules": {rule.ID: {"tier": tier}}}))
            p = subprocess.run([sys.executable, str(RUNNER), "--config", str(cfg), "--root", str(root), "--dry-run", "--exit-code", "--sha", "test"],
                               capture_output=True, text=True)
            if p.returncode != want:
                bad.append(f"tier {tier}: exit {p.returncode}, want {want}: {(p.stdout + p.stderr).strip()[-300:]}")
            elif VERBOSE:
                print(f"     tier {tier}: exit {p.returncode}")
        cfg = tmp / "options.json"
        cfg.write_text(json.dumps({"name": "test", "rules_dir": str(rules),
                                   "rules": {rule.ID: {"tier": "block", "options": {"globs": ["docs/sre/backups.md"], "max_age_days": 30}}}}))
        shutil.rmtree(root)
        shutil.copytree(FIXTURES / "stale", root)
        p = subprocess.run([sys.executable, str(RUNNER), "--config", str(cfg), "--root", str(root), "--dry-run", "--exit-code", "--sha", "test"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            bad.append(f"a stale page on the block tier must warn, not block: exit {p.returncode}")
    return bad


def main():
    failures = 0
    for fn in TESTS:
        try:
            bad = fn()
        except Exception as e:  # a crash is a failure of that case
            bad = [f"raised {type(e).__name__}: {e}"]
        print(f"{'ok  ' if not bad else 'FAIL'} {fn.__name__}")
        for b in bad:
            print(f"     {b}")
        failures += bool(bad)
    print(f"{len(TESTS)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
