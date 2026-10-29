"""Stage 1 (system python + lxml): stamp the splat fixture with x3dprov (ingest, validate) using the fork validator tree."""
import sys, os, json, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[0:0] = [HERE + "/xprov", HERE + "/x3d_mcp/src", HERE + "/x3d_mcp"]
import x3dprov as P
from validation.validate import validate_xml
from validation.semantic import validate_semantic

src = sys.argv[1]; out = sys.argv[2]
raw = open(src, "rb").read()
xml = raw.decode("utf-8")
fork = subprocess.run(["git", "-C", HERE + "/x3d_mcp", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

def codes(section):
    return sorted(set(l.split("]**")[0].split("[")[-1] for l in section.splitlines() if l.startswith("- **[")))

def verdict(x):
    r = validate_xml(x); sem = validate_semantic(x)
    errs = codes(sem.split("## Warnings")[0].split("## Info")[0]) if "## Errors" in sem else []
    warns = codes(sem.split("## Warnings")[1].split("## Info")[0]) if "## Warnings" in sem else []
    return {"xsd_valid": bool(r.get("valid")), "errors": errs, "warns": warns, "verdict": "valid" if (r.get("valid") and not errs) else "invalid"}

v0 = verdict(xml)
print("fixture verdict before stamping:", v0)
xml = P.add_step(xml, {"op": "ingest", "agent": "scratch-stage1", "kind": "fixture", "file_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
v1 = verdict(xml)
print("verdict after ingest stamp (x3dprov metas present):", v1)
xml = P.add_step(xml, {"op": "validate", "validator": "x3d_mcp", "validator_ref": fork, "xsd_valid": v1["xsd_valid"],
                       "semantic_error_codes": v1["errors"], "verdict": v1["verdict"]})
open(out, "w", encoding="utf-8").write(xml)
print("stamped:", P.verify(xml), "fork", fork)
print("verdict unchanged by x3dprov metas:", v0 == v1 or (v0["verdict"], v0["errors"], v0["xsd_valid"]) == (v1["verdict"], v1["errors"], v1["xsd_valid"]))
