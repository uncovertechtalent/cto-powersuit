#!/usr/bin/env python3
"""Build a static status page from the service catalogue and the incident records. Standard library only, Python 3.9+.

Reads:
  services/*.yml            one catalogue entry per service; files whose name starts with _ are skipped
  incidents/incidents.json  every incident with its updates; schema in incidents/incidents.schema.json
Writes, into --out (default site/status):
  index.html                overall state, one row per service, open incidents with their timeline, history
  status.json               the same data, machine-readable

The page loads nothing from a third party and needs no JavaScript. It is as fresh as its last build: run the
script in the deploy job, and again after every change to an incident.

Usage:
  python3 scripts/build_status.py [--services services] [--incidents incidents/incidents.json] [--out site/status]
                                  [--title Status] [--history-days 90] [--docs-prefix /docs/] [--today YYYY-MM-DD]
  python3 scripts/build_status.py --check
      Validates the records and prints each SLO target next to its dependency ceiling, the product of the
      targets of its serial dependencies (depends_on). Writes nothing.

A catalogue entry with status_page: hidden stays off the page, also in the service lists of incidents.

State of a service, from the open incidents that name it: impact none changes nothing, minor is Degraded,
major is Partial outage, critical is Major outage. A service with no open incident shows No open incident.

Exit codes: 0 done, 1 invalid records (or, with --check, a target above its ceiling), 2 usage or file error.
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

STAGES = ["investigating", "identified", "monitoring", "resolved"]
IMPACTS = {"none": "No user impact", "minor": "Degraded", "major": "Partial outage", "critical": "Major outage"}
RANK = {"none": 0, "minor": 1, "major": 2, "critical": 3}
SEVERITIES = ["sev1", "sev2", "sev3", "sev4"]
WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}Z)?$")
INCIDENT_FIELDS = {"id", "title", "services", "impact", "severity", "started", "resolved", "summary", "updates", "postmortem"}


class RecordError(Exception):
    pass


# ---------------------------------------------------------------- catalogue: a YAML subset

KEY = re.compile(r"^([A-Za-z_][\w-]*)\s*:(?:\s+(.*))?$")


def strip_comment(line):
    if line.lstrip().startswith("#"):
        return ""
    quote = None
    for i, ch in enumerate(line):
        if ch in "\"'":
            quote = None if quote == ch else (quote or ch)
        elif ch == "#" and quote is None and i > 0 and line[i - 1] in " \t":
            return line[:i].rstrip()
    return line.rstrip()


def scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return "" if v in ("~", "null") else v


def value(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    return scalar(v)


def parse_yaml(text, where):
    """Top-level 'key: value', flow lists [a, b], block lists, folded or literal blocks (> and |), and one
    nested mapping level. Values are strings or lists of strings."""
    rows = text.split("\n")
    data, i = {}, 0
    indented = lambda r: r[:1] in (" ", "\t")
    item = lambda r: r.strip() == "-" or r.startswith("- ")
    while i < len(rows):
        line = strip_comment(rows[i])
        if not line.strip() or line.strip() in ("---", "..."):
            i += 1
            continue
        m = KEY.match(line)
        if indented(line) or not m:
            raise RecordError(f"{where}:{i + 1}: expected 'key: value' at the start of the line")
        key, val = m.group(1), (m.group(2) or "").strip()
        i += 1
        if val in (">", "|", ">-", "|-"):
            block = []
            while i < len(rows) and (not rows[i].strip() or indented(rows[i])):
                block.append(rows[i].strip())
                i += 1
            data[key] = (" " if val[0] == ">" else "\n").join(block).strip()
        elif val:
            data[key] = value(val)
        else:
            items, sub = [], {}
            while i < len(rows) and (not strip_comment(rows[i]).strip() or indented(rows[i]) or item(rows[i])):
                s = strip_comment(rows[i]).strip()
                if s == "-" or s.startswith("- "):
                    items.append(scalar(s[1:]))
                elif s:
                    m2 = KEY.match(s)
                    if not m2:
                        raise RecordError(f"{where}:{i + 1}: expected '- item' or 'key: value' under {key}")
                    sub[m2.group(1)] = value(m2.group(2) or "")
                i += 1
            data[key] = items or sub or ""
    return data


def as_list(v):
    return v if isinstance(v, list) else [v] if v else []


def target_of(svc):
    slo = svc.get("slo")
    if not isinstance(slo, dict) or not isinstance(slo.get("target"), str):
        return None
    try:
        t = Decimal(slo["target"].strip().rstrip("%"))
    except InvalidOperation:
        return None
    return t if 0 < t < 100 else None


def load_catalog(folder, errors):
    svcs = {}
    files = sorted(p for p in Path(folder).glob("*.y*ml") if p.suffix in (".yml", ".yaml") and not p.name.startswith("_"))
    if not files:
        raise RecordError(f"no catalogue entries in {folder}/")
    for f in files:
        try:
            s = parse_yaml(f.read_text(encoding="utf-8"), f.as_posix())
        except RecordError as e:
            errors.append(str(e))
            continue
        sid = s.get("id") or f.stem
        if sid != f.stem:
            errors.append(f"{f.as_posix()}: id {sid} differs from the file name")
        if sid in svcs:
            errors.append(f"{f.as_posix()}: id {sid} is used twice")
        s["id"], s["_file"] = sid, f.as_posix()
        s["name"] = s.get("name") or sid
        svcs[sid] = s
    for s in svcs.values():
        for k in ("depends_on", "soft_depends_on"):
            for dep in as_list(s.get(k)):
                if dep not in svcs:
                    errors.append(f"{s['_file']}: {k} names {dep}, which has no catalogue entry")
    return svcs


def ceiling(svc, svcs):
    """(ceiling in percent, missing): the product of the targets of the serial dependencies, or None."""
    product, missing = Decimal(1), []
    for dep in as_list(svc.get("depends_on")):
        t = target_of(svcs[dep]) if dep in svcs else None
        if t is None:
            missing.append(dep)
        else:
            product *= t / 100
    return (None if missing else product * 100), missing


# ---------------------------------------------------------------- incidents

def load_incidents(path, svcs, errors):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise RecordError(f"{path}: {e.strerror}") from None
    except ValueError as e:
        raise RecordError(f"{path}: not valid JSON: {e}") from None
    if not isinstance(data, dict) or not isinstance(data.get("incidents"), list):
        raise RecordError(f"{path}: needs an object with an incidents list")
    seen, out = set(), []
    for n, inc in enumerate(data["incidents"]):
        where = f"{path}: incident {inc.get('id') if isinstance(inc, dict) else n}"
        if not isinstance(inc, dict):
            errors.append(f"{where}: not an object")
            continue
        before = len(errors)
        for k in sorted(set(inc) - INCIDENT_FIELDS):
            errors.append(f"{where}: unknown field {k}")
        for k in ("id", "title", "summary", "started"):
            if not isinstance(inc.get(k), str) or not inc[k].strip():
                errors.append(f"{where}: {k} must be a non-empty string")
        if inc.get("id") in seen:
            errors.append(f"{where}: id used twice")
        seen.add(inc.get("id"))
        if not isinstance(inc.get("services"), list) or not inc["services"]:
            errors.append(f"{where}: services must be a non-empty list of catalogue ids")
        else:
            errors += [f"{where}: service {s} has no catalogue entry" for s in inc["services"] if s not in svcs]
        if inc.get("impact") not in IMPACTS:
            errors.append(f"{where}: impact must be one of {', '.join(IMPACTS)}")
        if inc.get("severity") not in (None, *SEVERITIES):
            errors.append(f"{where}: severity must be one of {', '.join(SEVERITIES)}")
        for k in ("started", "resolved"):
            if inc.get(k) is not None and not (isinstance(inc[k], str) and WHEN.match(inc[k])):
                errors.append(f"{where}: {k} must be YYYY-MM-DD or YYYY-MM-DDTHH:MMZ (UTC)")
        ups = inc.get("updates")
        if not isinstance(ups, list) or not ups:
            errors.append(f"{where}: at least one update")
            continue
        last = -1
        for u in ups:
            if not isinstance(u, dict) or set(u) != {"stage", "at", "text"}:
                errors.append(f"{where}: each update has exactly stage, at and text")
                break
            if u["stage"] not in STAGES:
                errors.append(f"{where}: stage must be one of {', '.join(STAGES)}")
                break
            if not (isinstance(u["at"], str) and WHEN.match(u["at"])):
                errors.append(f"{where}: update time must be YYYY-MM-DD or YYYY-MM-DDTHH:MMZ (UTC)")
            if STAGES.index(u["stage"]) < last:
                errors.append(f"{where}: stages go forward: {', '.join(STAGES)}")
            last = STAGES.index(u["stage"])
        else:
            if (ups[-1]["stage"] == "resolved") != bool(inc.get("resolved")):
                errors.append(f"{where}: resolved is set exactly when the last update is resolved")
        if len(errors) == before:
            inc["stage"] = ups[-1]["stage"]
            out.append(inc)
    out.sort(key=lambda i: (i["started"], i["id"]), reverse=True)
    return out


def when(t):
    return t.replace("T", " ").replace("Z", " UTC") if "T" in t else t + ", time not recorded"


def minutes(start, end):
    if "T" not in start or "T" not in (end or ""):
        return None
    f = "%Y-%m-%dT%H:%MZ"
    return int((dt.datetime.strptime(end, f) - dt.datetime.strptime(start, f)).total_seconds() // 60)


def link(ref, docs_prefix):
    if ref.startswith("doc:"):
        space, _, slug = ref[4:].partition("/")
        return f"{docs_prefix}{space}/" + (f"{slug}/" if slug and slug != "index" else "")
    return ref


# ---------------------------------------------------------------- output

CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--line:#e3e3e6;--ok:#1e7f4f;--minor:#b26a00;--major:#c2410c;--critical:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececef;--muted:#a1a1aa;--line:#2c2c31;--ok:#4ade80;--minor:#fbbf24;--major:#fb923c;--critical:#f87171}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:52rem;margin:0 auto;padding:1.5rem 1rem 3rem}
h1{margin:.2rem 0 1rem}h2{margin-top:2.2rem;font-size:1.15rem}
.overall{padding:.9rem 1rem;border:1px solid var(--line);border-left:6px solid var(--ok);font-weight:600}
.overall.minor{border-left-color:var(--minor)}.overall.major{border-left-color:var(--major)}.overall.critical{border-left-color:var(--critical)}
ul.svc{list-style:none;padding:0;margin:0}ul.svc li{display:flex;flex-wrap:wrap;gap:.3rem 1rem;padding:.6rem 0;border-bottom:1px solid var(--line)}
.name{flex:1 1 14rem;font-weight:600}.meta,.note,.when{color:var(--muted);font-size:.9rem}
.state{font-weight:600;color:var(--ok)}.state.minor{color:var(--minor)}.state.major{color:var(--major)}.state.critical{color:var(--critical)}
article{border:1px solid var(--line);padding:.8rem 1rem;margin:1rem 0}article h3{margin:0 0 .3rem;font-size:1.05rem}
ol.tl{padding-left:1.2rem}ol.tl li{margin:.4rem 0}a{color:inherit}
"""


