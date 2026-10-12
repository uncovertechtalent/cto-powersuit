#!/usr/bin/env python3
"""Tests for the security module: the two gate checks beyond their fixture runs, and the three scripts.

- provenance.py: every recorded case in cases/provenance/ gives its risk grade and exactly its red and amber signals;
  the recommendation follows the archive install path and the data scope; attested release assets are counted per asset.
- access_review.py: every case in cases/access-review/ gives exactly its red and amber flags.
- intake.py: fix-by dates from the default windows, the policy template and a custom policy; dedupe; tracked issues.
- osv_query.py: purls from an SPDX and a CycloneDX SBOM, and the rows built from recorded OSV answers (no network).
- security.secrets: each fail fixture gives one hit of its kind; allow, allow_hashes and tracked_only behave.
- security.action-owners: each fail fixture gives one hit of its kind; the owner list option and the listing behave.
- security.private-terms: each fail fixture gives one hit of its kind; no output shows a term; n/a without a list; list errors
  name a line only; the allow file; tracked files and built folders; the pre-push hook against a local remote; the scan CLI.

Standard library only, Python 3.9+. Usage: python3 plugins/security/tests/test_security.py [-v]
"""
import contextlib, datetime, importlib.util, io, json, os, shutil, subprocess, sys, tempfile
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
private = load(MODULE / "checks/private_terms.py", "rule_private_terms")
PT = MODULE / "checks/fixtures/security.private-terms"
PT_LIST = PT / "overlay/security/private-terms.txt"
# Words of the made-up fixture terms. No output of the rule may contain one.
PT_WORDS = ["zanzibar", "kettlehost", "10.99.88.77", "bramblewood", "nightjar", "quillfeather"]
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
def provenance_attested_assets():
    """An attested release asset is no unverified binary; the count is per asset, so an older unattested copy of the same name still is."""
    bad = []
    c = json.loads((CASES / "provenance/attested-release.json").read_text())
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    if "gh attestation verify <file> --repo example-vendor/example-mcp" not in " ".join(r["recommendation"]):
        bad.append(f"attested assets: no verify command in the recommendation {r['recommendation']}")
    c["release_assets"] = c["release_assets"] + ["example-mcp-1.4.2.tar.gz"]
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    ev = [s["evidence"] for s in r["signals"] if s["id"] == "release-binaries"]
    if levels(r["signals"], "amber") != ["release-binaries"] or not ev[0].startswith("1 ") or "lookup failed" in ev[0]:
        bad.append(f"one unattested copy of an attested name: {r['signals']}")
    c["attestation_unknown"] = 1
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    if not any(s["id"] == "release-binaries" and "lookup failed for 1 of them" in s["evidence"] for s in r["signals"]):
        bad.append(f"a failed lookup must be named in the evidence: {r['signals']}")
    del c["attestation_unknown"]
    del c["attested_assets"]
    r = provenance.assess(c, datetime.date(2026, 10, 11))
    if not any(s["id"] == "release-binaries" and s["evidence"].startswith("3 ") for s in r["signals"]):
        bad.append(f"observations without attested_assets (recorded before the field existed): {r['signals']}")
    return bad


@test
def provenance_collect_looks_up_attestations():
    """collect() with recorded gh answers: one lookup per digest, 404 means no attestation, any other error means unknown."""
    bad, calls = [], []
    attested, missing, failing = "sha256:" + "a" * 64, "sha256:" + "b" * 64, "sha256:" + "c" * 64
    answers = {
        "repos/o/r": {"full_name": "o/r", "owner": {"login": "o", "type": "User"}, "created_at": "2025-01-01T00:00:00Z"},
        "users/o": {"created_at": "2020-01-01T00:00:00Z"},
        "repos/o/r/commits?per_page=1": [],
        "repos/o/r/releases?per_page=10": [
            {"assets": [{"name": "r-2.tar.gz", "digest": attested}, {"name": "r-2.tar.gz.sha256", "digest": "sha256:" + "d" * 64}]},
            {"assets": [{"name": "r-1.tar.gz", "digest": missing}, {"name": "r-1.zip", "digest": failing}, {"name": "r-0.zip"}]},
            {"assets": [{"name": "r-2-copy.tar.gz", "digest": attested}]},
        ],
        f"repos/o/r/attestations/{attested}": {"attestations": [{"bundle": {}}]},
    }
    errors = {f"repos/o/r/attestations/{missing}": "gh api: HTTP 404: Not Found",
              f"repos/o/r/attestations/{failing}": "gh api: HTTP 403: API rate limit exceeded"}

    def fake_gh(path, raw=False):
        calls.append(path)
        if raw:
            raise RuntimeError("no readme")
        if path in errors:
            raise RuntimeError(errors[path])
        return answers[path]

    real = provenance.gh
    provenance.gh = fake_gh
    try:
        obs = provenance.collect("o/r", 1)
    finally:
        provenance.gh = real
    if obs["attested_assets"] != ["r-2.tar.gz", "r-2-copy.tar.gz"]:
        bad.append(f"attested_assets {obs['attested_assets']}")
    if obs["attestation_unknown"] != 1:
        bad.append(f"attestation_unknown {obs['attestation_unknown']}, want 1 (the 403)")
    if calls.count(f"repos/o/r/attestations/{attested}") != 1:
        bad.append("the same digest was looked up twice")
    if any(c.endswith("d" * 64) for c in calls):
        bad.append("a .sha256 file (not a binary) was looked up")
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


