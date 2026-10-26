"""Blender-lane tether probe. Run: v/bin/python -I blender_lane_probe.py OUTDIR
Writer = a bpy script (what a Blender MCP execute_code would run). Accountable artifact = exported X3D 4.0.
Oracle = x3d_mcp fork main 8dd0d3e (XSD + semantic). Ledger = x3dprov head meta, carried via scene['x3d_head_meta'].
"""
import sys, os, json, hashlib, importlib, tempfile
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/agentics"
sys.path[:0] = [S + "/deps", S + "/x3d_mcp/src", S + "/x3d_mcp", "/mnt/project-files/research/traceability-2026-10-17"]
out = sys.argv[1]; os.makedirs(out, exist_ok=True)

import bpy, mathutils
pkg = tempfile.mkdtemp(prefix="x3dpkg_")
os.symlink(S + "/x3d-blender-io/source", pkg + "/io_scene_x3d")
sys.path.insert(0, pkg)
mod = importlib.import_module("io_scene_x3d"); mod.register()

from playground.report import full_report
import x3dprov

def validate(path):
    t = open(path, encoding="utf-8").read()
    r = full_report(t, with_repair_preview=False)
    return r

def summarize(r):
    f = r["findings"]
    return {"verdict": r.get("verdict"), "errors": sum(1 for x in f if x["level"] == "error"),
            "warnings": sum(1 for x in f if x["level"] == "warning"),
            "checks": sorted({(x["layer"], x["check"]) for x in f if x["level"] == "error"}),
            "first": [x["message"][:160] for x in f if x["level"] == "error"][:3]}

def export(path, anim=False):
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_animation=anim)
    return open(path, encoding="utf-8").read()

def head_infos(xml):
    from lxml import etree
    root = etree.fromstring(xml.encode())
    return [(m.get("name"), m.get("content")) for m in root.iter("meta")]

# ---------- writer: agent-style bpy script, intentionally Blender-lane-typical ----------
def writer_v0():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1)); sph = bpy.context.object; sph.name = "Ball"
    bpy.ops.mesh.primitive_plane_add(size=10); fl = bpy.context.object; fl.name = "Floor"
    fl.scale = (1, 2, 1)                       # non-uniform, unapplied scale
    m = bpy.data.materials.new("Red"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.8, 0.05, 0.05, 1); b.inputs["Metallic"].default_value = 0.9
    b.inputs["Roughness"].default_value = 0.2
    b.inputs["Emission Color"].default_value = (1, 0.3, 0, 1); b.inputs["Emission Strength"].default_value = 5.0   # >1: no X3D 4.0 field
    sph.data.materials.append(m)
    # procedural texture: cannot be expressed in X3D
    m2 = bpy.data.materials.new("Marble"); m2.use_nodes = True
    n = m2.node_tree.nodes.new("ShaderNodeTexNoise"); b2 = m2.node_tree.nodes["Principled BSDF"]
    m2.node_tree.links.new(n.outputs["Color"], b2.inputs["Base Color"]); fl.data.materials.append(m2)
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 6)); bpy.context.object.data.energy = 3.0
    bpy.ops.object.camera_add(location=(6, -6, 4), rotation=(1.1, 0, 0.8)); sc.camera = bpy.context.object

writer_v0()
p0 = out + "/v0_blender_lane.x3d"
x0 = export(p0)
r0 = validate(p0)
res = {"blender": bpy.app.version_string, "fork": "8dd0d3e", "importer": "482741b"}
res["v0"] = summarize(r0)
res["v0_head_meta"] = head_infos(x0)


# ---------- loss audit (Blender-side oracle the validator cannot be) ----------
def loss_audit():
    L = []
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                if n.inputs["Emission Strength"].default_value not in (0.0, 1.0) and any(c != 0 for c in n.inputs["Emission Color"].default_value[:3]):
                    L.append(("emission-strength-lost", m.name, n.inputs["Emission Strength"].default_value))
                for inp in n.inputs:
                    for lk in inp.links:
                        if lk.from_node.type not in ('TEX_IMAGE', 'NORMAL_MAP', 'BUMP', 'SEPARATE_COLOR', 'SEPARATE_RGB', 'MAPPING', 'TEX_COORD', 'UVMAP'):
                            L.append(("procedural-input-lost", m.name, f"{inp.name}<-{lk.from_node.bl_idname}"))
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.data.energy > 1.0:
            L.append(("light-intensity-clamped", o.name, o.data.energy))
    return L
audit = loss_audit()
res["v0_loss_audit"] = audit
print("LOSS AUDIT", audit)

# ---------- ledger through the file ----------
S256 = lambda b: hashlib.sha256(b).hexdigest()
writer_src = open(__file__).read().split("def writer_v0")[1].split("writer_v0()")[0]
x = x0
x = x3dprov.add_step(x, {"op": "generate", "agent": "bpy-script", "agent_ref": "blender 5.2.3", "prompt_sha256": S256(b"demo"), "script_sha256": S256(writer_src.encode())}, xml_after=x)
x = x3dprov.add_step(x, {"op": "transform", "tool": "x3d-blender-io", "agent_ref": "482741b", "detail": "export X3D 4.0 from .blend"})
rep = full_report(x, with_repair_preview=False)
x = x3dprov.add_step(x, {"op": "validate", "validator": "x3d_mcp fork", "validator_ref": "8dd0d3e", "verdict": rep.get("verdict"), "errors": 0})
x = x3dprov.add_step(x, {"op": "judge", "validator": "blender_loss_audit", "validator_ref": "probe-0", "verdict": "lossy", "findings": [a[0] for a in audit]})
p1 = out + "/v1_stamped.x3d"; open(p1, "w", encoding="utf-8").write(x)
res["stamped_verify"] = x3dprov.verify(x)
res["stamped_still_valid"] = summarize(validate(p1))      # does the ledger itself break the validator?

# ---------- through Blender: import, re-export ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.x3d(filepath=p1)
sc = bpy.context.scene
kept = [(d["name"]) for d in sc.get("x3d_head_meta", [])] if sc.get("x3d_head_meta") else []
res["import_kept_head_meta_names"] = kept
p2 = out + "/v2_roundtrip.x3d"
x2 = export(p2)
res["roundtrip_head_meta_names"] = [n for n, c in head_infos(x2)]
res["roundtrip_verify_unrecorded"] = x3dprov.verify(x2)
x2b = x3dprov.add_step(x2, {"op": "transform", "tool": "x3d-blender-io", "agent_ref": "482741b", "detail": "import+export round trip, bpy 5.2.3"})
res["roundtrip_verify_recorded"] = x3dprov.verify(x2b)
res["roundtrip_valid"] = summarize(validate(p2))
# does repeated export from same blend give the same content hash?
x2c = export(out + "/v2_again.x3d")
res["export_deterministic_content_hash"] = x3dprov.content_hash(x2) == x3dprov.content_hash(x2c)
# what did the importer see of the lost things (does the loss compound)?
res["audit_after_roundtrip"] = loss_audit()
open(out + "/v3_roundtrip_recorded.x3d", "w", encoding="utf-8").write(x2b)
json.dump(res, open(out + "/result.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:6000])
