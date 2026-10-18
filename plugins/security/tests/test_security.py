#!/usr/bin/env python3
"""Tests for the security module: the two gate checks beyond their fixture runs, and the three scripts.

- provenance.py: every recorded case in cases/provenance/ gives its risk grade and exactly its red and amber signals;
  the recommendation follows the archive install path and the data scope; attested release assets are counted per asset.
- access_review.py: every case in cases/access-review/ gives exactly its red and amber flags.
- intake.py: fix-by dates from the default windows, the policy template and a custom policy; dedupe; tracked issues.
- osv_query.py: purls from an SPDX and a CycloneDX SBOM, and the rows built from recorded OSV answers (no network).
- security.secrets: each fail fixture gives one hit of its kind; allow, allow_hashes, the allow file and tracked_only behave.
- security.action-owners: each fail fixture gives one hit of its kind; the owner list option and the listing behave;
  its LOCAL prefixes and USES pattern match gate.actions-pinned.
- security.secrets hooks (pre-push, pre-commit, check, history) against a local bare remote: each hit kind is refused with the remote
  unchanged and no value or way around the hook in any output; only added lines are read, also in merges; messages, tags, ref names and
  file names; the pushed gate config and allow file; git settings, attributes, binary files and replace refs that would hide a line;
  the dispatcher beside the private-terms hook in both install orders; a git template; foreign hooks are left alone; the repository's
  own files are clean with its .secrets-allow.
- security.private-terms: each fail fixture gives one hit of its kind; no output shows a term; n/a without a list; list errors
  name a line only; the allow file; tracked files and built folders; the pre-push hook against a local remote; the scan CLI.
- quarantine.py: save marks and stores an item without printing it, and refuses a store inside a vault, an overlay, a
  protected folder or a git work tree; list and remove stay inside the store; read returns the envelope and never the
  raw text, sends the reader fenced, stripped and truncated text with no tools in the request, and types, cleans and
  caps the reply or refuses it without an echo; the guard denies every known route into the store and allows the
  known near misses, as a function and as a hook process; the settings snippet. Canary strings only; no network.

Standard library only, Python 3.9+. Usage: python3 plugins/security/tests/test_security.py [-v]
"""
import contextlib, datetime, hashlib, importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile
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
            "keys/id_example": "private-key", ".secrets-allow": "allow-entry"}
    bad = [] if (kinds, len(res["hits"])) == (want, len(want)) else [f"hits: {[(h['file'], h.get('rule')) for h in res['hits']]}"]
    leaked = [h["snippet"] for h in res["hits"] if "EXAMPLE" in h["snippet"]]
    return bad + [f"value in a snippet: {s}" for s in leaked]


@test
def secrets_allow_options():
    fail = MODULE / "checks/fixtures/security.secrets/fail"
    bad = []
    res = check_rule(secrets, fail, allow=["config/*", "keys/*"])
    if sorted(h["file"] for h in res["hits"]) != [".env", ".secrets-allow"]:
        bad.append(f"allow by path: {[h['file'] for h in res['hits']]}")
    aws = [h for h in check_rule(secrets, fail)["hits"] if h.get("rule") == "aws-access-key-id"][0]
    digest = aws["snippet"].rsplit("sha256:", 1)[1]
    res = check_rule(secrets, fail, allow_hashes=[digest])
    if any(h.get("rule") == "aws-access-key-id" for h in res["hits"]) or len(res["hits"]) != 8:
        bad.append(f"allow by hash {digest}: {len(res['hits'])} hits")
    res = check_rule(secrets, fail, allow_hashes=[digest[:6]])
    if len(res["hits"]) != 9:
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
        (root / "local.env.txt").write_text(f"key = {AWS_EXAMPLE}\n")
        git("add", "README.md")
        res = check_rule(secrets, root)
        if res["hits"] or "1 tracked" not in res["detail"]:
            bad.append(f"untracked file read: {res['detail']}, {res['hits']}")
        (root / "logo.bin").write_bytes(b"\x89PNG\0\0 " + AWS_EXAMPLE.encode())
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


# ---------------------------------------------------------------- secrets hooks
# Made-up values, assembled at run time so that no source line matches a pattern and the repository's own scan stays clean.

FAKE = {
    "anthropic-key": "sk-ant-" + "api03-Zq8Xv2Lm9Rt4Wd7Yb1Nc",
    "sk-key": "sk-" + "Zq8Xv2Lm9Rt4Wd7Yb1Nc5Hs3Jk6Pf0Ae",
    "aws-access-key-id": "AKIA" + "IOSFODNN7EXAMPLE",
    "github-token": "ghp_" + "Zq8Xv2Lm9Rt4Wd7Yb1Nc5Hs3Jk6Pf0Ae1Bn",
    "github-fine-grained-token": "github_pat_" + "11ABCDEFG0Zq8Xv2Lm9Rt4Wd7Yb1Nc5Hs3Jk6Pf0Ae1Bn",
    "slack-token": "xoxb-" + "1234567890-Zq8Xv2Lm9Rt4",
    "private-key": "-----BEGIN RSA " + "PRIVATE KEY-----",
}
AWS_EXAMPLE = FAKE["aws-access-key-id"]
NO_HOOKS = ["-c", "core.hooksPath=" + os.devnull]  # builds a commit the hook under test has not seen


def sha12(value):
    return hashlib.sha256(value.encode()).hexdigest()[:12]


