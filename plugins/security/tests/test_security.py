#!/usr/bin/env python3
"""Tests for the security module: the two gate checks beyond their fixture runs, and the three scripts.

- provenance.py: every recorded case in cases/provenance/ gives its risk grade and exactly its red and amber signals;
  the recommendation follows the archive install path and the data scope; attested release assets are counted per asset.
- access_review.py: every case in cases/access-review/ gives exactly its red and amber flags; the MFA section reads the
  organisation's two-factor requirement from recorded answers, or says the caller could not read it.
- intake.py: fix-by dates from the default windows, the policy template and a custom policy; dedupe; tracked issues.
- osv_query.py: purls from an SPDX and a CycloneDX SBOM, and the rows built from recorded OSV answers (no network).
- security.secrets: each fail fixture gives one hit of its kind; allow, allow_hashes and tracked_only behave.
- security.action-owners: each fail fixture gives one hit of its kind; the owner list option and the listing behave;
  its LOCAL prefixes and USES pattern match gate.actions-pinned.
- security.admin-entrances: each fail row gives its rule; exceptions need a reason, a person and a date and end after
  their date; the options; the shipped template stays in step with the check; no output shows a cell value.
- security.private-terms: each fail fixture gives one hit of its kind; no output shows a term; n/a without a list; list errors
  name a line only; the allow file; tracked files and built folders; the pre-push hook against a local remote; the scan CLI.
- quarantine.py: save marks and stores an item without printing it, and refuses a store inside a vault, an overlay, a
  protected folder or a git work tree; list and remove stay inside the store; read returns the envelope and never the
  raw text, sends the reader fenced, stripped and truncated text with no tools in the request, and types, cleans and
  caps the reply or refuses it without an echo; the guard denies every known route into the store and allows the
  known near misses, as a function and as a hook process; the settings snippet. Canary strings only; no network.

Standard library only, Python 3.9+. Usage: python3 plugins/security/tests/test_security.py [-v]
"""
import contextlib, datetime, importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile
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
pinned = load(MODULE.parent / "gate/checks/actions_pinned.py", "rule_actions_pinned")
private = load(MODULE / "checks/private_terms.py", "rule_private_terms")
admin = load(MODULE / "checks/admin_entrances.py", "rule_admin_entrances")
quarantine = load(MODULE / "skills/quarantine/quarantine.py", "quarantine")
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
def action_owners_matches_actions_pinned():
    """security.action-owners keeps hand copies of LOCAL and USES from gate.actions-pinned; the copies must match (#11)."""
    bad = []
    if owners.LOCAL != pinned.LOCAL:
        bad.append(f"LOCAL differs: action_owners {owners.LOCAL}, actions_pinned {pinned.LOCAL}")
    if owners.USES.pattern != pinned.USES.pattern:
        bad.append(f"USES differs: action_owners {owners.USES.pattern!r}, actions_pinned {pinned.USES.pattern!r}")
    return bad

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


# ---------------------------------------------------------------- quarantine
# Test text is a harmless canary string, never real injection text. The reader
# backend is a fake, so these cases check the envelope and the request, not a model.

Q_CANARY = "QUARANTINE-CANARY-7f3a"
Q_REPLY_MARK = "REPLY-MARKER-0b1c"
Q_TEXT = (f"A post about local embeddings. {Q_CANARY}\n"
          "See https://example.org/a and https://docs.example.com/b?x=1\n"
          "Hidden\u200bcharacters\U000e0041here.\n")
Q_HOME = os.path.expanduser("~")
Q_STORE = os.path.join(Q_HOME, "quarantine")


@contextlib.contextmanager
def q_env(**extra):
    """A temporary store, vault and scratch folder; the caller's variables come back afterwards."""
    keys = ("QUARANTINE_ROOT", "QUARANTINE_PROTECT", "VAULT_PATH", "POWERSUIT_OVERLAY", "QUARANTINE_GUARD_LOG")
    saved = {k: os.environ.pop(k, None) for k in keys}
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(os.path.realpath(tmp))
        (t / "vault").mkdir()
        (t / "scratch").mkdir()
        os.environ.update({"QUARANTINE_ROOT": str(t / "quarantine"), "VAULT_PATH": str(t / "vault"),
                           "QUARANTINE_GUARD_LOG": str(t / "guard.log")})
        os.environ.update(extra)
        try:
            yield t
        finally:
            for k in keys:
                os.environ.pop(k, None)
                if saved[k] is not None:
                    os.environ[k] = saved[k]


def q_run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = quarantine.main(list(argv))
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


def q_save(t, text=Q_TEXT, name="paste.txt"):
    src = t / "scratch" / name
    src.write_text(text, encoding="utf-8")
    rc, out, err = q_run("save", "--source", "https://www.example.org/r/test/comments/abc/x/", "--kind", "post", str(src))
    if rc != 0:
        raise AssertionError(f"save failed: {err}")
    return json.loads(out), out


def q_reply(**over):
    obj = {"kind": "post", "language": "en", "topic": "Local embeddings",
           "summary": "The author describes a local embedding app.", "key_points": ["Runs on a laptop."],
           "addresses_ai": False, "asks_reader_to_act": True}
    obj.update(over)
    return json.dumps(obj)


@contextlib.contextmanager
def q_backend(reply=None):
    """Replace the reader backend; the calls land in the yielded list."""
    calls = []
    orig = quarantine.call_backend

    def fake(messages, url, model, timeout=180):
        calls.append(messages)
        return q_reply() if reply is None else reply

    quarantine.call_backend = fake
    try:
        yield calls
    finally:
        quarantine.call_backend = orig


@test
def quarantine_save_marks_the_item_and_prints_no_text():
    bad = []
    with q_env() as t:
        res, out = q_save(t)
        p = Path(res["path"])
        if Q_CANARY in out:
            bad.append("save printed the text")
        if p.parent != t / "quarantine" or not res["id"].endswith("example-org-r-test-comments-abc-x"):
            bad.append(f"item path {p}")
        if (oct(p.parent.stat().st_mode & 0o777), oct(p.stat().st_mode & 0o777)) != ("0o700", "0o600"):
            bad.append("modes are not 0700 and 0600")
        if (p.parent / ".ignore").read_text() != "*\n":
            bad.append("no .ignore in the store")
        meta, body = quarantine.read_item(p)
        if (meta.get("trust"), body, meta.get("sha256")) != ("external", Q_TEXT, res["sha256"]):
            bad.append(f"front matter or body differ: {meta}")
        src = t / "scratch" / "move.txt"
        src.write_text(Q_TEXT)
        rc, out, _ = q_run("save", "--source", "chat paste", "--move", str(src))
        if rc != 0 or src.exists() or not json.loads(out)["moved"]:
            bad.append("--move did not copy and delete")
        if not q_save(t)[0]["id"].endswith("-2"):
            bad.append("the same source twice did not get a suffix")
    return bad


