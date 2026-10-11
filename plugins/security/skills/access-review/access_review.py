#!/usr/bin/env python3
"""Read-only access review of one GitHub repository.

Lists who can change the repository and how: admins, collaborators and outside collaborators, deploy
keys, rulesets with their bypass actors, classic branch protection, the token lists the caller can see,
and every push or merge that went past a rule in the review window (rule suites with result "bypass",
mapped to their pull requests). Without access to rule suites it falls back to merged pull requests
with fewer approvals than the rules require.

Only GET requests through `gh api`. It changes no setting.

Usage:
  access_review.py <owner/repo> [--days 30] [--observations-out FILE] [--json]
  access_review.py --from-observations FILE [--json]

Exit codes: 0 no red flag, 1 red flags, 3 the repository could not be read.
Standard library only, Python 3.9+.
"""
import argparse, datetime, json, subprocess, sys

STALE_KEY_DAYS = 90
PERIODS = ((1, "day"), (7, "week"), (31, "month"))


def gh(path):
    """(data, None) or (None, error text). GET only."""
    paged = "per_page=100" in path
    p = subprocess.run(["gh", "api", "--paginate", "--slurp", path] if paged else ["gh", "api", path], capture_output=True, text=True)
    if p.returncode != 0:
        msg = (p.stderr or p.stdout).strip()
        return None, msg.splitlines()[-1][:160] if msg else f"exit {p.returncode}"
    data = json.loads(p.stdout or "null")
    if paged and isinstance(data, list) and all(isinstance(page, list) for page in data):
        data = [x for page in data for x in page]  # --slurp wraps the pages in one array
    return data, None


def collect(slug, days):
    obs = {"repo": slug, "days": days, "errors": {}}

    def get(key, path, shape=lambda x: x):
        data, err = gh(path)
        if err:
            obs["errors"][key] = err
        else:
            obs[key] = shape(data)
        return data

    repo = get("meta", f"repos/{slug}", lambda r: {"owner_type": r["owner"]["type"], "default_branch": r["default_branch"],
                                                   "visibility": r.get("visibility")})
    if repo is None:
        return obs
    branch, owner = repo["default_branch"], slug.split("/")[0]
    get("collaborators", f"repos/{slug}/collaborators?affiliation=all&per_page=100",
        lambda xs: [{"login": x["login"], "role": x.get("role_name")} for x in xs])
    if repo["owner"]["type"] == "Organization":
        get("outside", f"repos/{slug}/collaborators?affiliation=outside&per_page=100", lambda xs: [x["login"] for x in xs])
        get("org_admins", f"orgs/{owner}/members?role=admin&per_page=100", lambda xs: [x["login"] for x in xs])
        get("fine_grained_tokens", f"orgs/{owner}/personal-access-tokens?per_page=100",
            lambda xs: [{"owner": x["owner"]["login"], "expires": x.get("token_expires_at"), "last_used": x.get("token_last_used_at")} for x in xs])
        get("credential_authorizations", f"orgs/{owner}/credential-authorizations?per_page=100",
            lambda xs: [{"login": x["login"], "type": x.get("credential_type"), "last_used": x.get("credential_accessed_at")} for x in xs])
    get("deploy_keys", f"repos/{slug}/keys?per_page=100",
        lambda xs: [{"title": x["title"], "read_only": x["read_only"], "created_at": x["created_at"], "last_used": x.get("last_used")} for x in xs])
    rulesets = []
    for r in get("rulesets_list", f"repos/{slug}/rulesets?includes_parents=true&per_page=100", lambda xs: [x["id"] for x in xs]) or []:
        d, err = gh(f"repos/{slug}/rulesets/{r['id']}")
        if d:
            pr = next((x.get("parameters") or {} for x in d.get("rules", []) if x["type"] == "pull_request"), None)
            rulesets.append({"id": d["id"], "name": d["name"], "enforcement": d["enforcement"], "source": d.get("source_type"),
                             "include": (d.get("conditions") or {}).get("ref_name", {}).get("include", []),
                             "rules": [x["type"] for x in d.get("rules", [])],
                             "required_approvals": (pr or {}).get("required_approving_review_count") if pr is not None else None,
                             "bypass_actors": d.get("bypass_actors") or []})
    obs["rulesets"] = rulesets
    prot, err = gh(f"repos/{slug}/branches/{branch}/protection")
    obs["classic_protection"] = ({"enforce_admins": (prot.get("enforce_admins") or {}).get("enabled"),
                                  "required_approvals": (prot.get("required_pull_request_reviews") or {}).get("required_approving_review_count")}
                                 if prot else None)
    if err and "not protected" not in err.lower():
        obs["errors"]["classic_protection"] = err
    period = next((name for limit, name in PERIODS if days <= limit), "month")
    suites, err = gh(f"repos/{slug}/rulesets/rule-suites?ref=refs/heads/{branch}&rule_suite_result=bypass&time_period={period}&per_page=100")
    if err:
        obs["errors"]["rule_suites"] = err
        obs["bypass_suites"] = None
        merged, err = gh(f"repos/{slug}/pulls?state=closed&base={branch}&sort=updated&direction=desc&per_page=30")
        obs["merged_prs"] = []
        for p in (merged or [])[:30]:
            if p.get("merged_at") and p["merged_at"][:10] >= (datetime.date.today() - datetime.timedelta(days=days)).isoformat():
                reviews, _ = gh(f"repos/{slug}/pulls/{p['number']}/reviews")
                approvers = {r["user"]["login"] for r in reviews or [] if r.get("state") == "APPROVED"}
                obs["merged_prs"].append({"number": p["number"], "merged_at": p["merged_at"], "author": p["user"]["login"],
                                          "approvals": len(approvers)})
    else:
        obs["bypass_suites"] = []
        for s in suites or []:
            d, _ = gh(f"repos/{slug}/rulesets/rule-suites/{s['id']}")
            failed = [{"rule": e["rule_type"], "details": e.get("details", "")} for e in (d or {}).get("rule_evaluations", [])
                      if e.get("result") == "fail"]
            prs, _ = gh(f"repos/{slug}/commits/{s['after_sha']}/pulls")
            obs["bypass_suites"].append({"id": s["id"], "actor": s.get("actor_name"), "at": s.get("pushed_at"),
                                         "after_sha": s["after_sha"], "failed": failed,
                                         "pulls": [p["number"] for p in prs or [] if p.get("merged_at")]})
    return obs


