#!/usr/bin/env python3
"""Convert billing data to FOCUS columns and report on FOCUS files. Standard library only, Python 3.9+.

FOCUS is the FinOps Open Cost and Usage Specification. Check before use: FOCUS spec version. COLUMNS below
follows the Cost and Usage columns of one FOCUS release. Compare it with the current release before a file
goes to anyone outside the team, and list every column you leave empty as a declared deviation.

Subcommands:
  convert   a billing CSV and a column map (JSON) to a FOCUS CSV
  check     validate FOCUS CSV files and print the totals per provider and currency
  baseline  monthly cost per provider and service, with flags for missing months, one-off charges,
            spikes and currency changes
  showback  cost per team from tags and an allocation file; unallocated cost is its own line
  unit      cost per unit per month, from FOCUS files and a CSV of monthly counts

Examples, from the repository root:
  python3 scripts/focus_export.py convert --in <raw>/hosting-2026-09.csv \\
      --map finops/focus-maps/hosting.json --out finops/focus/hosting-2026-09.csv
  python3 scripts/focus_export.py check finops/focus/*.csv
  python3 scripts/focus_export.py baseline finops/focus/*.csv
  python3 scripts/focus_export.py showback --alloc finops/allocation.json --month 2026-09 finops/focus/*.csv
  python3 scripts/focus_export.py unit --counts finops/units/requests.csv --unit request finops/focus/*.csv

Every row carries x_Source, the file or export it came from. Amounts are never converted between currencies:
every report groups by BillingCurrency. Reports print Markdown to stdout, ready for a docs page, with the
cost_period and cost_source values for its front matter.

Exit codes: 0 done, 1 invalid rows or a failed check, 2 usage or file error.
"""
import argparse
import csv
import datetime as dt
import decimal
import json
import re
import statistics
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

COLUMNS = [
    "BilledCost", "BillingAccountId", "BillingAccountName", "BillingCurrency", "BillingPeriodStart",
    "BillingPeriodEnd", "ChargeCategory", "ChargeClass", "ChargeDescription", "ChargePeriodStart",
    "ChargePeriodEnd", "ContractedCost", "EffectiveCost", "HostProviderName", "InvoiceIssuerName",
    "ListCost", "PricingQuantity", "PricingUnit", "ResourceId", "ResourceName", "ServiceCategory",
    "ServiceName", "ServiceProviderName", "SkuId", "SkuPriceId", "SubAccountId", "SubAccountName",
    "ConsumedQuantity", "ConsumedUnit", "Tags", "x_Source",
]
REQUIRED = ["BilledCost", "BillingCurrency", "BillingPeriodStart", "BillingPeriodEnd", "ChargeCategory",
            "ChargePeriodStart", "ChargePeriodEnd", "ServiceName", "ServiceProviderName"]
NUMBERS = ("BilledCost", "ContractedCost", "EffectiveCost", "ListCost", "PricingQuantity", "ConsumedQuantity")
CATEGORIES = ("Usage", "Purchase", "Tax", "Credit", "Adjustment")
ONE_OFF = ("Purchase", "Credit", "Adjustment")
PLACEHOLDER = re.compile(r"<[^<>]+>")
CURRENCY = re.compile(r"^[A-Z]{3}$")
MONTH = re.compile(r"^\d{4}-\d{2}$")
NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- parsing

def parse_time(value, fmt="iso"):
    """A UTC datetime from an ISO date or timestamp, or from a strptime format."""
    v = (value or "").strip()
    if not v:
        raise ValueError("empty date")
    t = dt.datetime.fromisoformat(v.replace("Z", "+00:00")) if fmt == "iso" else dt.datetime.strptime(v, fmt)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def month_start(t):
    return t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month(t):
    return month_start(month_start(t) + dt.timedelta(days=32))