@test
def quarantine_save_from_the_clipboard():
    bad = []
    orig = quarantine.clipboard
    quarantine.clipboard = lambda: Q_TEXT.encode()
    try:
        with q_env():
            rc, out, _ = q_run("save", "--source", "clip", "--from-clipboard")
            if rc != 0 or Q_CANARY in out:
                bad.append(f"clipboard save: exit {rc}")
            elif quarantine.read_item(Path(json.loads(out)["path"]))[1] != Q_TEXT:
                bad.append("clipboard text not stored as given")
    finally:
        quarantine.clipboard = orig
    return bad


@test
def quarantine_store_placement_and_empty_input_are_refused():
    bad = []
    with q_env() as t:
        empty = t / "scratch" / "empty.txt"
        empty.write_text("  \n")
        rc, _, err = q_run("save", "--source", "x", str(empty))
        if rc != 2 or "empty" not in err:
            bad.append(f"empty input: exit {rc}")
        cases = {"inside the vault": {"QUARANTINE_ROOT": str(t / "vault" / "_quarantine")},
                 "inside a protected folder": {"QUARANTINE_PROTECT": str(t / "scratch"),
                                               "QUARANTINE_ROOT": str(t / "scratch" / "q")},
                 "inside the overlay": {"POWERSUIT_OVERLAY": str(t / "scratch"),
                                        "QUARANTINE_ROOT": str(t / "scratch" / "q")}}
        (t / "repo" / ".git").mkdir(parents=True)
        cases["inside a git work tree"] = {"QUARANTINE_ROOT": str(t / "repo" / "q")}
        src = t / "scratch" / "in.txt"
        src.write_text(Q_TEXT)
        for name, env in cases.items():
            saved = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
            try:
                rc, _, err = q_run("save", "--source", "x", str(src))
            finally:
                for k, v in saved.items():
                    os.environ.pop(k, None)
                    if v is not None:
                        os.environ[k] = v
            if rc != 2 or "outside" not in err:
                bad.append(f"store {name}: exit {rc}")
    return bad


@test
def quarantine_list_and_remove():
    bad = []
    with q_env() as t:
        a, _ = q_save(t)
        b, _ = q_save(t)
        rc, out, _ = q_run("list")
        rows = [json.loads(x) for x in out.splitlines()]
        if rc != 0 or Q_CANARY in out or sorted(r["id"] for r in rows) != sorted([a["id"], b["id"]]):
            bad.append(f"list: {out[:200]}")
        if any((r["trust"], r["sha256_ok"]) != ("external", True) for r in rows):
            bad.append("list rows not marked or hash mismatch")
        p = Path(a["path"])
        p.write_text(p.read_text() + "edited\n")
        rows = {r["id"]: r for r in map(json.loads, q_run("list")[1].splitlines())}
        if rows[a["id"]]["sha256_ok"] or not rows[b["id"]]["sha256_ok"]:
            bad.append("sha256_ok does not follow the changed item")
        rc, out, _ = q_run("remove", a["id"])
        if rc != 0 or p.exists() or not Path(b["path"]).exists():
            bad.append("remove did not delete exactly one item")
        outside = t / "vault" / "atom.md"
        outside.write_text("keep\n")
        if q_run("remove", str(outside))[0] != 2 or not outside.exists():
            bad.append("remove reached a file outside the store")
    return bad


@test
def quarantine_read_envelope_has_no_raw_text():
    bad = []
    with q_env() as t:
        res, _ = q_save(t)
        with q_backend() as calls:
            rc, out, err = q_run("read", res["id"])
        if rc != 0:
            return [f"read: exit {rc} {err}"]
        env = json.loads(out)
        if Q_CANARY in out:
            bad.append("the envelope carries the raw text")
        if set(env) != {"quarantine_read", "measured", "summary", "notice"}:
            bad.append(f"envelope keys {sorted(env)}")
        q = env["quarantine_read"]
        if (q["id"], q["kind"], q["integrity"], q["trust"], q["backend"]) != (res["id"], "post", "ok", "external", "ollama"):
            bad.append(f"quarantine_read {q}")
        m = env["measured"]
        if (m["domains"], m["urls"], m["hidden_chars"]) != (["docs.example.com", "example.org"], 2, 2):
            bad.append(f"measured {m}")
        if len(calls) != 1:
            bad.append(f"{len(calls)} backend calls")
        log = (t / "quarantine" / ".reads.log").read_text()
        if len(log.splitlines()) != 1 or Q_CANARY in log:
            bad.append("read log wrong or carries text")
        p = Path(res["path"])
        p.write_text(p.read_text() + "edited\n")
        with q_backend():
            if json.loads(q_run("read", res["id"])[1])["quarantine_read"]["integrity"] != "changed":
                bad.append("a changed item does not read integrity changed")
    return bad


@test
def quarantine_hash_survives_crlf_and_a_leading_newline():
    """An email with CRLF line ends and a paste that starts with a newline read back as written (#15 review)."""
    bad = []
    with q_env() as t:
        for name, text in (("crlf", "Line one." + "\r\n" + Q_CANARY + "\r\n"),
                           ("leading", "\n\nStarts after blank lines. " + Q_CANARY + "\n")):
            res, _ = q_save(t, text, name + ".txt")
            row = {r["id"]: r for r in map(json.loads, q_run("list")[1].splitlines())}[res["id"]]
            if not row["sha256_ok"]:
                bad.append(f"{name}: list reads sha256_ok false right after save")
            if quarantine.read_item(Path(res["path"]))[1] != text:
                bad.append(f"{name}: body changed on the way back")
            with q_backend():
                env = json.loads(q_run("read", res["id"])[1])
            if env["quarantine_read"]["integrity"] != "ok":
                bad.append(f"{name}: integrity {env['quarantine_read']['integrity']}")
            if env["measured"]["hidden_chars"] != 0:
                bad.append(f"{name}: hidden_chars {env['measured']['hidden_chars']}")
    return bad


