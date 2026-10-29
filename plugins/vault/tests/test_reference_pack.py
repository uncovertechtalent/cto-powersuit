#!/usr/bin/env python3
"""Tests for /vault:reference-pack, the importer of the machinebehavior.io corpus, beyond its fixture runs.

No network: every fetch replays a recorded copy of the site from tests/fixtures/reference-pack, and the test process
refuses any socket connection.

- The recorded corpus (pass/recorded: the real manifest entries and six real twins, fetched 2026-10-20): one note per page
  with source, fetched, sha256 (of the twin file as recorded), trust: third-party, the notice and the two markers.
- Text that gives orders (pass/instructions-as-data): imported byte for byte between the markers, front matter intact.
- The fail fixtures: hidden characters, a forged end marker, a manifest URL off the site, a twin that names another
  page, a manifest cut short. Each refuses the page, or stops the run with nothing written, and says why.
- Re-runs: unchanged pages stay byte for byte (mtime too), a changed page is reported by hash and rewritten alone,
  a page that left the corpus is kept until --prune, a dry run writes nothing.
- The boundary: nothing outside reference/machinebehavior/ is read or changed; a file in the pack folder that is not a
  pack note is kept, and a note of the user's with a page's name is left alone; symbolic links stop the run.
- Manifest and twin checks, each on a copy of the recorded corpus with one change: odd URLs, name collisions, a wrong
  twin URL, a missing twin, bad dates and titles, an oversize twin, bytes that are not UTF-8, a reply that is not a twin.
- A fetch failure stops the run before the first write.
- The command line: exit codes 0, 1, 2 and the JSON output.
- The text around it: the skill, the README, SEEDING.md, the starter .vsearchignore and the marketplace entry say
  what the importer does.

Standard library only, Python 3.9+. Usage: python3 plugins/vault/tests/test_reference_pack.py [-v]
"""
import hashlib, importlib.util, json, re, shutil, socket, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True

MODULE = Path(__file__).resolve().parent.parent
REPO = MODULE.parent.parent
FIXTURES = MODULE / "tests/fixtures/reference-pack"
SCRIPT = MODULE / "skills/reference-pack/reference_pack.py"
VERBOSE = "-v" in sys.argv
TODAY = "2026-10-20"
LATER = "2026-10-27"
BASE = "https://machinebehavior.io"

spec = importlib.util.spec_from_file_location("reference_pack", SCRIPT)
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)


def _no_network(*a, **k):
    raise AssertionError("the tests do not open sockets")


socket.socket.connect = _no_network
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def tmp():
    d = Path(tempfile.mkdtemp(prefix="reference-pack-test-"))
    CLEAN.append(d)
    return d


CLEAN = []


def copy_site(case):
    """A writable copy of a fixture's site folder."""
    dst = tmp() / "site"
    shutil.copytree(FIXTURES / case / "site", dst)
    return dst


def make_vault(files=None):
    v = tmp() / "vault"
    v.mkdir()
    for rel, text in (files or {}).items():
        p = v / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return v


def run(site, vault, today=TODAY, fetcher=None, **kw):
    return rp.sync(vault, fetcher or rp.Fetcher(site), today, **kw)


def pack(vault):
    return Path(vault) / "reference/machinebehavior"


