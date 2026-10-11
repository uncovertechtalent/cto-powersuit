#!/usr/bin/env python3
"""Read-only probes for /sdlc:sdlc-audit. Standard library only, Python 3.9+.

Two layers, so the decision rules can be tested on recorded input:
- collect(repo, args) runs read-only commands and reads tracked files, and returns observations;
- classify(observations, purpose) applies the rules and returns a state per stage with its evidence.

Usage:
  python3 probe.py [<repo>] [--purpose users|grader|nothing] [--author <pattern>] [--own <owner,...>]
                   [--no-gh] [--observations-out <file>] [--from-observations <file>]
Prints JSON. Changes nothing in the repository.
"""
import argparse, json, re, subprocess, sys, sysconfig
from pathlib import Path

BOTS = re.compile(r"\[bot\]|^gate-bot$|^conformity-bot$|^dependabot|^renovate|^github-actions", re.I)
TICKET = re.compile(r"#\d+|\b[A-Z][A-Z0-9]+-\d+\b|\b(?:ADR|RFC)-\d{1,4}\b", re.I)
PR_SUBJECT = re.compile(r"^Merge pull request #\d+|\(#\d+\)\s*$")
MANIFESTS = {"package.json": "npm", "pyproject.toml": "python", "requirements.txt": "python", "Pipfile": "python",
             "setup.py": "python", "setup.cfg": "python", "go.mod": "go", "Cargo.toml": "rust", "Gemfile": "ruby",
             "composer.json": "php", "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "java"}
LOCKS = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "poetry.lock", "uv.lock", "Pipfile.lock",
         "go.sum", "Cargo.lock", "Gemfile.lock", "composer.lock", "gradle.lockfile"}
DEPLOY = {  # keyword in a workflow or config -> deploy mechanism
    "actions/deploy-pages": "GitHub Pages", "pages-artifact": "GitHub Pages", "vercel": "Vercel", "netlify": "Netlify",
    "flyctl": "Fly.io", "fly deploy": "Fly.io", "kubectl": "Kubernetes", "helm upgrade": "Kubernetes",
    "terraform apply": "Terraform", "docker push": "container registry", "aws s3 sync": "S3", "cloudfront": "CloudFront",
    "gcloud run deploy": "Cloud Run", "heroku": "Heroku", "eb deploy": "Elastic Beanstalk", "serverless deploy": "Serverless",
    "rsync": "rsync to a host", "scp ": "copy to a host", "ssh ": "remote host",
}
DEPLOY_FILES = {"vercel.json": "Vercel", "netlify.toml": "Netlify", "fly.toml": "Fly.io", "app.yaml": "App Engine",
                "Procfile": "Heroku", "serverless.yml": "Serverless"}
SECRET = r"(\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-[A-Za-z0-9]{32,}|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
TEST_DIRS = {"test", "tests", "__tests__", "spec", "e2e", "eval", "evaluation", "evals", "bench", "benchmarks", "checks", "fixtures"}
TEST_FILE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.(py|go)|[^/]+\.(test|spec)\.[jt]sx?|[^/]+Test\.java)$")
VERIFY_DEF = re.compile(r"^\s*def (score|verify|evaluate|check)\w*\(", re.M)
TEST_RUNNERS = re.compile(r"pytest|unittest|npm (run )?test|yarn test|pnpm test|go test|cargo test|make (test|check)|mvn test|gradle test|rspec|phpunit|tox|nox")
PROTOCOL = re.compile(r"push(es|ed)? (directly )?to main|trunk[- ]based|commit(s)? (directly )?to main", re.I)
ROLLBACK = re.compile(r"\broll ?back\b|\brevert\b", re.I)
OBSERVE = re.compile(r"(^|/)(prometheus|grafana|alloy|otel|opentelemetry|sentry|datadog|loki)[^/]*(/|$)|\.alloy$|sentry|opentelemetry", re.I)
HYGIENE = re.compile(r"(^|/)__pycache__/|\.pyc$|\.zip$|(^|/)node_modules/|\.DS_Store$")
NOT_OWN = {"templates", "template", "fixtures", "examples", "example", "testdata", "vendor", "third_party", "node_modules"}
STAGES = ["request", "decision", "build", "review", "test", "gate", "release_record", "rollback", "observe", "incident",
          "docs", "dependencies", "secrets", "hygiene"]