@test
def quarantine_hidden_characters_and_clean_source():
    """Soft hyphen, U+180E, variation selectors and the tag block are stripped; the source holds no invisible character."""
    sample = "a\u00adb\u180ec\ufe0fd\U000e0100e\u200bf\U000e0041g\rh"
    cleaned, n = quarantine.strip_hidden(sample)
    bad = [] if (cleaned, n) == ("abcdefgh", 7) else [f"strip_hidden: {cleaned!r} {n}"]
    import unicodedata
    for f in (MODULE / "skills/quarantine/quarantine.py", MODULE / "skills/quarantine/SKILL.md", Path(__file__)):
        text = f.read_text(encoding="utf-8")
        hits = [hex(ord(c)) for c in text if unicodedata.category(c) in ("Cf", "Co") or 0xFE00 <= ord(c) <= 0xFE0F]
        if hits:
            bad.append(f"{f.name}: invisible characters {sorted(set(hits))}")
    return bad


@test
def quarantine_reader_gets_fenced_stripped_truncated_text():
    bad = []
    with q_env() as t:
        res, _ = q_save(t, Q_TEXT + "filler words " * 4000)
        with q_backend() as calls:
            q_run("read", res["id"])
        msgs = calls[0]
        if [m["role"] for m in msgs] != ["system", "user"]:
            bad.append("messages are not one system and one user message")
        user = msgs[1]["content"]
        marker = user.split("\n", 1)[0]
        if not re.match(r"^QDOC-[0-9a-f]{16}$", marker):
            bad.append(f"marker {marker[:30]}")
        doc = user.split(marker + "\n", 1)[1].rsplit("\n" + marker, 1)[0]
        if Q_CANARY not in doc or "\u200b" in doc or "\U000e0041" in doc or len(doc) != quarantine.MAX_CHARS:
            bad.append("text not stripped of hidden characters or not cut at MAX_CHARS")
        a = quarantine.build_messages("x")[1]["content"].split("\n", 1)[0]
        b = quarantine.build_messages("x")[1]["content"].split("\n", 1)[0]
        if a == b:
            bad.append("the marker repeats between reads")
    return bad


@test
def quarantine_backend_request_has_no_tools():
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"message": {"content": q_reply()}}).encode()

    def fake_urlopen(req, timeout=0):
        seen["url"], seen["payload"] = req.full_url, json.loads(req.data)
        return Resp()

    orig = quarantine.urllib.request.urlopen
    quarantine.urllib.request.urlopen = fake_urlopen
    try:
        content = quarantine.call_backend(quarantine.build_messages("x"), "http://h:1", "m")
    finally:
        quarantine.urllib.request.urlopen = orig
    p = seen["payload"]
    bad = [] if json.loads(content)["kind"] == "post" else ["reply not passed through"]
    if seen["url"] != "http://h:1/api/chat" or "tools" in p or p["format"] != quarantine.SCHEMA:
        bad.append(f"request: {seen['url']} keys {sorted(p)}")
    if p["stream"] is not False or p["options"]["temperature"] != 0:
        bad.append("request is streamed or not at temperature 0")
    return bad


@test
def quarantine_reply_is_typed_cleaned_capped_or_refused():
    bad = []
    with q_env() as t:
        res, _ = q_save(t)
        reply = q_reply(kind="manifesto", language="english", topic="T" * 500,
                        summary="Line one.\u200b\n\n\x1b[31mLine two." + "x" * 2000,
                        key_points=["p"] * 9 + [7], addresses_ai="yes", extra_field=Q_REPLY_MARK)
        with q_backend(reply):
            rc, out, _ = q_run("read", res["id"])
        s = json.loads(out)["summary"]
        if set(s) != {"kind", "language", "topic", "summary", "key_points", "addresses_ai", "asks_reader_to_act"}:
            bad.append(f"summary keys {sorted(s)}")
        if (s["kind"], s["language"], s["addresses_ai"]) != ("other", "und", None):
            bad.append(f"enum, language or bool not checked: {s['kind']} {s['language']} {s['addresses_ai']}")
        if len(s["topic"]) > quarantine.CAPS["topic"] or len(s["summary"]) > quarantine.CAPS["summary"]:
            bad.append("caps not applied")
        if any(c in s["summary"] for c in ("\u200b", "\x1b", "\n")) or len(s["key_points"]) != quarantine.MAX_POINTS:
            bad.append("summary not cleaned or points not capped")
        if Q_REPLY_MARK in out:
            bad.append("an unknown reply key came through")
        for reply in (f"not json {Q_REPLY_MARK}", json.dumps([Q_REPLY_MARK]), q_reply(summary="")):
            with q_backend(reply):
                rc, out, err = q_run("read", res["id"])
            if rc != 2 or out or Q_REPLY_MARK in err or Q_CANARY in err:
                bad.append(f"bad reply not refused cleanly: exit {rc}")
        with q_backend() as calls:
            rc, out, _ = q_run("read", res["id"], "--measure-only")
        if rc != 0 or calls or "summary" in json.loads(out) or Q_CANARY in out:
            bad.append("--measure-only called the model or printed text")
    return bad


@test
def quarantine_reader_refuses_files_outside_the_store():
    bad = []
    with q_env() as t:
        q_save(t)
        outside = t / "vault" / "atom.md"
        outside.write_text(f"vault atom {Q_CANARY}\n")
        link = t / "quarantine" / "link.md"
        link.symlink_to(outside)
        for ref in (str(outside), str(t / "quarantine" / ".." / "vault" / "atom.md"), "link", str(link),
                    "no-such-item", str(t / "quarantine" / ".reads.log")):
            with q_backend() as calls:
                rc, out, err = q_run("read", ref)
            if rc != 2 or calls or Q_CANARY in out + err:
                bad.append(f"read {ref}: exit {rc}, {len(calls)} calls")
    return bad


