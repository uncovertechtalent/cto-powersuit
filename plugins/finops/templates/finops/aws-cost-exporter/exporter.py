"""AWS spend as Prometheus metrics: Cost Explorer and AWS Budgets, served on :9202/metrics.

Cost Explorer charges per API request, so the exporter asks rarely and caches every answer in
CACHE_FILE (default /data/cache.json). A restart reads the cache and asks again only when the
cached part is due:
  - every POLL_SECONDS (default 12 h), and at each new month: this month's daily cost by service
  - every FORECAST_SECONDS (default 24 h): Cost Explorer's forecast for the rest of the month
  - every HISTORY_SECONDS (default 7 days), and at each new month: daily cost by service
    for the HISTORY_MONTHS (default 3) months before this one
  - every BUDGETS_SECONDS (default 6 h): AWS Budgets
That is about three Cost Explorer requests a day. Requests are counted per API and kept in the
cache. Set CE_PRICE_PER_REQUEST to the price of one Cost Explorer request, and
aws_cost_explorer_spend_usd_total shows what the exporter itself costs.
Check before use: the price per Cost Explorer request and the IAM actions below, in the AWS docs.

Credentials come from the AWS shared config, mounted read-only; AWS_PROFILE picks the profile.
The exporter needs ce:GetCostAndUsage, ce:GetCostForecast, budgets:ViewBudget and, without
AWS_ACCOUNT_ID, sts:GetCallerIdentity. The metrics carry real spend: keep the scrape target and
the dashboard internal. Cost Explorer data lags by up to a day, and the latest days are marked
estimated.

Run, as the user that owns ~/.aws:
  docker build --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" \
    -t aws-cost-exporter finops/aws-cost-exporter
  docker run -d --name aws-cost-exporter --network <network of Prometheus> \
    -v "$HOME/.aws:/aws:ro" -e AWS_CONFIG_FILE=/aws/config \
    -e AWS_SHARED_CREDENTIALS_FILE=/aws/credentials -e AWS_PROFILE=<profile> \
    -v aws-cost-cache:/data aws-cost-exporter
Publish no port. Prometheus on the same network scrapes aws-cost-exporter:9202.
"""

import json
import os
import statistics
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3

CACHE_FILE = os.environ.get("CACHE_FILE", "/data/cache.json")
POLL = int(os.environ.get("POLL_SECONDS", str(12 * 3600)))
FORECAST = int(os.environ.get("FORECAST_SECONDS", str(24 * 3600)))
HISTORY = int(os.environ.get("HISTORY_SECONDS", str(7 * 86400)))
BUDGETS = int(os.environ.get("BUDGETS_SECONDS", str(6 * 3600)))
HISTORY_MONTHS = int(os.environ.get("HISTORY_MONTHS", "3"))
MEDIAN_DAYS = int(os.environ.get("MEDIAN_DAYS", "28"))
# Charges that post once a period (domain renewals, monthly tax) stay out of the spike baseline.
SPIKE_EXCLUDE = {x.strip() for x in os.environ.get("SPIKE_EXCLUDE", "Amazon Registrar,Tax").split(",") if x.strip()}
PORT = int(os.environ.get("PORT", "9202"))
CE_PRICE = float(os.environ.get("CE_PRICE_PER_REQUEST", "0"))  # USD per Cost Explorer request; 0 hides the spend metric
CE_REGION = os.environ.get("CE_REGION", "us-east-1")  # the region of the Cost Explorer and Budgets endpoints
METRIC = "UnblendedCost"

lock = threading.Lock()
cache = {"requests": {}, "errors": 0}


def log(msg):
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


def count(api, n=1):
    cache["requests"][api] = cache["requests"].get(api, 0) + n


def month_start(d, back=0):
    y, m = d.year, d.month - back
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def next_month(d):
    return month_start(date(d.year + d.month // 12, d.month % 12 + 1, 1))


def daily_by_service(ce, start, end):
    """Daily cost by service for [start, end), all pages. Returns days, estimated days, unit."""
    days, estimated, unit, token = {}, [], "USD", None
    while True:
        args = dict(TimePeriod={"Start": start.isoformat(), "End": end.isoformat()}, Granularity="DAILY",
                    Metrics=[METRIC], GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}])
        if token:
            args["NextPageToken"] = token
        r = ce.get_cost_and_usage(**args)
        count("ce:GetCostAndUsage")
        for res in r["ResultsByTime"]:
            day = res["TimePeriod"]["Start"]
            row = days.setdefault(day, {})
            if res.get("Estimated"):
                estimated.append(day)
            for g in res.get("Groups", []):
                m = g["Metrics"][METRIC]
                unit = m.get("Unit", unit)
                row[g["Keys"][0]] = row.get(g["Keys"][0], 0.0) + float(m["Amount"])
        token = r.get("NextPageToken")
        if not token:
            return days, sorted(set(estimated)), unit


