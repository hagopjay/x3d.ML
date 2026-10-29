"""run the validators of one tree on one file: usage val_one.py <tree_dir> <file>; prints one JSON line"""
import sys, json, time
tree, f = sys.argv[1], sys.argv[2]
sys.path[0:0] = [tree + "/src", tree]
xml = open(f, encoding="utf-8", errors="replace").read()
t = time.time(); res = {"tree": tree.split("/")[-1], "file": f.split("/")[-1], "bytes": len(xml)}
try:
    from validation.validate import validate_xml
    r = validate_xml(xml); res["xsd_valid"] = r.get("valid"); res["xsd_err"] = (r.get("errors") or [None])[0] if not r.get("valid") else None
    res["xsd_keys"] = sorted(r.keys())
except Exception as e: res["xsd_exc"] = repr(e)[:200]
try:
    from validation.semantic import validate_semantic
    rep = validate_semantic(xml); res["sem_head"] = rep.splitlines()[0][:120] if rep else ""
except Exception as e: res["sem_exc"] = repr(e)[:200]
res["s"] = round(time.time() - t, 1)
print(json.dumps(res)[:900])