def q_guard_cases(script, link):
    S, Q, H = str(script), Q_STORE, Q_HOME
    deny = [
        ("Read", {"file_path": f"{Q}/2026-10-13-x.md"}, H), ("Read", {"file_path": "~/quarantine/x.md"}, "/tmp"),
        ("Read", {"file_path": "quarantine/x.md"}, H), ("Read", {"file_path": "../quarantine/x.md"}, f"{H}/vault"),
        ("Read", {"file_path": Q}, H), ("Read", {"file_path": str(link)}, "/tmp"),
        ("Edit", {"file_path": f"{Q}/x.md"}, H), ("Write", {"file_path": f"{Q}/new.md", "content": Q_CANARY}, H),
        ("NotebookEdit", {"notebook_path": f"{Q}/n.ipynb"}, H),
        ("Grep", {"pattern": Q_CANARY, "path": Q}, H), ("Grep", {"pattern": "x", "path": "~/quarantine/sub"}, H),
        ("Grep", {"pattern": "x"}, Q), ("Glob", {"pattern": "**/*.md", "path": Q}, H),
        ("Glob", {"pattern": f"{Q}/**/*.md"}, H), ("Glob", {"pattern": "quarantine/*.md"}, H),
        ("Bash", {"command": f"cat {Q}/x.md"}, "/tmp"), ("Bash", {"command": "cat ~/quarantine/x.md"}, "/tmp"),
        ("Bash", {"command": 'head -5 "$HOME/quarantine/x.md"'}, "/tmp"),
        ("Bash", {"command": "grep -r CANARY ${HOME}/quarantine"}, "/tmp"),
        ("Bash", {"command": "ls ~/quarantine"}, "/tmp"), ("Bash", {"command": "rg foo quarantine"}, H),
        ("Bash", {"command": "cd quarantine && cat *.md"}, H), ("Bash", {"command": "cat ./quarantine/x.md"}, H),
        ("Bash", {"command": "cat x.md"}, Q), ("Bash", {"command": "cd ~ && cat quarantine/x.md"}, "/tmp"),
        ("Bash", {"command": "cd && rg foo quarantine"}, "/tmp"), ("Bash", {"command": "pushd quarantine"}, H),
        ("Bash", {"command": f"python3 {S} read x; cat ~/quarantine/x.md"}, H),
        ("Bash", {"command": f"{S} read x && cat ~/quarantine/x.md"}, H),
        ("Bash", {"command": f"{S} read $(cat ~/quarantine/x.md)"}, H),
        ("Bash", {"command": f"{S} read ~/quarantine/x.md | tee out"}, H),
        ("Bash", {"command": f"{S} read ~/quarantine/x.md > out.json"}, H),
        ("Bash", {"command": f"{S} read ~/quarantine/x.md\ncat ~/quarantine/x.md"}, H),
        ("Bash", {"command": f"python3 -c \"print(open('{Q}/x.md').read())\""}, "/tmp"),
        ("Bash", {"command": f"python3 - <<'EOF'\nprint(open('{Q}/x.md').read())\nEOF"}, "/tmp"),
        ("Bash", {"command": "cat <<'EOF' | sh\ncat ~/quarantine/x.md\nEOF"}, "/tmp"),
        ("Bash", {"command": 'echo "see this $(cat ~/quarantine/x.md) here now"'}, "/tmp"),
        ("Bash", {"command": 'echo "see this `cat ~/quarantine/x.md` here now"'}, "/tmp"),
        ("Bash", {"command": "cat <<EOF\n$(cat ~/quarantine/x.md)\nEOF"}, "/tmp"),
        ("Bash", {"command": 'bash -c "cat ~/quarantine/x.md and more words"'}, "/tmp"),
        ("Bash", {"command": 'cat "~/quarantine/x.md"'}, "/tmp"),
        ("Bash", {"command": 'git commit -m "notes on ~/quarantine" && cat ~/quarantine/x.md'}, "/tmp"),
        ("Bash", {"command": f"{script.parent}/../quarantine/quarantine.py.bak read x ~/quarantine/x.md"}, H),
        # From the #15 review: operators before the script, and the bare name in other positions.
        ("Bash", {"command": f"true;cp${{IFS}}$HOME/quarantine/x.md${{IFS}}/tmp/x;/usr/bin/python3 {S} list"}, H),
        ("Bash", {"command": f"cat ~/quarantine/x.md;python3 {S} list"}, H),
        ("Bash", {"command": "cp -r quarantine /tmp/q"}, H),
        ("Bash", {"command": "tar cf /tmp/q.tar quarantine ."}, H),
        ("Bash", {"command": "find quarantine -name '*.md' -exec cat {} +"}, H),
        ("Bash", {"command": "grep -r foo quarantine -l"}, H),
        ("Bash", {"command": "grep -e foo quarantine"}, H),
        ("Bash", {"command": "ls notes && grep -rl x quarantine"}, H),
        ("Bash", {"command": "LC_ALL=C cat quarantine"}, H),
    ]
    allow = [
        ("Read", {"file_path": f"{H}/vault/_inbox/note.md"}, H), ("Read", {"file_path": f"{H}/quarantine-notes.md"}, H),
        ("Read", {"file_path": f"{H}/vault/quarantine/atom.md"}, H), ("Read", {"file_path": S}, H),
        ("Write", {"file_path": f"{H}/vault/_inbox/inbound quarantine.md", "content": "x"}, H),
        ("Grep", {"pattern": "quarantine", "path": f"{H}/vault"}, H),
        ("Glob", {"pattern": "**/quarantine*.md", "path": f"{H}/vault"}, H),
        ("Bash", {"command": f"python3 {S} read 2026-10-13-x"}, H),
        ("Bash", {"command": f"{S} read ~/quarantine/2026-10-13-x.md --measure-only"}, H),
        ("Bash", {"command": f"python3 -I {S} read {Q}/x.md"}, "/tmp"),
        ("Bash", {"command": f'{S} save --source "https://example.org/r/x/comments/1/" --from-clipboard'}, H),
        ("Bash", {"command": f"{S} list"}, Q), ("Bash", {"command": f'{S} save --source "a&b" --move /tmp/p.txt'}, H),
        ("Bash", {"command": 'git commit -m "add quarantine guard"'}, H),
        ("Bash", {"command": 'echo "the quarantine store"'}, H), ("Bash", {"command": f"cat {S}"}, H),
        ("Bash", {"command": "ls ~/quarantine-notes"}, "/tmp"), ("Bash", {"command": "grep -r quarantine ~/vault/_inbox"}, H),
        ("Bash", {"command": "rg -l quarantine vault/_inbox"}, H),
        ("Bash", {"command": "cd ~/vault && grep -rl quarantine _inbox"}, "/tmp"),
        ("Bash", {"command": "cat quarantine/x.md"}, f"{H}/vault"),
        ("Bash", {"command": 'bd create --title="Fetch" --description="Route long pages into ~/quarantine for the reader." -p 3'}, "/tmp"),
        ("Bash", {"command": "git commit -q -m 'Quarantine store at ~/quarantine, read via the reader'"}, "/tmp"),
        ("Bash", {"command": f"git commit -q -F - <<'EOF'\nAdd the store at ~/quarantine.\nItems: {Q}/<id>.md\nEOF"}, "/tmp"),
        ("Bash", {"command": "cat > /tmp/note.txt <<EOF\nThe store lives at ~/quarantine and nothing there runs.\nEOF"}, "/tmp"),
        ("WebFetch", {"url": "https://example.org/quarantine"}, H),
        ("Bash", {"command": "git grep quarantine"}, H),
        ("Bash", {"command": "grep -e quarantine notes"}, H),
        ("Bash", {"command": "rg --regexp=quarantine notes && grep -c quarantine notes/a.md"}, H),
        ("Bash", {"command": "grep -e foo -e quarantine notes"}, H),
        ("Bash", {"command": "LC_ALL=C grep quarantine notes"}, H),
    ]
    return deny, allow