def leaks(text):
    return [w for w in PT_WORDS if w in text.lower()]


@contextlib.contextmanager
def no_overlay_env():
    saved = os.environ.pop("POWERSUIT_OVERLAY", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["POWERSUIT_OVERLAY"] = saved


@test
def private_terms_each_fail_file_gives_one_hit_of_its_kind():
    res = check_rule(private, PT / "fail", terms_file=str(PT_LIST))
    got = sorted((h["file"], h.get("rule"), h["snippet"].split()[2] if h.get("rule") != "allow-without-reason" else "-") for h in res["hits"])
    want = sorted([(".private-terms-allow", "allow-without-reason", "-"), ("CHANGELOG.md", "private-term", "line8"),
                   ("README.md", "private-term", "employer-z"), ("deploy/inventory.yml", "private-term", "addr-x"),
                   ("docs/plan.md", "private-term", "shorthand-n"), ("drafts/****.txt", "private-term-in-path", "family-b"),
                   ("notes/wrapped.md", "private-term", "employer-z"), ("site/hosts.html", "private-term", "host-k"),
                   ("site/index.html", "private-term", "employer-z"), ("site/team.html", "private-term", "family-b")])
    bad = [] if got == want else [f"hits: {got}"]
    lines = {h["file"]: h["line"] for h in res["hits"]}
    if (lines["notes/wrapped.md"], lines["deploy/inventory.yml"], lines["site/index.html"]) != (1, 4, 5):
        bad.append(f"line numbers: {lines}")
    if check_rule(private, PT / "pass", terms_file=str(PT_LIST))["result"] != "pass":
        bad.append("pass fixture fails")
    return bad + [f"term in the output: {w}" for w in leaks(json.dumps(res))]


@test
def private_terms_without_a_list():
    bad = []
    with tempfile.TemporaryDirectory() as tmp, no_overlay_env():
        res = check_rule(private, PT / "fail")
        if res["result"] != "n/a" or "POWERSUIT_OVERLAY is unset" not in res["detail"]:
            bad.append(f"no variable, no option: {res['result']}, {res['detail']}")
        res = check_rule(private, PT / "fail", terms_file=str(Path(tmp) / "missing.txt"))
        if res["result"] != "n/a" or "no term list at" not in res["detail"]:
            bad.append(f"missing file: {res['result']}")
        empty = Path(tmp) / "empty.txt"
        empty.write_text("# no terms yet\n\n")
        if check_rule(private, PT / "fail", terms_file=str(empty))["result"] != "n/a":
            bad.append("an empty list must give n/a")
        if check_rule(private, PT / "fail", terms_file=str(empty), require_list=True)["result"] != "fail":
            bad.append("require_list with an empty list must fail")
        os.environ["POWERSUIT_OVERLAY"] = str(PT / "overlay")
        if check_rule(private, PT / "fail")["result"] != "fail":
            bad.append("the list under POWERSUIT_OVERLAY is not read")
        del os.environ["POWERSUIT_OVERLAY"]
        root = Path(tmp) / "repo"
        shutil.copytree(PT / "fail", root)
        shutil.copy(PT_LIST, root / "terms.txt")
        res = check_rule(private, root, terms_file=str(root / "terms.txt"))
        if res["result"] != "fail" or "inside the scanned tree" not in res["detail"]:
            bad.append(f"a list inside the tree must be refused: {res['detail']}")
    return bad


@test
def private_terms_list_errors_name_a_line_only():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for body, want in (("# c\nbad = re:quill(feather\n", "term list line 2: invalid regular expression"),
                           ("re:(quillfeather)?\n", "term list line 1: the expression matches an empty string"),
                           ("a = quillfeather\na = bramblewood\n", "term list line 2: label a is used twice")):
            f = Path(tmp) / "terms.txt"
            f.write_text(body)
            try:
                private.load_terms(f)
                bad.append(f"no error for: {want}")
            except private.ListError as e:
                if str(e) != want:
                    bad.append(f"message {e!s}, want {want}")
            res = check_rule(private, PT / "pass", terms_file=str(f))
            if res["result"] != "fail" or leaks(json.dumps(res)):
                bad.append(f"rule result for a broken list: {res['result']}, leaks {leaks(json.dumps(res))}")
    return bad


@test
def private_terms_allow_file():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "fail"
        shutil.copytree(PT / "fail", root)
        (root / ".private-terms-allow").write_text(
            "# test entries\nREADME.md employer-z Named on purpose in this test\nsite/* * Every term under site/ for this test\n"
            "nothing.md host-k An entry that matches nothing\ndocs/* unknown-label A label that is not in the list\n")
        res = check_rule(private, root, terms_file=str(PT_LIST))
        files = sorted(h["file"] for h in res["hits"])
        want = ["CHANGELOG.md", "deploy/inventory.yml", "docs/plan.md", "drafts/****.txt", "notes/wrapped.md"]
        if files != want:
            bad.append(f"hits after the allow file: {files}")
        for part in ("4 allowed", "matched nothing: lines 4, 5", "label not in the list: lines 5"):
            if part not in res["detail"]:
                bad.append(f"detail lacks '{part}': {res['detail']}")
        res = check_rule(private, root, terms_file=str(PT_LIST), allow_file="other-allow")
        if len(res["hits"]) != 9:
            bad.append(f"allow_file option: {len(res['hits'])} hits, want 9")
    return bad


@test
def private_terms_tracked_files_and_built_folders():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git = lambda *a: subprocess.run(["git", "-C", tmp, *a], capture_output=True, text=True, check=True)
        git("init", "-q")
        (root / "README.md").write_text("Nothing private here.\n")
        (root / "notes.md").write_text("Call Bramblewood about it.\n")
        (root / "public").mkdir()
        (root / "public/index.html").write_text("<p>Kettlehost.lan</p>\n")
        git("add", "README.md")
        res = check_rule(private, root, terms_file=str(PT_LIST))
        if res["result"] != "pass" or "1 tracked" not in res["detail"]:
            bad.append(f"untracked files read: {res['detail']}")
        res = check_rule(private, root, terms_file=str(PT_LIST), built=["public"])
        if [h["file"] for h in res["hits"]] != ["public/index.html"]:
            bad.append(f"built folder: {[h['file'] for h in res['hits']]}")
        res = check_rule(private, root, terms_file=str(PT_LIST), tracked_only=False)
        if sorted(h["file"] for h in res["hits"]) != ["notes.md", "public/index.html"]:
            bad.append(f"tracked_only false: {[h['file'] for h in res['hits']]}")
    return bad


@test
def private_terms_pre_push_hook():
    bad, seen = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        work, remote = tmp / "work", tmp / "remote.git"
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Fixture",
                   GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        env.pop("POWERSUIT_OVERLAY", None)

        def git(*a, cwd=work):
            return subprocess.run(["git", *a], cwd=cwd, env=env, capture_output=True, text=True)

        def commit(path, text, message):
            (work / path).parent.mkdir(parents=True, exist_ok=True)
            (work / path).write_text(text)
            git("add", "-A")
            git("commit", "-q", "-m", message)

        def push(*a, want):
            p = git("push", "-q", "origin", *a)
            seen.append(p.stderr)
            got = "ok" if p.returncode == 0 else "stopped"
            if got != want:
                bad.append(f"push {' '.join(a)}: {got}, want {want}: {p.stderr.strip()[-300:]}")
            return p.stderr

        git("init", "-q", "--bare", str(remote), cwd=tmp)
        git("init", "-q", str(work), cwd=tmp)
        git("checkout", "-q", "-b", "main")
        git("remote", "add", "origin", str(remote))
        code, _ = private.install_hook(work / ".git/hooks", str(PT_LIST))
        if code or "pre-push" not in (work / ".git/hooks/pre-push").read_text():
            bad.append("install_hook wrote no shim")
        commit("README.md", "# Project\n", "Start")
        push("main", want="ok")
        commit("docs/setup.md", "# Setup\n\nThe runner sits on Kettlehost.lan for now.\n", "Add setup notes")
        err = push("main", want="stopped")
        if "docs/setup.md:3 private term host-k" not in err:
            bad.append(f"added line not named by file and line: {err.strip()[-200:]}")
        commit("docs/setup.md", "# Setup\n\nThe runner sits on the build host.\n", "Reword setup notes")
        push("main", want="stopped")  # the earlier commit still carries the term
        git("reset", "-q", "--hard", "origin/main")
        commit("docs/setup.md", "# Setup\n", "Thanks to Zanzibar Widgets")
        err = push("main", want="stopped")
        if "message:1 private term employer-z" not in err:
            bad.append(f"commit message hit missing: {err.strip()[-200:]}")
        git("commit", "-q", "--amend", "-m", "Add setup page")
        push("main", want="ok")
        commit("docs/setup.md", "# Setup page\nRunner host: kettlehost.lan\n", "Edit two lines")
        err = push("main", want="stopped")
        if "docs/setup.md:2 private term host-k" not in err:
            bad.append(f"changed line not named by its new line number: {err.strip()[-200:]}")
        git("reset", "-q", "--hard", "origin/main")
        commit("legacy.md", "old line\nquillfeather\n", "Legacy file")
        push("--no-verify", "main", want="ok")
        commit("legacy.md", "old line\n", "Remove a name")
        push("main", want="ok")  # a deleted line sends nothing new
        commit("about.md", "I worked at Zanzibar Widgets.\n", "About page")
        push("main", want="stopped")
        commit(".private-terms-allow", "about.md employer-z Former employer, named on purpose\n", "Allow the about page mention")
        push("main", want="ok")
        commit("drafts/bramblewood.md", "notes\n", "Drafts")
        err = push("main", want="stopped")
        if "drafts/****.md private term family-b" not in err:
            bad.append(f"new file name hit missing: {err.strip()[-200:]}")
        git("reset", "-q", "--hard", "origin/main")
        git("checkout", "-q", "-b", "feature")
        commit("feature.md", "A feature.\n", "Feature")
        push("feature", want="ok")
        git("tag", "-a", "v1", "-m", "Release for project nightjar")
        push("v1", want="stopped")
        push("HEAD:refs/heads/project-nightjar", want="stopped")
        (tmp / "empty.txt").write_text("# no terms yet\n")
        (work / ".git/hooks/pre-push").write_text(f'#!/bin/sh\n# private-terms pre-push hook\nexec python3 "{MODULE / "checks/private_terms.py"}" pre-push "$@" --terms "{tmp / "empty.txt"}"\n')
        err = push("HEAD:refs/heads/empty-list", want="ok")
        if "no terms yet" not in err:
            bad.append(f"an empty list must let the push through with a note: {err.strip()[-200:]}")
        (work / ".git/hooks/pre-push").write_text(f'#!/bin/sh\n# private-terms pre-push hook\nexec python3 "{MODULE / "checks/private_terms.py"}" pre-push "$@" --terms "{tmp / "missing.txt"}"\n')
        err = push("main", want="stopped")
        if "no term list at" not in err:
            bad.append(f"missing list must stop the push: {err.strip()[-200:]}")
        h = subprocess.run([sys.executable, str(MODULE / "checks/private_terms.py"), "history", str(work), "--terms", str(PT_LIST)],
                           capture_output=True, text=True, env=env)
        seen.append(h.stdout + h.stderr)
        if h.returncode != 1 or "line8: 2 lines" not in h.stdout or "employer-z:" not in h.stdout:
            bad.append(f"history counts: exit {h.returncode}, {h.stdout.strip()[-200:]}")
        (work / ".git/hooks/pre-push").write_text("#!/bin/sh\nexit 0\n")
        if private.install_hook(work / ".git/hooks", str(PT_LIST))[0] != 2:
            bad.append("install_hook replaced another hook")
    return bad + [f"term in the hook output: {w}" for w in leaks("\n".join(seen))]


@test
def private_terms_scan_cli():
    bad = []
    script = MODULE / "checks/private_terms.py"
    run_cli = lambda *a: subprocess.run([sys.executable, str(script), "scan", *a], capture_output=True, text=True)
    for root, want in ((PT / "pass", 0), (PT / "fail", 1)):
        p = run_cli(str(root), "--terms", str(PT_LIST))
        if p.returncode != want or leaks(p.stdout + p.stderr):
            bad.append(f"scan {root.name}: exit {p.returncode}, want {want}; leaks {leaks(p.stdout + p.stderr)}")
    with no_overlay_env():
        p = run_cli(str(PT / "fail"))
    if p.returncode != 2:
        bad.append(f"scan without a list: exit {p.returncode}, want 2")
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
