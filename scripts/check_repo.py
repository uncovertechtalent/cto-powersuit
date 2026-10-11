#!/usr/bin/env python3
"""Cross-check the marketplace, the plugins and both root READMEs.

- every plugin folder has a marketplace entry, and every entry's skills array matches its skills folders;
- every plugin has a table row and an install line in README.md and README_de.md;
- the code blocks of README.md and README_de.md are identical;
- every plugin README has exactly one line that starts with "Demo:";
- every SKILL.md (and the vestige output-filter template) ends with the overlay section;
- no __pycache__ folder sits in the tree.
Standard library only. Exit 0 when all hold.

Usage: python3 scripts/check_repo.py
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
OVERLAY = re.compile(r'\n## Overlay\n.*\[ -n "\$POWERSUIT_OVERLAY" \] && ls -1 "\$POWERSUIT_OVERLAY/([a-z-]+)" 2>/dev/null \|\| true\n', re.S)


def main():
    problems = []
    market = json.loads((REPO / ".claude-plugin/marketplace.json").read_text())
    entries = {p["name"]: p for p in market["plugins"]}
    folders = sorted(d.name for d in (REPO / "plugins").iterdir() if (d / ".claude-plugin/plugin.json").is_file())
    for name in folders:
        if name not in entries:
            problems.append(f"plugins/{name}: no marketplace entry")
            continue
        skills = sorted("./skills/" + s.name for s in (REPO / "plugins" / name / "skills").iterdir() if (s / "SKILL.md").is_file())
        if sorted(entries[name].get("skills", [])) != skills:
            problems.append(f"marketplace {name}: skills array {entries[name].get('skills')} differs from the folders {skills}")
    for name in entries:
        if name not in folders:
            problems.append(f"marketplace {name}: no plugin folder")
    readmes = {f: (REPO / f).read_text() for f in ("README.md", "README_de.md")}
    for f, text in readmes.items():
        for name in entries:
            if not re.search(rf"^\| `{re.escape(name)}` \|", text, re.M):
                problems.append(f"{f}: no table row for {name}")
            if not re.search(rf"^claude plugin install {re.escape(name)}@cto-powersuit$", text, re.M):
                problems.append(f"{f}: no install line for {name}")
    blocks = {f: re.findall(r"```.*?```", t, re.S) for f, t in readmes.items()}
    if blocks["README.md"] != blocks["README_de.md"]:
        problems.append("README.md and README_de.md: code blocks differ")
    for name in folders:
        rd = REPO / "plugins" / name / "README.md"
        n = len(re.findall(r"^Demo:", rd.read_text(), re.M)) if rd.is_file() else 0
        if n != 1:
            problems.append(f"plugins/{name}/README.md: {n} demo lines, want 1")
    skill_files = sorted(REPO.glob("plugins/*/skills/*/SKILL.md")) + [REPO / "plugins/vestige/templates/output-filter/SKILL.md"]
    for f in skill_files:
        m = OVERLAY.search(f.read_text())
        module = f.relative_to(REPO).parts[1]
        if not m:
            problems.append(f"{f.relative_to(REPO)}: overlay section missing or outdated")
        elif m.group(1) != module:
            problems.append(f"{f.relative_to(REPO)}: overlay names module {m.group(1)}, want {module}")
    caches = [str(p.relative_to(REPO)) for p in REPO.rglob("__pycache__") if ".git" not in p.parts]
    problems += [f"{c}: remove it" for c in caches]
    print(f"{len(folders)} plugins, {sum(len(e.get('skills', [])) for e in entries.values())} skills, {len(skill_files)} skill files checked")
    for p in problems:
        print("FAIL " + p)
    print(f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