@test
def quarantine_guard_known_deny_and_allow():
    bad = []
    script = MODULE / "skills/quarantine/quarantine.py"
    saved = {k: os.environ.pop(k, None) for k in ("QUARANTINE_ROOT",)}
    os.environ["QUARANTINE_ROOT"] = Q_STORE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "looks-harmless.md"
            link.symlink_to(os.path.join(Q_STORE, "x.md"))  # dangling while the store does not exist
            deny, allow = q_guard_cases(script, link)
            for tool, inp, cwd in deny:
                if not quarantine.decide(tool, inp, cwd):
                    bad.append(f"not denied: {tool} {json.dumps(inp)[:100]} cwd={cwd}")
            for tool, inp, cwd in allow:
                hit = quarantine.decide(tool, inp, cwd)
                if hit:
                    bad.append(f"denied ({hit['rule']}): {tool} {json.dumps(inp)[:100]} cwd={cwd}")
        w = quarantine.words("git commit -m \"add quarantine guard\" && cat 'quarantine/x'")
        if "add quarantine guard" not in w or "quarantine/x" not in w:
            bad.append(f"words: {w}")
    finally:
        os.environ.pop("QUARANTINE_ROOT", None)
        if saved["QUARANTINE_ROOT"] is not None:
            os.environ["QUARANTINE_ROOT"] = saved["QUARANTINE_ROOT"]
    if VERBOSE:
        print(f"     {len(deny)} deny and {len(allow)} allow cases")
    return bad


@test
def quarantine_guard_as_a_hook_process():
    bad = []
    script = MODULE / "skills/quarantine/quarantine.py"
    with q_env(QUARANTINE_ROOT=Q_STORE) as t:
        def hook(stdin):
            return subprocess.run([sys.executable, str(script), "guard"], input=stdin, capture_output=True,
                                  text=True, env=dict(os.environ)).stdout
        deny = hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": f"{Q_STORE}/x.md"},
                                "cwd": Q_HOME, "session_id": "test"}))
        try:
            ok = json.loads(deny)["hookSpecificOutput"]["permissionDecision"] == "deny"
        except (ValueError, KeyError):
            ok = False
        if not ok:
            bad.append("deny case gave no deny decision")
        for name, stdin in (("allow", json.dumps({"tool_name": "Read", "tool_input": {"file_path": f"{Q_HOME}/vault/x.md"}})),
                            ("malformed", "{not json"), ("empty", ""),
                            ("odd input", json.dumps({"tool_name": "Read", "tool_input": "x"}))):
            if hook(stdin) != "":
                bad.append(f"{name}: the hook printed a decision")
        lines = (t / "guard.log").read_text().splitlines()
        if len(lines) != 1 or not re.search(r"tool=Read rule=read-in-store target=\S+x\.md$", lines[0]):
            bad.append(f"guard log: {lines}")
    return bad


