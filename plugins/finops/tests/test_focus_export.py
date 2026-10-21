#!/usr/bin/env python3
"""Tests for the finops module: scripts/focus_export.py on the synthetic example in examples/, and the example pages.

- convert: both example exports give the committed FOCUS files byte for byte, and the BilledCost total of each equals
  the sum of the raw file computed here without the script; the --start/--end window, invalid rows (nothing written,
  or the valid rows with --skip-invalid) and a map with a placeholder behave as the skills say.
- check: the example gives the committed output; bad FOCUS rows and a missing column are reported.
- baseline: the example gives the committed output and exactly one spike (the planted 2026-08 compute month); the
  --spike threshold, a currency change and a single-month service are flagged.
- showback: the example gives the committed output and reconciles to zero; even and weighted splits; bad allocation files.
- unit: cost per 1000 requests, a month without a count, and more than one currency.
- parse_amount: the number formats the script reads.
- examples: the pages embed the committed script output, the run rates and the SaaS figures match the inputs, every
  output and file carries the synthetic label, and finops.cost-provenance passes on the pages and fails on a copy of
  the baseline page without cost_period and cost_source.

Every input is synthetic. Standard library only, Python 3.9+. Usage: python3 plugins/finops/tests/test_focus_export.py [-v]
"""
import csv, datetime, importlib.util, json, re, statistics, subprocess, sys, tempfile
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True

FINOPS = Path(__file__).resolve().parent.parent
REPO = FINOPS.parent.parent
EX = FINOPS / "examples"
SCRIPT = FINOPS / "templates/scripts/focus_export.py"
RUNNER = REPO / "plugins/gate/templates/.github/actions/gate/run.py"
VERBOSE = "-v" in sys.argv

CLOUD_RAW = "inputs/synthetic-cloud-export-2026-04-to-2026-09.csv"
HOSTING_RAW = "inputs/synthetic-hosting-export-2026-04-to-2026-09.csv"
CLOUD_MAP = "finops/focus-maps/synthetic-cloud-export.json"
HOSTING_MAP = "finops/focus-maps/synthetic-hosting-export.json"
CLOUD_FOCUS = "finops/focus/synthetic-cloud-2026-04-to-2026-09.csv"
HOSTING_FOCUS = "finops/focus/synthetic-hosting-2026-04-to-2026-09.csv"
FOCUS_FILES = [CLOUD_FOCUS, HOSTING_FOCUS]
ALLOC = "finops/allocation.json"
# The control totals of the sample: the sums of the raw files, set when the files were made (see examples/README.md).
CONTROL = {"cloud": Decimal("45826.00"), "hosting": Decimal("8269.31")}
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def load_script():
    spec = importlib.util.spec_from_file_location("focus_export", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args, cwd=EX):
    p = subprocess.run([sys.executable, str(SCRIPT), *[str(a) for a in args]], cwd=str(cwd), capture_output=True, text=True)
    if VERBOSE:
        print("     $ focus_export.py " + " ".join(str(a) for a in args) + f"  -> exit {p.returncode}")
    return p


def text(rel):
    return (EX / rel).read_text(encoding="utf-8")


def read_csv(path, **kw):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, **kw))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def focus_rows(rel):
    return read_csv(EX / rel)


