"""T9: where can a MetadataSet sit and still survive x3d-blender-io import->export on bpy 5.2.3 (add-on 482741b)?"""
import sys, os, json, importlib, re
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S]
import bpy
from lxml import etree
sys.path.insert(0, S + "/out_t4/pkg"); importlib.import_module("io_scene_x3d").register()
os.makedirs(S + "/out_t9", exist_ok=True)
MS = lambda tag: f'<MetadataSet containerField="metadata" name="where_{tag}"><MetadataString name="units" value=\'"K"\'/></MetadataSet>'
splat = open(S + "/out_t7/splats0.x3d", encoding="utf-8").read()
# splat variant: MetadataSet child of GaussianSplats
sp = re.sub(r"(<GaussianSplats [^>]*?)\s*/>", lambda m: m.group(1) + ">" + MS("gsplat") + "</GaussianSplats>", splat, count=1)
base = lambda body: f'<?xml version="1.0" encoding="UTF-8"?><X3D profile="Immersive" version="4.0"><head/><Scene>{body}</Scene></X3D>'
cases = {
 "shape": base(f'<Shape>{MS("shape")}<Box/></Shape>'),
 "transform": base(f'<Transform translation="1 0 0">{MS("transform")}<Shape><Box/></Shape></Transform>'),
 "group": base(f'<Group>{MS("group")}<Shape><Box/></Shape></Group>'),
 "appearance_material": base('<Shape><Appearance><Material diffuseColor="1 0 0">' + MS("material") + '</Material></Appearance><Box/></Shape>'),
 "geometry_box": base('<Shape><Box>' + MS("box") + '</Box></Shape>'),
 "worldinfo": base('<WorldInfo title="w">' + MS("worldinfo") + '</WorldInfo><Shape><Box/></Shape>'),
 "gaussiansplats": sp,
}
res = {"bpy": bpy.app.version_string}
for name, x in cases.items():
    p = f"{S}/out_t9/{name}.x3d"; open(p, "w", encoding="utf-8").write(x)
    ver = "X3D41" if name == "gaussiansplats" else "X3D40"
    os.environ["X3D_SPLAT_IMPORT"] = "mesh"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ok = bpy.ops.import_scene.x3d(filepath=p) == {"FINISHED"}
    o = f"{S}/out_t9/{name}_out.x3d"
    ok2 = bpy.ops.export_scene.x3d(filepath=o, x3d_version=ver, use_selection=False) == {"FINISHED"}
    out = open(o, encoding="utf-8").read()
    res[name] = {"in": f"where_{name.split('_')[0] if name!='gaussiansplats' else 'gsplat'}" in x, "survived": ("where_" in out) and (f'name="where_' in out), "import_ok": ok, "export_ok": ok2}
    res[name]["survived"] = bool(re.search(r'name="where_', out))
print(json.dumps(res, indent=1))
