#!/usr/bin/env python3
"""Tests for the security module: the two gate checks beyond their fixture runs, and the three scripts.

- provenance.py: every recorded case in cases/provenance/ gives its risk grade and exactly its red and amber signals;
  the recommendation follows the archive install path and the data scope.
- access_review.py: every case in cases/access-review/ gives exactly its red and amber flags.
- intake.py: fix-by dates from the default windows, the policy template and a custom policy; dedupe; tracked issues.
- osv_query.py: purls from an SPDX and a CycloneDX SBOM, and the rows built from recorded OSV answers (no network).
- security.secrets: each fail fixture gives one hit of its kind; allow, allow_hashes and tracked_only behave.
- security.action-owners: each fail fixture gives one hit of its kind; the owner list option and the listing behave.

Standard library only, Python 3.9+. Usage: python3 plugins/security/tests/test_security.py [-v]
"""
import contextlib, datetime, importlib.util, io, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

MODULE = Path(__file__).resolve().parent.parent
CASES = Path(__file__).resolve().parent / "cases"
REPO = MODULE.parent.parent
VERBOSE = "-v" in sys.argv


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load(REPO / "plugins/gate/templates/.github/actions/gate/run.py", "gate_run")
provenance = load(MODULE / "skills/supply-chain/provenance.py", "provenance")
osv = load(MODULE / "skills/supply-chain/osv_query.py", "osv_query")
access = load(MODULE / "skills/access-review/access_review.py", "access_review")
intake = load(MODULE / "skills/vuln-intake/intake.py", "intake")
secrets = load(MODULE / "checks/secrets.py", "rule_secrets")
owners = load(MODULE / "checks/action_owners.py", "rule_action_owners")
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def check_rule(rule, root, **options):
    opts = json.loads(json.dumps(rule.DEFAULTS))
    opts.update(options)
    return run.run_one(rule, run.Ctx(root, opts, {}, [], "manual", None))


def levels(items, level):
    return sorted({x["id"] for x in items if x["level"] == level})


@test
def provenance_cases():
    bad = []
    for f in sorted((CASES / "provenance").glob("*.json")):
        c = json.loads(f.read_text())
        r = provenance.assess(c, datetime.date.fromisoformat(c["today"]))
        got = {"risk": r["risk"], "red": levels(r["signals"], "red"), "amber": levels(r["signals"], "amber")}
        if "exposure" in c["expect"]:
            got["exposure"] = r["exposure"]
        want = {k: sorted(v) if isinstance(v, list) else v for k, v in c["expect"].items()}
        if got != want:
            bad.append(f"{f.stem}: got {got}, want {want}")
        elif VERBOSE:
            print(f"     {f.stem}: {got}")
    return bad


@test
def provenance_exit_codes_from_observations():
    bad = []
    for name, code in (("vendor-official", 0), ("unverified-owner", 1), ("fakegit-throwaway", 2), ("new-tool-archive-install", 1)):
        p = subprocess.run([sys.executable, str(MODULE / "skills/supply-chain/provenance.py"), "--from-observations",
                            str(CASES / "provenance" / f"{name}.json")], capture_output=True, text=True)
        if p.returncode != code:
            bad.append(f"{name}: exit {p.returncode}, want {code}: {p.stderr.strip()[:200]}")
    return bad


@test
def provenance_recommendation_axes():
    bad = []
    c = json.loads((CASES / "provenance/new-tool-archive-install.json").read_text())
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    text = " ".join(r["recommendation"])
    for want in ("decides", "marketplace", "pinned commit", "no guarantee", "agent transcripts"):
        if want not in text:
            bad.append(f"archive install reading agent data: no {want!r} in the recommendation")
    c["data_scope"] = "repo"
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    if r["exposure"] != "medium" or "agent transcripts" in " ".join(r["recommendation"]):
        bad.append(f"data scope repo: exposure {r['exposure']}")
    del c["data_scope"]
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    if r["exposure"] != "unknown" or "--data-scope" not in " ".join(r["recommendation"]):
        bad.append("no data scope must ask for one")
    clean = json.loads((CASES / "provenance/vendor-official.json").read_text())
    r = provenance.assess(clean, datetime.date(2026, 10, 11))
    if "marketplace" in " ".join(r["recommendation"]) or r["pin"] not in r["recommendation"][0]:
        bad.append(f"no archive and low risk: {r['recommendation']}")
    return bad


@test
def provenance_reads_github_urls():
    bad = []
    for target in ("owner/repo", "https://github.com/owner/repo", "https://github.com/owner/repo.git", "git@github.com:owner/repo.git"):
        if provenance.slug_of(target) != "owner/repo":
            bad.append(f"{target}: {provenance.slug_of(target)}")
    return bad


