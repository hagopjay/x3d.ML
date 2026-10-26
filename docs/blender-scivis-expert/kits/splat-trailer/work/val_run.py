import sys, json, time, os
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1] + "/src")
from lxml import etree
print("lxml", etree.LXML_VERSION, "libxml2", etree.LIBXML_VERSION, file=sys.stderr)
from src.validation.validate import validate_xml
from src.validation.semantic import semantic_diagnostics
for p in sys.argv[2:]:
    s = open(p, encoding="utf-8").read()
    t = time.time(); r = validate_xml(s); t1 = time.time() - t
    try:
        sd = semantic_diagnostics(s); sem = {"errors": sum(d.level == "error" for d in sd), "warnings": sum(d.level == "warning" for d in sd), "checks": sorted({d.check for d in sd})}
    except Exception as e:
        sem = {"exception": str(e)[:200]}
    print(json.dumps({"file": os.path.basename(p), "xsd_valid": r.get("valid"), "xsd_errors": [str(e)[:160] for e in (r.get("errors") or [])][:2], "xsd_s": round(t1, 1), "semantic": sem}))