class HookRepo:
    """A work tree on branch main with a local bare remote and the secrets hook installed."""

    def __init__(self, tmp, tier="block", pre_commit=False, install=True, name="work"):
        self.tmp = Path(tmp)
        self.work, self.remote = self.tmp / name, self.tmp / (name + "-remote.git")
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Fixture",
                        GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.env.pop("POWERSUIT_OVERLAY", None)
        self.bad, self.seen = [], []
        self.git("init", "-q", "--bare", str(self.remote), cwd=self.tmp)
        self.git("init", "-q", str(self.work), cwd=self.tmp)
        self.git("checkout", "-q", "-b", "main")
        self.git("remote", "add", "origin", str(self.remote))
        if install:
            self.install(tier, pre_commit)

    def git(self, *a, cwd=None, inp=None):
        return subprocess.run(["git", *a], cwd=cwd or self.work, env=self.env, capture_output=True, text=True, input=inp)

    def install(self, tier="block", pre_commit=False):
        code, lines = secrets.install_hook(self.work / ".git/hooks", tier, pre_commit)
        if code:
            self.bad.append(f"install_hook: {lines}")

    def commit(self, path, text, message="Add a file", extra=()):
        f = self.work / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(text if isinstance(text, bytes) else text.encode())
        self.git("add", "-A")
        p = self.git(*extra, "commit", "-q", "-m", message)
        self.seen.append(p.stdout + p.stderr)
        return p

    def push(self, *args, want):
        p = self.git("push", "-q", "origin", *args)
        self.seen.append(p.stdout + p.stderr)
        got = "ok" if p.returncode == 0 else "stopped"
        if got != want:
            self.bad.append(f"push {' '.join(args)}: {got}, want {want}: {p.stderr.strip()[-300:]}")
        return p.stderr

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()

    def remote_has(self, rev):
        return self.git("cat-file", "-e", rev + "^{commit}", cwd=self.remote).returncode == 0

    def expect(self, text, *needles):
        for n in needles:
            if n not in text:
                self.bad.append(f"output lacks {n!r}: {text.strip()[-300:]}")

    def finish(self):
        """The failures so far, plus a check that no output held a value or a way around the hook."""
        text = "\n".join(self.seen)
        found = [f"value of {k} in the output" for k, v in FAKE.items() if v in text or v[-12:] in text]
        if "no-verify" in text.lower():
            found.append("the output names a way to skip the hook")
        return self.bad + found


@test
def secrets_hook_refuses_each_kind_and_prints_no_value():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        for kind, value in FAKE.items():
            r.commit(f"cfg/{kind}.txt", f"token = {value}\n", f"Add {kind}")
            tip = r.head()
            err = r.push("main", want="stopped")
            r.expect(err, f"cfg/{kind}.txt:1 {kind} ", f"sha256:{sha12(value)}", ".secrets-allow")
            if r.remote_has(tip):
                r.bad.append(f"{kind}: the commit reached the remote")
            r.git("reset", "-q", "--hard", "origin/main")
        r.commit("config.yml", "region = eu-central-1\nname = Project\n", "Clean file")
        r.push("main", want="ok")
        r.commit(".env", "PORT=8080\n", "Add .env")
        err = r.push("main", want="stopped")
        r.expect(err, ".env env-file")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit("app/.env.local", "PORT=8080\n", "Add .env.local")
        r.push("main", want="stopped")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit(".env.example", "PORT=\n", "Add the template")
        r.push("main", want="ok")
        return r.finish()


@test
def secrets_hook_reads_only_what_the_push_adds():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp, tier="warn")
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        r.commit("legacy.txt", f"first\nkey = {AWS_EXAMPLE}\n", "A key that is already public")
        err = r.push("main", want="ok")  # tier warn: the hits are reported, the push goes on
        r.expect(err, "tier warn", "legacy.txt:2 aws-access-key-id AKIA****")
        r.install("block")
        r.commit("legacy.txt", f"first\nkey = {AWS_EXAMPLE}\nlast line\n", "Add a line next to the key")
        r.push("main", want="ok")  # the key line is not an added line
        r.commit("legacy.txt", "first\nlast line\n", "Remove the key")
        r.push("main", want="ok")  # a deleted line sends nothing
        r.commit("notes.txt", f"one\ntwo\nkey = {FAKE['slack-token']}\n", "Add a key")
        r.commit("notes.txt", "one\ntwo\n", "Remove it again")
        err = r.push("main", want="stopped")  # the first commit still carries it
        r.expect(err, "notes.txt:3 slack-token xox?-****")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit("notes.txt", "one\nkey = " + FAKE["github-token"] + "\n", "Add a key")
        r.commit("notes.txt", "zero\none\nkey = " + FAKE["github-token"] + "\n", "Shift the line")
        err = r.push("main", want="stopped")
        r.expect(err, "notes.txt:2 github-token")
        if "notes.txt:3" in err:
            r.bad.append("a line that only moved counted as added")
        r.git("reset", "-q", "--hard", "origin/main")
        r.git("checkout", "-q", "-b", "feature")
        r.commit("feature.txt", "A feature.\n", "Feature")
        r.push("feature", want="ok")  # a new branch sends its own commits only
        r.push("HEAD:refs/heads/copy", want="ok")
        return r.finish()


