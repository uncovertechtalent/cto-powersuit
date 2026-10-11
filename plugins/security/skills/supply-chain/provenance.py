#!/usr/bin/env python3
"""Provenance check for a GitHub repository before you install an agent skill or an MCP server from it.

Reads public metadata with `gh api` (read only, nothing is downloaded or run) and rates it:
owner against the owner the registry or the vendor names, fork status, account and repository age,
the share of recent commits that touch only the README, README links to archives or executables,
and release assets. Any red signal gives "stop", any amber signal "check", none "proceed".

Usage:
  provenance.py <owner/repo or URL> [--expected-owner NAME] [--commits 20] [--today YYYY-MM-DD]
                [--observations-out FILE] [--json]
  provenance.py --from-observations FILE [--json]

Exit codes: 0 proceed, 1 check, 2 stop, 3 the metadata could not be read.
Standard library only, Python 3.9+.
"""
import argparse, datetime, json, re, subprocess, sys

THRESHOLDS = {
    "account_days": 90,       # an account younger than this is amber
    "repo_days": 30,          # a repository younger than this is amber
    "readme_only_red": 0.5,   # share of recent commits that touch only README files
    "readme_only_amber": 0.25,
    "readme_only_min": 3,     # fewer README-only commits than this never turn red
}
README = re.compile(r"(^|/)readme(\.[a-z0-9]+)?$", re.I)
LINK = re.compile(r"""(https?://[^\s)"'<>\]]+)|\]\(([^)\s]+)\)|href=["']([^"']+)["']""", re.I)
ARCHIVE = re.compile(r"\.(zip|rar|7z|exe|msi|dmg|pkg|scr|bat|cmd|ps1|vbs|jar|apk)(\?[^\s)\"'<>]*)?$", re.I)
ASSET_DOWNLOAD = re.compile(r"/releases/(latest/)?download/", re.I)
BINARY_ASSET = re.compile(r"\.(zip|rar|7z|exe|msi|dmg|pkg|tar\.gz|tgz|tar\.xz|appimage|deb|rpm|jar)$", re.I)


def gh(path, raw=False):
    cmd = ["gh", "api", path]
    if raw:
        cmd += ["-H", "Accept: application/vnd.github.raw"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"gh api {path}: {(p.stderr or p.stdout).strip()[:200]}")
    return p.stdout if raw else json.loads(p.stdout)


def slug_of(target):
    m = re.search(r"(?:github\.com[:/])?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", target.strip())
    if not m:
        raise ValueError(f"not a GitHub repository: {target}")
    return f"{m.group(1)}/{m.group(2)}"


def collect(slug, n_commits):
    repo = gh(f"repos/{slug}")
    owner = repo["owner"]["login"]
    account = gh(f"users/{owner}")
    commits = []
    for c in gh(f"repos/{slug}/commits?per_page={n_commits}"):
        files = [f["filename"] for f in gh(f"repos/{slug}/commits/{c['sha']}").get("files", [])]
        commits.append({"sha": c["sha"], "date": c["commit"]["author"]["date"],
                        "subject": c["commit"]["message"].split("\n", 1)[0][:100], "files": files})
    try:
        readme = gh(f"repos/{slug}/readme", raw=True)
    except RuntimeError:
        readme = ""
    assets = [a["name"] for r in gh(f"repos/{slug}/releases?per_page=10") for a in r.get("assets", [])]
    return {
        "repo": repo["full_name"], "owner": owner, "owner_type": repo["owner"]["type"],
        "created_at": repo["created_at"], "pushed_at": repo.get("pushed_at"), "archived": repo.get("archived", False),
        "fork": repo.get("fork", False), "parent": (repo.get("parent") or {}).get("full_name"),
        "default_branch": repo.get("default_branch"), "stars": repo.get("stargazers_count"),
        "account_created_at": account["created_at"], "commits": commits, "readme": readme, "release_assets": assets,
    }


def days(since, today):
    return (today - datetime.date.fromisoformat(since[:10])).days


