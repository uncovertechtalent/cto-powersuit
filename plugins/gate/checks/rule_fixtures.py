"""Every blocking rule has fixture trees it passes and fails, and a recorded false-positive test."""
import json

ID = "gate.rule-fixtures"
DESCRIPTION = ("Every rule in the checked tiers passes its pass fixture, fails its fail fixture "
               "and has a recorded false-positive test in gate.json.")
DEFAULTS = {"config": "gate/gate.json", "tiers": ["block"], "require_fp_test": True}


def check(ctx):
    cfg_rel = ctx.options["config"]
    cfg_path = ctx.root / cfg_rel
    if not cfg_path.exists():
        return {"result": "n/a", "detail": f"no gate config at {cfg_rel}"}
    cfg = json.loads(cfg_path.read_text())
    rules = ctx.load_rules(ctx.root / cfg.get("rules_dir", ".github/actions/gate/rules"))
    fx_rel = cfg.get("fixtures_dir", "gate/fixtures")
    hits, clean, checked = [], [], 0
    for rid, rc in cfg.get("rules", {}).items():
        if rid == ID or rc.get("tier", "block") not in ctx.options["tiers"]:
            continue
        checked += 1
        before = len(hits)
        if rid not in rules:
            hits.append({"file": cfg_rel, "snippet": f"{rid}: enabled, but no rule file defines it"})
            continue
        if ctx.options["require_fp_test"]:
            t = rc.get("false_positive_test") or {}
            if not (t.get("date") and "hits" in t and "legitimate" in t):
                hits.append({"file": cfg_rel, "snippet": f"{rid}: no recorded false-positive test (date, hits, legitimate)"})
        for kind in ("pass", "fail"):
            d = ctx.root / fx_rel / rid / kind
            where = f"{fx_rel}/{rid}/{kind}"
            if not d.is_dir():
                hits.append({"file": where, "snippet": f"{rid}: no {kind} fixture"})
                continue
            res = ctx.run_rule(rules[rid], d, rc.get("options"))
            if kind == "pass" and res["result"] == "fail":
                hits.append({"file": where, "snippet": f"{rid}: fails its pass fixture"})
            if kind == "fail" and res["result"] != "fail":
                hits.append({"file": where, "snippet": f"{rid}: does not fail its fail fixture (result {res['result']})"})
        if len(hits) == before:
            clean.append(rid)
    if not checked:
        return {"result": "n/a", "detail": f"no rule in tiers {', '.join(ctx.options['tiers'])} besides this one"}
    return {"result": "fail" if hits else "pass",
            "detail": f"{checked} rules in tiers {', '.join(ctx.options['tiers'])}: {len(clean)} with working fixtures and a false-positive test, {checked - len(clean)} without",
            "evidence": [f"ok: {r}" for r in clean], "hits": hits}