def visible(svc):
    return svc.get("status_page") != "hidden"


def incident_html(inc, svcs, docs_prefix):
    names = ", ".join(html.escape(svcs[s]["name"]) for s in inc["services"] if visible(svcs[s])) or "internal services"
    span = (f"{html.escape(when(inc['started']))} to {html.escape(when(inc['resolved']))}" if inc.get("resolved")
            else f"since {html.escape(when(inc['started']))}")
    mins = minutes(inc["started"], inc.get("resolved"))
    dur = f", {mins} min" if mins is not None else ""
    tl = "".join(f"<li><span class=\"when\">{html.escape(when(u['at']))}, {u['stage'].capitalize()}</span><br>{html.escape(' '.join(u['text'].split()))}</li>"
                 for u in inc["updates"])
    pm = (f"<p class=\"meta\"><a href=\"{html.escape(link(inc['postmortem'], docs_prefix))}\">Postmortem</a></p>"
          if inc.get("postmortem") else "")
    return (f"<article id=\"{html.escape(inc['id'])}\"><h3>{html.escape(inc['title'])}</h3>"
            f"<p class=\"meta\">{span}{dur} · {IMPACTS[inc['impact']]} · {inc['stage'].capitalize()} · services: {names}</p>"
            f"<p>{html.escape(' '.join(inc['summary'].split()))}</p>{pm}<ol class=\"tl\">{tl}</ol></article>")