@test
def secrets_hook_reads_messages_tags_ref_names_and_paths():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        r.commit("a.txt", "a\n", "Export TOKEN=" + FAKE["github-token"] + "\n\nsecond line")
        err = r.push("main", want="stopped")
        r.expect(err, "commit-message:1 github-token gh?_****")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit("b.txt", "b\n", "Add b")
        r.git("tag", "-a", "v1", "-m", "Release\nkey " + FAKE["sk-key"])
        err = r.push("v1", want="stopped")
        r.expect(err, "tag-message:2 sk-key sk-****")
        r.git("tag", "-d", "v1")
        r.git("tag", "-a", "inner", "-m", "Inner\nkey " + FAKE["slack-token"])
        inner = r.git("rev-parse", "inner").stdout.strip()
        r.git("tag", "-a", "outer", "-m", "Outer tag", inner)  # a tag that points to a tag
        err = r.push("outer", want="stopped")
        r.expect(err, "tag-message:2 slack-token xox?-****")
        r.git("tag", "-d", "outer", "inner")
        err = r.push("HEAD:refs/heads/" + FAKE["aws-access-key-id"], want="stopped")
        r.expect(err, "ref-name:1 aws-access-key-id")
        blob = r.git("hash-object", "-w", "--stdin", inp="plain text\n").stdout.strip()
        r.git("tag", "blobtag", blob)
        err = r.push("blobtag", want="stopped")
        r.expect(err, "points to a blob", "nothing was checked")
        return r.finish()


@test
def secrets_hook_masks_a_key_in_a_path():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        r.commit("keys/" + FAKE["aws-access-key-id"] + ".txt", f"x = {FAKE['aws-access-key-id']}\n", "A file named like its key")
        err = r.push("main", want="stopped")
        r.expect(err, "keys/AKIA****.txt:1 aws-access-key-id", "keys/AKIA****.txt aws-access-key-id AKIA****")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit("notes/" + FAKE["github-token"], "plain text\n", "A file named like a token, with nothing inside")
        err = r.push("main", want="stopped")
        r.expect(err, "notes/gh?_**** github-token gh?_****")
        return r.finish()


@test
def secrets_hook_merges_count_only_what_the_merge_adds():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp, tier="warn")
        r.commit("README.md", "# Project\n", "Start")
        r.commit("shared.txt", "one\n", "Shared file")
        r.push("main", want="ok")
        r.git("checkout", "-q", "-b", "feature")
        r.commit("legacy.txt", f"key = {AWS_EXAMPLE}\n", "A key on a branch")
        r.commit(".env", "PORT=1\n", "An env file on a branch")
        r.push("feature", want="ok")
        r.install("block")
        r.git("checkout", "-q", "main")
        r.commit("main.txt", "main\n", "Work on main")
        r.git("merge", "-q", "--no-ff", "-m", "Merge feature", "feature")
        r.push("main", want="ok")  # the key comes in with a commit the remote has
        r.git("checkout", "-q", "-b", "left")
        r.commit("shared.txt", "left two\n", "Left")
        r.git("checkout", "-q", "main")
        r.git("checkout", "-q", "-b", "right")
        r.commit("shared.txt", "right two\n", "Right")
        merged = r.git("merge", "-q", "left")
        (r.work / "shared.txt").write_text(f"key = {FAKE['github-token']}\n")
        r.git("add", "shared.txt")
        r.git("commit", "-q", "-m", "Merge left")
        err = r.push("right", want="stopped")  # the resolution adds a line that neither parent has
        r.expect(err, "shared.txt:1 github-token")
        if "CONFLICT" not in merged.stdout + merged.stderr:
            r.bad.append("the merge did not conflict")
        return r.finish()


@test
def secrets_hook_allow_file():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        aws = AWS_EXAMPLE
        entry = lambda glob, kind, digest, reason="Example value from the vendor documentation": f"{glob} {kind} {digest} {reason}\n"

        def attempt(name, allow, want, *needles, text=None):
            f = r.work / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text or f"key = {aws}\n")
            (r.work / ".secrets-allow").write_text(allow)
            r.git("add", "-A")
            r.git("commit", "-q", "-m", "Try " + name)
            err = r.push("main", want=want)
            r.expect(err, *needles)
            if want == "stopped":
                r.git("reset", "-q", "--hard", "origin/main")
            return err

        attempt("docs/a.md", entry("docs/a.md", "aws-access-key-id", "sha256:" + sha12(aws)), "ok",
                "this push changes .secrets-allow or gate/gate.json", "1 hits in this scan are allowed by .secrets-allow")
        attempt("docs/b.md", entry("docs/*", "*", sha12(aws).upper()), "ok")
        attempt("docs/c.md", entry("docs/*", "aws-access-key-id", "*"), "ok")
        attempt("docs/d.md", entry("docs/d.md", "aws-access-key-id", "sha256:" + sha12(aws)), "stopped", "docs/d.md:2 slack-token",
                text=f"key = {aws}\nother = {FAKE['slack-token']}\n")  # allows the one value only
        attempt("docs/e.md", entry("docs/e.md", "aws-access-key-id", "sha256:" + sha12(aws), ""), "stopped", ".secrets-allow:1 allow entry without a reason")
        attempt("docs/f.md", "docs/f.md aws-access-key-id sha256:xyz reason\n", "stopped", ".secrets-allow:1 allow entry whose hash")
        attempt("docs/g.md", entry("*", "*", "*"), "stopped", ".secrets-allow:1 allow entry that allows every secret")
        attempt("docs/h.md", entry("**", "aws-access-key-id", "*"), "stopped", ".secrets-allow:1 allow entry that allows every secret")
        attempt("docs/i.md", entry("docs/other.md", "aws-access-key-id", "sha256:" + sha12(aws)), "stopped", "docs/i.md:1 aws-access-key-id")
        attempt("docs/j.md", entry("docs/j.md", "slack-token", "*"), "stopped", "docs/j.md:1 aws-access-key-id")
        attempt("docs/k.md", entry("docs/k.md", "aws-access-key-id", "ffffffff"), "stopped", "docs/k.md:1 aws-access-key-id")
        attempt("app/.env", entry("app/.env", "env-file", "*"), "ok", text="PORT=1\n")
        attempt("app2/.env", entry("app2/.env", "env-file", "sha256:" + sha12(aws)), "stopped", "app2/.env env-file", text="PORT=1\n")
        # the file counts as the pushed commit has it: an edit in the work tree allows nothing
        r.commit("docs/l.md", f"key = {aws}\n", "Add a key", extra=())
        (r.work / ".secrets-allow").write_text(entry("docs/l.md", "*", "*"))
        r.push("main", want="stopped")
        return r.finish()