def fetch(ce, budgets, account):
    now = time.time()
    today = datetime.now(timezone.utc).date()
    this_month, following = month_start(today), next_month(today)
    hist_start = month_start(today, HISTORY_MONTHS)

    cur = cache.get("current", {})
    if cur.get("month") != this_month.isoformat() or now - cur.get("fetched", 0) >= POLL:
        days, est, unit = daily_by_service(ce, this_month, today + timedelta(days=1))
        cache["current"] = {"month": this_month.isoformat(), "fetched": now, "days": days, "estimated": est, "unit": unit}
        log(f"current month: {len(days)} days, estimated {est}")

    fc = cache.get("forecast", {})
    if fc.get("end") != following.isoformat() or now - fc.get("fetched", 0) >= FORECAST:
        fc = {"fetched": now, "amount": None, "start": today.isoformat(), "end": following.isoformat()}
        try:
            r = ce.get_cost_forecast(TimePeriod={"Start": today.isoformat(), "End": following.isoformat()},
                                     Metric="UNBLENDED_COST", Granularity="MONTHLY")
            fc["amount"] = float(r["Total"]["Amount"])
        except ce.exceptions.DataUnavailableException:
            log("forecast: no data yet")
        finally:
            count("ce:GetCostForecast")
        cache["forecast"] = fc

    hist = cache.get("history", {})
    if hist.get("start") != hist_start.isoformat() or hist.get("end") != this_month.isoformat() \
            or now - hist.get("fetched", 0) >= HISTORY:
        days, est, unit = daily_by_service(ce, hist_start, this_month)
        cache["history"] = {"start": hist_start.isoformat(), "end": this_month.isoformat(), "fetched": now,
                            "days": days, "estimated": est, "unit": unit}
        log(f"history: {len(days)} days from {hist_start}")

    if now - cache.get("budgets", {}).get("fetched", 0) >= BUDGETS:
        out, token = [], None
        while True:
            args = {"AccountId": account}
            if token:
                args["NextToken"] = token
            r = budgets.describe_budgets(**args)
            count("budgets:DescribeBudgets")
            for b in r.get("Budgets", []):
                spend = b.get("CalculatedSpend", {})
                out.append({"name": b["BudgetName"], "type": b.get("BudgetType"), "period": b.get("TimeUnit"),
                            "limit": float(b.get("BudgetLimit", {}).get("Amount", "nan")),
                            "unit": b.get("BudgetLimit", {}).get("Unit", ""),
                            "actual": float(spend.get("ActualSpend", {}).get("Amount", "nan")),
                            "forecast": float(spend.get("ForecastedSpend", {}).get("Amount", "nan"))})
            token = r.get("NextToken")
            if not token:
                break
        cache["budgets"] = {"fetched": now, "items": out}


def save():
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f)
    os.replace(tmp, CACHE_FILE)


def poller():
    session = boto3.Session()
    ce = session.client("ce", region_name=CE_REGION)
    budgets = session.client("budgets", region_name=CE_REGION)
    account = os.environ.get("AWS_ACCOUNT_ID")
    while True:
        try:
            if not account:
                account = session.client("sts", region_name=CE_REGION).get_caller_identity()["Account"]
            with lock:
                fetch(ce, budgets, account)
                cache["last_success"] = time.time()
                save()
        except Exception as e:  # keep serving the cache; the error count shows on the dashboard
            with lock:
                cache["errors"] = cache.get("errors", 0) + 1
                save()
            log(f"fetch failed: {type(e).__name__}: {e}")
        time.sleep(300)  # each part checks its own age, so a short loop asks the API no more often


