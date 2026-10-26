"""T7: splat fixture (x3d-blender-io tools/splat_fixture.py, 48 splats SH1) -> X3D 4.1 -> stamp x3dprov -> Blender 5.2.3 import (splat mesh fallback) -> X3D 4.1 export.
Checks: head meta/chain survive on the splat path, 4.1 XSD validity on fork 8dd0d3e, splat attribute drift."""
import sys, os, json, importlib, hashlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S, S + "/fork/src", S + "/bio/tools"]
import bpy
import x3dprov as P
from validation import validate as V
from lxml import etree
OUT = S + "/out_t7"; os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, S + "/out_t4/pkg"); importlib.import_module("io_scene_x3d").register()
import splat_fixture
bpy.ops.wm.read_factory_settings(use_empty=True)
splat_fixture.build_splat_fixture(count=48)
f0 = OUT + "/splats0.x3d"
assert bpy.ops.export_scene.x3d(filepath=f0, x3d_version="X3D41", use_selection=False) == {"FINISHED"}
x0 = open(f0, encoding="utf-8").read()
x1 = P.add_step(x0, {"op": "ingest", "agent": "t7", "agent_ref": "splat_fixture.py"})
v = V.validate_xml(x1)
x2 = P.add_step(x1, {"op": "validate", "validator": "x3d_mcp fork", "validator_ref": "8dd0d3e", "xsd": v["schema_version"], "xsd_valid": v["valid"]})
f1 = OUT + "/splats1_stamped.x3d"; open(f1, "w", encoding="utf-8").write(x2)
bpy.ops.wm.read_factory_settings(use_empty=True)
os.environ["X3D_SPLAT_IMPORT"] = "mesh"
assert bpy.ops.import_scene.x3d(filepath=f1) == {"FINISHED"}
objs = [(o.name, o.type, bool(o.data.get("x3d_gaussian_splats")) if o.type == "MESH" else None) for o in bpy.data.objects]
f2 = OUT + "/splats2.x3d"
assert bpy.ops.export_scene.x3d(filepath=f2, x3d_version="X3D41", use_selection=False) == {"FINISHED"}
x_out = open(f2, encoding="utf-8").read()
x3 = P.add_step(x2, {"op": "transform", "tool": "x3d-blender-io", "agent_ref": "482741b", "detail": "bpy %s import(mesh fallback)+export X3D41" % bpy.app.version_string}, x_out)
def attrs(x):
    r = etree.fromstring(x.encode()); g = next(e for e in r.iter() if e.tag == "GaussianSplats")
    return {k: [float(t) for t in v.split()] for k, v in g.attrib.items() if k not in ("DEF", "colorSpace", "USE")}
a0, a2 = attrs(x0), attrs(x_out)
drift = {k: (max(abs(p - q) for p, q in zip(a0[k], a2[k])) if k in a2 and len(a0[k]) == len(a2[k]) else "missing/len-mismatch") for k in a0}
res = {"bpy": bpy.app.version_string, "objects_after_import": objs,
       "head_prov_survived_names": [n for n, c in [(m.get("name"), m.get("content")) for m in etree.fromstring(x_out.encode()).iter("meta")] if n.startswith("x3dprov")],
       "stamped_xsd": {"valid": v["valid"], "schema": v["schema_version"]}, "out_xsd": V.validate_xml(x_out)["valid"],
       "verify_unrecorded": P.verify(x_out)["status"], "verify_after_transform_step": P.verify(x3)["status"],
       "splat_attr_max_abs_drift_first_vs_second_export": drift, "n_splats": len(a0["positions"]) // 3,
       "gaussian_nodes_in_out": sum(1 for e in etree.fromstring(x_out.encode()).iter() if e.tag == "GaussianSplats")}
print(json.dumps(res, indent=1, default=str)); json.dump(res, open(OUT + "/t7_result.json", "w"), indent=1, default=str)