def assess(obs, today):
    """Flags as {level, id, evidence}; level red or amber."""
    f = []

    def flag(level, fid, evidence):
        f.append({"level": level, "id": fid, "evidence": evidence})

    rulesets = [r for r in obs.get("rulesets", []) if r["enforcement"] == "active"]
    classic = obs.get("classic_protection")
    if not rulesets and not classic and "classic_protection" not in obs.get("errors", {}):
        flag("red", "no-branch-rules", "no active ruleset and no branch protection on the default branch")
    required = max([r["required_approvals"] or 0 for r in rulesets] + [(classic or {}).get("required_approvals") or 0])
    for r in rulesets:
        for a in r["bypass_actors"]:
            if a.get("bypass_mode") == "always":
                who = f"{a.get('actor_type')} {a.get('actor_id')}"
                flag("amber", "bypass-always", f"ruleset {r['name']} ({r['id']}): {who} may bypass on every push and merge; "
                                               "bypass_mode pull_request limits it to pull requests, where the bypass shows")
    if classic and classic.get("enforce_admins") is False:
        flag("amber", "admins-not-enforced", "branch protection does not apply to admins")
    for s in obs.get("bypass_suites") or []:
        failed = "; ".join(x["details"] or x["rule"] for x in s["failed"]) or "a rule"
        if s["pulls"]:
            flag("red", "bypass-merge", f"pull request #{', #'.join(str(n) for n in s['pulls'])} merged past the rules ({failed}) "
                                        f"by {s['actor']} at {s['at']}, rule suite {s['id']}")
        else:
            flag("red", "bypass-push", f"push {s['after_sha'][:8]} past the rules ({failed}) by {s['actor']} at {s['at']}, "
                                       f"rule suite {s['id']}")
    if obs.get("bypass_suites") is None and required:
        for p in obs.get("merged_prs", []):
            if p["approvals"] < required:
                flag("red", "merged-below-approvals", f"pull request #{p['number']} merged {p['merged_at'][:10]} with "
                                                       f"{p['approvals']} of {required} required approvals")
    outside = set(obs.get("outside") or [])
    for c in obs.get("collaborators") or []:
        if c["login"] in outside and c["role"] in ("write", "maintain", "admin"):
            flag("amber", "outside-collaborator", f"{c['login']} is an outside collaborator with {c['role']} access")
    for k in obs.get("deploy_keys") or []:
        if not k["read_only"]:
            flag("amber", "deploy-key-write", f"deploy key {k['title']!r} can push")
        used = k.get("last_used")
        idle = (today - datetime.date.fromisoformat((used or k["created_at"])[:10])).days
        if idle > STALE_KEY_DAYS:
            flag("amber", "deploy-key-stale", f"deploy key {k['title']!r} {'last used' if used else 'never used, created'} "
                                              f"{(used or k['created_at'])[:10]}, {idle} days ago")
    admins = sorted({c["login"] for c in obs.get("collaborators") or [] if c["role"] == "admin"})
    return {"repo": obs["repo"], "admins": admins, "required_approvals": required, "flags": f,
            "not_visible": obs.get("errors", {})}


def main():
    ap = argparse.ArgumentParser(description="Read-only access review of a GitHub repository")
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--today", default=None)
    ap.add_argument("--observations-out", default=None)
    ap.add_argument("--from-observations", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.from_observations:
        with open(a.from_observations, encoding="utf-8") as fh:
            obs = json.load(fh)
    elif a.repo:
        obs = collect(a.repo, a.days)
        obs["today"] = datetime.date.today().isoformat()
        if "meta" not in obs:
            print(f"access_review: {obs['errors'].get('meta')}", file=sys.stderr)
            sys.exit(3)
    else:
        ap.error("give a repository or --from-observations")
    today = datetime.date.fromisoformat(a.today or obs.get("today") or datetime.date.today().isoformat())
    if a.observations_out:
        with open(a.observations_out, "w", encoding="utf-8") as fh:
            json.dump(obs, fh, indent=1)
    r = assess(obs, today)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        counts = {}
        for x in r["flags"]:
            counts[x["id"]] = counts.get(x["id"], 0) + 1
        print(f"{r['repo']}: admins: {', '.join(r['admins']) or 'none visible'}; required approvals: {r['required_approvals']}; "
              f"flags: {', '.join(f'{k} {v}' for k, v in counts.items()) or 'none'}")
        for x in r["flags"]:
            print(f"  {x['level']:5} {x['id']}: {x['evidence']}")
        for k, v in r["not_visible"].items():
            print(f"  not visible: {k}: {v}")
    sys.exit(1 if any(x["level"] == "red" for x in r["flags"]) else 0)


if __name__ == "__main__":
    main()