@test
def access_review_cases():
    bad = []
    for f in sorted((CASES / "access-review").glob("*.json")):
        c = json.loads(f.read_text())
        r = access.assess(c, datetime.date.fromisoformat(c["today"]))
        got = {"red": levels(r["flags"], "red"), "amber": levels(r["flags"], "amber")}
        want = {k: sorted(v) for k, v in c["expect"].items()}
        if got != want:
            bad.append(f"{f.stem}: got {got}, want {want}")
        elif VERBOSE:
            print(f"     {f.stem}: {got}")
    one = access.assess(json.loads((CASES / "access-review/admin-bypass.json").read_text()), datetime.date(2026, 10, 11))
    merge = [x["evidence"] for x in one["flags"] if x["id"] == "bypass-merge"]
    if not merge or "#12" not in merge[0] or "9001" not in merge[0]:
        bad.append(f"admin-bypass: the merge flag names no pull request or rule suite: {merge}")
    return bad


@test
def access_review_sends_only_get_requests():
    src = (MODULE / "skills/access-review/access_review.py").read_text()
    forbidden = [w for w in ("-X", "--method", "-f ", "-F ", "--field", "--raw-field", "--input") if f'"{w.strip()}"' in src]
    return [f"access_review.py passes {w} to gh" for w in forbidden]


@test
def osv_purls_and_rows():
    bad = []
    spdx = json.loads((CASES / "sbom/github-dependency-graph.spdx.json").read_text())
    cdx = json.loads((CASES / "sbom/nested.cdx.json").read_text())
    got = osv.purls(spdx["sbom"])
    want = ["pkg:golang/golang.org/x/text@v0.37.0", "pkg:npm/left-pad", "pkg:npm/lodash@4.17.20"]
    if got != want:
        bad.append(f"spdx purls: {got}")
    if osv.purls(cdx) != ["pkg:pypi/requests@2.31.0", "pkg:pypi/urllib3@2.0.6"]:
        bad.append(f"cyclonedx purls: {osv.purls(cdx)}")
    api = json.loads((CASES / "sbom/osv-responses.json").read_text())
    calls = []

    def fake(url, body=None):
        calls.append(url)
        if url.endswith("/querybatch"):
            return {"results": [{"vulns": api["querybatch"].get(q["package"]["purl"], [])} for q in body["queries"]]}
        return api["vulns"][url.rsplit("/", 1)[1]]

    r = osv.query(got + osv.purls(cdx), get=fake)
    rows = sorted((v["purl"], v["id"], v["severity"], tuple(v["fixed"])) for v in r["vulns"])
    want_rows = [("pkg:golang/golang.org/x/text@v0.37.0", "GO-2026-0001", "high", ("0.39.0",)),
                 ("pkg:npm/lodash@4.17.20", "GHSA-0001-0001-0001", "medium", ("4.17.21",)),
                 ("pkg:pypi/urllib3@2.0.6", "GHSA-0002-0002-0002", "low", ("2.0.7",))]
    if rows != want_rows:
        bad.append(f"rows: {rows}")
    if (r["packages"], r["queried"], r["skipped_no_version"]) != (5, 4, 1):
        bad.append(f"counts: {r['packages']}, {r['queried']}, {r['skipped_no_version']}")
    if sum(u.endswith("/querybatch") for u in calls) != 1:
        bad.append(f"batch calls: {calls}")
    return bad


@test
def intake_drafts_and_windows():
    bad = []
    c = CASES / "intake"
    pages = json.loads((c / "dependabot.json").read_text())
    findings = list(intake.from_dependabot([x for page in pages for x in page])) + list(intake.from_osv(json.loads((c / "osv.json").read_text())))
    today = datetime.date(2026, 10, 11)
    titles = [i["title"] for i in json.loads((c / "existing.json").read_text())]
    out, tracked = intake.drafts(findings, today, intake.windows(), titles)
    got = [(d["key"], d["fix_by"], d["labels"][2], d["overdue"]) for d in out]
    want = [("GHSA-bbbb-bbbb-bbbb pip/example-http", "2026-08-30", "P2", True),
            ("GHSA-aaaa-aaaa-aaaa npm/example-parser", "2026-10-08", "P0", True),
            ("GO-2026-0042 pkg:golang/example.org/lib", "2026-11-10", "P1", False)]
    if got != want:
        bad.append(f"default windows: {got}")
    if tracked != ["GHSA-cccc-cccc-cccc npm/example-zip"]:
        bad.append(f"tracked: {tracked}")
    out, _ = intake.drafts(findings, today, intake.windows((c / "policy.md").read_text()))
    if [d["fix_by"] for d in out] != ["2026-07-31", "2026-10-04", "2026-10-19", "2026-10-25"]:
        bad.append(f"custom policy: {[d['fix_by'] for d in out]}")
    template = intake.windows((MODULE / "templates/docs/security/vuln-policy.md").read_text())
    if template != {"critical": (7, "P0"), "high": (30, "P1"), "medium": (90, "P2"), "low": (180, "P3"), "unknown": (30, "P1")}:
        bad.append(f"policy template: {template}")
    if intake.windows("| high | 14 days | `P1` |")["unknown"] != (14, "P1"):
        bad.append("an unrated finding must take the policy's high window when the policy has no unknown row")
    if not any("2.4.1 or later" in d["body"] for d in out) or not any("no fix is listed" in d["body"] for d in out):
        bad.append("acceptance criteria miss the fixed version or the no-fix case")
    return bad


