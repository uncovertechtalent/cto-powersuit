#!/usr/bin/env python3
"""Tests for scripts/check_release.py.

Each case builds a small marketplace repository in a temporary folder, tags a release, changes it,
runs the check as a subprocess and compares the exit code and one line of its output. Standard library only, Python 3.9+.

Usage: python3 scripts/test_release.py [-v]
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
CHECK = Path(__file__).resolve().parent / "check_release.py"
VERBOSE = "-v" in sys.argv
CHANGELOG = "# Changelog\n\n## Unreleased\n\n{releases}"


def git(root, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                   cwd=root, env=env, check=True, capture_output=True)


class Repo:
    def __init__(self, root, suit="0.1.0", plugins=None, releases=("0.1.0",)):
        self.root = Path(root)
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "m", "metadata": {"version": suit}, "plugins": []}))
        for name, v in (plugins or {"a": "0.1.0", "b": "0.1.0"}).items():
            self.version(name, v)
            self.write(f"plugins/{name}/skills/s/SKILL.md", "---\nname: s\n---\n")
        self.changelog(*releases)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def version(self, name, v):
        self.write(f"plugins/{name}/.claude-plugin/plugin.json", json.dumps({"name": name, "version": v}))

    def suit(self, v):
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "m", "metadata": {"version": v}, "plugins": []}))

    def changelog(self, *releases):
        self.write("CHANGELOG.md", CHANGELOG.format(releases="".join(f"## [{r}] - 2026-10-12\n\n- x\n\n" for r in releases)))

    def commit(self, tag=None):
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "c")
        if tag:
            git(self.root, "tag", tag)

    def run(self):
        p = subprocess.run([sys.executable, str(CHECK), "--repo", str(self.root)], capture_output=True, text=True)
        return p.returncode, p.stdout


def case_no_tag(r):
    r.commit()


def case_unchanged(r):
    r.commit("v0.1.0")


def case_changed_no_bump(r):
    r.commit("v0.1.0")
    r.write("plugins/a/skills/s/SKILL.md", "---\nname: s\n---\nnew step\n")
    r.commit()


def case_changed_with_bump(r):
    r.commit("v0.1.0")
    r.write("plugins/a/skills/s/SKILL.md", "---\nname: s\n---\nnew step\n")
    r.version("a", "0.1.1")
    r.commit()


def case_new_skill_no_bump(r):
    r.commit("v0.1.0")
    r.write("plugins/b/skills/t/SKILL.md", "---\nname: t\n---\n")
    r.commit()


def case_dev_files_only(r):
    r.commit("v0.1.0")
    r.write("plugins/a/evals/c1/prompt.md", "x")
    r.write("plugins/a/tests/test_x.py", "x")
    r.write("plugins/a/checks/fixtures/pass/f.txt", "x")
    r.write("plugins/a/skills/s/cases/one.json", "{}")
    r.write("plugins/a/skills/s/test_probe.py", "x")
    r.write("plugins/a/README.md", "x")
    r.commit()


def case_skill_readme_ships(r):
    r.commit("v0.1.0")
    r.write("plugins/a/skills/s/README.md", "x")
    r.commit()


def case_version_lowered(r):
    r.commit("v0.1.0")
    r.write("plugins/a/skills/s/SKILL.md", "changed")
    r.version("a", "0.0.9")
    r.commit()


def case_new_plugin_after_tag(r):
    r.commit("v0.1.0")
    r.version("c", "0.1.0")
    r.write("plugins/c/skills/s/SKILL.md", "x")
    r.commit()


def case_changelog_mismatch(r):
    r.suit("0.2.0")
    r.commit()


def case_no_metadata_version(r):
    r.write(".claude-plugin/marketplace.json", json.dumps({"name": "m", "plugins": []}))
    r.commit()


def case_bad_plugin_version(r):
    r.version("a", "1.0")
    r.commit()


def case_no_unreleased(r):
    r.write("CHANGELOG.md", "# Changelog\n\n## [0.1.0] - 2026-10-12\n")
    r.commit()


def case_bad_heading(r):
    r.write("CHANGELOG.md", CHANGELOG.format(releases="## [0.1.0] - 2026-10-12\n\n## 0.0.9 (1 October)\n"))
    r.commit()


def case_releases_out_of_order(r):
    r.changelog("0.1.0", "0.2.0")
    r.commit()


def case_suit_below_tag(r):
    r.commit("v0.2.0")
    r.write("plugins/a/README.md", "x")
    r.commit()


def case_tag_on_wrong_version(r):
    r.suit("0.3.0")
    r.changelog("0.3.0", "0.1.0")
    r.commit("v0.2.0")


def case_next_release(r):
    r.commit("v0.1.0")
    r.write("plugins/a/skills/s/SKILL.md", "changed")
    r.version("a", "0.2.0")
    r.suit("0.2.0")
    r.changelog("0.2.0", "0.1.0")
    r.commit("v0.2.0")



def case_tags_sort_by_number(r):
    r.suit("0.9.0")
    r.changelog("0.9.0")
    r.commit("v0.9.0")
    r.suit("0.10.0")
    r.changelog("0.10.0", "0.9.0")
    r.commit("v0.10.0")


CASES = [  # (case, want exit code, text the output must contain)
    (case_no_tag, 0, "no v* tag yet"),
    (case_unchanged, 0, "compared with v0.1.0: 0 plugins changed"),
    (case_changed_no_bump, 1, "FAIL plugins/a: 1 shipped files changed since v0.1.0"),
    (case_changed_with_bump, 0, "compared with v0.1.0: 1 plugins changed"),
    (case_new_skill_no_bump, 1, "FAIL plugins/b: 1 shipped files changed"),
    (case_dev_files_only, 0, "compared with v0.1.0: 0 plugins changed"),
    (case_skill_readme_ships, 1, "FAIL plugins/a: 1 shipped files changed"),
    (case_version_lowered, 1, "version still 0.0.9; bump it above 0.1.0"),
    (case_new_plugin_after_tag, 0, "compared with v0.1.0: 1 plugins changed"),
    (case_changelog_mismatch, 1, "FAIL CHANGELOG.md: newest release 0.1.0, metadata.version 0.2.0"),
    (case_no_metadata_version, 1, "FAIL marketplace.json: metadata.version is None"),
    (case_bad_plugin_version, 1, "FAIL plugins/a: version '1.0'"),
    (case_no_unreleased, 1, "FAIL CHANGELOG.md: the first section is not '## Unreleased'"),
    (case_bad_heading, 1, "FAIL CHANGELOG.md: heading '0.0.9 (1 October)'"),
    (case_releases_out_of_order, 1, "are not newest first"),
    (case_suit_below_tag, 1, "is lower than the newest tag v0.2.0"),
    (case_tag_on_wrong_version, 1, "FAIL tag v0.2.0 points at HEAD, metadata.version is 0.3.0"),
    (case_next_release, 0, "0 problems"),
    (case_tags_sort_by_number, 0, "compared with v0.10.0"),
]


def main():
    failures = 0
    for case, want, text in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            case(r)
            got, out = r.run()
        ok = got == want and text in out
        failures += not ok
        if VERBOSE or not ok:
            print(f"{'ok  ' if ok else 'FAIL'} {case.__name__}: exit {got}, want {want}")
            if not ok or VERBOSE:
                print("     " + out.strip().replace("\n", "\n     "))
    print(f"{len(CASES)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
