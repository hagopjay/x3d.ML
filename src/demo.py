"""Prototype run: ingest -> validate -> deterministic repair -> validate -> Blender round trip -> validate -> verify -> tamper tests.
Usage: python3 demo.py <in.x3d> <outdir>      Validator: fork x3d_mcp (path in VALIDATOR_TREE)."""
import sys, os, json, re, time, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P
VALIDATOR_TREE = "/tmp/claude-0/w/x3d_mcp"; VALIDATOR_REF = "eb4b4b4"
BRIDGE = "/tmp/claude-0/w/x3d-blender-io"; BRIDGE_REF = "206f139"
sys.path[0:0] = [VALIDATOR_TREE + "/src", VALIDATOR_TREE]
from validation.validate import validate_xml
from validation.semantic import validate_semantic

def validate(xml):
    t = time.time(); x = validate_xml(xml); sem = validate_semantic(xml)
    errs = re.findall(r"- \*\*\[([\w-]+)\]\*\*", sem.split("## Warnings")[0].split("## Info")[0]) if "## Errors" in sem else []
    return {"op": "validate", "validator": "x3d_mcp fork", "validator_ref": VALIDATOR_REF, "xsd": x.get("schema_version"),
            "xsd_valid": bool(x.get("valid")), "semantic_error_codes": sorted(set(errs)),
            "verdict": "valid" if x.get("valid") and not errs else "invalid", "ms": int((time.time() - t) * 1000)}

def autofix(xml, report):
    comps = sorted(set(re.findall(r"<component name='([^']+)' level='(\d+)'/>", report)))
    lines = "".join(f"<component name='{n}' level='{l}'/>" for n, l in comps)
    return re.sub(r"(<head\b[^>]*>)", r"\1" + lines, xml, count=1) if re.search(r"<head\b[^>]*>", xml) else \
        re.sub(r"(<X3D\b[^>]*>)", r"\1<head>" + lines + "</head>", xml, count=1)

BLENDER = r'''
import sys, bpy, importlib
sys.path.insert(0, sys.argv[-3]); m = importlib.import_module("io_scene_x3d")
try: m.register()
except Exception: pass
bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.x3d(filepath=sys.argv[-2]) == {"FINISHED"}
assert bpy.ops.export_scene.x3d(filepath=sys.argv[-1], x3d_version="X3D40", use_selection=False) == {"FINISHED"}
'''
def blender_roundtrip(xml, tmp):
    pk = os.path.join(tmp, "pk"); os.makedirs(pk, exist_ok=True)
    link = os.path.join(pk, "io_scene_x3d")
    if not os.path.exists(link): os.symlink(BRIDGE + "/source", link)
    src, dst = os.path.join(tmp, "in.x3d"), os.path.join(tmp, "out.x3d")
    open(src, "w").write(xml); open(os.path.join(tmp, "rt.py"), "w").write(BLENDER)
    r = subprocess.run([sys.executable, os.path.join(tmp, "rt.py"), pk, src, dst], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-800:])
    return open(dst).read()

def main(inp, out):
    os.makedirs(out, exist_ok=True); tmp = tempfile.mkdtemp()
    x = open(inp, encoding="utf-8").read(); log = []
    def save(name, text): open(os.path.join(out, name), "w").write(text)
    x = P.add_step(x, {"op": "ingest", "agent": "hand-or-cached", "origin": os.path.basename(inp)}); save("0-ingest.x3d", x)
    v = validate(x); x = P.add_step(x, v); save("1-validated.x3d", x)
    if v["verdict"] == "invalid":
        rep = validate_semantic(x)
        fixed = autofix(x, rep)
        x = P.add_step(x, {"op": "repair", "agent": "autofix:add-missing-component-lines", "kind": "deterministic", "model": None,
                           "report_shown": True, "fixes": v["semantic_error_codes"]}, fixed); save("2-repaired.x3d", x)
        v = validate(x); x = P.add_step(x, v); save("3-revalidated.x3d", x)
    rt = blender_roundtrip(x, tmp)
    kept = len(P.read_steps(rt))
    x = P.add_step(x, {"op": "transform", "agent": "x3d-blender-io", "agent_ref": BRIDGE_REF, "tool": "blender 5.2.2 (bpy wheel)",
                       "detail": "import_scene.x3d -> export_scene.x3d X3D40", "record_survived_in_tool_output": kept}, rt); save("4-blender.x3d", x)
    v = validate(x); x = P.add_step(x, v); save("5-final.x3d", x)
    res = {"bytes_in": os.path.getsize(inp), "bytes_out": len(x.encode()), "input": os.path.basename(inp), "final_verify": P.verify(x), "steps": P.summary(x),
           "blender_kept_meta_steps": kept}
    # tamper tests
    t1 = re.sub(r'(<Box size=")([^"]*)', r'\g<1>9 9 9', x, count=1) if "<Box" in x else x.replace("<Shape", "<Shape DEF='Z'", 1)
    t2 = re.sub(r'<meta name="x3dprov\.step\.2"[^>]*/>', "", x)
    q = "&quot;verdict&quot;:&quot;"
    j = x.find(q + "invalid"); k = x.find(q + "valid")
    t3 = (x[:j] + q + "valid" + x[j + len(q) + 7:]) if j >= 0 else (x[:k] + q + "invalid" + x[k + len(q) + 5:])   # interior step verdict flipped
    last = x.rindex(q + "valid"); t4 = x[:last] + q + "invalid" + x[last + len(q) + 5:]           # LAST step: valid -> invalid
    res["tamper"] = {"content edited after last step": P.verify(t1)["status"], "step 2 deleted": P.verify(t2)["status"],
                     "interior step verdict flipped": P.verify(t3)["status"], "LAST step verdict flipped (no successor, unsigned)": P.verify(t4)["status"], "pristine": P.verify(x)["status"]}
    save("result.json", json.dumps(res, indent=1)); print(json.dumps({k: res[k] for k in ("final_verify", "blender_kept_meta_steps", "tamper")}, indent=1))
    return res
if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
