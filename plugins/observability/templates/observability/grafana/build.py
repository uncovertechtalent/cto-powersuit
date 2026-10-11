#!/usr/bin/env python3
"""Dashboards as code: build Grafana dashboard JSON from small JSON specs.

Standard library only, Python 3.9+. Paths default to the folders next to this file.

  python3 build.py                       build every specs/*.json into dashboards/<uid>.json
  python3 build.py --check               build in memory; exit 1 when a file in dashboards/ differs from its spec
  python3 build.py --diff EXPORT.json    compare a dashboard exported from the Grafana UI with the build of its spec;
                                         exit 1 when they differ
  python3 build.py --import EXPORT.json  write specs/<uid>.json from an exported dashboard, every panel as raw JSON
                                         (add --force to replace an existing spec)

Spec format: see specs/service-overview.json and the dashboards-as-code skill. Commit each spec together
with the dashboard JSON it builds, so both diffs are in one review. Never edit the files in dashboards/ by hand.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PANEL_TYPES = ("stat", "gauge", "timeseries", "table", "logs", "heatmap", "text", "raw")
DEFAULT_SIZE = {"stat": (6, 4), "gauge": (6, 4), "text": (24, 3)}  # (w, h); other types 12 x 8
DEFAULT_DATASOURCE = {"logs": "loki"}  # other types default to prometheus
UID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

# --diff reports leaves that only one side has when they sit under these paths.
DIFF_WATCH = ("type", "title", "description", "datasource", "targets", "transformations", "fieldConfig.overrides",
              "fieldConfig.defaults.unit", "fieldConfig.defaults.decimals", "fieldConfig.defaults.min",
              "fieldConfig.defaults.max", "fieldConfig.defaults.thresholds", "fieldConfig.defaults.mappings")
# Keys the Grafana UI adds or changes on its own; --diff skips them.
DIFF_IGNORE = {"id", "gridPos", "pluginVersion", "editorMode", "exemplar", "interval", "intervalFactor", "key", "range"}


class SpecError(Exception):
    pass


class Layout:
    """Places panels left to right on Grafana's 24-column grid."""

    def __init__(self):
        self.x = self.y = self.row_h = 0
        self.next_id = 1

    def place(self, panel, w, h):
        if self.x + w > 24:
            self.x, self.y, self.row_h = 0, self.y + self.row_h, 0
        panel["gridPos"] = {"x": self.x, "y": self.y, "w": w, "h": h}
        panel["id"] = self.next_id
        self.next_id += 1
        self.x += w
        self.row_h = max(self.row_h, h)
        return panel

    def row(self, title):
        self.x, self.y, self.row_h = 0, self.y + self.row_h, 0
        panel = self.place({"type": "row", "title": title, "collapsed": False, "panels": []}, 24, 1)
        self.x, self.y, self.row_h = 0, self.y + 1, 0
        return panel


def ds_ref(value):
    """A data source by provisioned uid ("prometheus", "loki") or as a full {"type", "uid"} object."""
    if isinstance(value, dict):
        return value
    return {"type": value, "uid": value}


def build_targets(p, ds, kind, where):
    items = p.get("targets")
    if items is None:
        if not p.get("expr"):
            raise SpecError(f"{where}: a {kind} panel needs expr or targets")
        items = [{"expr": p["expr"], "legend": p.get("legend", "")}]
    out = []
    for i, t in enumerate(items):
        if isinstance(t, str):
            t = {"expr": t}
        if not isinstance(t, dict) or not t.get("expr"):
            raise SpecError(f"{where}: target {i + 1} needs an expr")
        q = {"datasource": ds, "expr": t["expr"], "refId": chr(65 + i)}
        if t.get("legend"):
            q["legendFormat"] = t["legend"]
        if kind == "table" and ds.get("type") == "prometheus":
            q.update({"instant": True, "format": "table"})
        if kind == "heatmap":
            q.update({"format": "heatmap", "legendFormat": t.get("legend") or "{{le}}"})
        if kind in ("stat", "gauge") and ds.get("type") == "loki":
            q["queryType"] = "instant"
        out.append(q)
    return out


