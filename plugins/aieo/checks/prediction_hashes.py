"""Every prediction file matches the sha256 published for it, and every prediction file is listed."""
import hashlib
import re

ID = "aieo.prediction-hashes"
DESCRIPTION = ("Every file listed in predictions/HASHES.txt exists and matches its sha256, "
               "and every predictions/*.txt file other than HASHES.txt is listed.")
DEFAULTS = {
    "dir": "predictions",        # folder with the prediction files and HASHES.txt
    "hashes_file": "HASHES.txt",
}

ENTRY = re.compile(r"^(\S+\.txt)\s+sha256\s+([0-9a-f]{64})\s*$")
ENTRY_START = re.compile(r"^(\S+\.txt)\s+sha256\b")


def parse_hashes(text):
    """Return ({name: sha256 or None}, {name: line}). A line '<name>.txt  sha256 <64 hex>' is an entry;
    a line that starts like an entry and breaks the format gets None; '#' lines and other lines are notes."""
    listed, lines = {}, {}
    for n, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = ENTRY.match(s)
        if m:
            listed[m.group(1)], lines[m.group(1)] = m.group(2), n
            continue
        m = ENTRY_START.match(s)
        if m:
            listed[m.group(1)], lines[m.group(1)] = None, n
    return listed, lines


def check(ctx):
    d = ctx.options["dir"].strip("/")
    hname = ctx.options["hashes_file"]
    folder = ctx.root / d
    hfile = folder / hname
    if not folder.is_dir() or not hfile.is_file():
        return {"result": "n/a", "detail": f"no {d}/{hname}", "hits": []}
    listed, lines = parse_hashes(ctx.read(hfile))
    hrel = f"{d}/{hname}"
    present = [f for f in ctx.files([f"{d}/*.txt"])
               if f.name != hname and not any(p.startswith("_") for p in ctx.rel(f).split("/"))]
    if not listed and not present:
        return {"result": "n/a", "detail": f"{hrel} lists no file and {d}/ holds no prediction file", "hits": []}

    hits, ok = [], []
    for name, want in listed.items():
        f = folder / name
        where = f"{d}/{name}"
        if want is None:
            hits.append({"file": hrel, "line": lines[name], "snippet": f"{name}: malformed line in {hname}"})
        elif not f.is_file():
            hits.append({"file": hrel, "line": lines[name], "snippet": f"{name}: file missing"})
        elif hashlib.sha256(f.read_bytes()).hexdigest() != want:
            hits.append({"file": where, "snippet": f"{name}: sha256 differs from {hname}"})
        else:
            ok.append(f"ok: {name} {want[:12]}")
    for f in present:
        if f.name not in listed:
            hits.append({"file": ctx.rel(f), "snippet": f"{f.name}: not listed in {hname}"})
    detail = f"{len(listed)} files listed in {hrel}, {len(ok)} match; {len(hits)} problems"
    return {"result": "fail" if hits else "pass", "detail": detail,
            "evidence": ok + [h["snippet"] for h in hits], "hits": hits}
