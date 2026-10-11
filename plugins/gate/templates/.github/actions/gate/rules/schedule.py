"""The scheduled run happened within its interval."""
import datetime

ID = "gate.schedule"
DESCRIPTION = "A scheduled gate run happened within schedule.interval_days of this run."
DEFAULTS = {}


def check(ctx):
    sched = ctx.config.get("schedule") or {}
    interval = int(sched.get("interval_days", 7))
    runs = [h["ts"] for h in ctx.history if h.get("trigger") == "schedule"]
    if ctx.trigger == "schedule":
        runs.append(ctx.now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if not runs:
        return {"result": "n/a", "detail": f"no scheduled run yet; interval {interval} days, cron {sched.get('cron', 'not set')}"}
    last = max(runs)
    age = (ctx.now - datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).days
    ok = age <= interval
    return {"result": "pass" if ok else "fail",
            "detail": f"last scheduled run {last}, {age} days ago; interval {interval} days",
            "hits": [] if ok else [{"file": "gate/gate.json", "snippet": f"no scheduled run within {interval} days"}]}
