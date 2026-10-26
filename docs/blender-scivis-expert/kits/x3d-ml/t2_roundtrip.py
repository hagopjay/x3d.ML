"""T2: x3dprov head-meta + node Metadata survival through x3d-blender-io on bpy 5.2.3 (scratch, read-only inputs).
Run: v/bin/python -I t2_roundtrip.py   (paths below are absolute; lxml/jsonschema live in pylib)"""
import sys, os, json, hashlib, tempfile, shutil, importlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S, S + "/fork/src"]
import bpy
import x3dprov as P
from validation import validate as V
from lxml import etree

OUT = S + "/out_t2"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)

# register the add-on exactly as its own tests do (package dir symlink -> source/)
pkg = os.path.join(OUT, "pkg"); os.makedirs(pkg)
os.symlink(S + "/bio/source", os.path.join(pkg, "io_scene_x3d"))
sys.path.insert(0, pkg)
mod = importlib.import_module("io_scene_x3d")
mod.register()

DATA = b"x,y,z,t_K\n0,0,0,290.1\n1,0,0,291.2\n0,1,0,295.9\n1,1,1,301.4\n"   # stand-in dataset
data_sha = hashlib.sha256(DATA).hexdigest()

def scene_xml(tag="A"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Immersive" version="4.0"><head>
<meta name="title" content="sci point cloud {tag}"/>
<meta name="reference" content="data sha256 {data_sha[:16]} (synthetic temperature field)"/>
<meta name="license" content="CC0 synthetic"/>
</head><Scene>
<Shape DEF="T"><MetadataSet containerField="metadata" name="sci" reference="units-v0">
<MetadataString name="units" value='"K"'/><MetadataString name="colormap" value='"viridis"'/>
<MetadataString name="data_sha256" value='"{data_sha}"'/><MetadataDouble name="vmin" value="290.1"/><MetadataDouble name="vmax" value="301.4"/></MetadataSet>
<PointSet><Coordinate point="0 0 0 1 0 0 0 1 0 1 1 1"/><Color color="0.27 0.0 0.33 0.13 0.57 0.55 0.37 0.79 0.38 0.99 0.91 0.14"/></PointSet></Shape>
<Transform translation="3 0 0"><Shape DEF="M"><MetadataSet containerField="metadata" name="sci" reference="units-v0">
<MetadataString name="units" value='"K"'/><MetadataString name="colormap" value='"viridis"'/>
<MetadataString name="data_sha256" value='"{data_sha}"'/><MetadataDouble name="vmin" value="290.1"/><MetadataDouble name="vmax" value="301.4"/></MetadataSet>
<Appearance><Material diffuseColor="0.2 0.5 0.8"/></Appearance><Box size="1 1 1"/></Shape></Transform>
</Scene></X3D>
"""

def head(path_or_xml):
    x = open(path_or_xml, encoding="utf-8").read() if os.path.exists(path_or_xml) else path_or_xml
    r = etree.fromstring(x.encode())
    return [(m.get("name"), m.get("content")) for m in r.iter("meta")]

def meta_nodes(xml):
    r = etree.fromstring(xml.encode())
    return [(e.tag, e.get("name"), e.get("value")) for e in r.iter() if isinstance(e.tag, str) and e.tag.startswith("Metadata")]

def run_blender(inp, outp, keep_scene=False):
    if not keep_scene:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.ops.import_scene.x3d(filepath=inp) == {"FINISHED"}
    return bpy

def export(outp):
    assert bpy.ops.export_scene.x3d(filepath=outp, x3d_version="X3D40", use_selection=False) == {"FINISHED"}
    return open(outp, encoding="utf-8").read()

res = {"bpy": bpy.app.version_string, "bpy_hash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else bpy.app.build_hash,
       "addon": "x3d-blender-io main 482741b (manifest 2.6.4)", "validator": "x3d_mcp fork main 8dd0d3e (XSD only here)"}

# --- A: stamp a 3-step chain on the source scene
x0 = scene_xml("A")
x1 = P.add_step(x0, {"op": "ingest", "agent": "t2_roundtrip.py", "agent_ref": "scratch", "data_sha256": data_sha, "data_bytes": len(DATA)})
v0 = V.validate_xml(x1)
x2 = P.add_step(x1, {"op": "validate", "validator": "x3d_mcp fork", "validator_ref": "8dd0d3e", "xsd": v0.get("schema_version"), "xsd_valid": v0["valid"],
                     "verdict": "valid" if v0["valid"] else "invalid"})
res["A_source_verify"] = P.verify(x2)
src = os.path.join(OUT, "A_src.x3d"); open(src, "w", encoding="utf-8").write(x2)

# --- B: Blender round trip
run_blender(src, None)
scn_prop = [dict(i) for i in bpy.context.scene.get("x3d_head_meta", [])]
res["B_scene_prop_x3d_head_meta_count"] = len(scn_prop)
res["B_scene_prop_names"] = [i["name"] for i in scn_prop]
objs = [(o.name, o.type, o.get("x3d_metadata") is not None) for o in bpy.data.objects]
res["B_objects"] = objs
x_b = export(os.path.join(OUT, "B_out.x3d"))
hb = head(x_b)
res["B_out_head_names"] = [n for n, c in hb]
res["B_out_prov_survived"] = [n for n, c in hb if n.startswith("x3dprov.")] == [n for n, c in head(x2) if n.startswith("x3dprov.")]
res["B_out_prov_content_identical"] = [(n, c) for n, c in hb if n.startswith("x3dprov.")] == [(n, c) for n, c in head(x2) if n.startswith("x3dprov.")]
res["B_out_verify_before_transform_step"] = P.verify(x_b)
res["B_out_geom_tags"] = sorted({e.tag for e in etree.fromstring(x_b.encode()).iter() if isinstance(e.tag, str)})
res["B_out_metadata_nodes"] = meta_nodes(x_b)
res["A_metadata_nodes"] = meta_nodes(x2)
vb = V.validate_xml(x_b)
res["B_out_xsd"] = {"valid": vb["valid"], "n_err": len(vb["errors"]), "first": vb["errors"][:2]}
# record the Blender step (what DESIGN section 2 prescribes) and verify
x_b2 = P.add_step(x2, {"op": "transform", "tool": "x3d-blender-io", "agent_ref": "482741b", "detail": "bpy %s import+export X3D40" % bpy.app.version_string}, x_b)
res["B_after_transform_step_verify"] = P.verify(x_b2)

# --- C: Blender round trip idempotence of the record (re-import own export)
open(os.path.join(OUT, "B2.x3d"), "w", encoding="utf-8").write(x_b2)
run_blender(os.path.join(OUT, "B2.x3d"), None)
x_c = export(os.path.join(OUT, "C_out.x3d"))
res["C_verify_after_second_roundtrip_unrecorded"] = P.verify(x_c)["status"]
res["C_prov_content_identical_to_B2"] = [(n, c) for n, c in head(x_c) if n.startswith("x3dprov.")] == [(n, c) for n, c in head(x_b2) if n.startswith("x3dprov.")]

# --- D: two files with different chains imported into ONE Blender scene (multi-file import / Inline / merge)
other = P.add_step(scene_xml("B-other"), {"op": "ingest", "agent": "t2_roundtrip.py", "agent_ref": "other", "data_sha256": "f" * 64})
open(os.path.join(OUT, "D_other.x3d"), "w", encoding="utf-8").write(other)
bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.x3d(filepath=src) == {"FINISHED"}
assert bpy.ops.import_scene.x3d(filepath=os.path.join(OUT, "D_other.x3d")) == {"FINISHED"}
names = [i["name"] for i in bpy.context.scene.get("x3d_head_meta", [])]
res["D_scene_prop_names_after_two_imports"] = names
x_d = export(os.path.join(OUT, "D_out.x3d"))
res["D_out_prov_names"] = [n for n, c in head(x_d) if n.startswith("x3dprov.")]
res["D_verify"] = P.verify(x_d)
# --- E: one file imported twice
bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.x3d(filepath=src) == {"FINISHED"}
assert bpy.ops.import_scene.x3d(filepath=src) == {"FINISHED"}
x_e = export(os.path.join(OUT, "E_out.x3d"))
res["E_same_file_twice_prov_names"] = [n for n, c in head(x_e) if n.startswith("x3dprov.")]

print(json.dumps(res, indent=1, default=str))
json.dump(res, open(OUT + "/t2_result.json", "w"), indent=1, default=str)
