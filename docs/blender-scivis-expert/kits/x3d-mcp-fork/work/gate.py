"""Phase B of the guardrail (validator venv): gate an exported X3D and finish the ledger row."""
import sys, os, json, hashlib, subprocess
from pathlib import Path
src, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, src); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics
import sci_checks
bl = json.loads(Path(out, "bl_phase.json").read_text())
text = Path(out, "export.x3d").read_text(encoding="utf-8")
commit = subprocess.run(["git", "-C", src, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
xsd = validate_xml(text); sem = semantic_diagnostics(text); sci = sci_checks.run(text, src)
row = dict(bl, sha256_16=hashlib.sha256(text.encode()).hexdigest()[:16], bytes=len(text), validator_commit=commit,
           xsd_valid=xsd["valid"], xsd_errors=xsd["errors"][:3], schema_version=xsd["schema_version"],
           semantic=[[d.level, d.check] for d in sem],
           sci=[[d.level, d.check, d.message[:260]] for d in sci if d.check not in ("splat-size-budget", "provenance-meta-missing")])
Path(out, "ledger.json").write_text(json.dumps(row, indent=1))
errs = [g for g in bl["guard"] if g[0] == "error"] + [d for d in sem if d.level == "error"] + [d for d in sci if d.level == "error"]
warn = bl["guard"] + [d for d in sem + sci if d.level == "warning"]
verdict = "FAIL" if (errs or not xsd["valid"]) else ("WARN" if warn else "PASS")
print(json.dumps({"verdict": verdict, "sha": row["sha256_16"], "xsd_valid": xsd["valid"], "validator": commit, "addon": bl["addon"],
                  "guard": bl["guard"], "semantic": row["semantic"], "sci": [[s[0], s[1]] for s in row["sci"]]}))
sys.exit(1 if verdict == "FAIL" else 0)
