import sys, os, json, hashlib
from pathlib import Path
br, x3d, out = sys.argv[sys.argv.index("--")+1:][:3]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("lo_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
pkg = tmp / "io_scene_x3d"
if not pkg.exists(): pkg.symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib
m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register()
bpy.ops.import_scene.x3d(filepath=x3d)
rows = []
for o in bpy.data.objects:
    mats = [s.material.name for s in o.material_slots if s.material]
    info = {"name": o.name, "type": o.type, "mats": mats, "hide_render": o.hide_render, "hide_viewport": o.hide_viewport}
    for s in o.material_slots:
        mt = s.material
        if mt and mt.use_nodes:
            p = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if p:
                info["emission"] = [round(v, 3) for v in p.inputs["Emission Color"].default_value[:3]]
                info["alpha_linked"] = p.inputs["Alpha"].is_linked
                info["alpha"] = round(p.inputs["Alpha"].default_value, 3)
                info["render_method"] = mt.surface_render_method
                info["emis_linked"] = p.inputs["Emission Color"].is_linked
    rows.append(info)
json.dump(rows, open(out, "w"), indent=0)
print("N", len(rows))