def build_panel(p, where):
    kind = p.get("type")
    if kind not in PANEL_TYPES:
        raise SpecError(f"{where}: unknown panel type {kind!r}; use one of {', '.join(PANEL_TYPES)}")
    if kind == "raw":
        panel = {k: v for k, v in (p.get("panel") or {}).items() if k not in ("id", "gridPos")}
        if not panel:
            raise SpecError(f"{where}: a raw panel needs a 'panel' object")
        return panel
    if not p.get("title"):
        raise SpecError(f"{where}: a panel needs a title")
    panel = {"type": kind, "title": p["title"], "description": p.get("description", "")}
    if kind == "text":
        panel["options"] = {"mode": "markdown", "content": p.get("content", "")}
        return panel

    ds = ds_ref(p.get("datasource", DEFAULT_DATASOURCE.get(kind, "prometheus")))
    panel["datasource"] = ds
    panel["targets"] = build_targets(p, ds, kind, where)
    defaults = {k: p[k] for k in ("unit", "decimals", "min", "max") if k in p}
    if "thresholds" in p:
        defaults["thresholds"] = {"mode": "absolute",
                                  "steps": [{"color": color, "value": value} for color, value in p["thresholds"]]}
    if kind == "timeseries":
        stack = bool(p.get("stack"))
        defaults["custom"] = {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 15 if stack else 0,
                              "showPoints": "never", "stacking": {"mode": "normal" if stack else "none"}}
        panel["options"] = {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max"]},
                            "tooltip": {"mode": "multi"}}
    elif kind == "stat":
        panel["options"] = {"reduceOptions": {"calcs": ["lastNotNull"]}, "graphMode": "area",
                            "colorMode": "value" if "thresholds" in p else "none"}
    elif kind == "gauge":
        panel["options"] = {"reduceOptions": {"calcs": ["lastNotNull"]}, "showThresholdMarkers": True}
    elif kind == "table":
        panel["options"] = {"showHeader": True}
    elif kind == "heatmap":
        panel["options"] = {"calculate": False, "yAxis": {"unit": p.get("unit", "s")}, "color": {"scheme": "Oranges"},
                            "cellGap": 1, "tooltip": {"show": True, "yHistogram": True}}
    elif kind == "logs":
        panel["options"] = {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending",
                            "enableLogDetails": True, "prettifyLogMessage": False}
    if kind != "logs":
        panel["fieldConfig"] = {"defaults": defaults, "overrides": []}
    return panel


def build_variable(v, where):
    if "raw" in v:
        return v["raw"]
    if not v.get("name") or not v.get("query"):
        raise SpecError(f"{where}: a variable needs name and query")
    include_all = v.get("include_all", True)
    var = {"name": v["name"], "label": v.get("label", v["name"]), "type": "query",
           "datasource": ds_ref(v.get("datasource", "prometheus")),
           "query": {"query": v["query"], "refId": v["name"]}, "definition": v["query"],
           "includeAll": include_all, "multi": v.get("multi", True), "refresh": 2, "sort": 1}
    if include_all:
        # ".+" also works in Loki, which rejects a selector that matches the empty string.
        var["allValue"] = v.get("all_value", ".+")
        var["current"] = {"text": "All", "value": "$__all"}
    return var


def build_dashboard(spec, where):
    uid, title = spec.get("uid", ""), spec.get("title", "")
    if not UID.match(uid):
        raise SpecError(f"{where}: uid must be 1 to 40 characters of a-z, A-Z, 0-9, _ and -")
    if not title:
        raise SpecError(f"{where}: the spec needs a title")
    layout, panels = Layout(), []
    rows = list(spec.get("rows", []))
    if spec.get("panels"):
        rows.insert(0, {"panels": spec["panels"]})
    for ri, row in enumerate(rows, 1):
        if row.get("title"):
            panels.append(layout.row(row["title"]))
        for pi, p in enumerate(row.get("panels", []), 1):
            at = f"{where}: row {ri}, panel {pi}"
            w0, h0 = DEFAULT_SIZE.get(p.get("type"), (12, 8))
            w, h = p.get("w", w0), p.get("h", h0)
            if not (isinstance(w, int) and 1 <= w <= 24 and isinstance(h, int) and h >= 1):
                raise SpecError(f"{at}: w must be 1 to 24 and h at least 1")
            panels.append(layout.place(build_panel(p, at), w, h))
    tags = list(spec.get("tags", ["observability"]))
    return {
        "uid": uid, "title": title, "description": spec.get("description", ""), "tags": tags,
        "timezone": "browser", "schemaVersion": 41, "version": 1, "editable": True,
        "refresh": spec.get("refresh", "30s"), "time": {"from": spec.get("time", "now-6h"), "to": "now"},
        "templating": {"list": [build_variable(v, f"{where}: variable {i}") for i, v in enumerate(spec.get("variables", []), 1)]},
        "panels": panels,
        "links": [{"type": "dashboards", "tags": tags[:1], "asDropdown": True, "title": "Dashboards"}] if tags else [],
    }


