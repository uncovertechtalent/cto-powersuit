#!/usr/bin/env python3
"""Query the OSV vulnerability database for every package in an SBOM, without a scanner installed.

Reads the package URLs (purl) from an SPDX 2.x JSON or a CycloneDX JSON SBOM, asks the OSV batch API
(https://api.osv.dev, public, no key) which known vulnerabilities affect each pinned version, then
reads each vulnerability for its severity (from its advisory alias when the entry has none), aliases
and fixed versions. Packages without a version in
the purl are skipped and counted: OSV needs the version.

Usage:
  osv_query.py <sbom.json> [--json]

Exit codes: 0 no known vulnerability, 1 vulnerabilities found, and 3 the SBOM or the API could not be read.
Standard library only, Python 3.9+. Sends package names and versions to api.osv.dev, nothing else.
"""
import argparse, json, sys, urllib.request

API = "https://api.osv.dev/v1"
BATCH = 1000
RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}


def fetch(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def purls(sbom):
    """Package URLs from an SPDX (packages[].externalRefs) or CycloneDX (components[].purl) document."""
    found = []
    for p in sbom.get("packages", []):
        for ref in p.get("externalRefs", []):
            if ref.get("referenceType") == "purl" and ref.get("referenceLocator"):
                found.append(ref["referenceLocator"])

    def walk(components):
        for c in components or []:
            if c.get("purl"):
                found.append(c["purl"])
            walk(c.get("components"))
    walk(sbom.get("components"))
    return sorted(set(found))


def severity(vuln):
    sev = (vuln.get("database_specific") or {}).get("severity")
    if sev:
        return {"MODERATE": "medium"}.get(sev.upper(), sev.lower())
    return "unknown"


def fixed_versions(vuln, purl):
    base = purl.split("@", 1)[0].lower()
    out = []
    for a in vuln.get("affected", []):
        if (a.get("package") or {}).get("purl", "").split("@", 1)[0].lower() not in ("", base):
            continue
        for r in a.get("ranges", []):
            out += [e["fixed"] for e in r.get("events", []) if "fixed" in e]
    return sorted(set(out))


def query(all_purls, get=fetch):
    pinned = [p for p in all_purls if "@" in p]
    rows, details = [], {}
    for i in range(0, len(pinned), BATCH):
        chunk = pinned[i:i + BATCH]
        res = get(f"{API}/querybatch", {"queries": [{"package": {"purl": p}} for p in chunk]})
        for p, r in zip(chunk, res.get("results", [])):
            for v in r.get("vulns", []):
                if v["id"] not in details:
                    details[v["id"]] = get(f"{API}/vulns/{v['id']}")
                d = details[v["id"]]
                sev = severity(d)
                for alias in d.get("aliases", []):
                    if sev == "unknown" and alias.startswith("GHSA-"):
                        if alias not in details:
                            details[alias] = get(f"{API}/vulns/{alias}")  # advisory entries carry a severity level
                        sev = severity(details[alias])
                rows.append({"purl": p, "id": v["id"], "aliases": d.get("aliases", []), "severity": sev,
                             "fixed": fixed_versions(d, p), "summary": (d.get("summary") or "")[:120]})
    return {"packages": len(all_purls), "queried": len(pinned), "skipped_no_version": len(all_purls) - len(pinned), "vulns": rows}


def main():
    ap = argparse.ArgumentParser(description="OSV lookup for the packages of an SBOM")
    ap.add_argument("sbom")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        with open(a.sbom, encoding="utf-8") as f:
            doc = json.load(f)
        r = query(purls(doc.get("sbom", doc)))  # the GitHub dependency-graph export wraps the SPDX document in "sbom"
    except (OSError, ValueError, KeyError) as e:
        print(f"osv_query: {e}", file=sys.stderr)
        sys.exit(3)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{r['packages']} packages, {r['queried']} queried, {r['skipped_no_version']} without a version, {len(r['vulns'])} known vulnerabilities")
        for v in sorted(r["vulns"], key=lambda v: RANK.get(v["severity"], len(RANK))):
            print(f"  {v['severity']:8} {v['id']:22} {v['purl']}  fixed in: {', '.join(v['fixed']) or 'no fix listed'}")
    sys.exit(1 if r["vulns"] else 0)


if __name__ == "__main__":
    main()
