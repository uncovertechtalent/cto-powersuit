#!/usr/bin/env python3
"""Check the release metadata: the suit version, the changelog and the plugin versions.

- metadata.version in the marketplace manifest and every plugin.json version read x.y.z;
- CHANGELOG.md starts with '## Unreleased', its release headings read '## [x.y.z] - YYYY-MM-DD', newest
  first, and the newest one equals metadata.version;
- metadata.version is not lower than the newest v* tag, and a commit that carries a v* tag carries
  that version in metadata.version;
- since the newest v* tag, every plugin whose shipped files changed has a higher version than at that
  tag. `claude plugin update` compares the plugin.json version only, so a change without a bump never
  reaches an installed plugin. Evals, tests, fixtures, recorded cases and the plugin README do not ship
  behaviour and do not need a bump.
Needs the git history and tags (actions/checkout with fetch-depth: 0). Without a v* tag the git
checks are skipped. Standard library only. Exit 0 when all hold.

Usage: python3 scripts/check_release.py [--repo <path>]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
HEADING = re.compile(r"^## (.+)$", re.M)
RELEASE = re.compile(r"^\[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$")
NO_BUMP_DIRS = {"evals", "tests", "fixtures", "cases"}
NO_BUMP_FILES = re.compile(r"^(test_.*\.py|README(_\w+)?\.md)$")


def key(v):
    return tuple(int(x) for x in v.split("."))


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def ships(rel_parts):
    """True when a path inside a plugin folder (parts after plugins/<name>/) changes what users install and run."""
    if any(part in NO_BUMP_DIRS for part in rel_parts[:-1]):
        return False
    if NO_BUMP_FILES.match(rel_parts[-1]) and (len(rel_parts) == 1 or rel_parts[-1].startswith("test_")):
        return False
    return True


def plugin_version(text):
    try:
        return json.loads(text).get("version")
    except (TypeError, ValueError):
        return None


def check(repo):
    problems, notes = [], []
    market = json.loads((repo / ".claude-plugin/marketplace.json").read_text())
    suit = (market.get("metadata") or {}).get("version")
    if not suit or not SEMVER.match(suit):
        problems.append(f"marketplace.json: metadata.version is {suit!r}, want x.y.z")
        suit = None
    plugins = {}
    for pj in sorted(repo.glob("plugins/*/.claude-plugin/plugin.json")):
        name = pj.parent.parent.name
        v = plugin_version(pj.read_text())
        if not v or not SEMVER.match(v):
            problems.append(f"plugins/{name}: version {v!r}, want x.y.z")
        else:
            plugins[name] = v

    cl = repo / "CHANGELOG.md"
    if not cl.is_file():
        problems.append("CHANGELOG.md: missing")
    else:
        heads = HEADING.findall(cl.read_text())
        if not heads or heads[0] != "Unreleased":
            problems.append("CHANGELOG.md: the first section is not '## Unreleased'")
        releases = []
        for h in heads[1:] if heads and heads[0] == "Unreleased" else heads:
            m = RELEASE.match(h)
            if not m:
                problems.append(f"CHANGELOG.md: heading {h!r}, want '[x.y.z] - YYYY-MM-DD'")
            else:
                releases.append(m.group(1))
        if any(key(a) <= key(b) for a, b in zip(releases, releases[1:])):
            problems.append(f"CHANGELOG.md: releases {releases} are not newest first")
        if suit and releases and releases[0] != suit:
            problems.append(f"CHANGELOG.md: newest release {releases[0]}, metadata.version {suit}")
        if suit and not releases:
            problems.append(f"CHANGELOG.md: no release heading for metadata.version {suit}")

    if git(repo, "rev-parse", "HEAD") is None:
        notes.append("not a git repository: tag and version-bump checks skipped")
        return problems, notes
    tags = [t for t in (git(repo, "tag", "--list", "v*") or "").split() if SEMVER.match(t[1:])]
    if not tags:
        notes.append("no v* tag yet: tag and version-bump checks skipped")
        return problems, notes
    last = max(tags, key=lambda t: key(t[1:]))
    if suit and key(suit) < key(last[1:]):
        problems.append(f"marketplace.json: metadata.version {suit} is lower than the newest tag {last}")
    for t in (git(repo, "tag", "--points-at", "HEAD") or "").split():
        if t in tags and suit and t[1:] != suit:
            problems.append(f"tag {t} points at HEAD, metadata.version is {suit}")
    changed = (git(repo, "diff", "--name-only", f"{last}..HEAD", "--", "plugins") or "").splitlines()
    touched = {}
    for path in changed:
        parts = Path(path).parts
        if len(parts) > 2 and ships(parts[2:]):
            touched.setdefault(parts[1], []).append(path)
    for name, paths in sorted(touched.items()):
        if name not in plugins:
            continue
        before = plugin_version(git(repo, "show", f"{last}:plugins/{name}/.claude-plugin/plugin.json"))
        if before is None or not SEMVER.match(before):
            continue  # a plugin added after the tag starts at any version
        if key(plugins[name]) <= key(before):
            problems.append(f"plugins/{name}: {len(paths)} shipped files changed since {last} "
                            f"(first: {paths[0]}), version still {plugins[name]}; bump it above {before}")
    notes.append(f"compared with {last}: {len(touched)} plugins changed")
    return problems, notes


def main():
    ap = argparse.ArgumentParser(description="Check the suit version, the changelog and the plugin versions")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    problems, notes = check(Path(args.repo))
    for n in notes:
        print(n)
    for p in problems:
        print("FAIL " + p)
    print(f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