def build(svcs, incidents, args, today):
    open_inc = [i for i in incidents if i["stage"] != "resolved"]
    worst = {}
    for inc in open_inc:
        for s in inc["services"]:
            if RANK[inc["impact"]] > RANK[worst.get(s, "none")]:
                worst[s] = inc["impact"]
    since = (today - dt.timedelta(days=args.history_days)).isoformat()
    history = [i for i in incidents if i["stage"] == "resolved" and i["resolved"][:10] >= since]
    tier = lambda s: (str(s.get("tier") or "9"), s["name"].lower())
    order = sorted((s for s in svcs.values() if visible(s)), key=tier)
    affected = [s for s in order if worst.get(s["id"], "none") != "none"]
    top = max((RANK[worst[s["id"]]] for s in affected), default=0)
    level = [k for k, v in RANK.items() if v == top][0]
    overall = (f"{len(affected)} of {len(order)} services affected by an open incident" if affected
               else f"No open incident affects the {len(order)} services on this page")

    rows = ""
    for s in order:
        imp = worst.get(s["id"], "none")
        state = IMPACTS[imp] if imp != "none" else "No open incident"
        t = target_of(s)
        meta = " · ".join(x for x in (f"tier {s['tier']}" if s.get("tier") else "", f"SLO {t}%" if t is not None else "") if x)
        rows += (f"<li id=\"svc-{html.escape(s['id'])}\"><span class=\"name\">{html.escape(s['name'])}</span>"
                 f"<span class=\"meta\">{meta}</span><span class=\"state {imp}\">{state}</span></li>")
    open_html = "".join(incident_html(i, svcs, args.docs_prefix) for i in open_inc) or "<p class=\"note\">No open incident.</p>"
    hist_html = "".join(incident_html(i, svcs, args.docs_prefix) for i in history) or f"<p class=\"note\">No incident resolved in the last {args.history_days} days.</p>"
    title = html.escape(args.title)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class="overall {level}">{html.escape(overall)}</p>