@test
def secrets_hook_reads_the_gate_config_of_the_pushed_commit():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        aws = AWS_EXAMPLE
        r.commit("gate/fixtures/security.secrets/fail/aws.txt", f"key = {aws}\n", "Gate fixtures")
        r.push("main", want="ok")  # the gate's default exclude list covers /gate/, so the hook leaves it out too
        gate = lambda body: json.dumps(body)
        r.commit("gate/gate.json", gate({"exclude": [".git/"], "rules": {}}), "Gate config without /gate/")
        r.commit("gate/fixtures/security.secrets/fail/slack.txt", f"key = {FAKE['slack-token']}\n", "More fixtures")
        err = r.push("main", want="stopped")
        r.expect(err, "gate/fixtures/security.secrets/fail/slack.txt:1 slack-token")
        r.git("reset", "-q", "--hard", "origin/main")
        team = {"rules": {"security.secrets": {"tier": "block", "options": {"patterns": {"acme-token": [r"\bacme_[0-9a-f]{20}\b", "acme_****"]}}}}}
        r.commit("gate/gate.json", gate(team), "Add the team's token format")
        r.commit("c.txt", "token = acme_" + "0123456789abcdef0123\n" + f"key = {aws}\n", "Use it")
        err = r.push("main", want="stopped")
        r.expect(err, "c.txt:1 acme-token acme_****")
        if "aws-access-key-id" in err:
            r.bad.append("the team's pattern list replaces the defaults, as in the gate check")
        r.git("reset", "-q", "--hard", "origin/main")
        r.commit("gate/gate.json", gate({"rules": {"security.secrets": {"options": {"allow": ["docs/*"], "allow_hashes": [sha12(FAKE["slack-token"])]}}}}), "Allow by the gate's options")
        r.commit("docs/x.md", f"key = {aws}\nother = {FAKE['slack-token']}\n", "Documented values")
        r.push("main", want="ok")
        for bad_config, needle in (("{not json", "gate/gate.json is not valid JSON"),
                                   (gate([1]), "gate/gate.json is not a JSON object"),
                                   (gate({"rules": {"security.secrets": {"options": {"allow": "docs/*"}}}}), "option allow has the wrong type"),
                                   (gate({"rules": {"security.secrets": {"options": {"patterns": {}}}}}), "option patterns is empty"),
                                   (gate({"rules": {"security.secrets": {"options": {"patterns": {"x": ["(", "x****"]}}}}}), "pattern x is not a")):
            r.commit("gate/gate.json", bad_config, "Broken config")
            err = r.push("main", want="stopped")
            r.expect(err, needle, "nothing was checked")
            r.git("reset", "-q", "--hard", "origin/main")
        return r.finish()


@test
def secrets_hook_ignores_git_config_that_would_hide_a_line():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        marker = Path(tmp) / "textconv-ran"
        script = Path(tmp) / "textconv.sh"
        script.write_text(f"#!/bin/sh\ntouch '{marker}'\ncat \"$1\"\n")
        script.chmod(0o755)
        r.git("config", "color.ui", "always")
        r.git("config", "diff.evil.textconv", str(script))
        r.git("config", "diff.context", "9")
        r.commit(".gitattributes", "*.hidden -diff\n*.bin binary\n*.cfg diff=evil\n", "Attributes")
        r.push("main", want="ok")
        aws = AWS_EXAMPLE
        for i, (name, body) in enumerate((("a.hidden", f"key = {aws}\n"), ("b.bin", f"key = {aws}\n"), ("c.cfg", f"key = {aws}\n"),
                                          ("d.dat", b"\x00\x01\x02 binary then " + aws.encode() + b" \x00\x03"),
                                          ('odd dir/ünï "q".txt', f"key = {aws}\n"), ("e.txt", f"a\r\nkey = {aws}\r\n"))):
            # the diff prefix settings change the path in the diff header; the hit must still name the file
            r.git("config", "--unset-all", "diff.noprefix")
            r.git("config", "--unset-all", "diff.mnemonicPrefix")
            r.git("config", "diff.noprefix" if i % 2 else "diff.mnemonicPrefix", "true")
            r.commit(name, body, "Try " + name.split()[0])
            err = r.push("main", want="stopped")
            r.expect(err, f" {name}:{2 if name == 'e.txt' else 1} aws-access-key-id AKIA****" if name != "d.dat" else " d.dat:", "aws-access-key-id AKIA****")
            r.git("reset", "-q", "--hard", "origin/main")
        if marker.exists():
            r.bad.append("a textconv program of the repository ran")
        # a replace ref must not swap the commit under the scan
        r.git("checkout", "-q", "-b", "swap")
        r.commit("f.txt", f"key = {aws}\n", "The key")
        keyed = r.head()
        r.git("checkout", "-q", "main")
        r.git("checkout", "-q", "-b", "clean")
        r.commit("f.txt", "nothing\n", "Clean twin")
        r.git("replace", keyed, r.head())
        r.git("checkout", "-q", "swap")
        err = r.push("swap", want="stopped")
        r.expect(err, "f.txt:1 aws-access-key-id")
        return r.finish()


