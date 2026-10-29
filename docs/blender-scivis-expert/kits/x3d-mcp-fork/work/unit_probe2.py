import sys, os, importlib, tempfile, json, re
from pathlib import Path
import bpy
addon, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp(); (Path(tmp) / "io_scene_x3d").symlink_to(Path(addon), target_is_directory=True); sys.path.insert(0, tmp)
importlib.import_module("io_scene_x3d").register()
res = {"bpy": bpy.app.version_string}
for label, scale_len, unit_mode in (("scene_mm_scale0.001__file_unit_M", 0.001, "M"), ("scene_mm_scale0.001__file_unit_MM", 0.001, "MM"), ("scene_m_scale1__file_unit_M", 1.0, "M"), ("scene_m_scale1__file_unit_MM", 1.0, "MM")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = scale_len
    bpy.ops.mesh.primitive_cube_add(size=40, location=(0, 0, 0))
    p = os.path.join(out, "u2.x3d")
    bpy.ops.export_scene.x3d(filepath=p, x3d_version="X3D40", file_unit=unit_mode)
    t = Path(p).read_text()
    m = re.search(r'<Coordinate[^>]*point="([^"]+)"', t)
    res[label] = {"first_coord": m.group(1).split()[:3] if m else None, "unit_stmt": "<unit" in t}
print(json.dumps(res, indent=1))