def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def render():
    out = []

    def m(name, kind, help_, samples):
        out.append(f"# HELP {name} {help_}\n# TYPE {name} {kind}")
        for labels, value in samples:
            if value is None or value != value:
                continue
            lab = ",".join(f'{k}="{esc(v)}"' for k, v in labels.items())
            out.append(f"{name}{{{lab}}} {value}" if lab else f"{name} {value}")

    with lock:
        cur, hist = cache.get("current", {}), cache.get("history", {})
        days = {**hist.get("days", {}), **cur.get("days", {})}
        estimated = set(hist.get("estimated", [])) | set(cur.get("estimated", []))
        today = datetime.now(timezone.utc).date().isoformat()
        totals = {d: sum(s.values()) for d, s in days.items()}
        months, month_tot = {}, {}
        for d, s in days.items():
            for svc, v in s.items():
                months[(d[:7], svc)] = months.get((d[:7], svc), 0.0) + v
            month_tot[d[:7]] = month_tot.get(d[:7], 0.0) + totals[d]
        this_month = cur.get("month", "")[:7]
        mtd_svc = {svc: v for (mo, svc), v in months.items() if mo == this_month}
        fc = cache.get("forecast", {})
        # the forecast covers [fc.start, month end); actual days before its start complete the month
        before_forecast = sum(t for d, t in totals.items() if d.startswith(this_month) and d < fc.get("start", today))
        usage = {d: sum(v for svc, v in s.items() if svc not in SPIKE_EXCLUDE) for d, s in days.items()}
        complete = sorted(d for d in usage if d < today)
        latest = complete[-1] if complete else None
        window = [usage[d] for d in complete[-1 - MEDIAN_DAYS:-1]]

        m("aws_cost_day_usd", "gauge", "Unblended cost of one UTC day by service, from Cost Explorer.",
          [({"day": d, "service": svc}, round(v, 6)) for d, s in sorted(days.items()) for svc, v in s.items() if abs(v) >= 1e-6])
        m("aws_cost_day_total_usd", "gauge", "Unblended cost of one UTC day, all services.",
          [({"day": d, "estimated": str(d in estimated).lower()}, round(t, 6)) for d, t in sorted(totals.items())])
        m("aws_cost_month_usd", "gauge", "Unblended cost of a calendar month by service (this month: to date).",
          [({"month": mo, "service": svc}, round(v, 6)) for (mo, svc), v in sorted(months.items()) if abs(v) >= 1e-6])
        m("aws_cost_month_total_usd", "gauge", "Unblended cost of a calendar month, all services (this month: to date).",
          [({"month": mo}, round(v, 6)) for mo, v in sorted(month_tot.items())])
        m("aws_cost_mtd_usd", "gauge", "This month to date, today's partial cost included.",
          [({}, round(month_tot.get(this_month, 0.0), 6))] if cur else [])
        m("aws_cost_mtd_by_service_usd", "gauge", "This month to date by service.",
          [({"service": svc}, round(v, 6)) for svc, v in sorted(mtd_svc.items()) if abs(v) >= 1e-6])
        m("aws_cost_month_forecast_usd", "gauge",
          "Month-end forecast: actual days before the forecast's start plus Cost Explorer's forecast to month end.",
          [({}, round(before_forecast + fc["amount"], 6))] if fc.get("amount") is not None and fc.get("start", "")[:7] == this_month else [])
        m("aws_cost_latest_day_usd", "gauge", "Cost of the latest UTC day before today without SPIKE_EXCLUDE services (may be partial).",
          [({}, round(usage[latest], 6))] if latest else [])
        m("aws_cost_latest_day_estimated", "gauge", "1 when Cost Explorer marks the latest day as estimated.",
          [({}, int(latest in estimated))] if latest else [])
        m("aws_cost_trailing_median_day_usd", "gauge", f"Median daily cost of the {MEDIAN_DAYS} days before the latest day, same services.",
          [({}, round(statistics.median(window), 6))] if window else [])
        b = cache.get("budgets", {}).get("items", [])
        m("aws_budget_limit_usd", "gauge", "Budget amount from AWS Budgets.",
          [({"budget": x["name"], "period": x["period"], "unit": x["unit"]}, x["limit"]) for x in b])
        m("aws_budget_actual_usd", "gauge", "Actual spend in the budget period, as AWS Budgets calculates it.",
          [({"budget": x["name"], "period": x["period"], "unit": x["unit"]}, x["actual"]) for x in b])
        m("aws_budget_forecast_usd", "gauge", "Forecast spend for the budget period, as AWS Budgets calculates it.",
          [({"budget": x["name"], "period": x["period"], "unit": x["unit"]}, x["forecast"]) for x in b])
        m("aws_cost_exporter_api_requests_total", "counter", "AWS API requests made by this exporter, kept across restarts.",
          [({"api": k}, v) for k, v in sorted(cache["requests"].items())])
        ce_n = sum(v for k, v in cache["requests"].items() if k.startswith("ce:"))
        m("aws_cost_explorer_spend_usd_total", "counter", "What the exporter's Cost Explorer requests cost, at CE_PRICE_PER_REQUEST each.",
          [({}, round(ce_n * CE_PRICE, 2))] if CE_PRICE > 0 else [])
        m("aws_cost_exporter_fetch_timestamp_seconds", "gauge", "When each part was last fetched.",
          [({"part": k}, cache[k]["fetched"]) for k in ("current", "forecast", "history", "budgets") if k in cache])
        m("aws_cost_exporter_last_success_timestamp_seconds", "gauge", "Last poll loop (every 5 min) that ended without an error.",
          [({}, cache.get("last_success"))])
        m("aws_cost_exporter_errors_total", "counter", "Failed polls, kept across restarts.", [({}, cache.get("errors", 0))])
        unit = cur.get("unit") or hist.get("unit")
        m("aws_cost_exporter_unit_info", "gauge", "Currency unit Cost Explorer reported.", [({"unit": unit}, 1)] if unit else [])
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = render().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    global cache
    try:
        with open(CACHE_FILE) as f:
            cache = {**cache, **json.load(f)}
        log(f"cache loaded, requests so far {cache['requests']}")
    except FileNotFoundError:
        log("no cache yet")
    threading.Thread(target=poller, daemon=True).start()
    log(f"serving :{PORT}/metrics")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