def fields_of(rel):
    with open(EX / rel, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def raw_total(rel, delimiter, amount_col, decimal_mark):
    """Sum of a raw billing file, read here without the script."""
    total = Decimal(0)
    for r in read_csv(EX / rel, delimiter=delimiter):
        v = r[amount_col]
        total += Decimal(v.replace(".", "").replace(",", ".") if decimal_mark == "," else v)
    return total


def table_lines(s):
    return [ln for ln in s.splitlines() if ln.startswith("|")]


def md_table(page, heading):
    """The data rows (cells) of the first table after '## <heading>' on a page."""
    body = page.split(f"\n## {heading}\n", 1)[1]
    rows = [ln for ln in body.split("\n## ", 1)[0].splitlines() if ln.startswith("|")]
    return [[c.strip() for c in ln.strip("|").split("|")] for ln in rows[2:]]


def eur(s):
    return Decimal(re.search(r"EUR ([\d,]+\.\d\d)", s).group(1).replace(",", ""))


# ---------------------------------------------------------------- convert

@test
def convert_gives_the_committed_focus_files():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, raw, mp, rel, key, delim, mark, col in (
                ("cloud", CLOUD_RAW, CLOUD_MAP, CLOUD_FOCUS, "cloud", ",", ".", "amount"),
                ("hosting", HOSTING_RAW, HOSTING_MAP, HOSTING_FOCUS, "hosting", ";", ",", "net_amount")):
            out = Path(tmp) / Path(rel).name
            p = run("convert", "--in", raw, "--map", mp, "--out", out, "--start", "2026-04-01", "--end", "2026-10-01")
            if p.returncode != 0:
                bad.append(f"{name}: exit {p.returncode}: {p.stderr.strip()[:200]}")
                continue
            if out.read_bytes() != (EX / rel).read_bytes():
                bad.append(f"{name}: the converted file differs from {rel}")
            total = raw_total(raw, delim, col, mark)
            if total != CONTROL[key]:
                bad.append(f"{name}: the raw file sums to {total}, the control total is {CONTROL[key]}")
            if f"BilledCost EUR {CONTROL[key]:,.2f}" not in p.stdout:
                bad.append(f"{name}: convert did not print BilledCost EUR {CONTROL[key]:,.2f}: {p.stdout.strip()}")
            rows = len(read_csv(EX / raw, delimiter=delim))
            if f"{rows} rows written, 0 outside --start/--end, 0 invalid rows skipped" not in p.stdout:
                bad.append(f"{name}: expected {rows} rows written, got: {p.stdout.splitlines()[0]}")
    return bad


@test
def convert_start_end_window():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "window.csv"
        p = run("convert", "--in", CLOUD_RAW, "--map", CLOUD_MAP, "--out", out, "--start", "2026-05-01", "--end", "2026-07-01")
        raw = read_csv(EX / CLOUD_RAW)
        keep = [r for r in raw if "2026-05-01" <= r["usage_month"] < "2026-07-01"]
        want = f"{len(keep)} rows written, {len(raw) - len(keep)} outside --start/--end, 0 invalid rows skipped"
        if want not in p.stdout:
            bad.append(f"want '{want}', got: {p.stdout.splitlines()[0] if p.stdout else p.stderr}")
        months = sorted({r["ChargePeriodStart"][:7] for r in read_csv(out)})
        if months != ["2026-05", "2026-06"]:
            bad.append(f"months in the window file: {months}")
    return bad


@test
def convert_stops_on_invalid_rows_and_skip_invalid_writes_the_rest():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.csv"
        rows = read_csv(EX / CLOUD_RAW)[:4]
        rows[1]["amount"] = "twelve"
        rows[2]["usage_month"] = "April"
        rows[3]["line_type"] = "refund"
        write_csv(raw, rows, list(rows[0]))
        out = Path(tmp) / "out.csv"
        p = run("convert", "--in", raw, "--map", CLOUD_MAP, "--out", out)
        if p.returncode != 1 or out.exists():
            bad.append(f"invalid rows: exit {p.returncode}, output file exists: {out.exists()}")
        for frag in ("not a number: 'twelve'", "ChargeCategory is not one of", "nothing written"):
            if frag not in p.stderr:
                bad.append(f"stderr lacks '{frag}'")
        p = run("convert", "--in", raw, "--map", CLOUD_MAP, "--out", out, "--skip-invalid")
        written = read_csv(out) if out.exists() else []
        if p.returncode != 1 or len(written) != 1:
            bad.append(f"--skip-invalid: exit {p.returncode}, {len(written)} rows written, want exit 1 and 1 row")
        if "1 rows written, 0 outside --start/--end, 3 invalid rows skipped" not in p.stdout:
            bad.append(f"--skip-invalid summary: {p.stdout.splitlines()[0] if p.stdout else ''}")
    return bad


@test
def convert_refuses_a_map_with_a_placeholder_or_a_missing_column():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.csv"
        p = run("convert", "--in", CLOUD_RAW, "--map", FINOPS / "templates/finops/focus-maps/example.json", "--out", out)
        if p.returncode != 2 or "placeholder" not in p.stderr or out.exists():
            bad.append(f"template map: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
        mp = json.loads(text(CLOUD_MAP))
        mp["columns"]["BilledCost"] = "no_such_column"
        mpath = Path(tmp) / "map.json"
        mpath.write_text(json.dumps(mp))
        p = run("convert", "--in", CLOUD_RAW, "--map", mpath, "--out", out)
        if p.returncode != 2 or "no_such_column" not in p.stderr or out.exists():
            bad.append(f"missing column: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
        mp = json.loads(text(CLOUD_MAP))
        mp["extra"] = {"InvoiceId": "line_id"}
        mpath.write_text(json.dumps(mp))
        p = run("convert", "--in", CLOUD_RAW, "--map", mpath, "--out", out)
        if p.returncode != 2 or "x_ prefix" not in p.stderr:
            bad.append(f"extra column without x_: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
    return bad


# ---------------------------------------------------------------- check

@test
def check_gives_the_committed_output():
    p = run("check", *FOCUS_FILES)
    bad = []
    if p.returncode != 0:
        bad.append(f"exit {p.returncode}: {p.stderr.strip()[:200]}")
    if p.stdout != text("outputs/check.txt"):
        bad.append("the output differs from outputs/check.txt")
    return bad


@test
def check_reports_bad_rows_and_a_missing_column():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        fields = fields_of(CLOUD_FOCUS)
        rows = focus_rows(CLOUD_FOCUS)[:4]
        rows[0]["ChargeCategory"] = "Foo"
        rows[1]["BillingCurrency"] = "EURO"
        rows[2]["Tags"] = "not json"
        rows[3]["ChargePeriodEnd"] = rows[3]["ChargePeriodStart"]
        f = Path(tmp) / "bad.csv"
        write_csv(f, rows, fields)
        p = run("check", f)
        want = ("ChargeCategory is not one of", "BillingCurrency is not a three-letter code", "Tags is not valid JSON",
                "ChargePeriodEnd is not after ChargePeriodStart", "4 invalid rows")
        if p.returncode != 1 or any(w not in p.stderr for w in want):
            bad.append(f"bad rows: exit {p.returncode}, stderr: {p.stderr.strip()[:300]}")
        slim = [c for c in fields if c != "ServiceProviderName"]
        write_csv(f, [{c: r[c] for c in slim} for r in focus_rows(CLOUD_FOCUS)[:2]], slim)
        p = run("check", f)
        if p.returncode != 2 or "missing FOCUS columns: ServiceProviderName" not in p.stderr:
            bad.append(f"missing column: exit {p.returncode}, stderr: {p.stderr.strip()[:200]}")
        p = run("check", Path(tmp) / "absent.csv")
        if p.returncode != 2:
            bad.append(f"missing file: exit {p.returncode}, want 2")
    return bad


# ---------------------------------------------------------------- baseline

@test
def baseline_gives_the_committed_output_with_the_planted_spike():
    p = run("baseline", *FOCUS_FILES, "--from", "2026-04", "--to", "2026-09")
    bad = []
    if p.returncode != 0:
        bad.append(f"exit {p.returncode}: {p.stderr.strip()[:200]}")
    if p.stdout != text("outputs/baseline.md"):
        bad.append("the output differs from outputs/baseline.md")
    spikes = p.stdout.split("### Spikes and single months\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    want = ["- Synthetic Cloud, Compute, 2026-08: EUR 8,375.00, above 2.0 times the median of its other months (EUR 3,705.00)"]
    if spikes != want:
        bad.append(f"spike lines: {spikes}")
    if "- Synthetic Hosting: no rows for 2026-06" not in p.stdout:
        bad.append("the missing hosting month 2026-06 is not flagged")
    one_off = [ln for ln in p.stdout.splitlines() if re.match(r"\| 2026-\d\d \|.*\| (Purchase|Credit) \|", ln)]
    if len(one_off) != 3:
        bad.append(f"expected 3 one-off rows (2 purchases, 1 credit), got {len(one_off)}")
    return bad


@test
def baseline_spike_threshold_is_an_option():
    bad = []
    for factor, flagged in (("2.2", True), ("2.3", False)):  # the planted month is 2.26 times the median of the others
        p = run("baseline", *FOCUS_FILES, "--spike", factor)
        has = "above " + factor + " times the median" in p.stdout
        if has != flagged:
            bad.append(f"--spike {factor}: spike flagged is {has}, want {flagged}")
    return bad


@test
def baseline_flags_a_currency_change_and_a_single_month_service():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        hosting = focus_rows(HOSTING_FOCUS)
        for r in hosting:
            if r["ChargePeriodStart"].startswith("2026-09"):
                r["BillingCurrency"] = "USD"
        write_csv(Path(tmp) / "hosting.csv", hosting, fields_of(HOSTING_FOCUS))
        cloud = focus_rows(CLOUD_FOCUS)
        extra = dict(next(r for r in cloud if r["ServiceName"] == "Data Transfer" and r["ChargePeriodStart"].startswith("2026-07")))
        extra["ServiceName"], extra["ChargeDescription"] = "Pilot Service", "Pilot service, one month"
        cloud.append(extra)
        write_csv(Path(tmp) / "cloud.csv", cloud, fields_of(CLOUD_FOCUS))
        p = run("baseline", Path(tmp) / "cloud.csv", Path(tmp) / "hosting.csv")
        if "- Synthetic Hosting: EUR in 2026-04, 2026-05, 2026-07, 2026-08; USD in 2026-09" not in p.stdout:
            bad.append("the currency change is not flagged")
        provider_rows = [ln for ln in p.stdout.split("## By service")[0].splitlines() if ln.startswith("| Synthetic Hosting")]
        if len(provider_rows) != 2 or not any("USD 1,630.30" in ln for ln in provider_rows):
            bad.append(f"By provider should hold one Synthetic Hosting row per currency: {provider_rows}")
        if "- Synthetic Cloud, Pilot Service: rows in 2026-07 only. One-off or new service?" not in p.stdout:
            bad.append("the single-month service is not flagged")
    return bad


@test
def baseline_stops_on_invalid_rows_and_on_an_empty_selection():
    bad = []
    p = run("baseline", *FOCUS_FILES, "--from", "2027-01", "--to", "2027-03")
    if p.returncode != 2 or "no rows in the selected months" not in p.stderr:
        bad.append(f"empty selection: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
    p = run("baseline", *FOCUS_FILES, "--from", "April")
    if p.returncode != 2 or "not a month" not in p.stderr:
        bad.append(f"bad month: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
    with tempfile.TemporaryDirectory() as tmp:
        rows = focus_rows(CLOUD_FOCUS)[:3]
        rows[0]["BilledCost"] = "x"
        write_csv(Path(tmp) / "bad.csv", rows, fields_of(CLOUD_FOCUS))
        p = run("baseline", Path(tmp) / "bad.csv")
        if p.returncode != 1 or p.stdout:
            bad.append(f"invalid rows: exit {p.returncode}, stdout '{p.stdout[:80]}'")
    return bad


# ---------------------------------------------------------------- showback

@test
def showback_gives_the_committed_output_and_reconciles():
    p = run("showback", "--alloc", ALLOC, "--month", "2026-08", *FOCUS_FILES)
    bad = []
    if p.returncode != 0:
        bad.append(f"exit {p.returncode}: {p.stderr.strip()[:200]}")
    if p.stdout != text("outputs/showback-2026-08.md"):
        bad.append("the output differs from outputs/showback-2026-08.md")
    if "Reconciliation: teams plus unallocated minus total = EUR 0.00" not in p.stdout:
        bad.append("the reconciliation line does not read zero")
    # The same month, summed here from the FOCUS rows without the script.
    rows = [r for f in FOCUS_FILES for r in focus_rows(f) if r["ChargePeriodStart"].startswith("2026-08")]
    total = sum(Decimal(r["BilledCost"]) for r in rows)
    untagged = sum(Decimal(r["BilledCost"]) for r in rows
                   if not json.loads(r["Tags"] or "{}").get("team") and r["SubAccountId"] != "acct-syn-dev"
                   and r["ServiceName"] not in ("Support Plan", "VAT"))
    if f"| Total |  |  |  | EUR {total:,.2f} | 100.0% |" not in p.stdout:
        bad.append(f"the total row is not EUR {total:,.2f}")
    if f"| Unallocated |  |  |  | EUR {untagged:,.2f} |" not in p.stdout:
        bad.append(f"the unallocated row is not EUR {untagged:,.2f}")
    return bad


@test
def showback_even_and_weighted_splits():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        alloc = json.loads(text(ALLOC))
        alloc["shared"] = [{"name": "Cloud support plan", "services": ["Support Plan"], "split": {"checkout": 60, "search": 40}}]
        path = Path(tmp) / "weights.json"
        path.write_text(json.dumps(alloc))
        p = run("showback", "--alloc", path, "--month", "2026-08", *FOCUS_FILES)
        rows = {ln.split("|")[1].strip(): [c.strip() for c in ln.split("|")[2:-1]] for ln in p.stdout.splitlines()
                if ln.startswith("| ") and ln.split("|")[1].strip() in ("checkout", "search", "platform", "Unallocated")}
        if (rows.get("checkout") or [""] * 4)[2] != "EUR 300.00" or (rows.get("search") or [""] * 4)[2] != "EUR 200.00" \
                or (rows.get("platform") or [""] * 4)[2] != "EUR 0.00":
            bad.append(f"weights 60/40 of EUR 500.00: team rows {rows}")
        if "| Synthetic Hosting | VAT | no team tag and no rule | EUR 260.30 |" not in p.stdout:
            bad.append("VAT is no longer shared, so it should show as unallocated")
        if "= EUR 0.00" not in p.stdout:
            bad.append("the weighted split does not reconcile to zero")
        alloc["shared"] = [{"name": "Cloud support plan", "services": ["Support Plan"], "split": "even"}]
        path.write_text(json.dumps(alloc))
        p = run("showback", "--alloc", path, "--month", "2026-08", *FOCUS_FILES)
        if p.stdout.count("| EUR 166.67 |") != 3 or "= EUR 0.00" not in p.stdout:
            bad.append("an even split of EUR 500.00 over three teams should give EUR 166.67 to each and reconcile to zero")
    return bad


@test
def showback_refuses_a_bad_allocation_file():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "alloc.json"
        for label, change, frag in (
                ("placeholder", lambda a: a["teams"].append({"team": "<team>", "owner": "x"}), "placeholder"),
                ("unknown team", lambda a: a["rules"].append({"team": "nobody", "services": ["Compute"]}), "nobody"),
                ("bad split", lambda a: a["shared"].append({"name": "x", "services": ["Compute"], "split": "random"}), "split must be")):
            alloc = json.loads(text(ALLOC))
            change(alloc)
            path.write_text(json.dumps(alloc))
            p = run("showback", "--alloc", path, "--month", "2026-08", *FOCUS_FILES)
            if p.returncode != 2 or frag not in p.stderr or p.stdout:
                bad.append(f"{label}: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
    return bad


# ---------------------------------------------------------------- unit costs

@test
def unit_costs_per_thousand_requests():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        counts = Path(tmp) / "requests.csv"
        src = "SYNTHETIC request counts for the test, not a real metric"
        # Chosen so the cost per 1000 requests is EUR 1.00, then 2.00, then 1.00; 2026-07 has no count.
        write_csv(counts, [{"month": m, "count": c, "source": src} for m, c in (
            ("2026-04", 3650000), ("2026-05", 3045000), ("2026-06", 3705000), ("2026-08", 4187500), ("2026-09", 3840000))],
            ["month", "count", "source"])
        p = run("unit", "--counts", counts, "--unit", "request", "--per", "1000", "--provider", "Synthetic Cloud",
                "--service", "Compute", *FOCUS_FILES)
        want = ["| 2026-04 | EUR 3,650.00 | 3,650,000 | EUR 1.00 |  |",
                "| 2026-05 | EUR 6,090.00 | 3,045,000 | EUR 2.00 | +100.0% |",
                "| 2026-06 | EUR 3,705.00 | 3,705,000 | EUR 1.00 | -50.0% |",
                "| 2026-07 | EUR 3,355.00 | no count |  |  |",
                "| 2026-08 | EUR 8,375.00 | 4,187,500 | EUR 2.00 |  |",
                "| 2026-09 | EUR 3,840.00 | 3,840,000 | EUR 1.00 | -50.0% |"]
        lines = table_lines(p.stdout)[2:]
        if p.returncode != 0 or lines != want:
            bad.append(f"exit {p.returncode}, rows: {lines}")
        if "cost_source: " not in p.stdout or src not in p.stdout:
            bad.append("cost_source does not name the metric")
        write_csv(counts, [{"month": "2026-04", "count": 1, "source": ""}], ["month", "count", "source"])
        p = run("unit", "--counts", counts, *FOCUS_FILES)
        if p.returncode != 2 or "no source column values" not in p.stderr:
            bad.append(f"a count without a source: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
        hosting = focus_rows(HOSTING_FOCUS)
        hosting[0]["BillingCurrency"] = "USD"
        write_csv(Path(tmp) / "hosting.csv", hosting, fields_of(HOSTING_FOCUS))
        write_csv(counts, [{"month": "2026-04", "count": 1, "source": src}], ["month", "count", "source"])
        p = run("unit", "--counts", counts, Path(tmp) / "hosting.csv")
        if p.returncode != 2 or "more than one currency" not in p.stderr:
            bad.append(f"two currencies: exit {p.returncode}, stderr '{p.stderr.strip()[:120]}'")
    return bad


# ---------------------------------------------------------------- parsing

@test
def parse_amount_formats():
    fx = load_script()
    D = Decimal
    bad = []
    for value, mark, want in (("1,234.56", ".", D("1234.56")), ("1.234,56 EUR", ",", D("1234.56")), ("-$5", ".", D(-5)),
                              ("(12.00)", ".", D(-12)), ("12.00-", ".", D(-12)), ("EUR 7", ".", D(7)),
                              ("1.2E-5", ".", D("1.2E-5")), ("1'250.00", ".", D(1250)), ("99,00", ",", D(99))):
        try:
            got = fx.parse_amount(value, mark)
        except ValueError as e:
            bad.append(f"{value!r}: {e}")
            continue
        if got != want:
            bad.append(f"{value!r}: got {got}, want {want}")
    for value in ("abc", "", "1,2,3x"):
        try:
            fx.parse_amount(value)
            bad.append(f"{value!r} should not parse")
        except ValueError:
            pass
    if fx.unit_money("EUR", D("0.0123")) != "EUR 0.0123" or fx.unit_money("EUR", D("12.5")) != "EUR 12.50":
        bad.append("unit_money: small amounts need three significant digits, larger ones two decimals")
    return bad


# ---------------------------------------------------------------- the example pages

@test
def pages_embed_the_committed_script_output():
    bad = []
    base, show = text("docs/fin/cost-baseline.md"), text("docs/fin/showback-2026-08.md")
    for page, out, name in ((base, text("outputs/baseline.md"), "cost-baseline.md"),
                            (show, text("outputs/showback-2026-08.md"), "showback-2026-08.md")):
        page_lines = set(table_lines(page))
        for ln in table_lines(out):
            if ln not in page_lines:
                bad.append(f"{name} lacks the script table line: {ln[:80]}")
    for frag in ("- Synthetic Cloud, Compute, 2026-08: EUR 8,375.00, above 2.0 times the median of its other months (EUR 3,705.00)",
                 "- Synthetic Hosting: no rows for 2026-06"):
        if frag not in base:
            bad.append(f"cost-baseline.md lacks the flag: {frag[:70]}")
    if "Reconciliation: teams plus unallocated minus total = EUR 0.00" not in show:
        bad.append("showback-2026-08.md lacks the zero reconciliation line")
    return bad


@test
def run_rates_on_the_baseline_page_match_the_data():
    """The run rate is the median of a provider's months with its Purchase, Credit and Adjustment lines taken out."""
    fx = load_script()
    page = text("docs/fin/cost-baseline.md")
    bad = []
    for provider, rel in (("Synthetic Cloud", CLOUD_FOCUS), ("Synthetic Hosting", HOSTING_FOCUS)):
        months = {}
        for r in focus_rows(rel):
            if r["ChargeCategory"] not in fx.ONE_OFF:
                months[r["ChargePeriodStart"][:7]] = months.get(r["ChargePeriodStart"][:7], Decimal(0)) + Decimal(r["BilledCost"])
        rate = statistics.median(months.values())
        if f"- {provider}: EUR {rate:,.2f} per month" not in page:
            bad.append(f"{provider}: the page does not state the run rate EUR {rate:,.2f} per month")
    return bad


@test
def saas_inventory_matches_its_inputs():
    page = text("docs/fin/saas-inventory.md")
    billing = read_csv(EX / "inputs/synthetic-saas-billing-2025-10-to-2026-09.csv")
    sso = {r["app"]: r for r in read_csv(EX / "inputs/synthetic-sso-app-export-2026-09-30.csv")}
    terms = {r["tool"]: r for r in read_csv(EX / "inputs/synthetic-saas-owners-and-terms.csv")}
    total, seats = {}, {}
    for r in billing:
        tool = r["description"].split()[0]
        total[tool] = total.get(tool, Decimal(0)) + Decimal(r["amount"])
        seats[tool] = r["seats"]
    bad = []
    rows = {r[0]: r for r in md_table(page, "Tools")}
    if sorted(rows) != sorted(total) or sorted(terms) != sorted(total):
        bad.append(f"tools differ: page {sorted(rows)}, billing {sorted(total)}, owners list {sorted(terms)}")
    for tool, cells in rows.items():
        job, owner, _billing, renewal, notice, paid, used, cost, decision = cells[1:]
        t = terms.get(tool, {})
        month = total.get(tool, Decimal(0)) / 12
        checks = [(job, t.get("job"), "job"), (owner, t.get("owner") or "none after asking", "owner"),
                  (renewal, t.get("renewal"), "renewal"), (paid, seats.get(tool) or "flat plan", "seats paid"),
                  (used, sso[tool]["users_active_90d"] if tool in sso else "unknown", "seats used")]
        if t.get("billing_cycle") == "annual":
            due = datetime.date.fromisoformat(t["renewal"]) - datetime.timedelta(days=int(t["notice_days"]))
            checks.append((notice, due.isoformat(), "notice by"))
        for got, want, what in checks:
            if got != want:
                bad.append(f"{tool}, {what}: page '{got}', inputs '{want}'")
        if eur(cost) != month:
            bad.append(f"{tool}, cost per month: page {eur(cost)}, billing {month}")
        if not decision.startswith(("Keep", "Cut", "Replace")):
            bad.append(f"{tool}: the decision does not start with Keep, Cut or Replace")
    kinds = {c[-1].split(":")[0].split()[0] for c in rows.values()}
    if not {"Keep", "Cut", "Replace"} <= kinds:
        bad.append(f"the page needs at least one keep, one cut and one replace row, has {sorted(kinds)}")
    month_total, year_total = sum(total.values()) / 12, sum(total.values())
    for frag in (f"EUR {month_total:,.2f} per month together", f"EUR {year_total:,.2f} over the 12 months"):
        if frag not in page:
            bad.append(f"the page lacks '{frag}'")
    if "unknown" not in rows["SynthTickets"][7] or "SynthTickets" in sso:
        bad.append("SynthTickets has no SSO app, so its seats used must read unknown")
    return bad


@test
def everything_is_labelled_synthetic():
    bad = []
    for rel in FOCUS_FILES:
        for n, r in enumerate(focus_rows(rel), 2):
            if not r["x_Source"].startswith("SYNTHETIC") or not r["ServiceProviderName"].startswith("Synthetic"):
                bad.append(f"{rel}:{n}: x_Source or ServiceProviderName is not labelled synthetic")
                break
    for rel in ("outputs/check.txt", "outputs/baseline.md", "outputs/showback-2026-08.md"):
        if "SYNTHETIC" not in text(rel):
            bad.append(f"{rel} does not carry the synthetic label")
    for f in sorted((EX / "inputs").iterdir()):
        if not f.name.startswith("synthetic-"):
            bad.append(f"inputs/{f.name}: the name does not start with synthetic-")
    for f in sorted((EX / "docs/fin").glob("*.md")):
        s = f.read_text(encoding="utf-8")
        if "**Synthetic sample.**" not in s or "(synthetic sample)" not in s.split("---")[1]:
            bad.append(f"{f.name}: no synthetic banner or no synthetic title")
    if "synthetic" not in text("README.md").lower():
        bad.append("README.md does not say the data is synthetic")
    return bad


@test
def cost_provenance_passes_on_the_pages_and_fails_without_front_matter():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "gate.json"
        cfg.write_text(json.dumps({"name": "finops-example", "rules_dir": str(FINOPS / "checks"),
                                   "rules": {"finops.cost-provenance": {"tier": "block"}}}))

        def gate(root):
            return subprocess.run([sys.executable, str(RUNNER), "--config", str(cfg), "--root", str(root), "--dry-run", "--exit-code",
                                   "--sha", "example"], capture_output=True, text=True)

        p = gate(EX)
        if p.returncode != 0 or "finops.cost-provenance:pass" not in p.stdout:
            bad.append(f"the pages should pass: exit {p.returncode}: {p.stdout.strip()[:300]}")
        copy = Path(tmp) / "copy"
        (copy / "docs/fin").mkdir(parents=True)
        page = re.sub(r"^cost_(period|source):.*\n", "", text("docs/fin/cost-baseline.md"), flags=re.M)
        (copy / "docs/fin/cost-baseline.md").write_text(page, encoding="utf-8")
        p = gate(copy)
        hits = [ln.strip() for ln in p.stdout.splitlines() if "cost figure without period and source" in ln]
        golden = [ln.strip() for ln in text("outputs/cost-provenance-fail.txt").splitlines() if "cost figure without period and source" in ln]
        if p.returncode != 1 or not hits:
            bad.append(f"the copy without cost_period and cost_source should fail: exit {p.returncode}")
        elif hits != golden:
            bad.append("the hits differ from outputs/cost-provenance-fail.txt")
        if "docs/fin/cost-baseline.md:22 cost figure without period and source: EUR 45,826.00" not in hits:
            bad.append("the first hit should be the Synthetic Cloud total on line 22")
    return bad


@test
def examples_readme_has_the_three_line_video_section():
    s = text("README.md")
    if "\n## What a video can show\n" not in s:
        return ["README.md has no '## What a video can show' section"]
    section = s.split("\n## What a video can show\n", 1)[1].split("\n## ", 1)[0]
    lines = [ln for ln in section.splitlines() if ln.strip()]
    bad = []
    if len(lines) != 3 or not all(ln.startswith("- ") for ln in lines):
        bad.append(f"the section should be three bullet lines, got {len(lines)} lines")
    for needle, what in (("spike", "the spike flag"), ("Cut", "a cut row"), ("finops.cost-provenance", "the cost-provenance check")):
        if not any(needle in ln for ln in lines):
            bad.append(f"the section does not name {what}")
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