@test
def secrets_each_fail_file_gives_one_hit_of_its_kind():
    fail = MODULE / "checks/fixtures/security.secrets/fail"
    res = check_rule(secrets, fail)
    kinds = {h["file"]: h.get("rule") for h in res["hits"]}
    want = {".env": "env-file", "config/anthropic.env.txt": "anthropic-key", "config/sk-key.txt": "sk-key",
            "config/aws-credentials.ini": "aws-access-key-id", "config/github.yml": "github-token",
            "config/github-fine-grained.yml": "github-fine-grained-token", "config/slack.txt": "slack-token",
            "keys/id_example": "private-key"}
    bad = [] if (kinds, len(res["hits"])) == (want, len(want)) else [f"hits: {[(h['file'], h.get('rule')) for h in res['hits']]}"]
    leaked = [h["snippet"] for h in res["hits"] if "EXAMPLE" in h["snippet"]]
    return bad + [f"value in a snippet: {s}" for s in leaked]


@test
def secrets_allow_options():
    fail = MODULE / "checks/fixtures/security.secrets/fail"
    bad = []
    res = check_rule(secrets, fail, allow=["config/*", "keys/*"])
    if [h["file"] for h in res["hits"]] != [".env"]:
        bad.append(f"allow by path: {[h['file'] for h in res['hits']]}")
    aws = [h for h in check_rule(secrets, fail)["hits"] if h.get("rule") == "aws-access-key-id"][0]
    digest = aws["snippet"].rsplit("sha256:", 1)[1]
    res = check_rule(secrets, fail, allow_hashes=[digest])
    if any(h.get("rule") == "aws-access-key-id" for h in res["hits"]) or len(res["hits"]) != 7:
        bad.append(f"allow by hash {digest}: {len(res['hits'])} hits")
    res = check_rule(secrets, fail, allow_hashes=[digest[:6]])
    if len(res["hits"]) != 8:
        bad.append("a hash prefix under 8 digits must not allow anything")
    return bad


@test
def secrets_tracked_only_reads_tracked_files():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git = lambda *a: subprocess.run(["git", "-C", tmp, *a], capture_output=True, text=True, check=True)
        git("init", "-q")
        (root / "README.md").write_text("no secrets here\n")
        (root / "local.env.txt").write_text("key = AKIAIOSFODNN7EXAMPLE\n")
        git("add", "README.md")
        res = check_rule(secrets, root)
        if res["hits"] or "1 tracked" not in res["detail"]:
            bad.append(f"untracked file read: {res['detail']}, {res['hits']}")
        (root / "logo.bin").write_bytes(b"\x89PNG\0\0 AKIAIOSFODNN7EXAMPLE")
        res = check_rule(secrets, root, tracked_only=False)
        if len(res["hits"]) != 1:
            bad.append(f"tracked_only false: {len(res['hits'])} hits, want 1 (binary files are skipped, as git grep -I)")
        git("add", "local.env.txt")
        if len(check_rule(secrets, root)["hits"]) != 1:
            bad.append("tracked file with a key gives no hit")
    return bad


@test
def action_owners_each_fail_file_gives_one_hit_of_its_kind():
    fail = MODULE / "checks/fixtures/security.action-owners/fail"
    res = check_rule(owners, fail)
    got = sorted((h["file"], h.get("rule")) for h in res["hits"])
    want = sorted([(".github/actions/build/action.yml", "owner-not-allowed"), (".github/workflows/docker.yml", "image-not-allowed"),
                   (".github/workflows/flow-style.yml", "owner-not-allowed"), (".github/workflows/other-owner.yml", "owner-not-allowed"),
                   (".github/workflows/reusable.yml", "owner-not-allowed"), (".github/workflows/typosquat.yml", "owner-not-allowed")])
    return [] if got == want else [f"hits: {got}"]


@test
def action_owners_options_and_listing():
    fail = MODULE / "checks/fixtures/security.action-owners/fail"
    bad = []
    res = check_rule(owners, fail, owners=["actions", "some-org", "actlons", "other-org", "flow-org", "composite-org"],
                     images=["docker://alpine@"])
    if res["result"] != "pass":
        bad.append(f"every owner listed: {res['result']}, {[h['snippet'] for h in res['hits']]}")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sys.argv, saved = ["action_owners.py", str(MODULE / "checks/fixtures/security.action-owners/pass")], sys.argv
        try:
            exec(compile((MODULE / "checks/action_owners.py").read_text(), "action_owners.py", "exec"), {"__name__": "__main__"})
        finally:
            sys.argv = saved
    listed = [line.split("\t")[0] for line in out.getvalue().splitlines()]
    if listed != ["actions"]:
        bad.append(f"listing of the pass fixture: {listed}")
    return bad


def main():
    failures = 0
    for fn in TESTS:
        try:
            bad = fn()
        except Exception as e:  # a crash is a failure of that case
            bad = [f"raised {type(e).__name__}: {e}"]
        print(f"{'ok  ' if not bad else 'FAIL'} {fn.__name__}")
        for b in bad:
            print(f"     {b}")
        failures += bool(bad)
    print(f"{len(TESTS)} cases, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