@test
def quarantine_settings_snippet():
    with q_env(QUARANTINE_ROOT=Q_STORE):
        home_rules = quarantine.settings_snippet()["permissions"]["deny"]
    with q_env(QUARANTINE_ROOT="/srv/quarantine"):
        abs_rules = quarantine.settings_snippet()["permissions"]["deny"]
        hook = quarantine.settings_snippet()["hooks"]["PreToolUse"][0]
    bad = []
    if home_rules != ["Read(~/quarantine/**)", "Edit(~/quarantine/**)"]:
        bad.append(f"home rules {home_rules}")
    if abs_rules != ["Read(//srv/quarantine/**)", "Edit(//srv/quarantine/**)"]:
        bad.append(f"absolute rules {abs_rules}")
    if not hook["hooks"][0]["command"].endswith("quarantine.py guard") or "Bash" not in hook["matcher"]:
        bad.append(f"hook entry {hook}")
    orig = quarantine.SCRIPT
    quarantine.SCRIPT = "/opt/a b/quarantine.py"
    try:
        cmd = quarantine.settings_snippet()["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    finally:
        quarantine.SCRIPT = orig
    if cmd != "python3 '/opt/a b/quarantine.py' guard":
        bad.append(f"a path with a space is not quoted: {cmd}")
    return bad


@test
def access_review_mfa_section_prints_or_says_it_could_not_read():
    bad = []
    script = str(MODULE / "skills/access-review/access_review.py")

    def run_case(name, code, *want, mutate=None):
        c = json.loads((CASES / "access-review" / f"{name}.json").read_text())
        if mutate:
            mutate(c)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "obs.json"
            f.write_text(json.dumps(c))
            p = subprocess.run([sys.executable, script, "--from-observations", str(f)], capture_output=True, text=True)
        if p.returncode != code:
            bad.append(f"{name}: exit {p.returncode}, want {code}")
        for w in want:
            if w not in p.stdout:
                bad.append(f"{name}: no {w!r} in the output: {p.stdout.strip()}")

    run_case("org-2fa-off", 1, "mfa: organisation requires two-factor authentication: no; members with it off: 3",
             "insecure second factor: 1", "outside collaborators with it off: 1", "member-2fa-off: 1 admin(s)", "lead")
    run_case("org-2fa-required", 0, "mfa: organisation requires two-factor authentication: yes; members with it off: 0")
    run_case("org-2fa-not-visible", 0, "mfa: not read (the caller must be an organisation owner)", "not visible: org_2fa")
    run_case("clean", 0, "mfa: not read in this observation file")
    run_case("clean", 0, "mfa: not applicable: the owner is a user account", mutate=lambda c: c["meta"].update(owner_type="User"))
    return bad


@test
def access_review_reads_two_factor_from_a_fixture_organisation():
    """collect_two_factor() with recorded gh answers: an owner sees the lists, a member does not, and a failed list is named."""
    bad, calls = [], []
    org = {"login": "o", "type": "Organization", "two_factor_requirement_enabled": False}
    owner_answers = {
        "orgs/o": org,
        "orgs/o/members?filter=2fa_disabled&per_page=100": [{"login": "dev"}, {"login": "qa"}],
        "orgs/o/members?filter=2fa_insecure&per_page=100": [{"login": "ops"}],
        "orgs/o/outside_collaborators?filter=2fa_disabled&per_page=100": [{"login": "contractor"}],
    }

    def with_answers(answers, errors=None):
        def fake(path):
            calls.append(path)
            if path in (errors or {}):
                return None, errors[path]
            return answers[path], None
        real = access.gh
        access.gh = fake
        try:
            obs = {"errors": {}}
            access.collect_two_factor(obs, "o")
        finally:
            access.gh = real
        return obs

    obs = with_answers(owner_answers)
    want = {"required": False, "members_off": ["dev", "qa"], "members_insecure": ["ops"], "outside_off": ["contractor"]}
    if obs.get("org_2fa") != want or obs["errors"]:
        bad.append(f"owner: {obs}")
    err = "gh: Must be an owner of the organization (HTTP 403)"
    obs = with_answers({"orgs/o": {"login": "o"}}, {"orgs/o/members?filter=2fa_disabled&per_page=100": err})
    if "org_2fa" in obs or obs["errors"].get("org_2fa") != err:
        bad.append(f"member: {obs}")
    obs = with_answers({"orgs/o": {"login": "o"}, "orgs/o/members?filter=2fa_disabled&per_page=100": []})
    if "org_2fa" in obs or "two_factor_requirement_enabled" not in obs["errors"].get("org_2fa", ""):
        bad.append(f"organisation record without the field: {obs}")
    insecure_path = "orgs/o/members?filter=2fa_insecure&per_page=100"
    obs = with_answers(owner_answers, {insecure_path: "gh: Validation Failed (HTTP 422)"})
    if obs.get("org_2fa", {}).get("members_insecure") is not None or "org_2fa_insecure" not in obs["errors"]:
        bad.append(f"a failed insecure list must stay unread and be named: {obs}")
    if any(not c.startswith("orgs/o") for c in calls):
        bad.append(f"a request outside the organisation: {calls}")
    return bad


@test
def access_review_mfa_flags_split_admins_from_members():
    bad = []
    c = json.loads((CASES / "access-review/org-2fa-off.json").read_text())
    r = access.assess(c, datetime.date(2026, 10, 11))
    by = {(x["level"], x["id"]): x["evidence"] for x in r["flags"]}
    red, amber = by.get(("red", "member-2fa-off"), ""), by.get(("amber", "member-2fa-off"), "")
    if "lead" not in red or "dev" in red:
        bad.append(f"the admin flag must name lead only: {red}")
    if "dev" not in amber or "qa" not in amber or "lead" in amber:
        bad.append(f"the member flag must name dev and qa only: {amber}")
    c["org_2fa"]["members_off"] = [f"user{i:02}" for i in range(25)]
    amber = [x["evidence"] for x in access.assess(c, datetime.date(2026, 10, 11))["flags"] if x["id"] == "member-2fa-off"][0]
    if "and 15 more" not in amber or "user24" in amber:
        bad.append(f"a long list must be capped at {access.LOGIN_LIST} logins: {amber}")
    return bad


def entrance_row(entrance="Cloud console", kind="cloud", holders="1 role", owner="Dana Example", enforced="yes", method="security-key",
                 reason="", who="", expires="", checked="2026-10-01", evidence="Sign-in policy"):
    return "| " + " | ".join([entrance, kind, holders, owner, enforced, method, reason, who, expires, checked, evidence]) + " |"


ENTRANCE_HEAD = ("| Entrance | Kind | Admin holders | Owner | MFA enforced | Method | Reason | Accepted by | Expires | Last checked | Evidence |\n"
                 "|---|---|---|---|---|---|---|---|---|---|---|\n")
TODAY = datetime.date(2026, 10, 18)


def check_entrances(root, today=TODAY, **options):
    opts = json.loads(json.dumps(admin.DEFAULTS))
    opts.update(options)
    ctx = run.Ctx(root, opts, {}, [], "manual", None)
    ctx.today = today
    return run.run_one(admin, ctx)


def entrances(rows, today=TODAY, text=None, **options):
    """Run the check on a page with these rows (or this text); returns (result, [(rule, entrance), ...]).
    required_kinds defaults to none, so a test sees only the rule it is about."""
    options.setdefault("required_kinds", [])
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "docs/security/admin-entrances.md"
        page.parent.mkdir(parents=True)
        page.write_text(text if text is not None else "---\nowner: x\n---\n" + ENTRANCE_HEAD + "\n".join(rows) + "\n")
        res = check_entrances(Path(tmp), today, **options)
    return res, sorted((h["rule"], h["snippet"].split(":")[0]) for h in res["hits"])


@test
def admin_entrances_fixtures():
    bad = []
    fx = MODULE / "checks/fixtures/security.admin-entrances"
    res = check_entrances(fx / "pass")
    if res["result"] != "pass" or res["hits"]:
        bad.append(f"pass fixture: {res['result']}, {res['hits']}")
    res = check_entrances(fx / "fail")
    got = sorted((h["rule"], h["snippet"].split(":")[0]) for h in res["hits"])
    want = sorted([("mfa-not-enforced", "Cloud console and root account"), ("weak-method", "Identity provider admin"),
                   ("exception-expired", "Domain controller"), ("row-incomplete", "VPN"),
                   ("row-incomplete", "Source control organisation"), ("row-incomplete", "Source control organisation"),
                   ("row-incomplete", "Domain registrar"), ("row-incomplete", "Domain registrar"),
                   ("kind-missing", "no row of kind source-ci; add one, or a row with MFA enforced n/a and a reason"),
                   ("kind-missing", "no row of kind password-manager; add one, or a row with MFA enforced n/a and a reason"),
                   ("kind-missing", "no row of kind saas; add one, or a row with MFA enforced n/a and a reason"),
                   ("kind-missing", "no row of kind on-prem; add one, or a row with MFA enforced n/a and a reason")])
    if res["result"] != "fail" or got != want:
        bad.append(f"fail fixture: {res['result']}, got {got}")
    for name, code in (("pass", 0), ("fail", 1)):
        p = subprocess.run([sys.executable, str(MODULE / "checks/admin_entrances.py"), str(fx / name)], capture_output=True, text=True)
        if p.returncode != code:
            bad.append(f"standalone run on {name}: exit {p.returncode}, want {code}: {p.stdout.strip()[:200]}")
    return bad


@test
def admin_entrances_exceptions_need_a_reason_a_person_and_a_date():
    bad = []
    full = dict(enforced="no", method="none", reason="Vendor has no second factor; office range only", who="Sam Example, CTO", expires="2026-12-01")
    res, got = entrances([entrance_row("A", **full)])
    if res["result"] != "pass" or "1 on a dated exception" not in res["detail"]:
        bad.append(f"a complete exception: {res['result']}, {got}, {res['detail']}")
    for field, label in (("reason", "a reason"), ("who", "a person who accepted it"), ("expires", "an expiry date")):
        res, got = entrances([entrance_row("A", **{**full, field: ""})])
        if got != [("mfa-not-enforced", "A")] or label not in res["hits"][0]["snippet"]:
            bad.append(f"no {field}: {got}, {[h['snippet'] for h in res['hits']]}")
    res, got = entrances([entrance_row("A", **{**full, "expires": "2026-12-32"})])
    if got != [("mfa-not-enforced", "A")] or "YYYY-MM-DD" not in res["hits"][0]["snippet"]:
        bad.append(f"an impossible date: {got}")
    res, got = entrances([entrance_row("A", **{**full, "reason": "<reason>"})])
    if got != [("mfa-not-enforced", "A")]:
        bad.append(f"a placeholder reason: {got}")
    # The exception ends after its date: valid on the day, a hit the day after.
    if entrances([entrance_row("A", **{**full, "expires": "2026-10-18"})])[1]:
        bad.append("an exception that expires today must still hold")
    res, got = entrances([entrance_row("A", **{**full, "expires": "2026-10-17"})])
    if got != [("exception-expired", "A")] or "2026-10-17" not in res["hits"][0]["snippet"]:
        bad.append(f"an exception that expired yesterday: {got}")
    res, got = entrances([entrance_row("A", **{**full, "enforced": "partial", "method": "security-key"})])
    if res["result"] != "pass":
        bad.append(f"partial with a complete exception: {got}")
    res, got = entrances([entrance_row("A", **{**full, "enforced": "partial", "reason": "", "who": "", "expires": ""})])
    if got != [("mfa-not-enforced", "A")] or "some admin accounts only" not in res["hits"][0]["snippet"]:
        bad.append(f"partial without an exception: {got}")
    return bad


@test
def admin_entrances_method_bar():
    bad = []
    for method, want in (("security-key", []), ("passkey", []), ("certificate", []), ("totp", []), ("push", []),
                         ("sms", [("weak-method", "A")]), ("voice", [("weak-method", "A")]), ("email", [("weak-method", "A")]),
                         ("none", [("row-incomplete", "A")]), ("magic", [("row-incomplete", "A")]), ("", [("row-incomplete", "A")]),
                         ("security-key, sms", [("weak-method", "A")]), ("passkey + totp", []), ("SMS", [("weak-method", "A")])):
        got = entrances([entrance_row("A", method=method)])[1]
        if got != want:
            bad.append(f"default bar, method {method!r}: {got}, want {want}")
    for method, want in (("security-key", []), ("totp", [("weak-method", "A")]), ("push", [("weak-method", "A")]),
                         ("passkey, totp", [("weak-method", "A")]), ("sms", [("weak-method", "A")])):
        got = entrances([entrance_row("A", method=method)], phishing_resistant_only=True)[1]
        if got != want:
            bad.append(f"phishing_resistant_only, method {method!r}: {got}, want {want}")
    exempt = dict(method="sms", reason="Vendor supports SMS only; office range only", who="Sam Example", expires="2026-12-01")
    res, got = entrances([entrance_row("A", **exempt)])
    if res["result"] != "pass":
        bad.append(f"a weak method with a complete exception: {got}")
    return bad


@test
def admin_entrances_rows_name_an_owner_a_kind_and_evidence():
    bad = []
    cases = [
        (entrance_row("A", owner=""), "no owner"), (entrance_row("A", owner="<name>"), "no owner"),
        (entrance_row("A", kind="database"), "kind is not one of"), (entrance_row("A", holders=""), "no admin holders"),
        (entrance_row("A", evidence=""), "no evidence"), (entrance_row("A", checked=""), "no last checked"),
        (entrance_row("A", checked="01.10.2026"), "not a YYYY-MM-DD"), (entrance_row("A", checked="2026-10-19"), "in the future"),
        (entrance_row("A", enforced="maybe"), "MFA enforced is not yes"), (entrance_row("A", enforced="")  , "MFA enforced is not yes"),
    ]
    for row, want in cases:
        res, got = entrances([row])
        if [r for r, _ in got] != ["row-incomplete"] or want not in res["hits"][0]["snippet"]:
            bad.append(f"{want}: {got}, {[h['snippet'] for h in res['hits']]}")
    na = entrance_row("Domain controller", kind="directory", enforced="n/a", method="none", reason="No directory server", holders="", evidence="", checked="")
    if entrances([na])[1]:
        bad.append("a kind the organisation does not have needs an owner and a reason only")
    got = entrances([entrance_row("Domain controller", kind="directory", enforced="n/a", method="none", reason="")])[1]
    if got != [("row-incomplete", "Domain controller")]:
        bad.append(f"n/a without a reason: {got}")
    half = "| | cloud | 1 role | Dana | yes | passkey | | | | 2026-10-01 | policy |"
    if entrances([half])[1] != [("row-incomplete", "row has no entrance name")]:
        bad.append(f"a half-filled row without an entrance name: {entrances([half])[1]}")
    placeholder_row = "| `<cloud console>` | cloud | `<roles>` | `<name>` | `<yes>` | `<method>` | `<reason>` | `<name>` | `<date>` | `<date>` | `<where>` |"
    res, got = entrances([placeholder_row], required_kinds=["cloud"])
    if [r for r, _ in got] != ["kind-missing"]:
        bad.append(f"an unfilled template row counts as no row: {got}")
    res, got = entrances(["| Cloud console | cloud | 1 role |"])
    if res["result"] != "fail" or not got:
        bad.append(f"a row with fewer cells than the header must be reported: {got}")
    return bad


@test
def admin_entrances_required_kinds_and_page_shape():
    bad = []
    rows = [entrance_row("A", kind="cloud"), entrance_row("B", kind="saas", enforced="n/a", method="none", reason="No SaaS admin consoles")]
    res, got = entrances(rows, required_kinds=["cloud", "saas", "on-prem"])
    if [r for r, _ in got] != ["kind-missing"] or "on-prem" not in res["hits"][0]["snippet"]:
        bad.append(f"required kinds: {got}")
    if entrances(rows, required_kinds=["Cloud"])[1]:
        bad.append("kind names compare without case")
    res, _ = entrances([], text="")
    with tempfile.TemporaryDirectory() as tmp:
        res = check_entrances(Path(tmp))
    if res["result"] != "n/a":
        bad.append(f"no page: {res['result']}")
    res, got = entrances([], text="---\nowner: x\n---\nNo table here.\n")
    if res["result"] != "fail" or got != [("no-table", "no inventory table")]:
        bad.append(f"no table: {res['result']}, {got}")
    res, got = entrances([], text="| Entrance | Kind | MFA enforced |\n|---|---|---|\n| A | cloud | yes |\n")
    if res["result"] != "fail" or not got or any(r != "no-table" for r, _ in got):
        bad.append(f"a table without the other columns: {res['result']}, {got}")
    fenced = "```\n" + ENTRANCE_HEAD + entrance_row("A", enforced="no", method="none") + "\n```\n"
    res, got = entrances([], text=fenced)
    if got != [("no-table", "no inventory table")]:
        bad.append(f"a table inside a code fence must not count: {got}")
    res, got = entrances([], text="---\nowner: x\n---\n" + ENTRANCE_HEAD)
    if res["result"] != "n/a":
        bad.append(f"a table with no rows and no required kinds: {res['result']}, {got}")
    shuffled = ("| MFA enforced | Entrance | Evidence | Kind | Admin holders | Owner | Method | Reason | Accepted by | Expires | Last checked |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| yes | A | policy | cloud | 1 role | Dana | security-key | | | | 2026-10-01 |\n")
    res, got = entrances([], text=shuffled)
    if res["result"] != "pass":
        bad.append(f"columns read by name, not by position: {got}")
    with tempfile.TemporaryDirectory() as tmp:
        other = Path(tmp) / "ops/mfa.md"
        other.parent.mkdir()
        other.write_text(ENTRANCE_HEAD + entrance_row("A") + "\n")
        res = check_entrances(Path(tmp), page="ops/mfa.md", required_kinds=[])
    if res["result"] != "pass":
        bad.append(f"page option: {res['result']}")
    return bad


@test
def admin_entrances_template_stays_in_step_with_the_check():
    bad = []
    text = (MODULE / "templates/docs/security/admin-entrances.md").read_text()
    tabs = admin.tables(text)
    inventory = [t for t in tabs if "entrance" in [admin.plain(c).lower() for c in t[0][1]]]
    if len(inventory) != 1:
        return [f"want one inventory table in the template, found {len(inventory)}"]
    head = [admin.plain(c).lower() for c in inventory[0][0][1]]
    if tuple(head) != admin.COLUMNS:
        bad.append(f"template columns {head} differ from the check's {list(admin.COLUMNS)}")
    explained = [admin.plain(r[1][0]).lower() for t in tabs if t[0][1][0] == "Column" for r in t[1:]]
    if tuple(explained) != admin.COLUMNS:
        bad.append(f"the column table of the template lists {explained}")
    for kind in admin.KINDS:
        if f"`{kind}`" not in text:
            bad.append(f"kind {kind} is not named in the template")
    for method in admin.WEAKNESS:
        if f"`{method}`" not in text:
            bad.append(f"method {method} is not named in the template")
    # As installed (every cell a placeholder), the page reports only the kinds that have no row yet.
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "docs/security/admin-entrances.md"
        page.parent.mkdir(parents=True)
        page.write_text(text)
        res = check_entrances(Path(tmp))
    rules = sorted({h["rule"] for h in res["hits"]})
    if res["result"] != "fail" or rules != ["kind-missing"]:
        bad.append(f"the template as installed: {res['result']}, rules {rules}")
    reported = sorted(re.match(r"no row of kind ([\w-]+)", h["snippet"]).group(1) for h in res["hits"])
    if reported != sorted(admin.DEFAULTS["required_kinds"]):
        bad.append(f"the template as installed reports kinds {reported}, want {sorted(admin.DEFAULTS['required_kinds'])}")
    unknown = [k for k in admin.DEFAULTS["required_kinds"] if k not in admin.KINDS]
    if unknown:
        bad.append(f"required_kinds names kinds the check does not know: {unknown}")
    return bad


@test
def admin_entrances_output_shows_no_cell_value():
    """A hit names the entrance and the field. Reason, holders, evidence and owner text never reach the output."""
    canary = "CANARY-7f3a"
    rows = [entrance_row("A", enforced="no", method="none", reason=f"{canary}-reason", who=f"{canary}-who", expires="2020-01-01",
                         holders=f"{canary}-holders", owner=f"{canary}-owner", evidence=f"{canary}-evidence"),
            entrance_row("B", enforced="no", method="none", reason=f"{canary}-reason", who="", expires="", evidence=f"{canary}-evidence")]
    res, _ = entrances(rows)
    bad = [] if canary not in json.dumps(res) else ["the result carries a cell value"]
    if len(res["hits"]) != 2:
        bad.append(f"want two hits, got {len(res['hits'])}")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "docs/security/admin-entrances.md"
        page.parent.mkdir(parents=True)
        page.write_text(ENTRANCE_HEAD + "\n".join(rows) + "\n")
        p = subprocess.run([sys.executable, str(MODULE / "checks/admin_entrances.py"), tmp], capture_output=True, text=True)
    if canary in p.stdout + p.stderr:
        bad.append("the standalone run prints a cell value")
    if p.returncode != 1:
        bad.append(f"standalone run: exit {p.returncode}, want 1")
    return bad


@test
def admin_entrances_lists_every_kind_the_skill_walks():
    """The skill walks the kinds in the check's order and the README names the module's check next to its siblings."""
    bad = []
    skill = (MODULE / "skills/admin-entrances/SKILL.md").read_text()
    for kind in admin.KINDS:
        if f"`{kind}`" not in skill:
            bad.append(f"the skill does not walk kind {kind}")
    readme = (MODULE / "README.md").read_text()
    if "security.admin-entrances" not in readme or "### security.admin-entrances" not in readme:
        bad.append("the README has no section for security.admin-entrances")
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
