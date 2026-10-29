import sys, os, json, importlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S]
import bpy
sys.path.insert(0, S + "/out_t4/pkg"); importlib.import_module("io_scene_x3d").register()
bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.x3d(filepath=S + "/out_t2/B2.x3d") == {"FINISHED"}
p = S + "/out_t4/prov.blend"; bpy.ops.wm.save_as_mainfile(filepath=p)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=p)
sc = bpy.context.scene
res = {"blend_bytes": os.path.getsize(p), "scene_prop_names_after_reload": [i["name"] for i in sc["x3d_head_meta"]],
       "object_meta_after_reload": {o.name: [n.get("name") for n in (o.get("x3d_metadata", {}).get("value", []) if hasattr(o.get("x3d_metadata", None), "get") else [])] for o in bpy.data.objects},
       "handlers": sorted(h for h in dir(bpy.app.handlers) if not h.startswith("_") and ("render" in h or "save" in h or "load" in h)),
       "color_mgmt": {"view_transforms": [e.identifier for e in sc.view_settings.bl_rna.properties["view_transform"].enum_items][:8]}}
print(json.dumps(res, indent=1))
