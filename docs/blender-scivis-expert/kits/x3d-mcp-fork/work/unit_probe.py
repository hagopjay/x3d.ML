import sys, os, importlib, tempfile, json, re
from pathlib import Path
import bpy
addon, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp(); (Path(tmp) / "io_scene_x3d").symlink_to(Path(addon), target_is_directory=True); sys.path.insert(0, tmp)
importlib.import_module("io_scene_x3d").register()
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = 0.001; sc.unit_settings.length_unit = "MILLIMETERS"
bpy.ops.mesh.primitive_cube_add(size=40, location=(0, 0, 0))   # 40 mm cube in a mm scene
res = {"bpy": bpy.app.version_string, "unit_scale_length": sc.unit_settings.scale_length}
for ver in ("X3D33", "X3D40", "X3D41"):
    p = os.path.join(out, f"unit_{ver}.x3d")
    r = bpy.ops.export_scene.x3d(filepath=p, x3d_version=ver, file_unit="MM", meta_title="t", meta_creator="c", meta_license="Unlicense")
    t = Path(p).read_text()
    head = t[t.find("<head>"):t.find("</head>")]
    pts = re.findall(r'(?:point|size)="([^"]+)"', t)
    res[ver] = {"has_unit_stmt": "<unit" in t, "meta_names": re.findall(r'<meta name="([^"]+)"', head), "first_point_or_size": pts[:1]}
print(json.dumps(res, indent=1))