@test
def secrets_hook_fails_closed_and_tier_warn_goes_on():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        shim = r.work / ".git/hooks/pre-push.d/20-secrets"
        text = shim.read_text()
        shim.write_text(text.replace("secrets.py", "missing.py"))
        shim.chmod(0o755)
        r.commit("a.txt", "a\n", "A")
        r.push("main", want="stopped")  # a hook that cannot run stops the push
        shim.write_text(text)
        shim.chmod(0o755)
        r.push("main", want="ok")
        r.install("warn")
        r.commit("gate/gate.json", "{not json", "Broken config")
        err = r.push("main", want="ok")
        r.expect(err, "nothing was checked and the push goes on")
        return r.finish()


@test
def secrets_hook_runs_beside_the_private_terms_hook():
    with tempfile.TemporaryDirectory() as tmp:
        failures = []
        for first in ("private", "secrets"):
            (Path(tmp) / first).mkdir()
            r = HookRepo(Path(tmp) / first, install=False)
            hooks = r.work / ".git/hooks"
            install_private = lambda: private.install_hook(hooks, str(PT_LIST))
            install_secrets = lambda: secrets.install_hook(hooks, "block")
            for step in ((install_private, install_secrets) if first == "private" else (install_secrets, install_private)):
                code, lines = step()
                if code:
                    failures.append(f"{first} first: install {lines}")
            if not (hooks / "pre-push.d/10-private-terms").is_file() or not (hooks / "pre-push.d/20-secrets").is_file():
                failures.append(f"{first} first: hooks are not side by side: {sorted(p.name for p in (hooks / 'pre-push.d').iterdir())}")
            if "powersuit hook dispatcher" not in (hooks / "pre-push").read_text():
                failures.append(f"{first} first: pre-push is not the dispatcher")
            r.commit("README.md", "# Project\n", "Start")
            r.push("main", want="ok")
            r.commit("a.md", "The runner sits on Kettlehost.lan.\n", "Private term")
            err = r.push("main", want="stopped")
            r.expect(err, "private term host-k")
            r.git("reset", "-q", "--hard", "origin/main")
            r.commit("b.md", f"key = {AWS_EXAMPLE}\n", "Key")
            err = r.push("main", want="stopped")
            r.expect(err, "b.md:1 aws-access-key-id")
            r.git("reset", "-q", "--hard", "origin/main")
            r.commit("c.md", f"key = {AWS_EXAMPLE}\nand Kettlehost.lan\n", "Both")
            err = r.push("main", want="stopped")
            r.expect(err, "private term host-k", "c.md:1 aws-access-key-id")  # one failing hook does not hide the other
            r.git("reset", "-q", "--hard", "origin/main")
            before = {p.name: p.read_text() for p in (hooks / "pre-push.d").iterdir()}
            before["pre-push"] = (hooks / "pre-push").read_text()
            install_secrets()
            after = {p.name: p.read_text() for p in (hooks / "pre-push.d").iterdir()}
            after["pre-push"] = (hooks / "pre-push").read_text()
            if before != after:
                failures.append(f"{first} first: a second install changed the hooks")
            failures += [f"{first} first: {b}" for b in r.finish() if "Kettlehost" not in b]
            if "kettlehost" in "\n".join(r.seen).lower():
                failures.append(f"{first} first: the private term shows in the output")
        return failures


@test
def secrets_hook_install_leaves_other_hooks_alone():
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        hooks = Path(tmp) / "hooks"
        hooks.mkdir()
        (hooks / "pre-push").write_text("#!/bin/sh\nexit 0\n")
        code, lines = secrets.install_hook(hooks, "block", True)
        if code != 2 or (hooks / "pre-push").read_text() != "#!/bin/sh\nexit 0\n" or (hooks / "pre-push.d").exists() or (hooks / "pre-commit").exists():
            bad.append(f"another pre-push hook: {code}, {lines}")
        if private.install_hook(hooks, str(PT_LIST))[0] != 2:
            bad.append("private_terms replaced another hook")
        (hooks / "pre-push").unlink()
        target = Path(tmp) / "shared-hook"
        target.write_text("#!/bin/sh\nexit 0\n")
        (hooks / "pre-push").symlink_to(target)
        code, lines = secrets.install_hook(hooks, "block")
        if code != 2 or target.read_text() != "#!/bin/sh\nexit 0\n" or not (hooks / "pre-push").is_symlink():
            bad.append(f"a linked pre-push hook: {code}, {lines}")
        (hooks / "pre-push").unlink()
        chain = hooks / "pre-push.d"
        chain.mkdir()
        (chain / "20-secrets").write_text("#!/bin/sh\necho other\n")
        if secrets.install_hook(hooks, "block")[0] != 2 or (chain / "20-secrets").read_text() != "#!/bin/sh\necho other\n":
            bad.append("another hook under the secrets name was replaced")
        (chain / "20-secrets").unlink()
        (hooks / "pre-commit").write_text("#!/bin/sh\nexit 0\n")
        if secrets.install_hook(hooks, "block", True)[0] != 2 or (hooks / "pre-push").exists():
            bad.append("a refused pre-commit hook must leave pre-push unwritten as well")
        fresh = Path(tmp) / "fresh"
        private.install_hook(fresh, str(PT_LIST))
        if secrets.PRIVATE_TERMS_MARK not in (fresh / "pre-push").read_text():
            bad.append("secrets.py would not recognise the shim that private_terms.py writes")
    if secrets.DISPATCH_MARK != private.DISPATCH_MARK or secrets.DISPATCH_MARK not in secrets.dispatcher_text("pre-push"):
        bad.append("the dispatcher markers of the two checks differ")
    return bad


