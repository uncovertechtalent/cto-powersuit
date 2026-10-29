#!/usr/bin/env python3
"""Provenance check for a GitHub repository before you install an agent skill, an MCP server or a tool from it.

Reads public metadata with `gh api` (read only, nothing is downloaded or run) and grades it on two axes.
Source risk (low, medium, high) comes from the signals: owner against the owner the registry or the
vendor names, fork status, account and repository age, copied history, the share of recent commits that
touch only the README, README links to archives or executables, archives or executables committed to the tree
with little or no code beside them, and release assets. A release asset with a
build provenance attestation in the same repository (looked up by the asset's sha256 digest) does not count
as an unverified binary. Any red signal gives high, any amber signal medium, none low. Exposure (low,
medium, high) comes from --data-scope, what the tool will read once installed. Both go into the
recommendation.

Usage:
  provenance.py <owner/repo or URL> [--expected-owner NAME] [--data-scope SCOPE] [--commits 20]
                [--today YYYY-MM-DD] [--observations-out FILE] [--json]
  provenance.py --from-observations FILE [--data-scope SCOPE] [--json]

Data scope: none, repo (the working repository), home (files across the home folder), agent-data (agent
transcripts, settings or memory, such as ~/.claude/projects), secrets (credentials, tokens or keys), or
unknown (the default).

Exit codes: 0 low, 1 medium, 2 high source risk, 3 the metadata could not be read.
Standard library only, Python 3.9+.
"""
import argparse, collections, datetime, json, re, subprocess, sys, urllib.parse

TREE_DIRS = 10  # folder listings read after the top level of the tree; deeper folders are not read
THRESHOLDS = {
    "account_days": 90,       # an account younger than this is amber
    "repo_days": 30,          # a repository younger than this is amber
    "readme_only_red": 0.5,   # share of recent commits that touch only README files
    "readme_only_amber": 0.25,
    "readme_only_min": 3,     # fewer README-only commits than this never turn red
}
README = re.compile(r"(^|/)readme(\.[a-z0-9]+)?$", re.I)
LINK = re.compile(r"""(https?://[^\s)"'<>\]]+)|\]\(([^)\s]+)\)|href=["']([^"']+)["']""", re.I)
ARCHIVE = re.compile(r"\.(zip|rar|7z|tgz|tar\.gz|vsix|exe|msi|dmg|pkg|scr|bat|cmd|ps1|vbs|jar|apk)(\?[^\s)\"'<>]*)?$", re.I)
ASSET_DOWNLOAD = re.compile(r"/releases/(latest/)?download/", re.I)
BINARY_ASSET = re.compile(r"\.(zip|rar|7z|exe|msi|dmg|pkg|tar\.gz|tgz|tar\.xz|vsix|appimage|deb|rpm|jar)$", re.I)
EXPOSURE = {"none": "low", "repo": "medium", "home": "high", "agent-data": "high", "secrets": "high", "unknown": "unknown"}
SCOPE_TEXT = {"home": "files across the home folder", "agent-data": "agent transcripts, settings or memory",
              "secrets": "credentials, tokens or keys"}


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
    assets = [a for r in gh(f"repos/{slug}/releases?per_page=10") for a in r.get("assets", [])]
    seen = {}
    looked_up = [(a["name"], attested_in(slug, a.get("digest"), seen)) for a in assets if BINARY_ASSET.search(a["name"])]
    tree, unread = tree_of(slug)
    return {
        "repo": repo["full_name"], "owner": owner, "owner_type": repo["owner"]["type"],
        "created_at": repo["created_at"], "pushed_at": repo.get("pushed_at"), "archived": repo.get("archived", False),
        "fork": repo.get("fork", False), "parent": (repo.get("parent") or {}).get("full_name"),
        "default_branch": repo.get("default_branch"), "stars": repo.get("stargazers_count"),
        "account_created_at": account["created_at"], "commits": commits, "readme": readme,
        "release_assets": [a["name"] for a in assets], "attested_assets": [n for n, ok in looked_up if ok],
        "attestation_unknown": sum(ok is None for _, ok in looked_up),
        "tree": tree, "tree_unread": unread, "languages": gh(f"repos/{slug}/languages"),
    }


def tree_of(slug):
    """The files of the default branch with their sizes, from the contents listing: the top level, then folders breadth
    first up to TREE_DIRS listings. Returns the files and the number of folders left unread. An empty repository
    answers 404 and has no files. Lists names and sizes only; no file content is fetched."""
    files, queue, listed = [], [""], 0
    while queue and listed <= TREE_DIRS:
        path = queue.pop(0)
        try:
            entries = gh(f"repos/{slug}/contents/{urllib.parse.quote(path)}" if path else f"repos/{slug}/contents")
        except RuntimeError as e:
            if path or "404" not in str(e):
                raise
            entries = []
        listed += 1
        for e in entries:
            if e.get("type") == "dir":
                queue.append(e["path"])
            elif e.get("type") == "file":
                files.append({"path": e["path"], "size": e.get("size") or 0})
    return files, len(queue)


def size_text(n):
    return f"{n} bytes" if n < 1024 else f"{n / 1024:.0f} KB" if n < 1024 ** 2 else f"{n / 1024 ** 2:.1f} MB"


def attested_in(slug, digest, seen):
    """Whether the repository holds a build provenance attestation for this asset digest (sha256:<hex>):
    True, False (no digest, or the API answers 404), or None when the lookup failed for another reason."""
    if not digest or not digest.startswith("sha256:"):
        return False
    if digest not in seen:
        try:
            seen[digest] = bool(gh(f"repos/{slug}/attestations/{digest}").get("attestations"))
        except RuntimeError as e:
            seen[digest] = False if "404" in str(e) else None
    return seen[digest]


