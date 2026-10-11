"""Shared agent settings in the repository do not switch the stance filters off."""
import json

ID = "stance.shared-defaults"
DESCRIPTION = ("The agent settings checked into the repository keep the stance filters on: no shared file sets "
               "STANCE_RECEIPTS, GOOD_CHAD_DEFAULT_MODE or PROFESSIONAL_B2_DEFAULT_MODE to off, or disables all hooks. "
               "Personal settings files stay out of scope.")
DEFAULTS = {
    "files": [".claude/settings.json"],
    "env_off": {"STANCE_RECEIPTS": "off", "GOOD_CHAD_DEFAULT_MODE": "off", "PROFESSIONAL_B2_DEFAULT_MODE": "off"},
}


def check(ctx):
    present = [f for f in ctx.options["files"] if (ctx.root / f).is_file()]
    if not present:
        return {"result": "n/a", "detail": "no shared agent settings file: " + ", ".join(ctx.options["files"])}
    hits = []
    for rel in present:
        try:
            data = json.loads((ctx.root / rel).read_text(encoding="utf-8"))
        except ValueError as e:
            hits.append({"file": rel, "snippet": f"not valid JSON: {type(e).__name__}"})
            continue
        env = data.get("env") or {}
        for key, off in ctx.options["env_off"].items():
            if str(env.get(key, "")).strip().lower() == off:
                hits.append({"file": rel, "snippet": f"env {key}={off} switches a stance filter off for everyone"})
        if data.get("disableAllHooks") is True:
            hits.append({"file": rel, "snippet": "disableAllHooks is true; the stance hooks do not run"})
    return {"result": "fail" if hits else "pass",
            "detail": f"{len(present)} shared settings files checked, {len(hits)} problems",
            "hits": hits}