@test
def secrets_hook_comes_with_a_new_clone_through_the_git_template():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        template = tmp / "template"
        for step in (lambda: private.install_hook(template / "hooks", str(PT_LIST)), lambda: secrets.install_hook(template / "hooks", "block")):
            code, lines = step()
            if code:
                return [f"template install: {lines}"]
        (tmp / "clone").mkdir()
        r = HookRepo(tmp / "clone", install=False)
        fresh = tmp / "fresh"
        subprocess.run(["git", "init", "-q", "--template", str(template), str(fresh)], env=r.env, check=True, capture_output=True)
        bad = []
        for rel in ("pre-push", "pre-push.d/10-private-terms", "pre-push.d/20-secrets"):
            if not os.access(fresh / ".git/hooks" / rel, os.X_OK):
                bad.append(f"the template did not copy {rel}")
        r.work = fresh
        r.git("checkout", "-q", "-b", "main")
        r.git("remote", "add", "origin", str(r.remote))
        r.commit("a.md", f"key = {AWS_EXAMPLE}\n", "Key")
        r.expect(r.push("main", want="stopped"), "a.md:1 aws-access-key-id")
        return bad + r.finish()


@test
def secrets_pre_commit_hook():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp, pre_commit=True)
        aws = AWS_EXAMPLE
        r.git("config", "diff.mnemonicPrefix", "true")  # a staged diff then names its files c/ and i/
        p = r.commit("a.txt", f"key = {aws}\n", "First commit with a key")  # no HEAD yet
        r.expect(p.stderr, "secrets: commit stopped", "staged a.txt:1 aws-access-key-id AKIA****", f"sha256:{sha12(aws)}")
        if p.returncode == 0 or r.git("rev-parse", "-q", "--verify", "HEAD").returncode == 0:
            r.bad.append("the first commit with a key was made")
        r.git("rm", "-q", "--cached", "a.txt")
        (r.work / "a.txt").unlink()
        r.commit("b.txt", "clean\n", "Clean commit")
        if r.git("rev-parse", "-q", "--verify", "HEAD").returncode != 0:
            r.bad.append("a clean commit was refused")
        p = r.commit(".env", "PORT=1\n", "An env file")
        r.expect(p.stderr, ".env env-file")
        r.git("reset", "-q")
        (r.work / ".env").unlink()
        (r.work / ".secrets-allow").write_text(f"docs/*.md aws-access-key-id sha256:{sha12(aws)} Example value from the vendor documentation\n")
        p = r.commit("docs/x.md", f"key = {aws}\n", "Allowed in the same commit")  # the index holds the allow file
        if p.returncode:
            r.bad.append(f"an allowed value was refused: {p.stderr.strip()[-200:]}")
        p = r.commit("docs/y.md", f"key = {aws}\nother = {FAKE['github-token']}\n", "One allowed, one not")
        r.expect(p.stderr, "docs/y.md:2 github-token")
        r.git("reset", "-q", "--hard")
        # a merge commit: lines taken from the other parent were scanned with it
        r.git("checkout", "-q", "-b", "feature")
        r.commit("shared.txt", f"key = {FAKE['slack-token']}\n", "Legacy key on feature", extra=NO_HOOKS)
        r.git("checkout", "-q", "main")
        r.commit("shared.txt", "main side\n", "Main side")
        r.git("merge", "-q", "feature")
        (r.work / "shared.txt").write_text(f"key = {FAKE['slack-token']}\nplus a clean line\n")
        r.git("add", "shared.txt")
        p = r.git("commit", "-q", "-m", "Merge feature")
        if p.returncode:
            r.bad.append(f"a merge that keeps a line of the other parent was refused: {p.stderr.strip()[-200:]}")
        (r.work / "later.txt").write_text(f"key = {FAKE['slack-token']}\n")
        r.git("add", "later.txt")
        p = r.git("commit", "-q", "-m", "The same line in a new file")
        r.expect(p.stderr, "later.txt:1 slack-token")
        return r.finish()


