import sys, glob, os, re, json
src = sys.argv[1]; sys.path.insert(0, src)
from lxml import etree
from validation.validate import validate_xml
from validation.semantic import validate_semantic
from validation.profile import check_profile
res = {}
for path in sys.argv[2:]:
    raw = open(path, "rb").read(); xml = raw.decode("utf-8")
    try:
        schema = validate_xml(xml)
    except Exception as e:
        schema = {"valid": None, "errors": [f"EXC {type(e).__name__}: {e}"]}
    try:
        sem = validate_semantic(xml)
        m = re.search(r"Found (\d+) error\(s\), (\d+) warning", sem); se, sw = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    except Exception as e:
        sem, se, sw = f"EXC {e}", None, None
    try:
        prof = check_profile(etree.fromstring(raw)); pok = prof.ok; pm = [x.get("node") for x in prof.missing][:5]
    except Exception as e:
        pok, pm = None, [f"EXC {e}"]
    print(f"{os.path.basename(path):34s} {len(raw):>9d}B xsd={schema.get('valid')} sem={se}e/{sw}w profile_ok={pok} {pm} {[str(x)[:160] for x in (schema.get('errors') or [])][:2]}")