<p class="note">Built {today.isoformat()} from the service catalogue and the incident records. The page shows the state at its last build.</p>
<h2>Services</h2>
<ul class="svc">{rows}</ul>
<h2>Open incidents</h2>
{open_html}
<h2>Resolved in the last {args.history_days} days</h2>
{hist_html}
<h2>How the state is decided</h2>
<ul>
<li><b>No open incident</b>: no open incident names the service.</li>
<li><b>Degraded</b>, <b>Partial outage</b>, <b>Major outage</b>: an open incident with impact minor, major or critical names the service. The highest impact sets the state.</li>
<li>An incident with impact none changes no state. Times are UTC. Stages: {", ".join(STAGES)}.</li>
</ul>
</main>
</body>
</html>
"""
    data = {
        "generated": today.isoformat(), "title": args.title, "overall": {"level": level, "text": overall},
        "services": [{"id": s["id"], "name": s["name"], "tier": s.get("tier") or None,
                      "slo_target": str(target_of(s)) if target_of(s) is not None else None,
                      "state": worst.get(s["id"], "none"),
                      "open_incidents": [i["id"] for i in open_inc if s["id"] in i["services"]]} for s in order],
        "open": [{k: v for k, v in i.items() if k in INCIDENT_FIELDS or k == "stage"} for i in open_inc],
        "history": [{k: v for k, v in i.items() if k in INCIDENT_FIELDS or k == "stage"} for i in history],
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "status.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{out}/index.html, {out}/status.json: {len(order)} services, {len(open_inc)} open incidents, "
          f"{len(history)} resolved in the last {args.history_days} days")


def check(svcs, incidents):
    over = 0
    print("| Service | Tier | Target | Serial dependencies | Ceiling | Result |")
    print("|---|---|---|---|---|---|")
    for s in sorted(svcs.values(), key=lambda s: s["id"]):
        t = target_of(s)
        ceil, missing = ceiling(s, svcs)
        deps = ", ".join(as_list(s.get("depends_on"))) or "none"
        if t is None:
            result = "no numeric target"
        elif missing:
            result = "ceiling unknown: no target for " + ", ".join(missing)
        elif t > ceil:
            result, over = "above ceiling", over + 1
        else:
            result = "ok"
        print(f"| {s['id']} | {s.get('tier') or ''} | {t if t is not None else ''} | {deps} | "
              f"{'' if ceil is None else f'{ceil:.4f}'.rstrip('0').rstrip('.')} | {result} |")
    print(f"\n{len(svcs)} services, {len(incidents)} incidents, {sum(i['stage'] != 'resolved' for i in incidents)} open, "
          f"{over} targets above their ceiling")
    return over


def main():
    ap = argparse.ArgumentParser(description="Build a static status page from the service catalogue and the incident records.")
    ap.add_argument("--services", default="services")
    ap.add_argument("--incidents", default="incidents/incidents.json")
    ap.add_argument("--out", default="site/status")
    ap.add_argument("--title", default="Status")
    ap.add_argument("--history-days", type=int, default=90)
    ap.add_argument("--docs-prefix", default="/docs/", help="URL prefix for doc:<space>/<slug> links")
    ap.add_argument("--today", help="build date, YYYY-MM-DD; default: today in UTC")
    ap.add_argument("--check", action="store_true", help="validate and print targets against dependency ceilings; write nothing")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()

    errors = []
    svcs = load_catalog(args.services, errors)
    incidents = load_incidents(args.incidents, svcs, errors)
    if errors:
        for e in errors:
            print("  " + e, file=sys.stderr)
        print(f"build_status.py: {len(errors)} problems in the records; nothing written", file=sys.stderr)
        sys.exit(1)
    if args.check:
        sys.exit(1 if check(svcs, incidents) else 0)
    build(svcs, incidents, args, today)


if __name__ == "__main__":
    try:
        main()
    except (RecordError, ValueError) as e:
        print(f"build_status.py: {e}", file=sys.stderr)
        sys.exit(2)