def assess(obs, today, t=THRESHOLDS):
    """Signals as (level, id, evidence), with level red or amber, and the verdict."""
    s = []
    exp = (obs.get("expected_owner") or "").strip().lower()
    owner = obs["owner"].lower()
    parent_owner = (obs.get("parent") or "").split("/")[0].lower()
    if not exp:
        s.append(("amber", "owner-unverified", "no owner from a registry entry or the vendor's own docs to compare with"))
    elif owner != exp:
        s.append(("red", "owner-mismatch", f"repository owner {obs['owner']}, the registry or vendor names {obs['expected_owner']}"))
    if obs.get("fork"):
        if exp and parent_owner == exp:
            s.append(("red", "fork-of-listed", f"a fork of {obs['parent']}; install from {obs['parent']}"))
        else:
            s.append(("amber", "fork", f"a fork of {obs.get('parent') or 'an unknown parent'}"))
    age = days(obs["account_created_at"], today)
    if age < t["account_days"]:
        s.append(("amber", "young-account", f"account {obs['owner']} is {age} days old"))
    age = days(obs["created_at"], today)
    if age < t["repo_days"]:
        s.append(("amber", "young-repo", f"repository is {age} days old"))
    dated = [c["date"][:10] for c in obs.get("commits", []) if c.get("date")]
    if dated and days(min(dated), datetime.date.fromisoformat(obs["created_at"][:10])) > t["repo_days"]:
        s.append(("amber", "imported-history", f"commits from {min(dated)} in a repository created {obs['created_at'][:10]}: "
                                               "history copied from another project, or a migration"))
    commits = [c for c in obs.get("commits", []) if c.get("files")]
    readme_only = [c for c in commits if all(README.search(f) for f in c["files"])]
    if commits:
        share = len(readme_only) / len(commits)
        ev = f"{len(readme_only)} of the last {len(commits)} commits touch only README files"
        if share >= t["readme_only_red"] and len(readme_only) >= t["readme_only_min"]:
            s.append(("red", "readme-only-commits", ev))
        elif share >= t["readme_only_amber"] and len(readme_only) >= 2:
            s.append(("amber", "readme-only-commits", ev))
    links = sorted({next(g for g in m.groups() if g) for m in LINK.finditer(obs.get("readme", ""))})
    downloads = [u for u in links if ARCHIVE.search(u) or ASSET_DOWNLOAD.search(u)]
    if downloads:
        s.append(("red", "download-link", f"README links to {len(downloads)} archive or executable downloads: {', '.join(downloads[:3])}"))
    binaries = [a for a in obs.get("release_assets", []) if BINARY_ASSET.search(a)]
    if binaries:
        s.append(("amber", "release-binaries", f"{len(binaries)} archive or binary release assets, e.g. {', '.join(binaries[:3])}; verify checksums or signatures"))
    if obs.get("archived"):
        s.append(("amber", "archived", "the repository is archived; it gets no fixes"))
    levels = {lvl for lvl, _, _ in s}
    verdict = "stop" if "red" in levels else "check" if "amber" in levels else "proceed"
    head = obs["commits"][0]["sha"] if obs.get("commits") else None
    return {"repo": obs["repo"], "verdict": verdict, "pin": head,
            "signals": [{"level": lvl, "id": i, "evidence": e} for lvl, i, e in s]}


def main():
    ap = argparse.ArgumentParser(description="Provenance check before installing a skill or an MCP server")
    ap.add_argument("target", nargs="?")
    ap.add_argument("--expected-owner", default=None, help="the owner the registry entry or the vendor's own docs name")
    ap.add_argument("--commits", type=int, default=20)
    ap.add_argument("--today", default=None)
    ap.add_argument("--observations-out", default=None)
    ap.add_argument("--from-observations", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    if a.from_observations:
        with open(a.from_observations, encoding="utf-8") as f:
            obs = json.load(f)
        if obs.get("today") and not a.today:
            today = datetime.date.fromisoformat(obs["today"])
    elif a.target:
        try:
            obs = collect(slug_of(a.target), a.commits)
        except (RuntimeError, ValueError, KeyError) as e:
            print(f"provenance: {e}", file=sys.stderr)
            sys.exit(3)
        obs["expected_owner"] = a.expected_owner
        obs["today"] = today.isoformat()
    else:
        ap.error("give a repository or --from-observations")
    if a.observations_out:
        with open(a.observations_out, "w", encoding="utf-8") as f:
            json.dump(obs, f, indent=1)
    r = assess(obs, today)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{r['repo']}: {r['verdict']}" + (f" (pin {r['pin']})" if r["pin"] else ""))
        for sig in r["signals"]:
            print(f"  {sig['level']:5} {sig['id']}: {sig['evidence']}")
    sys.exit({"proceed": 0, "check": 1, "stop": 2}[r["verdict"]])


if __name__ == "__main__":
    main()