OUT_OF_SCOPE = {"grader": {"gate", "release_record", "rollback", "observe", "incident"},
                "nothing": {"gate", "release_record", "rollback", "observe", "incident"}}


# ---------- collect ----------
def run(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def py_imports(text):
    mods = set()
    for m in re.finditer(r"^\s*(?:from\s+([A-Za-z_][\w]*)[\w.]*\s+import|import\s+([A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w.]*)*))", text, re.M):
        if m.group(1):
            mods.add(m.group(1))
        else:
            mods.update(x.strip().split(".")[0] for x in m.group(2).split(","))
    return mods


def js_imports(text):
    mods = set()
    for m in re.finditer(r"(?:require\(\s*|from\s+|import\s+)['\"]([^'\"./][^'\"]*)['\"]", text):
        name = m.group(1)
        mods.add("/".join(name.split("/")[:2]) if name.startswith("@") else name.split("/")[0])
    return mods


def pinned_installs(text):
    """Packages a file pins in an install line of its own, such as 'npm install x@1.2.3' or 'pip install x==1.2'."""
    names = set(re.findall(r"npm (?:install|i) (?:-[-\w]+ )*(@?[\w./-]+?)@\d", text))
    names |= set(re.findall(r"pip3? install (?:-[-\w]+ )*([\w.-]+)==\d", text))
    return sorted(names)


def collect(repo, args):
    obs = {"repo": str(repo)}
    rc, out = run(["git", "ls-files"], repo)
    files = out.splitlines() if rc == 0 else []
    obs["files"] = files
    texts = {}
    for f in files:
        p = repo / f
        low = f.lower()
        want = (low.startswith(".github/workflows/") or Path(f).name in MANIFESTS or Path(f).name in LOCKS
                or low.endswith(".md") or low in {"makefile", "procfile"} or Path(f).name in DEPLOY_FILES)
        if want and p.is_file() and p.stat().st_size < 400_000:
            texts[f] = p.read_text(encoding="utf-8", errors="replace")
    obs["texts"] = texts
    by_file, inline, verify = {}, [], []
    for f in files:
        p = repo / f
        if not p.is_file() or p.stat().st_size > 400_000:
            continue
        if f.endswith(".py"):
            t = p.read_text(encoding="utf-8", errors="replace")
            by_file[f] = {"python": sorted(py_imports(t)), "pinned": pinned_installs(t)}
            if re.search(r"^# /// script\s*$", t, re.M):
                inline.append(f)
            if VERIFY_DEF.search(t):
                verify.append(f)
        elif re.search(r"\.(m?[jt]sx?|cjs)$", f):
            t = p.read_text(encoding="utf-8", errors="replace")
            by_file[f] = {"js": sorted(js_imports(t)), "pinned": pinned_installs(t)}
    obs["imports_by_file"] = by_file
    obs["inline_manifests"] = inline  # PEP 723 inline script metadata
    obs["verify_defs"] = verify
    local = set()
    for f in files:
        first = Path(f).parts[0]
        local.add(first[:-3] if first.endswith(".py") else first)
        if f.endswith(".py"):
            local.add(Path(f).stem)
    obs["local_modules"] = sorted(local)
    # remote and GitHub scope
    rc, url = run(["git", "remote", "get-url", "origin"], repo)
    obs["remote_url"] = url if rc == 0 else None
    own = [x for x in (args.own or "").split(",") if x]
    gh_ok = not args.no_gh and run(["gh", "--version"], repo)[0] == 0
    if gh_ok and not own:
        rc, login = run(["gh", "api", "user", "--jq", ".login"], repo)
        if rc == 0:
            own.append(login.strip())
            rc, orgs = run(["gh", "api", "user/orgs", "--jq", ".[].login"], repo)
            own += orgs.split() if rc == 0 else []
        else:
            gh_ok = False
    obs["gh_available"], obs["own_owners"] = gh_ok, own
    slug = github_slug(obs["remote_url"])
    obs["branch_protection"] = obs["failed_runs"] = obs["issues"] = None
    if gh_ok and slug and slug.split("/")[0].lower() in {o.lower() for o in own}:
        rc, out = run(["gh", "api", f"repos/{slug}/branches/{default_branch(repo)}/protection"], repo)
        obs["branch_protection"] = {"exit": rc, "output": out[:400]}
        rc, out = run(["gh", "run", "list", "--limit", "30", "--json", "conclusion", "--repo", slug], repo)
        if rc == 0:
            obs["failed_runs"] = sum(1 for r in json.loads(out or "[]") if r.get("conclusion") == "failure")
        rc, out = run(["gh", "issue", "list", "--state", "all", "--limit", "50", "--json", "number", "--repo", slug], repo)
        obs["issues"] = len(json.loads(out or "[]")) if rc == 0 else None
    # history
    author = args.author or run(["git", "config", "user.email"], repo)[1] or run(["git", "config", "user.name"], repo)[1]
    obs["author"] = author
    rc, log = run(["git", "log", "--format=%H%x1f%an%x1f%ae%x1f%s%x1f%P", "--first-parent"], repo)
    commits = []
    for line in (log.splitlines() if rc == 0 else []):
        sha, an, ae, subj, parents = (line.split("\x1f") + [""] * 5)[:5]
        commits.append({"sha": sha, "author": an, "email": ae, "subject": subj, "merge": len(parents.split()) > 1})
    obs["first_parent"] = commits
    rc, log = run(["git", "log", "--format=%H%x1f%an%x1f%ae", "--shortstat"], repo)
    allc, cur = [], None
    for line in (log.splitlines() if rc == 0 else []):
        if "\x1f" in line:
            sha, an, ae = line.split("\x1f")[:3]
            cur = {"sha": sha, "author": an, "email": ae, "lines": 0, "files": 0}
            allc.append(cur)
        elif cur and "changed" in line:
            nums = dict((k, int(v)) for v, k in re.findall(r"(\d+) (file|insertion|deletion)", line))
            cur["files"] = nums.get("file", 0)
            cur["lines"] = nums.get("insertion", 0) + nums.get("deletion", 0)
    obs["all_commits"] = allc
    rc, out = run(["git", "log", "-i", "-E", "--grep=revert|hotfix|rollback", "--format=%h %s"], repo)
    obs["hurt_commits"] = out.splitlines() if rc == 0 and out else []
    secret_rx, hits = re.compile(SECRET), []
    for f in files:
        p = repo / f
        if not p.is_file() or p.stat().st_size > 400_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if secret_rx.search(line):
                hits.append(f"{f}:{n}: {mask(line.strip())[:120]}")
    obs["secret_hits"] = hits
    rc, out = run(["git", "tag", "--list"], repo)
    obs["tags"] = out.split() if rc == 0 else []
    return obs


def default_branch(repo):
    rc, out = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    return out.split("/", 1)[1] if rc == 0 and "/" in out else "main"


def mask(line):
    return re.sub(SECRET, lambda m: m.group(0)[:6] + "****", line)


def github_slug(url):
    if not url:
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


# ---------- classify ----------
def stdlib_names():
    names = set(getattr(sys, "stdlib_module_names", ())) | set(sys.builtin_module_names)
    if not getattr(sys, "stdlib_module_names", None):
        std = Path(sysconfig.get_paths()["stdlib"])
        names |= {p.stem for p in std.glob("*.py")} | {p.name for p in std.iterdir() if p.is_dir()}
    return names | {"__future__"}


NODE_BUILTINS = {"assert", "buffer", "child_process", "crypto", "dns", "events", "fs", "http", "https", "net", "os", "path",
                 "process", "querystring", "readline", "stream", "string_decoder", "timers", "tls", "url", "util", "zlib",
                 "worker_threads", "node:fs", "node:path", "node:os", "node:crypto", "node:child_process", "node:http", "node:url"}


def is_user(c, author):
    a = (author or "").lower()
    return bool(a) and (a in c.get("email", "").lower() or a in c.get("author", "").lower())


def own_path(f):
    """Files under templates, fixtures, examples or vendored code are not evidence of this repository's own practice."""
    return not any(part.lower() in NOT_OWN for part in Path(f).parts[:-1])


def npm_has_deps(text):
    try:
        d = json.loads(text)
    except ValueError:
        return True
    return any(d.get(k) for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"))


def classify(obs, purpose="users"):
    all_files, all_texts = obs.get("files", []), obs.get("texts", {})
    files = [f for f in all_files if own_path(f)]
    texts = {f: t for f, t in all_texts.items() if own_path(f)}
    wf = {f: t for f, t in texts.items() if f.startswith(".github/workflows/")}
    wf_all = "\n".join(wf.values()).lower()
    names = {Path(f).name for f in files}
    st = {}

    def put(stage, state, *evidence):
        st[stage] = {"state": state, "evidence": [e for e in evidence if e]}

    # GitHub scope (D1)
    slug = github_slug(obs.get("remote_url"))
    own = {o.lower() for o in obs.get("own_owners", [])}
    if not obs.get("gh_available"):
        gh = ("not-checked", "gh not available or not logged in")
    elif not slug:
        gh = ("not-checked", "origin is not a GitHub repository")
    elif slug.split("/")[0].lower() not in own:
        gh = ("not-checked", f"origin {slug} belongs to another account (upstream); gh probes skipped")
    else:
        gh = ("checked", f"origin {slug}")
    scope = {"github": gh[0], "reason": gh[1], "purpose": purpose}

    # history (D9)
    author = obs.get("author", "")
    allc = [c for c in obs.get("all_commits", []) if not BOTS.search(c.get("author", ""))]
    user_c = [c for c in allc if is_user(c, author)]
    fp = [c for c in obs.get("first_parent", []) if not BOTS.search(c.get("author", ""))]
    fp_user = [c for c in fp if is_user(c, author)] or []
    history = {"author": author, "commits": len(allc), "user_commits": len(user_c), "inherited_commits": len(allc) - len(user_c),
               "bot_commits": len(obs.get("all_commits", [])) - len(allc), "thin": len(user_c) <= 3}
    if history["thin"] and user_c:
        big = max(user_c, key=lambda c: c.get("lines", 0))
        history["largest_user_commit"] = {k: big.get(k) for k in ("sha", "files", "lines")}
    basis = fp_user if fp_user else []

    # request
    templates = [f for f in files if f.startswith(".github/ISSUE_TEMPLATE/")]
    traced = sum(1 for c in basis if TICKET.search(c.get("subject", "")))
    share = f"{traced} of {len(basis)} of the user's main-line commits name a ticket" if basis else "no main-line commits by the user"
    issues = obs.get("issues")
    req_state = "present" if templates and basis and traced * 2 >= len(basis) else "partial" if templates or traced or issues else "missing"
    put("request", req_state, f"issue templates: {len(templates)}", share,
        f"issues: {issues}" if issues is not None else f"issues: not checked ({gh[1]})")

    # decision
    dec = [f for f in files if re.search(r"(^|/)(adr|decisions?)/|(^|/)(adr|rfc)-\d+", f, re.I)]
    put("decision", "present" if dec else "missing", f"{len(dec)} decision files" if dec else "no ADR or RFC files")

    # gate and deploy path
    mechanisms = sorted({v for k, v in DEPLOY.items() if k in wf_all} | {v for k, v in DEPLOY_FILES.items() if k in names})
    deploy_gated = any(re.search(r"needs:", t) and any(k in t.lower() for k in DEPLOY) for t in wf.values())
    if not wf:
        gate = ("missing", "no CI workflows")
    elif deploy_gated:
        gate = ("present", "a deploy job waits for another job (needs:)")
    elif mechanisms:
        gate = ("partial", "CI exists; the deploy job waits for no check")
    else:
        gate = ("partial", "CI exists; no deploy job found")
    put("gate", gate[0], gate[1], f"deploy path: {', '.join(mechanisms) or 'none found'}")

    # build (D7)
    pr = [c for c in basis if c.get("merge") or PR_SUBJECT.search(c.get("subject", ""))]
    protocol = any(PROTOCOL.search(t) for f, t in texts.items() if f.lower().endswith(".md"))
    if basis and len(pr) * 2 >= len(basis):
        build = ("present", f"{len(pr)} of {len(basis)} of the user's main-line commits arrive through pull requests")
    elif protocol and gate[0] == "present":
        build = ("partial", "direct pushes to main with a documented protocol and a pre-deploy gate")
    elif basis:
        build = ("missing", f"direct pushes: {len(basis) - len(pr)} of {len(basis)} of the user's main-line commits, no documented protocol or no pre-deploy gate")
    else:
        build = ("not-checked", "no main-line commits by the user")
    put("build", build[0], build[1])

    # review (D2)
    bp = obs.get("branch_protection")
    if gh[0] != "checked" or bp is None:
        prot = f"branch protection: not checked ({gh[1]})"
    elif bp["exit"] == 0:
        prot = "branch protection: on"
    elif "Branch not protected" in bp["output"]:
        prot = "branch protection: off (Branch not protected)"
    else:
        prot = "branch protection: not checked (no access: " + bp["output"].splitlines()[0][:60] + ")"
    owners = any(Path(f).name == "CODEOWNERS" for f in files)
    prt = any(f.lower() in {".github/pull_request_template.md", "pull_request_template.md", "docs/pull_request_template.md"} for f in files)
    on, off = prot.endswith(": on"), ": off" in prot
    if on and (owners or prt):
        rv = "present"
    elif on or owners or prt or build[0] == "present":
        rv = "partial"
    elif off or build[0] == "missing":
        rv = "missing"  # protection off, or direct pushes with no review artifact
    else:
        rv = "not-checked"
    put("review", rv, prot, f"CODEOWNERS: {owners}", f"pull request template: {prt}")

    # test (D6)
    tests = [f for f in all_files if TEST_FILE.search(f) or any(p in TEST_DIRS for p in Path(f).parts[:-1])]
    verify = obs.get("verify_defs", [])
    runs = bool(TEST_RUNNERS.search(wf_all)) or any(Path(f).stem.lower() in wf_all for f in verify + tests[:50])
    if not tests and not verify:
        put("test", "missing", "no test files, eval harness or verify functions")
    elif runs:
        put("test", "present", f"{len(tests)} test files, {len(verify)} files with verify functions; CI runs them")
    else:
        put("test", "partial", f"{len(tests)} test files, {len(verify)} files with verify functions; nothing runs them on a trigger")

    # release record and rollback (D4, D12)
    tags = obs.get("tags", [])
    changelog = any(Path(f).name.lower().startswith("changelog") for f in files)
    put("release_record", "present" if tags or changelog else "missing", f"tags: {len(tags)}", f"changelog: {changelog}")
    notes = {f: t for f, t in texts.items() if f.lower().endswith(".md") and ROLLBACK.search(t)}
    fitting = [f for f, t in notes.items() if any(m.lower() in t.lower() for m in mechanisms)]
    if not notes:
        put("rollback", "missing", "no note mentions a rollback or revert")
    elif fitting:
        put("rollback", "present", f"rollback note names this repository's deploy path: {', '.join(sorted(fitting))}")
    else:
        put("rollback", "partial", f"rollback notes found ({', '.join(sorted(notes)[:3])}) but none names this repository's deploy path ({', '.join(mechanisms) or 'none found'})")

    # observe, incident, docs
    obsv = [f for f in files if OBSERVE.search(f)]
    put("observe", "present" if obsv else "missing", f"{len(obsv)} observability files")
    inc = [f for f in files if re.search(r"(^|/)(runbooks?|incidents?|postmortems?)/|runbook|postmortem|on-?call|status", f, re.I)]
    put("incident", "present" if inc else "missing", f"{len(inc)} runbook, incident or status files")
    readme = next((t for f, t in texts.items() if f.lower() == "readme.md"), "")
    runs_doc = bool(re.search(r"(?i)```(bash|sh|shell)?\n.*(install|run|start|build|test)", readme, re.S))
    put("docs", "present" if runs_doc else "partial" if readme else "missing",
        "README with run instructions" if runs_doc else "README without run instructions" if readme else "no README")

    # dependencies (D3)
    manifests = sorted(f for f in files if Path(f).name in MANIFESTS
                       and not (Path(f).name == "package.json" and f in texts and not npm_has_deps(texts[f])))
    locks = sorted(f for f in files if Path(f).name in LOCKS)
    std = stdlib_names()
    local = set(obs.get("local_modules", []))
    inline = [f for f in obs.get("inline_manifests", []) if own_path(f)]
    by_file = obs.get("imports_by_file") or {"(all files)": obs.get("imports", {})}
    py_mods, js_mods, pinned_mods = set(), set(), set()
    for f, imp in by_file.items():
        if f in inline or (f != "(all files)" and not own_path(f)):
            continue  # inline metadata declares this file's dependencies; templates and fixtures are not the repo's own
        pins = set(imp.get("pinned", []))
        for m in imp.get("python", []):
            (pinned_mods if m in pins else py_mods).add(m)
        for m in imp.get("js", []):
            (pinned_mods if m in pins else js_mods).add(m)
    third_py = sorted(m for m in py_mods if m not in std and m not in local)
    third_js = sorted(m for m in js_mods if m not in NODE_BUILTINS and m not in local)
    manifests = manifests + [f"{f} (inline script metadata)" for f in inline]
    reqs = [t for f, t in texts.items() if Path(f).name == "requirements.txt"]
    pinned = bool(reqs) and all(re.match(r"^\s*([#-]|$|[A-Za-z0-9_.\[\]-]+==)", l) for t in reqs for l in t.splitlines())
    third_pinned = sorted(m for m in pinned_mods if m not in std and m not in NODE_BUILTINS and m not in local)
    if not manifests and not third_py and not third_js and third_pinned:
        put("dependencies", "partial", f"no manifest; tool scripts pin their own packages in an install line: {', '.join(third_pinned[:8])}")
    elif not manifests and not third_py and not third_js:
        put("dependencies", "present", "no manifest and no third-party imports: no dependencies")
    elif not manifests:
        put("dependencies", "missing", f"third-party imports without a manifest: {', '.join((third_py + third_js)[:8])}")
    elif locks or pinned:
        put("dependencies", "present", f"manifests: {', '.join(manifests)}", f"lock files: {', '.join(locks) or 'requirements pinned with =='}")
    else:
        put("dependencies", "partial", f"manifests: {', '.join(manifests)}", "no lock file; version ranges stay unpinned")

    # secrets (D5)
    hits = obs.get("secret_hits", [])
    envs = [f for f in files if re.search(r"(^|/)\.env(\.|$)", f) and not f.endswith(".example")]
    put("secrets", "missing" if hits or envs else "present",
        f"{len(hits)} secret-pattern hits (masked)" if hits else "no secret-pattern hits", *(hits[:5]),
        f".env files in git: {', '.join(envs)}" if envs else "")

    # hygiene (D12)
    junk = [f for f in files if HYGIENE.search(f)]
    put("hygiene", "missing" if junk else "present", f"{len(junk)} generated or archive files tracked: {', '.join(junk[:5])}" if junk else "no generated files tracked",
        ".gitignore present" if ".gitignore" in files else "no .gitignore")

    # scope (D10)
    for s in OUT_OF_SCOPE.get(purpose, set()):
        st[s] = {"state": "out-of-scope", "evidence": [f"the repository ships to: {purpose}"] + st[s]["evidence"]}

    hurt = {"revert_or_hotfix_commits": len(obs.get("hurt_commits", [])), "failed_runs_last_30": obs.get("failed_runs")}
    return {"scope": scope, "history": history, "hurt": hurt, "stages": {k: st[k] for k in STAGES}}


def main():
    ap = argparse.ArgumentParser(description="Read-only probes for sdlc-audit")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--purpose", choices=["users", "grader", "nothing"], default="users")
    ap.add_argument("--author", default=None, help="the repo user's commits: email or name pattern (default: git config user.email)")
    ap.add_argument("--own", default=None, help="comma-separated GitHub owners that count as the user's own")
    ap.add_argument("--no-gh", action="store_true")
    ap.add_argument("--observations-out", default=None)
    ap.add_argument("--from-observations", default=None)
    args = ap.parse_args()
    if args.from_observations:
        obs = json.loads(Path(args.from_observations).read_text())
    else:
        repo = Path(args.repo).resolve()
        if run(["git", "rev-parse", "--is-inside-work-tree"], repo)[0] != 0:
            sys.exit(f"probe: {repo} is not a git repository")
        obs = collect(repo, args)
    if args.observations_out:
        Path(args.observations_out).write_text(json.dumps(obs, indent=1))
    print(json.dumps(classify(obs, args.purpose), indent=1))


if __name__ == "__main__":
    main()