def days(since, today):
    return (today - datetime.date.fromisoformat(since[:10])).days


def assess(obs, today, t=THRESHOLDS):
    """Signals as (level, id, evidence), with level red or amber, the source risk, the exposure, and the recommendation."""
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
        s.append(("amber", "download-link", f"README links to {len(downloads)} archive or executable downloads: {', '.join(downloads[:3])}"))
        if any(i == "readme-only-commits" for _, i, _ in s):
            s.append(("red", "archive-lure", "README-only commits and an archive download link together: the FakeGit pattern"))
    langs = obs.get("languages")
    packed = sorted((f for f in obs.get("tree") or [] if ARCHIVE.search(f["path"])), key=lambda f: -(f.get("size") or 0))
    if packed and langs is not None:
        big, code = packed[0], sum(langs.values())
        if not langs or (big.get("size") or 0) > code:
            ev = (f"{big['path']} ({size_text(big.get('size') or 0)}"
                  + (f", the largest of {len(packed)} archives or executables" if len(packed) > 1 else "") + ") in the tree, "
                  + ("and GitHub finds no code in the repository" if not langs else
                     f"against {size_text(code)} of code ({', '.join(sorted(langs, key=langs.get, reverse=True)[:3])})"))
            if any(i == "readme-only-commits" for _, i, _ in s):
                s.append(("red", "archive-in-tree", ev + "; with README-only commits: the FakeGit pattern without a download link"))
            else:
                s.append(("amber", "archive-in-tree", ev))
    attested = obs.get("attested_assets", [])
    binaries = list((collections.Counter(a for a in obs.get("release_assets", []) if BINARY_ASSET.search(a))
                     - collections.Counter(attested)).elements())
    if binaries:
        unknown = obs.get("attestation_unknown", 0)
        s.append(("amber", "release-binaries", f"{len(binaries)} archive or binary release assets without a provenance attestation, "
                                               f"e.g. {', '.join(list(dict.fromkeys(binaries))[:3])}; verify checksums or signatures"
                                               + (f"; the attestation lookup failed for {unknown} of them (rate limit or network), "
                                                  "so run the check again later" if unknown else "")))
    if obs.get("archived"):
        s.append(("amber", "archived", "the repository is archived; it gets no fixes"))
    levels = {lvl for lvl, _, _ in s}
    risk = "high" if "red" in levels else "medium" if "amber" in levels else "low"
    scope = obs.get("data_scope") or "unknown"
    exposure = EXPOSURE.get(scope, "unknown")
    head = obs["commits"][0]["sha"] if obs.get("commits") else None
    archive = any(i in ("download-link", "release-binaries") for _, i, _ in s)
    advice = {
        "high": "Do not install from this source. Get it from the registry entry or the vendor's own repository.",
        "medium": "The user decides with these signals, and the reason goes into the provenance log.",
        "low": f"Install pinned to commit {head} or to an exact package version." if head else "Install pinned to an exact version.",
    }[risk]
    rec = [advice]
    if archive:
        rec.append("Prefer the marketplace or registry install, or a build from a pinned commit, over release archives: an archive "
                   "can be swapped in a fork, through a link in a comment, or in a compromised release. A marketplace install is no "
                   "guarantee either, so pin the version.")
    if risk != "high" and any(i == "archive-in-tree" for _, i, _ in s):
        rec.append("Install from a tagged release or a build from a pinned commit, never from an archive or executable in the tree: "
                   "what it holds shows in no diff and no code view. Ask the owner for the source tree.")
    if attested:
        rec.append(f"{len(attested)} release assets carry a build provenance attestation from this repository. Check a file "
                   f"before you use it: gh attestation verify <file> --repo {obs['repo']}")
    if exposure == "high":
        rec.append(f"Once installed it reads {SCOPE_TEXT[scope]}. Read the code that reads it before you install, and give it the narrowest "
                   "access you can.")
    elif exposure == "unknown":
        rec.append("Data scope unknown: find out from the code or the docs what it reads, then run again with --data-scope.")
    return {"repo": obs["repo"], "risk": risk, "exposure": exposure, "data_scope": scope, "pin": head,
            "signals": [{"level": lvl, "id": i, "evidence": e} for lvl, i, e in s], "recommendation": rec}


def main():
    ap = argparse.ArgumentParser(description="Provenance check before installing a skill or an MCP server")
    ap.add_argument("target", nargs="?")
    ap.add_argument("--expected-owner", default=None, help="the owner the registry entry or the vendor's own docs name")
    ap.add_argument("--data-scope", choices=sorted(EXPOSURE), default=None, help="what the tool reads once installed")
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
    if a.data_scope:
        obs["data_scope"] = a.data_scope
    if a.observations_out:
        with open(a.observations_out, "w", encoding="utf-8") as f:
            json.dump(obs, f, indent=1)
    r = assess(obs, today)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{r['repo']}: source risk {r['risk']}, exposure {r['exposure']} (data scope {r['data_scope']})"
              + (f", head {r['pin']}" if r["pin"] else ""))
        for sig in r["signals"]:
            print(f"  {sig['level']:5} {sig['id']}: {sig['evidence']}")
        for line in r["recommendation"]:
            print(f"  -> {line}")
    sys.exit({"low": 0, "medium": 1, "high": 2}[r["risk"]])


if __name__ == "__main__":
    main()