def month_range(first, last):
    """Every YYYY-MM from first to last, both included."""
    y, m = map(int, first.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def parse_amount(value, decimal_mark="."):
    """A Decimal from text such as '1,234.56', '1.234,56 EUR', '-$5', '(12.00)', '12.00-' or '1.2E-5'."""
    v = (value or "").strip().replace("\u00a0", " ")
    neg = False
    if v.startswith("(") and v.endswith(")"):
        neg, v = True, v[1:-1].strip()
    if v.endswith("-"):
        neg, v = not neg, v[:-1].strip()
    if v.startswith("-"):
        neg, v = not neg, v[1:].strip()
    v = re.sub(r"^(?:[A-Z]{3}|[€$£])\s*|\s*(?:[A-Z]{3}|[€$£])$", "", v)
    if v.startswith("-"):
        neg, v = not neg, v[1:]
    v = v.replace(" ", "").replace("'", "")
    v = v.replace(".", "").replace(",", ".") if decimal_mark == "," else v.replace(",", "")
    if not NUMBER.fullmatch(v):
        raise ValueError(f"not a number: {value!r}")
    x = Decimal(v)
    return -x if neg else x


def money(currency, value, places=2):
    return f"{currency} {value:,.{places}f}"


def unit_money(currency, value):
    """Two decimals from 1 up; below 1, enough decimals for three significant digits."""
    if value == 0 or abs(value) >= 1:
        return money(currency, value)
    places = max(2, 2 - abs(value).adjusted())
    return money(currency, value, places)


# ---------------------------------------------------------------- validation and loading

def problems(row):
    out = [f"{c} is empty" for c in REQUIRED if not (row.get(c) or "").strip()]
    for c in NUMBERS:
        if (row.get(c) or "").strip():
            try:
                Decimal(row[c])
            except decimal.InvalidOperation:
                out.append(f"{c} is not a number: {row[c]!r}")
    if row.get("BillingCurrency") and not CURRENCY.match(row["BillingCurrency"]):
        out.append(f"BillingCurrency is not a three-letter code: {row['BillingCurrency']!r}")
    if row.get("ChargeCategory") and row["ChargeCategory"] not in CATEGORIES:
        out.append(f"ChargeCategory is not one of {', '.join(CATEGORIES)}: {row['ChargeCategory']!r}")
    try:
        if row.get("ChargePeriodStart") and row.get("ChargePeriodEnd") and \
                parse_time(row["ChargePeriodStart"]) >= parse_time(row["ChargePeriodEnd"]):
            out.append("ChargePeriodEnd is not after ChargePeriodStart")
        for c in ("ChargePeriodStart", "ChargePeriodEnd", "BillingPeriodStart", "BillingPeriodEnd"):
            if row.get(c):
                parse_time(row[c])
    except ValueError as e:
        out.append(f"bad date: {e}")
    if row.get("Tags"):
        try:
            if not isinstance(json.loads(row["Tags"]), dict):
                out.append("Tags is not a JSON object")
        except ValueError:
            out.append("Tags is not valid JSON")
    return out


def read_focus(paths):
    rows, errors = [], []
    for p in paths:
        try:
            f = open(p, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise InputError(f"{p}: {e.strerror}") from None
        with f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise InputError(f"{p}: missing FOCUS columns: {', '.join(missing)}")
            for n, row in enumerate(reader, 2):
                for msg in problems(row):
                    errors.append(f"{p}:{n}: {msg}")
                row["_where"] = f"{p}:{n}"
                row["_month"] = (row.get("ChargePeriodStart") or "")[:7]
                row["_source"] = (row.get("x_Source") or "").strip() or Path(p).name
                rows.append(row)
    return rows, errors


def load_valid(args):
    """Rows of the FOCUS files in args.files, filtered by --from/--to months. Stops on invalid rows."""
    rows, errors = read_focus(args.files)
    if errors:
        print_errors(errors)
        sys.exit(1)
    lo, hi = getattr(args, "from_month", None), getattr(args, "to_month", None)
    if getattr(args, "month", None):
        lo = hi = args.month
    for m in (lo, hi):
        if m and not MONTH.match(m):
            raise InputError(f"not a month (YYYY-MM): {m}")
    rows = [r for r in rows if (not lo or r["_month"] >= lo) and (not hi or r["_month"] <= hi)]
    if not rows:
        raise InputError("no rows in the selected months")
    return rows


def print_errors(errors, limit=30):
    for e in errors[:limit]:
        print("  " + e, file=sys.stderr)
    if len(errors) > limit:
        print(f"  ... and {len(errors) - limit} more", file=sys.stderr)
    print(f"focus_export.py: {len(errors)} invalid rows", file=sys.stderr)


def tags_of(row):
    try:
        t = json.loads(row.get("Tags") or "{}")
    except ValueError:
        return {}
    return t if isinstance(t, dict) else {}


def provenance(rows):
    months = sorted(r["_month"] for r in rows)
    sources = sorted({r["_source"] for r in rows})
    return months[0], months[-1], sources


def print_front_matter(rows, extra_sources=()):
    first, last, sources = provenance(rows)
    print(f"cost_period: {first}/{last}")
    print(f"cost_source: {'; '.join(list(sources) + list(extra_sources))}")
    print()


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print()


def no_placeholders(obj, where):
    if isinstance(obj, str) and PLACEHOLDER.search(obj):
        raise InputError(f"{where} still holds a placeholder: {obj}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k != "about":
                no_placeholders(k, where)
                no_placeholders(v, f"{where}.{k}")
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            no_placeholders(v, f"{where}[{i}]")


def load_json(path, what):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise InputError(f"{path}: {e.strerror}") from None
    except ValueError as e:
        raise InputError(f"{path}: not valid JSON: {e}") from None
    no_placeholders(data, what)
    return data


# ---------------------------------------------------------------- convert

def cmd_convert(args):
    m = load_json(args.map, args.map)
    cols, const = m.get("columns", {}), m.get("constants", {})
    values, tag_cols, extra = m.get("values", {}), m.get("tags", {}), m.get("extra", {})
    unknown = [c for c in list(cols) + list(const) + list(values) if c not in COLUMNS]
    if unknown:
        raise InputError(f"{args.map}: not a column of this script: {', '.join(unknown)}. Custom columns go under extra, with an x_ prefix.")
    bad_extra = [c for c in extra if not c.startswith("x_")]
    if bad_extra:
        raise InputError(f"{args.map}: custom columns need the x_ prefix: {', '.join(bad_extra)}")
    fmt, mark, gran = m.get("date_format", "iso"), m.get("decimal", "."), m.get("granularity", "day")
    source = m.get("source") or Path(args.inp).name
    lo = parse_time(args.start) if args.start else None
    hi = parse_time(args.end) if args.end else None

    try:
        f = open(args.inp, newline="", encoding="utf-8-sig")
    except OSError as e:
        raise InputError(f"{args.inp}: {e.strerror}") from None
    out, errors, outside, invalid = [], [], 0, 0
    with f:
        reader = csv.DictReader(f, delimiter=m.get("delimiter", ","))
        named = list(cols.values()) + list(tag_cols.values()) + list(extra.values())
        missing = [c for c in named if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{args.inp}: columns named in the map are missing from the file: {', '.join(missing)}")
        for n, src in enumerate(reader, 2):
            row = {c: "" for c in COLUMNS}
            row.update({k: str(v) for k, v in const.items()})
            for focus_col, src_col in cols.items():
                v = (src.get(src_col) or "").strip()
                if v:
                    row[focus_col] = values.get(focus_col, {}).get(v, v)
            try:
                for c in NUMBERS:
                    if row[c]:
                        row[c] = str(parse_amount(row[c], mark))
                start = parse_time(row["ChargePeriodStart"], fmt)
                if row["ChargePeriodEnd"]:
                    end = parse_time(row["ChargePeriodEnd"], fmt)
                else:
                    end = next_month(start) if gran == "month" else start + dt.timedelta(days=1)
                row["ChargePeriodStart"], row["ChargePeriodEnd"] = iso(start), iso(end)
                for c, default in (("BillingPeriodStart", month_start(start)), ("BillingPeriodEnd", next_month(start))):
                    row[c] = iso(parse_time(row[c], fmt)) if row[c] else iso(default)
            except ValueError as e:
                errors.append(f"{args.inp}:{n}: {e}")
                invalid += 1
                continue
            if (lo and start < lo) or (hi and start >= hi):
                outside += 1
                continue
            tags = {k: (src.get(c) or "").strip() for k, c in tag_cols.items() if (src.get(c) or "").strip()}
            if tags:
                row["Tags"] = json.dumps(tags, sort_keys=True)
            for k, c in extra.items():
                row[k] = (src.get(c) or "").strip()
            row["x_Source"] = row["x_Source"] or source
            found = problems(row)
            if found:
                errors += [f"{args.inp}:{n}: {msg}" for msg in found]
                invalid += 1
                continue
            out.append(row)

    if errors and not args.skip_invalid:
        print_errors(errors)
        print("focus_export.py: nothing written; fix the map or the rows, or pass --skip-invalid", file=sys.stderr)
        sys.exit(1)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + sorted(extra), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    totals = defaultdict(Decimal)
    for r in out:
        totals[r["BillingCurrency"]] += Decimal(r["BilledCost"])
    print(f"{args.out}: {len(out)} rows written, {outside} outside --start/--end, {invalid} invalid rows skipped")
    for cur, v in sorted(totals.items()):
        print(f"  BilledCost {money(cur, v)}")
    if errors:
        print_errors(errors)
        sys.exit(1)


# ---------------------------------------------------------------- check

def cmd_check(args):
    rows, errors = read_focus(args.files)
    if errors:
        print_errors(errors)
        sys.exit(1)
    if not rows:
        raise InputError("no rows")
    groups = defaultdict(lambda: [0, Decimal(0)])
    for r in rows:
        g = groups[(r["ServiceProviderName"], r["BillingCurrency"])]
        g[0] += 1
        g[1] += Decimal(r["BilledCost"])
    first, last, sources = provenance(rows)
    print(f"{len(rows)} rows in {len(args.files)} files, months {first} to {last}")
    table(["Provider", "Rows", "BilledCost"], [[p, n, money(c, v)] for (p, c), (n, v) in sorted(groups.items())])
    print("Sources: " + "; ".join(sources))
    no_source = [r["_where"] for r in rows if not (r.get("x_Source") or "").strip()]
    if no_source:
        print(f"warning: {len(no_source)} rows have no x_Source; the file name stands in for it")
    print("check: ok")


# ---------------------------------------------------------------- baseline

def cmd_baseline(args):
    rows = load_valid(args)
    first, last, _ = provenance(rows)
    months = month_range(first, last)
    by_provider = defaultdict(lambda: defaultdict(Decimal))
    by_service = defaultdict(lambda: defaultdict(Decimal))
    currencies = defaultdict(lambda: defaultdict(set))
    service_months = defaultdict(set)
    one_off = defaultdict(Decimal)
    for r in rows:
        p, s, c, mo, v = r["ServiceProviderName"], r["ServiceName"], r["BillingCurrency"], r["_month"], Decimal(r["BilledCost"])
        by_provider[(p, c)][mo] += v
        by_service[(p, s, c)][mo] += v
        currencies[p][c].add(mo)
        service_months[(p, s)].add(mo)
        if r["ChargeCategory"] in ONE_OFF or r.get("ChargeClass") == "Correction":
            one_off[(mo, p, s, r["ChargeCategory"], r.get("ChargeDescription") or "", c)] += v

    print(f"# Cost baseline {first} to {last}\n")
    print_front_matter(rows)
    print("## By provider\n")
    table(["Provider"] + months + ["Total"],
          [[p] + [money(c, row[mo]) if mo in row else "no data" for mo in months] + [money(c, sum(row.values()))]
           for (p, c), row in sorted(by_provider.items())])
    print("## By service\n")
    table(["Provider", "Service"] + months + ["Total"],
          [[p, s] + [money(c, row[mo]) if mo in row else "" for mo in months] + [money(c, sum(row.values()))]
           for (p, s, c), row in sorted(by_service.items())])

    print("## Flags\n")
    print("### Missing months\n")
    gaps = []
    for p in sorted(currencies):
        present = set().union(*currencies[p].values())
        own = month_range(min(present), max(present))
        missing = [mo for mo in own if mo not in present]
        if missing:
            gaps.append(f"- {p}: no rows for {', '.join(missing)}")
        if own[0] > first or own[-1] < last:
            gaps.append(f"- {p}: rows from {own[0]} to {own[-1]} only; the baseline runs from {first} to {last}")
    print("\n".join(gaps) if gaps else "None.")
    print("\n### One-off charges\n")
    if one_off:
        table(["Month", "Provider", "Service", "Category", "Description", "Amount"],
              [[mo, p, s, cat, desc, money(c, v)] for (mo, p, s, cat, desc, c), v in sorted(one_off.items())])
    else:
        print("None with ChargeCategory Purchase, Credit or Adjustment.\n")
    print("### Spikes and single months\n")
    spikes = [f"- {p}, {s}: rows in {next(iter(ms))} only. One-off or new service?"
              for (p, s), ms in sorted(service_months.items()) if len(months) >= 3 and len(ms) == 1]
    for (p, s, c), row in sorted(by_service.items()):
        if len(row) < 3:
            continue
        for mo, v in sorted(row.items()):
            others = [x for k, x in row.items() if k != mo]
            med = statistics.median(others)
            if med > 0 and v > Decimal(str(args.spike)) * med:
                spikes.append(f"- {p}, {s}, {mo}: {money(c, v)}, above {args.spike} times the median of its other months ({money(c, med)})")
    print("\n".join(spikes) if spikes else "None.")
    print("\n### Currency changes\n")
    changes = [f"- {p}: " + "; ".join(f"{c} in {', '.join(sorted(ms))}" for c, ms in sorted(cs.items()))
               for p, cs in sorted(currencies.items()) if len(cs) > 1]
    print("\n".join(changes) if changes else "None.")
    print()


# ---------------------------------------------------------------- showback

def matches(rule, row, tags):
    conds = []
    if "tags" in rule:
        conds.append(all(tags.get(k) in vs for k, vs in rule["tags"].items()))
    if "sub_accounts" in rule:
        conds.append(row.get("SubAccountId") in rule["sub_accounts"] or row.get("SubAccountName") in rule["sub_accounts"])
    if "services" in rule:
        conds.append(row["ServiceName"] in rule["services"])
    if "providers" in rule:
        conds.append(row["ServiceProviderName"] in rule["providers"])
    return bool(conds) and all(conds)


def cmd_showback(args):
    alloc = load_json(args.alloc, args.alloc)
    rows = load_valid(args)
    teams = {t["team"]: t.get("owner", "") for t in alloc.get("teams", [])}
    rules, shared, team_tag = alloc.get("rules", []), alloc.get("shared", []), alloc.get("team_tag", "")
    unknown = sorted({r["team"] for r in rules if teams and r["team"] not in teams})
    if unknown:
        raise InputError(f"{args.alloc}: rules name teams that are not in teams: {', '.join(unknown)}")
    for s in shared:
        how = s.get("split", "proportional")
        if not (how in ("proportional", "even") or isinstance(how, dict)):
            raise InputError(f"{args.alloc}: shared cost {s.get('name')!r}: split must be proportional, even or an object of team weights")

    first, last, _ = provenance(rows)
    print(f"# Showback {first} to {last}\n")
    print_front_matter(rows, [Path(args.alloc).name])
    for cur in sorted({r["BillingCurrency"] for r in rows}):
        part = [r for r in rows if r["BillingCurrency"] == cur]
        direct, pool, unalloc = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
        tagged = Decimal(0)
        for r in part:
            v, tags = Decimal(r["BilledCost"]), tags_of(r)
            if team_tag and tags.get(team_tag):
                tagged += v
            s = next((x for x in shared if matches(x, r, tags)), None)
            rule = next((x for x in rules if matches(x, r, tags)), None)
            if s:
                pool[s["name"]] += v
            elif rule:
                direct[rule["team"]] += v
            elif team_tag and tags.get(team_tag):
                direct[tags[team_tag]] += v
            else:
                reason = f"no {team_tag} tag and no rule" if team_tag else "no rule"
                unalloc[(r["ServiceProviderName"], r["ServiceName"], reason)] += v
        base = {t: v for t, v in direct.items() if v > 0}
        spread = defaultdict(Decimal)
        split_rows = []
        for s in shared:
            amount = pool.get(s["name"], Decimal(0))
            if not amount:
                continue
            how = s.get("split", "proportional")
            weights = base if how == "proportional" else {t: 1 for t in base} if how == "even" else how
            total_w = sum(Decimal(str(w)) for w in weights.values()) if isinstance(weights, dict) else 0
            if not total_w:
                unalloc[("shared", s["name"], "no team to split to")] += amount
                split_rows.append([s["name"], money(cur, amount), "not split: no team to split to"])
                continue
            for t, w in weights.items():
                spread[t] += amount * Decimal(str(w)) / total_w
            label = how if isinstance(how, str) else ", ".join(f"{t} {w}" for t, w in how.items())
            split_rows.append([s["name"], money(cur, amount), label])

        total = sum(Decimal(r["BilledCost"]) for r in part)
        names = sorted(set(direct) | set(spread), key=lambda t: -(direct[t] + spread[t]))
        unalloc_total = sum(unalloc.values())
        pct = (lambda v: f"{v / total * 100:.1f}%") if total else (lambda v: "")
        print(f"## Cost per team, {cur}\n")
        table(["Team", "Owner", "Direct", "Shared", "Total", "Share"],
              [[t, teams.get(t, "not in the teams list"), money(cur, direct[t]), money(cur, spread[t]),
                money(cur, direct[t] + spread[t]), pct(direct[t] + spread[t])] for t in names]
              + [["Unallocated", "", "", "", money(cur, unalloc_total), pct(unalloc_total)],
                 ["Total", "", "", "", money(cur, total), pct(total)]])
        if team_tag:
            print(f"Cost with a `{team_tag}` tag: {money(cur, tagged)}, {pct(tagged)} of the total.\n")
        print(f"### Unallocated, {cur}\n")
        if unalloc:
            table(["Provider", "Service", "Reason", "Amount"],
                  [[p, s, why, money(cur, v)] for (p, s, why), v in sorted(unalloc.items(), key=lambda kv: -kv[1])])
        else:
            print("None.\n")
        print(f"### Shared costs, {cur}\n")
        if split_rows:
            table(["Shared cost", "Amount", "Split"], split_rows)
        else:
            print("None.\n")
        diff = total - sum(direct.values()) - sum(spread.values()) - unalloc_total
        print(f"Reconciliation: teams plus unallocated minus total = {cur} {diff:.2f}\n")


# ---------------------------------------------------------------- unit costs

def cmd_unit(args):
    rows = load_valid(args)
    for spec in args.tag:
        if "=" not in spec:
            raise InputError(f"--tag needs key=value: {spec}")
    want_tags = dict(spec.split("=", 1) for spec in args.tag)
    rows = [r for r in rows
            if (not args.provider or r["ServiceProviderName"] in args.provider)
            and (not args.service or r["ServiceName"] in args.service)
            and all(tags_of(r).get(k) == v for k, v in want_tags.items())]
    if not rows:
        raise InputError("no rows match the filters")
    curs = sorted({r["BillingCurrency"] for r in rows})
    if len(curs) > 1:
        raise InputError(f"the rows hold more than one currency ({', '.join(curs)}); filter with --provider or --service, or convert first with a named rate")
    cur = curs[0]
    cost = defaultdict(Decimal)
    for r in rows:
        cost[r["_month"]] += Decimal(r["BilledCost"])
    counts, count_sources = {}, set()
    try:
        f = open(args.counts, newline="", encoding="utf-8-sig")
    except OSError as e:
        raise InputError(f"{args.counts}: {e.strerror}") from None
    with f:
        reader = csv.DictReader(f)
        if not {"month", "count"} <= set(reader.fieldnames or []):
            raise InputError(f"{args.counts}: must have the columns month, count and source")
        for n, r in enumerate(reader, 2):
            if not MONTH.match(r["month"].strip()):
                raise InputError(f"{args.counts}:{n}: not a month (YYYY-MM): {r['month']!r}")
            counts[r["month"].strip()] = parse_amount(r["count"])
            if (r.get("source") or "").strip():
                count_sources.add(r["source"].strip())
    if not count_sources:
        raise InputError(f"{args.counts}: no source column values; give every count the metric it comes from")

    print(f"# Cost per {args.unit}\n")
    print_front_matter(rows, sorted(count_sources))
    out, prev = [], None
    for mo in month_range(min(cost), max(cost)):
        c, n = cost.get(mo), counts.get(mo)
        if c is None or n is None or n == 0:
            out.append([mo, money(cur, c) if c is not None else "no data", f"{n:,}" if n is not None else "no count", "", ""])
            prev = None
            continue
        u = c / n * args.per
        change = f"{(u / prev - 1) * 100:+.1f}%" if prev else ""
        out.append([mo, money(cur, c), f"{n:,}", unit_money(cur, u), change])
        prev = u
    per = f"{args.per:,} {args.unit}s" if args.per != 1 else args.unit
    table(["Month", "Cost", f"Count ({args.unit})", f"Cost per {per}", "Change"], out)
    print("Count source: " + "; ".join(sorted(count_sources)) + "\n")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Convert billing data to FOCUS columns and report on FOCUS files.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("convert", help="billing CSV + column map -> FOCUS CSV")
    p.add_argument("--in", dest="inp", required=True, help="billing CSV")
    p.add_argument("--map", required=True, help="column map, JSON")
    p.add_argument("--out", required=True, help="FOCUS CSV to write")
    p.add_argument("--start", help="first day to keep, YYYY-MM-DD")
    p.add_argument("--end", help="day after the last day to keep, YYYY-MM-DD")
    p.add_argument("--skip-invalid", action="store_true", help="write the valid rows and report the others")

    p = sub.add_parser("check", help="validate FOCUS CSV files")
    p.add_argument("files", nargs="+")

    def report(name, text):
        q = sub.add_parser(name, help=text)
        q.add_argument("files", nargs="+", help="FOCUS CSV files")
        q.add_argument("--from", dest="from_month", help="first month, YYYY-MM")
        q.add_argument("--to", dest="to_month", help="last month, YYYY-MM")
        return q

    p = report("baseline", "monthly cost per provider and service, with flags")
    p.add_argument("--spike", type=float, default=2.0, help="flag a service month above this many times the median of its other months")
    p = report("showback", "cost per team from tags and an allocation file")
    p.add_argument("--alloc", required=True, help="allocation file, JSON")
    p.add_argument("--month", help="one month, YYYY-MM")
    p = report("unit", "cost per unit per month")
    p.add_argument("--counts", required=True, help="CSV with month, count, source")
    p.add_argument("--unit", default="unit", help="name of the unit, for the table header")
    p.add_argument("--per", type=int, default=1, help="cost per this many units, for example 1000")
    p.add_argument("--provider", action="append", default=[], help="keep only this ServiceProviderName; repeatable")
    p.add_argument("--service", action="append", default=[], help="keep only this ServiceName; repeatable")
    p.add_argument("--tag", action="append", default=[], help="keep only rows with this tag, key=value; repeatable")

    args = ap.parse_args()
    {"convert": cmd_convert, "check": cmd_check, "baseline": cmd_baseline,
     "showback": cmd_showback, "unit": cmd_unit}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except InputError as e:
        print(f"focus_export.py: {e}", file=sys.stderr)
        sys.exit(2)