def render(dashboard):
    return json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n"


def load_specs(specs_dir):
    """(spec file, dashboard) for every specs/*.json; files starting with _ are skipped."""
    built, uids = [], {}
    for f in sorted(Path(specs_dir).glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            spec = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SpecError(f"{f.name}: not valid JSON: {e}")
        d = build_dashboard(spec, f.name)
        if d["uid"] in uids:
            raise SpecError(f"{f.name}: uid {d['uid']} is also used by {uids[d['uid']]}")
        uids[d["uid"]] = f.name
        built.append((f, d))
    return built


def read_export(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("dashboard", data)  # the API wraps the dashboard; the UI export does not


def flat_panels(panels):
    """Panels in grid order, with the panels of collapsed rows after their row."""
    out = []
    for p in sorted(panels, key=lambda p: (p.get("gridPos", {}).get("y", 0), p.get("gridPos", {}).get("x", 0))):
        out.append(p)
        if p.get("type") == "row":
            out.extend(sorted(p.get("panels") or [], key=lambda c: (c.get("gridPos", {}).get("y", 0), c.get("gridPos", {}).get("x", 0))))
    return out


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in DIFF_IGNORE:
                continue
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list) and obj:
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def watched(path):
    return any(path == w or path.startswith(w + ".") or path.startswith(w + "[") for w in DIFF_WATCH)


def diff_panel(name, built, exported):
    lines = []
    b = dict(leaves({k: v for k, v in built.items() if k != "panels"}))
    e = dict(leaves({k: v for k, v in exported.items() if k != "panels"}))
    for path in sorted(set(b) | set(e)):
        if path in b and path in e:
            if b[path] != e[path]:
                lines.append(f"  {name}: {path}: {json.dumps(b[path])} -> {json.dumps(e[path])}")
        elif watched(path):
            side = "only in the export" if path in e else "only in the spec"
            lines.append(f"  {name}: {path}: {side}: {json.dumps(e.get(path, b.get(path)))}")
    bw, ew = built.get("gridPos", {}), exported.get("gridPos", {})
    if (bw.get("w"), bw.get("h")) != (ew.get("w"), ew.get("h")):
        lines.append(f"  {name}: size w={bw.get('w')} h={bw.get('h')} -> w={ew.get('w')} h={ew.get('h')}")
    return lines


def diff(built, exported):
    lines = []
    for key in ("title", "description", "refresh", "tags"):
        if built.get(key) != exported.get(key):
            lines.append(f"  dashboard {key}: {json.dumps(built.get(key))} -> {json.dumps(exported.get(key))}")
    if built.get("time", {}).get("from") != exported.get("time", {}).get("from"):
        lines.append(f"  dashboard time: {built['time'].get('from')} -> {exported.get('time', {}).get('from')}")
    bv = {v.get("name"): v for v in built.get("templating", {}).get("list", [])}
    ev = {v.get("name"): v for v in exported.get("templating", {}).get("list", [])}
    for name in sorted(set(bv) | set(ev)):
        if name not in ev:
            lines.append(f"  variable {name}: only in the spec")
        elif name not in bv:
            lines.append(f"  variable {name}: only in the export")
        elif bv[name].get("definition") != ev[name].get("definition"):
            lines.append(f"  variable {name}: query {json.dumps(bv[name].get('definition'))} -> {json.dumps(ev[name].get('definition'))}")

    def by_title(panels):
        out = {}
        for p in flat_panels(panels):
            key = ("row " if p.get("type") == "row" else "panel ") + json.dumps(p.get("title", ""))
            n, k = 2, key
            while k in out:
                k, n = f"{key} ({n})", n + 1
            out[k] = p
        return out

    bp, ep = by_title(built.get("panels", [])), by_title(exported.get("panels", []))
    for name in bp:
        if name not in ep:
            lines.append(f"  {name}: only in the spec")
    for name in ep:
        if name not in bp:
            lines.append(f"  {name}: only in the export")
        else:
            lines.extend(diff_panel(name, bp[name], ep[name]))
    if [k for k in bp if k in ep] != [k for k in ep if k in bp]:
        lines.append("  panel order differs")
    return lines


def to_spec(exported):
    """A spec that rebuilds the exported dashboard: rows kept, every panel as raw JSON."""
    spec = {"uid": exported.get("uid", ""), "title": exported.get("title", ""),
            "description": exported.get("description", ""), "tags": exported.get("tags", []),
            "refresh": exported.get("refresh") or "30s", "time": exported.get("time", {}).get("from", "now-6h"),
            "variables": [{"raw": v} for v in exported.get("templating", {}).get("list", [])], "rows": []}
    row = {"panels": []}
    for p in flat_panels(exported.get("panels", [])):
        if p.get("type") == "row":
            if row["panels"] or row.get("title"):
                spec["rows"].append(row)
            row = {"title": p.get("title", ""), "panels": []}
            continue
        gp = p.get("gridPos", {})
        row["panels"].append({"type": "raw", "w": gp.get("w", 12), "h": gp.get("h", 8),
                              "panel": {k: v for k, v in p.items() if k not in ("id", "gridPos")}})
    if row["panels"] or row.get("title"):
        spec["rows"].append(row)
    return spec


def main():
    ap = argparse.ArgumentParser(description="Build Grafana dashboards from JSON specs.")
    ap.add_argument("--specs", default=str(HERE / "specs"), help="folder with the specs (default: specs/ next to this file)")
    ap.add_argument("--out", default=str(HERE / "dashboards"), help="folder for the dashboard JSON (default: dashboards/)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="write nothing; exit 1 when a dashboard file differs from its spec")
    mode.add_argument("--diff", metavar="EXPORT", help="compare a dashboard exported from Grafana with the build of its spec")
    mode.add_argument("--import", dest="import_", metavar="EXPORT", help="write a spec from a dashboard exported from Grafana")
    ap.add_argument("--force", action="store_true", help="with --import: replace an existing spec")
    args = ap.parse_args()
    specs, out = Path(args.specs), Path(args.out)

    if args.import_:
        exported = read_export(args.import_)
        spec = to_spec(exported)
        build_dashboard(spec, args.import_)  # fails early on a missing uid or title
        target = specs / f"{spec['uid']}.json"
        if target.exists() and not args.force:
            raise SpecError(f"{target} exists; check that git holds it, then rerun with --force")
        specs.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n = sum(len(r["panels"]) for r in spec["rows"])
        print(f"wrote {target} ({n} panels as raw JSON)")
        if "${DS_" in target.read_text(encoding="utf-8"):
            print("warning: the export names data sources as ${DS_...}; export without 'share externally', or set the uids by hand")
        return 0

    built = load_specs(specs)
    if args.diff:
        exported = read_export(args.diff)
        match = [d for _f, d in built if d["uid"] == exported.get("uid")]
        if not match:
            raise SpecError(f"no spec in {specs} has uid {exported.get('uid')!r}; use --import for a new dashboard")
        lines = diff(match[0], exported)
        print(f"{exported.get('uid')}: " + (f"{len(lines)} differences" if lines else "no differences"))
        for line in lines:
            print(line)
        return 1 if lines else 0

    changed = 0
    for f, d in built:
        path = out / f"{d['uid']}.json"
        text = render(d)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            ok = current == text
            changed += not ok
            print(f"{'ok  ' if ok else 'DIFF'} {path.name} from {f.name}" + ("" if ok else ": run build.py and commit the result"))
        else:
            out.mkdir(parents=True, exist_ok=True)
            if current != text:
                path.write_text(text, encoding="utf-8")
            print(f"{'wrote' if current != text else 'same '} {path.name} from {f.name} ({len(d['panels'])} panels)")
    known = {f"{d['uid']}.json" for _f, d in built}
    for extra in sorted(out.glob("*.json")) if out.is_dir() else []:
        if extra.name not in known:
            print(f"note: no spec builds {extra.name}; import it with --import, or delete it by hand if it is obsolete")
    if not built:
        print(f"no specs in {specs}")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SpecError as e:
        print(f"build.py: {e}", file=sys.stderr)
        sys.exit(2)