@test
def secrets_check_and_history_commands():
    bad = []
    script = MODULE / "checks/secrets.py"
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp, install=False)
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        cmd = lambda *a: subprocess.run([sys.executable, str(script), *a], cwd=r.work, env=r.env, capture_output=True, text=True)
        p = cmd("check")
        if p.returncode != 0 or "no hits" not in p.stderr:
            bad.append(f"check on a clean branch: {p.returncode}, {p.stderr.strip()}")
        r.commit("a.txt", f"key = {AWS_EXAMPLE}\n", "A key")
        r.commit("a.txt", "removed\n", "Removed")
        p = cmd("check")
        r.expect(p.stderr, "secrets: push to origin (2 commits) stopped, 1 hits", "a.txt:1 aws-access-key-id AKIA****")
        if p.returncode != 1 or r.remote_has(r.head()):
            bad.append(f"check on a branch with a key: exit {p.returncode}, pushed {r.remote_has(r.head())}")
        if cmd("check", "--tier", "warn").returncode != 0:
            bad.append("check with tier warn must exit 0")
        p = cmd("history")
        r.expect(p.stdout, "a.txt:1 aws-access-key-id AKIA****", "secrets: 3 commits read, 1 hits")
        if p.returncode != 1:
            bad.append(f"history exit {p.returncode}")
        r.seen += [p.stdout + p.stderr]
        r.git("reset", "-q", "--hard", "origin/main")
        p = cmd("history")
        if "0 hits" not in p.stdout or p.returncode != 0:
            bad.append(f"history of a clean repository: {p.returncode}, {p.stdout.strip()}")
        bad += r.finish()
    return bad


@test
def secrets_gate_check_allow_file():
    bad = []
    aws = AWS_EXAMPLE
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()
        (root / "docs/a.md").write_text(f"key = {aws}\n")
        (root / "docs/b.md").write_text(f"key = {aws}\nother = {FAKE['slack-token']}\n")
        (root / "app").mkdir()
        (root / "app/.env").write_text("PORT=1\n")
        allow = root / ".secrets-allow"
        allow.write_text("# documented values\n"
                         f"docs/*.md aws-access-key-id sha256:{sha12(aws)} Example value from the vendor documentation\n"
                         "app/.env env-file * Local development defaults, no secrets\n"
                         f"gone/* * * An entry that matches nothing\n")
        res = check_rule(secrets, root)
        files = sorted((h["file"], h.get("rule")) for h in res["hits"])
        if files != [("docs/b.md", "slack-token")]:
            bad.append(f"hits with an allow file: {files}")
        if "3 allowed by .secrets-allow" not in res["detail"] or "matched nothing: lines 4" not in res["detail"]:
            bad.append(f"detail: {res['detail']}")
        allow.write_text(f"docs/a.md aws-access-key-id sha256:{sha12(aws)}\n* * * Everything\n* aws-access-key-id sha256:zz Reason\n")
        res = check_rule(secrets, root)
        rules = sorted((h["file"], h.get("line"), h.get("rule")) for h in res["hits"] if h["file"] == ".secrets-allow")
        if rules != [(".secrets-allow", 1, "allow-entry"), (".secrets-allow", 2, "allow-entry"), (".secrets-allow", 3, "allow-entry")]:
            bad.append(f"allow entries without a reason, too broad, or with a bad hash: {rules}")
        if any(aws in h["snippet"] for h in res["hits"]):
            bad.append("a snippet shows a value")
        res = check_rule(secrets, root, allow_file="nothing-here")
        if not any(h["file"] == "docs/a.md" for h in res["hits"]):
            bad.append("allow_file option ignored")
    return bad


@test
def secrets_hook_is_clean_on_the_repositorys_own_files():
    bad = []
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True, text=True, check=True).stdout
    names = [n for n in listed.split("\0") if n and (REPO / n).is_file()]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for n in names:
            (work / n).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / n, work / n)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Fixture",
                   GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        git = lambda *a: subprocess.run(["git", *a], cwd=work, env=env, capture_output=True, text=True, check=True)
        git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "The repository")
        sha = git("rev-parse", "HEAD").stdout.strip()
        read = lambda path: secrets.git_blob(sha, path, work)
        found = secrets.Scan(work, read).commit(sha)
        if found:
            bad.append(f"hits with the repository's .secrets-allow: {[(f[1], f[2], f[3]) for f in found][:5]}")
        if not (REPO / ".secrets-allow").is_file():
            bad.append("the repository has no .secrets-allow for its fixtures")
        bare = secrets.Scan(work, lambda path: None if path == ".secrets-allow" else read(path))
        unallowed = bare.commit(sha)
        prefixes = ("plugins/security/checks/fixtures/security.secrets/", "plugins/fit/skills/repo-clinic/cases/")
        stray = sorted({f[1] for f in unallowed if not f[1].startswith(prefixes)})
        if stray or len(unallowed) < 8:
            bad.append(f"without the allow file: {len(unallowed)} hits, outside the known fixtures: {stray}")
    return bad


