import sys, os, importlib, tempfile, json, re
from pathlib import Path
import bpy
addon = sys.argv[1]; out = sys.argv[2]
tmp = tempfile.mkdtemp(); (Path(tmp) / "io_scene_x3d").symlink_to(Path(addon), target_is_directory=True); sys.path.insert(0, tmp)
importlib.import_module("io_scene_x3d").register()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); cube = bpy.context.active_object
cube.location = (0, 0, 0); cube.keyframe_insert("location", frame=1)
cube.location = (4, 0, 0); cube.keyframe_insert("location", frame=49)
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 49
bpy.context.scene.render.fps = 24
res = {"bpy": bpy.app.version_string, "blender_version_higher_44_flag": None}
try:
    sys.path.insert(0, addon)
    mod = sys.modules["io_scene_x3d"]
    res["blender_version_higher_44_flag"] = getattr(mod, "blender_version_higher_44", "attr missing")
except Exception as e:
    res["flag_err"] = repr(e)
res["anim_data"] = cube.animation_data is not None and cube.animation_data.action is not None
for ver in ("X3D40", "X3D41"):
    p = os.path.join(out, f"anim_{ver}.x3d")
    r = bpy.ops.export_scene.x3d(filepath=p, x3d_version=ver, use_animation=True)
    t = Path(p).read_text()
    res[ver] = {"result": sorted(r), "TimeSensor": len(re.findall(r"<TimeSensor", t)), "PositionInterpolator": len(re.findall(r"<PositionInterpolator", t)),
                "ROUTE": len(re.findall(r"<ROUTE", t)), "keyframe_cycleInterval": re.findall(r'cycleInterval="([^"]+)"', t)[:1]}
print(json.dumps(res))
