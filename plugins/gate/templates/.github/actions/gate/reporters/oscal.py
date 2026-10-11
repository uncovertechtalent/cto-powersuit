"""Writes an OSCAL-shaped assessment-results record next to each run record."""
import json, uuid

ID = "gate.oscal"
DESCRIPTION = "An OSCAL-shaped assessment-results record per run, next to the run record in runs/."


def report(r):
    rec = r.record
    observations = [{"uuid": str(uuid.uuid4()), "title": rid, "description": c["detail"], "methods": ["TEST"], "collected": r.ts,
                     "x-result": c["result"], "x-effective": c["effective"], "x-tier": c["tier"],
                     "relevant-evidence": [{"description": e} for e in c["evidence"][:50]]} for rid, c in rec["checks"].items()]
    findings = [{"uuid": str(uuid.uuid4()), "title": f["id"], "description": f"{f['check']}: {f.get('file') or ''} {f.get('snippet') or ''}".strip(),
                 "x-status": f["status"], "x-requirements": f.get("requirements", [])} for f in r.findings if f["status"] == "open"]
    doc = {
        "assessment-results": {
            "uuid": str(uuid.uuid4()),
            "metadata": {"title": f"Gate run, {rec['gate']}", "last-modified": r.ts, "version": r.ts, "oscal-version": "1.1.2",
                         "x-note": "OSCAL-shaped; not validated against the OSCAL schema"},
            "results": [{"uuid": str(uuid.uuid4()), "title": f"Run {r.ts} ({r.trigger})", "start": r.ts, "end": r.ts,
                         "observations": observations, "findings": findings}],
        },
        "x-gate": {"commit": rec["commit"], "overall": rec["overall"], "run_record": rec["uuid"], "components": rec["components"],
                   "requirement_states": r.requirement_states},
    }
    return {"files": {f"runs/{r.ts.replace(':', '')}-{rec['uuid'][:8]}.oscal.json": json.dumps(doc, indent=1)}}
