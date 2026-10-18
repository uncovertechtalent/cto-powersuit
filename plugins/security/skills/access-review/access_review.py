#!/usr/bin/env python3
"""Read-only access review of one GitHub repository.

Lists who can change the repository and how: admins, collaborators and outside collaborators, deploy
keys, rulesets with their bypass actors, classic branch protection, the token lists the caller can see,
and every push or merge that went past a rule in the review window (rule suites with result "bypass",
mapped to their pull requests). Without access to rule suites it falls back to merged pull requests
with fewer approvals than the rules require. For an organisation it also reads whether two-factor
authentication is required and which members and outside collaborators have it off, when the caller is
an organisation owner, and says what it could not read.

Only GET requests through `gh api`. It changes no setting.

Usage:
  access_review.py <owner/repo> [--days 30] [--observations-out FILE] [--json]
  access_review.py --from-observations FILE [--json]

Exit codes: 0 no red flag, 1 red flags, 3 the repository could not be read.
Standard library only, Python 3.9+.
"""
import argparse, datetime, json, subprocess, sys

STALE_KEY_DAYS = 90
LOGIN_LIST = 10   # logins named in one flag; the rest is a count
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
        collect_two_factor(obs, owner)
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


def collect_two_factor(obs, owner):
    """obs["org_2fa"] from the organisation and the three 2FA filters, or an entry in obs["errors"]["org_2fa"].
    The filter 2fa_disabled works for organisation owners only, so its answer also tells whether the
    two_factor_requirement_enabled field of the organisation can be trusted: GitHub documents the field for the
    full organisation record, which only owners get (a classic token also needs the admin:org scope), and says
    nothing about its value for anyone else."""
    org, org_err = gh(f"orgs/{owner}")
    off, off_err = gh(f"orgs/{owner}/members?filter=2fa_disabled&per_page=100")
    required = (org or {}).get("two_factor_requirement_enabled") if isinstance(org, dict) else None
    if off_err or not isinstance(required, bool):
        obs["errors"]["org_2fa"] = off_err or org_err or "the organisation record has no two_factor_requirement_enabled (organisation owners only; a classic token needs the admin:org scope)"
        return
    insecure, insecure_err = gh(f"orgs/{owner}/members?filter=2fa_insecure&per_page=100")
    outside, outside_err = gh(f"orgs/{owner}/outside_collaborators?filter=2fa_disabled&per_page=100")
    logins = lambda xs: None if xs is None else [x["login"] for x in xs]
    obs["org_2fa"] = {"required": required, "members_off": logins(off), "members_insecure": logins(insecure),
                      "outside_off": logins(outside)}
    for key, err in (("org_2fa_insecure", insecure_err), ("org_2fa_outside", outside_err)):
        if err:
            obs["errors"][key] = err


def named(logins):
    return ", ".join(logins[:LOGIN_LIST]) + (f" and {len(logins) - LOGIN_LIST} more" if len(logins) > LOGIN_LIST else "")


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
    tf = obs.get("org_2fa")
    if tf:
        org_admins = set(obs.get("org_admins") or []) | set(admins)
        if not tf["required"]:
            flag("red", "org-2fa-not-required", f"organisation {obs['repo'].split('/')[0]} does not require two-factor authentication "
                                                "(with Enterprise Managed Users the identity provider handles it: check its policy)")
        off = tf.get("members_off") or []
        admin_off, other_off = sorted(x for x in off if x in org_admins), sorted(x for x in off if x not in org_admins)
        if admin_off:
            flag("red", "member-2fa-off", f"{len(admin_off)} admin(s) without two-factor authentication: {named(admin_off)}")
        if other_off:
            flag("amber", "member-2fa-off", f"{len(other_off)} member(s) without two-factor authentication: {named(other_off)}")
        if tf.get("members_insecure"):
            flag("amber", "member-2fa-insecure", f"{len(tf['members_insecure'])} member(s) whose second factor GitHub lists as insecure: "
                                                 f"{named(sorted(tf['members_insecure']))}")
        if tf.get("outside_off"):
            flag("amber", "outside-2fa-off", f"{len(tf['outside_off'])} outside collaborator(s) without two-factor authentication: "
                                             f"{named(sorted(tf['outside_off']))}")
    elif "org_2fa" in obs.get("errors", {}):
        flag("amber", "org-2fa-not-read", "the organisation's two-factor setting could not be read, so this review does not cover it: "
                                          "run it as an organisation owner (a classic token also needs the admin:org scope)")
    return {"repo": obs["repo"], "admins": admins, "required_approvals": required, "flags": f,
            "mfa": mfa_summary(obs), "not_visible": obs.get("errors", {})}


def mfa_summary(obs):
    """One line for the MFA section: what was read, or why it was not."""
    tf = obs.get("org_2fa")
    if tf:
        count = lambda xs: "not read" if xs is None else str(len(xs))
        return (f"organisation requires two-factor authentication: {'yes' if tf['required'] else 'no'}; members with it off: "
                f"{count(tf.get('members_off'))}; insecure second factor: {count(tf.get('members_insecure'))}; "
                f"outside collaborators with it off: {count(tf.get('outside_off'))}")
    if "org_2fa" in obs.get("errors", {}):
        return "not read (the caller must be an organisation owner, with the admin:org scope on a classic token); see not visible below"
    if (obs.get("meta") or {}).get("owner_type") == "User":
        return "not applicable: the owner is a user account; two-factor authentication is a setting of each account and GitHub does not show it to others"
    return "not read in this observation file"


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
        print(f"  mfa: {r['mfa']}")
        for x in r["flags"]:
            print(f"  {x['level']:5} {x['id']}: {x['evidence']}")
        for k, v in r["not_visible"].items():
            print(f"  not visible: {k}: {v}")
    sys.exit(1 if any(x["level"] == "red" for x in r["flags"]) else 0)


if __name__ == "__main__":
    main()
