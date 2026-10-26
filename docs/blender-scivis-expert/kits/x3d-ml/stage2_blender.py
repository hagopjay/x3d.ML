"""Stage 2 (bpy 5.2.3 venv python -I): import the stamped splat fixture with x3d-blender-io, export X3D 4.1 and 4.0, and also
render a tiny Cycles-CPU still with stamp metadata to test how a figure can carry a pointer back to the chain."""
import sys, os, json, tempfile, struct, zlib, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE + "/x3d-blender-io/source"
tmp = tempfile.mkdtemp(prefix="x3dml_rt_")
pkg = os.path.join(tmp, "io_scene_x3d")
os.symlink(SRC, pkg, target_is_directory=True)
sys.path.insert(0, tmp)
import bpy
mod = importlib.import_module("io_scene_x3d")
mod.register()
print("bpy", bpy.app.version_string, "build_hash", bpy.app.build_hash.decode(), "addon bl_info version", mod.bl_info["version"])

os.environ["X3D_SPLAT_IMPORT"] = "mesh"       # 5.2 has no native splat PointCloud; the add-on's mesh route
inp, out41, out40 = sys.argv[1], sys.argv[2], sys.argv[3]
bpy.ops.wm.read_factory_settings(use_empty=True)
r = bpy.ops.import_scene.x3d(filepath=inp)
print("import:", r, "objects:", [(o.name, o.type) for o in bpy.data.objects])
sc = bpy.context.scene
print("scene custom props:", list(sc.keys()))
hm = sc.get("x3d_head_meta")
print("kept head meta entries:", len(hm) if hm else 0, [m["name"] for m in hm] if hm else None)
print("export 41:", bpy.ops.export_scene.x3d(filepath=out41, x3d_version="X3D41", use_selection=False))
print("export 40:", bpy.ops.export_scene.x3d(filepath=out40, x3d_version="X3D40", use_selection=False))