def tree(root):
    """{relative path: (sha256, mtime_ns)} of every file under root."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and not p.is_symlink():
            out[str(p.relative_to(root))] = (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
    return out


def front(path):
    return rp.read_front(path)


def sha_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def edit_manifest(site, fn):
    f = Path(site) / "llms-passages.json"
    data = json.loads(f.read_text())
    fn(data)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def reasons(result, key="refused"):
    return " | ".join(x["reason"] for x in result[key])


def aborts(site, vault, **kw):
    try:
        run(site, vault, **kw)
    except rp.Abort as e:
        return str(e)
    raise AssertionError("expected the run to stop")


class Recording(rp.Fetcher):
    """A replay that remembers every URL it was asked for."""

    def __init__(self, site):
        super().__init__(site)
        self.asked = []

    def get(self, url, limit):
        self.asked.append(url)
        return super().get(url, limit)


# ---------------------------------------------------------------- the recorded corpus

RECORDED = FIXTURES / "pass/recorded/site"
NOTES = {  # page path -> note file
    "/": "home.md", "/map/": "map.md", "/inside/search/": "inside__search.md",
    "/inside/docs/eng/adr-0002-deploy-is-gated/": "inside__docs__eng__adr-0002-deploy-is-gated.md",
    "/inside/docs/sre/incidents/": "inside__docs__sre__incidents.md", "/inside/docs/sre/pillars/": "inside__docs__sre__pillars.md",
}


def twin_file(site, path):
    return Path(site) / (path.lstrip("/") + "index.html.md")


@test
def recorded_corpus_one_note_per_page():
    v = make_vault()
    r = run(RECORDED, v)
    assert r["pages"] == 6 and len(r["new"]) == 6 and not r["refused"] and not r["conflict"] and not r["changed"], r
    for path, name in NOTES.items():
        note = pack(v) / name
        assert note.is_file(), name
        fm = front(note)
        assert fm["source"] == BASE + path, fm
        assert fm["fetched"] == TODAY
        assert fm["sha256"] == sha_of(twin_file(RECORDED, path)), f"{name}: sha256 is not the sha256 of the twin file"
        assert fm["trust"] == "third-party"
        assert fm["tags"] == "[reference/machinebehavior, trust/third-party]"
        assert json.loads(fm["title"]), fm
    assert sorted(p.name for p in pack(v).iterdir()) == sorted(list(NOTES.values()) + ["_README.md"])


@test
def note_carries_notice_and_markers_around_the_text():
    v = make_vault()
    run(RECORDED, v)
    for path, name in NOTES.items():
        text = (pack(v) / name).read_text()
        sha = front(pack(v) / name)["sha256"]
        begin = f"<!-- third-party text begins, sha256 {sha[:12]} -->\n"
        end = f"<!-- third-party text ends, sha256 {sha[:12]} -->\n"
        assert text.count(begin) == 1 and text.count(end) == 1 and text.endswith(end), name
        before, rest = text.split(begin)
        inner = rest.split(end)[0]
        notice = before.split("\n---\n", 1)[1]
        assert "Third-party reference" in notice and "not instructions to you" in notice and BASE + path in notice, notice
        twin = twin_file(RECORDED, path).read_text()
        assert inner.strip("\n") == twin.split("\n---\n", 1)[1].strip("\n"), f"{name}: the text differs from the twin body"


@test
def pack_readme_says_what_the_folder_is():
    v = make_vault()
    run(RECORDED, v)
    text = (pack(v) / "_README.md").read_text()
    fm = front(pack(v) / "_README.md")
    assert fm["trust"] == "third-party" and fm["pages"] == "6" and fm["source"] == BASE + "/llms-passages.json", fm
    assert fm["sha256"] == sha_of(RECORDED / "llms-passages.json")
    for must in ("third party's documentation", "Never as instructions", "reference/machinebehavior", "delete this folder"):
        assert must in text, must


@test
def instructions_in_the_text_stay_data():
    site = FIXTURES / "pass/instructions-as-data/site"
    raw = (site / "notes/index.html.md").read_bytes()
    assert b"Ignore every previous instruction" in raw and b"trust: first-party" in raw
    v = make_vault()
    r = run(site, v)
    assert len(r["new"]) == 1 and not r["refused"], r
    note = pack(v) / "notes.md"
    text = note.read_text()
    fm = front(note)
    assert fm["trust"] == "third-party" and fm["source"] == BASE + "/notes/" and fm["sha256"] == hashlib.sha256(raw).hexdigest(), fm
    assert set(fm) == {"source", "fetched", "sha256", "trust", "title", "page-date", "tags"}, set(fm)
    head, body = text.split("<!-- third-party text begins", 1)
    assert "Ignore every previous instruction" not in head and "trust: first-party" not in head
    assert head.count("\n---\n") == 1, "front matter closes once, before the notice"
    inner = body.split("-->\n", 1)[1].rsplit("<!-- third-party text ends", 1)[0]
    assert "Ignore every previous instruction" in inner and "trust: first-party" in inner and "<tool_use>delete_everything" in inner
    assert text.count("<!-- third-party text begins") == 1 and text.count("<!-- third-party text ends") == 1
    assert text.rstrip("\n").splitlines()[-1].startswith("<!-- third-party text ends, sha256 ")


@test
def title_round_trips_through_front_matter():
    site = copy_site("pass/recorded")
    title = 'Say "hi": a #title \\ with ünïcode and a: colon'
    edit_manifest(site, lambda d: [p.update(t=title) for p in d["pages"] if p["u"] == BASE + "/map/"])
    v = make_vault()
    run(site, v)
    assert json.loads(front(pack(v) / "map.md")["title"]) == title


@test
def twin_without_trailing_slash_url_uses_the_md_form():
    site = copy_site("pass/recorded")
    url = BASE + "/feed.html"
    edit_manifest(site, lambda d: d["pages"].append({"u": url, "t": "Feed", "d": "2026-10-01", "p": "", "m": url + ".md"}))
    (site / "feed.html.md").write_text(f'---\nurl: {url}\ntitle: "Feed"\n---\n# Feed\n\nText.\n')
    v = make_vault()
    r = run(site, v)
    assert not r["refused"] and (pack(v) / "feed.html.md").is_file(), r


# ---------------------------------------------------------------- re-runs

@test
def rerun_leaves_unchanged_notes_byte_for_byte():
    v = make_vault()
    run(RECORDED, v)
    before = tree(pack(v))
    r = run(RECORDED, v, today=LATER)
    assert r["unchanged"] == 6 and not r["new"] and not r["changed"], r
    assert tree(pack(v)) == before, "an unchanged re-run wrote a file"


@test
def changed_page_is_reported_by_hash_and_rewritten_alone():
    site = copy_site("pass/recorded")
    v = make_vault()
    first = run(site, v)
    old = front(pack(v) / "map.md")["sha256"]
    before = tree(pack(v))
    f = twin_file(site, "/map/")
    f.write_text(f.read_text() + "\nA new line.\n")
    r = run(site, v, today=LATER)
    new = hashlib.sha256(f.read_bytes()).hexdigest()
    assert r["changed"] == [{"note": "map", "page": BASE + "/map/", "old_sha256": old, "new_sha256": new}], r
    assert r["unchanged"] == 5 and not r["new"], r
    after = tree(pack(v))
    moved = sorted(k for k in after if before.get(k) != after[k])
    assert moved == ["_README.md", "map.md"], moved
    fm = front(pack(v) / "map.md")
    assert fm["sha256"] == new and fm["fetched"] == LATER
    assert "A new line." in (pack(v) / "map.md").read_text()
    assert f"map: {old[:12]} -> {new[:12]}" in rp.report(r)


@test
def page_that_left_the_corpus_stays_until_prune():
    site = copy_site("pass/recorded")
    v = make_vault()
    run(site, v)
    edit_manifest(site, lambda d: d.update(pages=[p for p in d["pages"] if p["u"] != BASE + "/map/"]))
    r = run(site, v)
    assert r["gone"] == ["map.md"] and r["unchanged"] == 5 and not r["pruned"], r
    assert (pack(v) / "map.md").is_file()
    r = run(site, v, prune=True)
    assert r["gone"] == ["map.md"] and r["pruned"], r
    assert not (pack(v) / "map.md").exists()
    assert front(pack(v) / "_README.md")["pages"] == "5"


@test
def dry_run_writes_nothing():
    v = make_vault({"a/Atom.md": "mine\n"})
    before = tree(v)
    r = run(RECORDED, v, dry_run=True)
    assert r["dry_run"] and len(r["new"]) == 6, r
    assert tree(v) == before and not (v / "reference").exists()
    run(RECORDED, v)
    after = tree(v)
    r = run(RECORDED, v, today=LATER, dry_run=True)
    assert r["unchanged"] == 6 and tree(v) == after


# ---------------------------------------------------------------- the boundary

@test
def nothing_outside_the_pack_is_read_or_changed():
    own = {"work/Atom.md": "my atom\n", "CLAUDE.md": "rules\n", ".vsearchignore": "# mine\n", "_inbox/README.md": "inbox\n",
           "reference/Other note.md": "keep\n", "reference/other-pack/x.md": "---\ntrust: third-party\nsource: https://machinebehavior.io/x\n---\n",
           "reference/machinebehavior/mine.md": "my own note in the pack folder\n", "reference/machinebehavior/data.txt": "x\n"}
    v = make_vault(own)
    before = tree(v)
    site = copy_site("pass/recorded")
    run(site, v)
    edit_manifest(site, lambda d: d.update(pages=d["pages"][:3]))
    r = run(site, v, today=LATER, prune=True)
    assert r["foreign_files"] == 1 and len(r["gone"]) == 3, r
    after = tree(v)
    for rel in own:
        assert after[rel] == before[rel], f"{rel} changed"
    outside = {k for k in after if not k.startswith("reference/machinebehavior/")}
    assert outside == {k for k in before if not k.startswith("reference/machinebehavior/")}, "a file outside the pack appeared or vanished"
    managed = {k for k in after if k.startswith("reference/machinebehavior/")} - {"reference/machinebehavior/mine.md", "reference/machinebehavior/data.txt"}
    assert all(front(v / k) and front(v / k)["trust"] == "third-party" for k in managed if k.endswith(".md")), managed


@test
def fetcher_never_asks_for_a_url_off_the_site():
    f = Recording(FIXTURES / "fail/offsite-url/site")
    run(None, make_vault(), fetcher=f)
    assert f.asked and all(u.startswith(BASE + "/") for u in f.asked), f.asked
    assert not any("evil.example" in u for u in f.asked)
    try:
        rp.Fetcher(RECORDED).get("https://evil.example/llms-passages.json", 1000)
    except rp.FetchError as e:
        assert e.kind == "redirect"
    else:
        raise AssertionError("the fetcher read a URL off the site")


@test
def redirect_off_the_site_is_refused():
    handler = rp._SameHost()
    try:
        handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/x")
    except rp.FetchError as e:
        assert e.kind == "redirect"
    else:
        raise AssertionError("redirect to another host followed")
    try:
        handler.redirect_request(None, None, 302, "Found", {}, "http://machinebehavior.io/x")
    except rp.FetchError as e:
        assert e.kind == "redirect"
    else:
        raise AssertionError("redirect to plain http followed")


@test
def user_note_with_a_page_name_is_left_alone():
    v = make_vault({"reference/machinebehavior/map.md": "my own thoughts about maps\n"})
    r = run(RECORDED, v)
    assert [c["page"] for c in r["conflict"]] == [BASE + "/map/"], r
    assert (pack(v) / "map.md").read_text() == "my own thoughts about maps\n"
    assert len(r["new"]) == 5
    # a note of this pack for another page under the same name is also not overwritten
    other = rp.render_note(rp.Page({"u": BASE + "/elsewhere/", "t": "x", "d": "", "p": "", "m": BASE + "/elsewhere/index.html.md"}), "text\n", "a" * 64, TODAY)
    (pack(v) / "map.md").write_text(other)
    r = run(RECORDED, v, today=LATER)
    assert len(r["conflict"]) == 1 and (pack(v) / "map.md").read_text() == other


@test
def symbolic_links_stop_or_skip():
    v = make_vault()
    outside = tmp() / "outside"
    outside.mkdir()
    (v / "reference").mkdir()
    (v / "reference/machinebehavior").symlink_to(outside)
    msg = aborts(RECORDED, v)
    assert "symbolic link" in msg and not list(outside.iterdir()), msg
    v2 = make_vault()
    (v2 / "reference").symlink_to(outside)
    assert "symbolic link" in aborts(RECORDED, v2) and not list(outside.iterdir())
    v3 = make_vault()
    pack(v3).mkdir(parents=True)
    target = outside / "victim.md"
    target.write_text("do not touch\n")
    (pack(v3) / "map.md").symlink_to(target)
    r = run(RECORDED, v3)
    assert any("symbolic link" in c["reason"] for c in r["conflict"]) and target.read_text() == "do not touch\n", r


@test
def missing_vault_stops_the_run():
    assert "vault-init" in aborts(RECORDED, tmp() / "nowhere")


# ---------------------------------------------------------------- the fail fixtures

@test
def fail_hidden_chars():
    site = FIXTURES / "fail/hidden-chars/site"
    raw = (site / "notes/index.html.md").read_text()
    assert "​" in raw and "‮" in raw, "the fixture lost its hidden characters"
    v = make_vault()
    r = run(site, v)
    assert [x["page"] for x in r["refused"]] == [BASE + "/notes/"] and "U+200B" in reasons(r), r
    assert (pack(v) / "map.md").is_file() and not (pack(v) / "notes.md").exists()


@test
def fail_marker_forgery():
    v = make_vault()
    r = run(FIXTURES / "fail/marker-forgery/site", v)
    assert len(r["refused"]) == 1 and "marker" in reasons(r) and not r["new"], r
    assert not (pack(v) / "notes.md").exists()


@test
def fail_offsite_url():
    v = make_vault()
    r = run(FIXTURES / "fail/offsite-url/site", v)
    assert len(r["refused"]) == 1 and "https page on machinebehavior.io" in reasons(r) and r["new"] == ["map"], r
    assert sorted(p.name for p in pack(v).iterdir()) == ["_README.md", "map.md"]


@test
def fail_url_mismatch():
    v = make_vault()
    r = run(FIXTURES / "fail/url-mismatch/site", v)
    assert len(r["refused"]) == 1 and "names the url" in reasons(r) and not r["new"], r


@test
def fail_truncated_manifest_writes_nothing():
    v = make_vault()
    before = tree(v)
    msg = aborts(FIXTURES / "fail/truncated-manifest/site", v)
    assert "not valid JSON" in msg and "cut short" in msg, msg
    assert tree(v) == before and not (v / "reference").exists()


# ---------------------------------------------------------------- manifest and twin checks

@test
def odd_urls_are_refused():
    bad = ["/a/../b/", "/a%2fb/", "/a b/", "/a?x=1", "/a#f", "/a/", "/a__b/", "/.hidden/", "/a//b/", "/ünï/", "/" + "x" * 250 + "/"]
    site = copy_site("pass/recorded")
    entries = []
    for p in bad:
        entries.append({"u": BASE + p, "t": "t", "d": "", "p": "", "m": BASE + p + "index.html.md"})
    entries[5]["u"] = "http://machinebehavior.io/a/"
    entries.append({"u": "https://machinebehavior.io:8443/a/", "t": "t", "d": "", "p": "", "m": "https://machinebehavior.io:8443/a/index.html.md"})
    entries.append({"u": "https://user@machinebehavior.io/a/", "t": "t", "d": "", "p": "", "m": "https://user@machinebehavior.io/a/index.html.md"})
    entries.append({"u": "https://MACHINEBEHAVIOR.IO/a/", "t": "t", "d": "", "p": "", "m": "https://MACHINEBEHAVIOR.IO/a/index.html.md"})
    entries.append("not an object")
    entries.append({"t": "no url"})
    edit_manifest(site, lambda d: d["pages"].extend(entries))
    v = make_vault()
    f = Recording(site)
    r = run(site, v, fetcher=f)
    assert len(r["refused"]) == len(entries), reasons(r)
    assert len(r["new"]) == 6 and sorted(p.name for p in pack(v).iterdir()) == sorted(list(NOTES.values()) + ["_README.md"])
    assert all(u.startswith(BASE + "/") and ".." not in u and "evil" not in u for u in f.asked)


@test
def name_collisions_are_refused():
    site = copy_site("pass/recorded")
    def add(d):
        for path, title in (("/Map/", "Capital"), ("/inside__search/", "Double score")):
            d["pages"].append({"u": BASE + path, "t": title, "d": "", "p": "", "m": BASE + path + "index.html.md"})
    edit_manifest(site, add)
    v = make_vault()
    r = run(site, v)
    assert len(r["refused"]) == 2 and "same note name" in reasons(r), r
    assert len(r["new"]) == 6


@test
def wrong_twin_url_is_refused():
    site = copy_site("pass/recorded")
    edit_manifest(site, lambda d: [p.update(m=BASE + "/llms-full.txt") for p in d["pages"] if p["u"] == BASE + "/map/"])
    r = run(site, make_vault())
    assert len(r["refused"]) == 1 and "twin url is not" in reasons(r), r


@test
def missing_twin_is_refused_and_the_old_note_stays():
    site = copy_site("pass/recorded")
    v = make_vault()
    run(site, v)
    before = (pack(v) / "map.md").read_bytes()
    twin_file(site, "/map/").unlink()
    r = run(site, v, today=LATER)
    assert len(r["refused"]) == 1 and "no twin" in reasons(r) and r["unchanged"] == 5, r
    assert (pack(v) / "map.md").read_bytes() == before


@test
def bad_dates_and_titles_are_refused():
    site = copy_site("pass/recorded")
    def edit(d):
        bymap = {p["u"]: p for p in d["pages"]}
        bymap[BASE + "/"]["d"] = "2026-13-45"
        bymap[BASE + "/map/"]["p"] = "yesterday"
        bymap[BASE + "/inside/search/"]["t"] = "two\nlines"
        bymap[BASE + "/inside/docs/sre/pillars/"]["t"] = "x" * 201
        bymap[BASE + "/inside/docs/sre/incidents/"]["t"] = "zero​width"
    edit_manifest(site, edit)
    r = run(site, make_vault())
    assert len(r["refused"]) == 5 and len(r["new"]) == 1, reasons(r)


@test
def oversize_twin_is_refused():
    old = rp.MAX_TWIN
    rp.MAX_TWIN = 700
    try:
        v = make_vault()
        r = run(RECORDED, v)
    finally:
        rp.MAX_TWIN = old
    assert len(r["refused"]) >= 1 and "larger than 700" in reasons(r), r
    assert all(not (pack(v) / n).exists() for n in [NOTES["/"]]), "the big home page was written"


@test
def twin_that_is_not_text_or_not_a_twin_is_refused():
    site = copy_site("pass/recorded")
    twin_file(site, "/map/").write_bytes(b"---\nurl: " + (BASE + "/map/").encode() + b"\n---\n\xff\xfe broken\n")
    twin_file(site, "/inside/search/").write_text("<!doctype html><title>Not found</title>\n")
    twin_file(site, "/inside/docs/sre/pillars/").write_text("---\nurl: " + BASE + "/inside/docs/sre/pillars/\nno closing line\n")
    twin_file(site, "/inside/docs/sre/incidents/").write_text("---\nurl: " + BASE + "/inside/docs/sre/incidents/\n---\n# T\n\nA line with a bare return\r\nhere.\n")
    r = run(site, make_vault())
    why = reasons(r)
    assert len(r["refused"]) == 4 and "UTF-8" in why and "no front matter" in why and "does not close" in why and "U+000D" in why, why
    assert len(r["new"]) == 2


@test
def fetch_failure_stops_before_the_first_write():
    class Flaky(rp.Fetcher):
        def get(self, url, limit):
            if url.endswith("/map/index.html.md"):
                raise rp.FetchError("http", "503 for " + url)
            return super().get(url, limit)
    v = make_vault({"a.md": "x\n"})
    before = tree(v)
    msg = aborts(RECORDED, v, fetcher=Flaky(RECORDED))
    assert "nothing written" in msg and "503" in msg
    assert tree(v) == before and not (v / "reference").exists()
    # a missing manifest stops the run as well
    msg = aborts(tmp(), v)
    assert "llms-passages.json" in msg and tree(v) == before


@test
def manifest_must_be_the_sites_passage_index():
    site = copy_site("pass/recorded")
    for change in (lambda d: d.update(site="https://example.com"), lambda d: d.update(pages=[]), lambda d: d.update(pages="x"), lambda d: d.pop("pages")):
        shutil.copyfile(RECORDED / "llms-passages.json", site / "llms-passages.json")
        edit_manifest(site, change)
        assert "passage index" in aborts(site, make_vault()) or "lists 0 pages" in aborts(site, make_vault())
    (site / "llms-passages.json").write_text("[1, 2, 3]")
    assert "passage index" in aborts(site, make_vault())


# ---------------------------------------------------------------- the command line

def cli(*args):
    p = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


@test
def command_line_exit_codes_and_json():
    v = make_vault()
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(RECORDED), "--today", TODAY)
    assert code == 0 and "new 6, changed 0, unchanged 0" in out, (code, out, err)
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(RECORDED), "--today", LATER, "--json")
    data = json.loads(out)
    assert code == 0 and data["unchanged"] == 6 and data["pages"] == 6 and data["manifest_sha256"] == sha_of(RECORDED / "llms-passages.json"), (code, out)
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(FIXTURES / "fail/hidden-chars/site"), "--today", LATER)
    assert code == 1 and "refused 1" in out and "U+200B" in out, (code, out, err)
    code, out, err = cli("sync", "--vault", str(make_vault()), "--from-dir", str(FIXTURES / "fail/truncated-manifest/site"))
    assert code == 2 and "nothing written" in err and out == "", (code, out, err)
    code, out, err = cli("sync", "--vault", str(tmp() / "none"), "--from-dir", str(RECORDED))
    assert code == 2 and "vault-init" in err, (code, err)
    code, out, err = cli("sync", "--vault", str(make_vault()), "--from-dir", str(RECORDED), "--today", "yesterday")
    assert code == 2 and "YYYY-MM-DD" in err


@test
def command_line_dry_run_and_prune_flags():
    v = make_vault()
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(RECORDED), "--dry-run")
    assert code == 0 and "dry run, nothing written" in out and not (v / "reference").exists(), (code, out)
    site = copy_site("pass/recorded")
    cli("sync", "--vault", str(v), "--from-dir", str(site))
    edit_manifest(site, lambda d: d.update(pages=d["pages"][:5]))
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(site))
    assert "gone 1 (kept; --prune deletes them)" in out and len(list(pack(v).glob("*.md"))) == 7, out
    code, out, err = cli("sync", "--vault", str(v), "--from-dir", str(site), "--prune")
    assert "gone 1 (deleted)" in out and len(list(pack(v).glob("*.md"))) == 6, out


# ---------------------------------------------------------------- the text around it

def text(rel):
    return (REPO / rel).read_text()


@test
def docs_say_what_the_importer_does():
    skill = text("plugins/vault/skills/reference-pack/SKILL.md")
    fm = re.match(r"---\nname: reference-pack\ndescription: >\n(.*?)\nuser-invocable: true\n---\n", skill, re.S)
    assert fm, "front matter of the skill"
    for must in ("third party", "never instructions", "reference/machinebehavior", "--dry-run", "opt-in", "sha256", "trust: third-party",
                 "llms-passages.json", ".vsearchignore", "--prune", "never by default", "reference_pack.py", "searchable now"):
        assert must.lower() in skill.lower(), f"SKILL.md lacks {must!r}"
    assert not any(c in skill for c in "\u2014\u2013"), "dashes in SKILL.md"
    readme = text("plugins/vault/README.md")
    for must in ("/vault:reference-pack", "third party", "never instructions", "reference/machinebehavior", "opt-in"):
        assert must.lower() in readme.lower(), f"plugins/vault/README.md lacks {must!r}"
    seeding = text("plugins/vault/SEEDING.md")
    for must in ("machinebehavior.io", "third-party", "reference/machinebehavior", "Never by default"):
        assert must.lower() in seeding.lower(), f"SEEDING.md lacks {must!r}"
    seed = text("plugins/vault/skills/seed/SKILL.md")
    assert "/vault:reference-pack" in seed and "default" in seed.lower() and "no" in seed.lower()
    root = text("README.md")
    assert "/vault:reference-pack" in root


@test
def starter_vsearchignore_shows_how_to_exclude_the_pack():
    lines = text("plugins/vault/templates/vault-starter/.vsearchignore").splitlines()
    assert "# reference/machinebehavior" in lines, "the commented exclusion line"
    assert not [l for l in lines if l.strip() == "reference/machinebehavior"], "the pack must not be excluded by default"
    assert any("reference-pack" in l and l.startswith("#") for l in lines), "a comment names the skill"


@test
def skill_is_listed_and_versioned():
    market = json.loads(text(".claude-plugin/marketplace.json"))
    vault = [p for p in market["plugins"] if p["name"] == "vault"][0]
    assert "./skills/reference-pack" in vault["skills"], vault["skills"]
    version = json.loads(text("plugins/vault/.claude-plugin/plugin.json"))["version"]
    assert tuple(int(x) for x in version.split(".")) > (0, 1, 0), version
    # The entry that introduced the skill names it; it sits under Unreleased until a release moves it under
    # a version heading, and later vault versions need no entry of their own for it.
    entries = [l for l in text("CHANGELOG.md").splitlines() if l.startswith("- `vault` ") and "reference-pack" in l]
    assert entries, "a CHANGELOG entry of the vault plugin names reference-pack"
    logged = max(tuple(int(x) for x in l.split("`vault` ", 1)[1].split(":", 1)[0].split(".")) for l in entries)
    assert tuple(int(x) for x in version.split(".")) >= logged, (version, logged)
    assert "plugins/vault/tests/test_reference_pack.py" in text(".github/workflows/checks.yml")


def main():
    failed = 0
    try:
        for fn in TESTS:
            try:
                fn()
                if VERBOSE:
                    print(f"ok   {fn.__name__}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    finally:
        for d in CLEAN:
            shutil.rmtree(d, ignore_errors=True)
    print(f"{len(TESTS) - failed} of {len(TESTS)} reference pack tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