@test
def secrets_hook_diff_parsing():
    bad = []
    if secrets.unquote('"a\\tb\\"c\\\\d"') != 'a\tb"c\\d' or secrets.unquote('"\\303\\251"') != "é" or secrets.unquote("plain b/x") != "plain b/x":
        bad.append("unquote")
    diff = "\n".join([
        "diff --git a/old.txt b/new.txt", "similarity index 90%", "rename from old.txt", "rename to new.txt", "--- a/old.txt", "+++ b/new.txt\t",
        "@@ -2,0 +3,2 @@", "+++ looks like a header", "+second", "@@ -9 +10 @@", "-gone", "+changed",
        'diff --git "a/q\\"x.txt" "b/q\\"x.txt"', "--- /dev/null", '+++ "b/q\\"x.txt"', "@@ -0,0 +1 @@", "+quoted",
        "diff --git a/del.txt b/del.txt", "--- a/del.txt", "+++ /dev/null", "@@ -1 +0,0 @@", "-bye",
        "diff --git a/mode.sh b/mode.sh", "old mode 100644", "new mode 100755",
        "diff --git a/n.txt b/n.txt", "--- a/n.txt", "+++ b/n.txt", "@@ -1 +1 @@", "-a", "\\ No newline at end of file", "+b", "\\ No newline at end of file",
    ])
    got = secrets.added_lines(diff)
    want = [("new.txt", 3, "++ looks like a header"), ("new.txt", 4, "second"), ("new.txt", 10, "changed"), ('q"x.txt', 1, "quoted"), ("n.txt", 1, "b")]
    if got != want:
        bad.append(f"added_lines: {got}")
    if secrets.new_paths("A\0one\0M\0two\0R090\0old\0three\0C100\0src\0four\0D\0five\0") != ["one", "three", "four"]:
        bad.append("new_paths")
    return bad


@test
def secrets_hook_scripts_pass_shellcheck():
    exe = shutil.which("shellcheck")
    if not exe:
        return []
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in (("dispatcher-push.sh", secrets.dispatcher_text("pre-push")), ("dispatcher-commit.sh", secrets.dispatcher_text("pre-commit")),
                           ("shim-push.sh", secrets.shim_text("pre-push", "block")), ("shim-commit.sh", secrets.shim_text("pre-commit", "warn"))):
            f = Path(tmp) / name
            f.write_text(text)
            p = subprocess.run([exe, "-S", "warning", str(f)], capture_output=True, text=True)
            if p.returncode:
                bad.append(f"shellcheck {name}: {p.stdout.strip()[:300]}")
    return bad


@test
def secrets_hook_stops_a_pattern_that_backtracks_without_end():
    if not hasattr(__import__("signal"), "SIGALRM"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp)
        r.env["SECRETS_HOOK_SECONDS"] = "2"
        r.commit("README.md", "# Project\n", "Start")
        r.push("main", want="ok")
        evil = {"rules": {"security.secrets": {"options": {"patterns": {"evil": ["(a+)+$", "evil-****"]}}}}}
        r.commit("gate/gate.json", json.dumps(evil), "A pattern that backtracks")
        r.commit("a.txt", "a" * 60 + "!\n", "A line that makes it backtrack")
        # run the push in its own process group, so that a hook that never ends cannot hang the suite
        p = subprocess.Popen(["git", "push", "-q", "origin", "main"], cwd=r.work, env=r.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, start_new_session=True)
        try:
            out, err = p.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            p.communicate()
            return ["the budget did not stop the scan: the hook ran for 90 seconds"]
        r.seen.append(out + err)
        if p.returncode == 0:
            r.bad.append("a scan that hit the budget let the push through")
        r.expect(err, "took longer than 2 seconds", "nothing was checked")
        return r.finish()


@test
def secrets_hook_reads_a_push_by_url_like_a_push_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        r = HookRepo(tmp, tier="warn")
        r.commit("README.md", "# Project\n", "Start")
        r.commit("legacy.txt", f"key = {AWS_EXAMPLE}\n", "A key that is already public")
        r.push("main", want="ok")
        r.install("block")
        r.commit("clean.txt", "clean\n", "A clean commit")
        r.push("HEAD:refs/heads/feature", want="ok")  # by name
        url_push = r.git("push", "-q", str(r.remote), "HEAD:refs/heads/by-url")
        r.seen.append(url_push.stderr)
        if url_push.returncode:
            r.bad.append(f"a push by the URL of a configured remote read the history the remote has: {url_push.stderr.strip()[-200:]}")
        other = Path(tmp) / "other.git"
        r.git("init", "-q", "--bare", str(other), cwd=Path(tmp))
        stranger = r.git("push", "-q", str(other), "HEAD:refs/heads/main")
        r.seen.append(stranger.stderr)
        if stranger.returncode == 0 or "legacy.txt:1 aws-access-key-id" not in stranger.stderr:
            r.bad.append("a push to a repository that no remote names must read the whole history of a new ref")
        r.commit("k.txt", f"key = {FAKE['slack-token']}\n", "A key")
        code, lines = secrets.pre_push("https://user:hunter2@example.invalid/x.git", [f"refs/heads/k {r.head()} refs/heads/k {'0' * 40}"], r.work, "block")
        shown = "\n".join(lines)
        if code != 1 or "hunter2" in shown or "https://example.invalid/x.git" not in shown:
            r.bad.append(f"a URL login must not reach the output: exit {code}, {shown[:200]}")
        return r.finish()


@test
def secrets_hook_masks_an_error_with_the_patterns_of_the_scan():
    token = "acme_" + "0123456789abcdef0123"
    config = json.dumps({"rules": {"security.secrets": {"options": {"patterns": {"acme-token": [r"\bacme_[0-9a-f]{20}\b", "acme_****"]}}}}})
    secrets.Scan(Path("."), lambda path: config if path == "gate/gate.json" else None)
    try:
        text = secrets.error_text(RuntimeError(f"git failed on {token} and {FAKE['sk-key']} at https://user:{FAKE['github-token']}@example.org/r.git"))
    finally:
        secrets.ACTIVE_KINDS[:] = []
    return [f"unmasked: {w}" for w in (token, FAKE["sk-key"], FAKE["github-token"]) if w in text]


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
