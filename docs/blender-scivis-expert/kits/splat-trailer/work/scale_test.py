import os, sys, json, importlib, tempfile, time, re, resource
from pathlib import Path
addon_root, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(); deg, n = int(sys.argv[3]), int(sys.argv[4]); target = sys.argv[5]
os.environ["X3D_SPLAT_IMPORT"] = target
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, rt_test_lib as L
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_sc_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
importlib.import_module("io_scene_x3d").register()
from io_scene_x3d import splat_io, import_x3d
from bpy_extras.io_utils import axis_conversion
G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()
ply = work / f"sc_sh{deg}_{n}.ply"; L.make_ply(ply, n, deg, np.random.default_rng(3))
bpy.ops.wm.read_factory_settings(use_empty=True)
t = time.time(); s = splat_io.read_splats(str(ply), name="S"); t_read = time.time() - t
t = time.time(); o = import_x3d._build_splat_object(bpy.context.scene.collection, "S", s); o.matrix_world = G; t_build = time.time() - t
del s
xo = work / f"sc_sh{deg}_{n}.x3d"
t = time.time(); bpy.ops.export_scene.x3d(filepath=str(xo), x3d_version="X3D41", use_selection=False); t_exp = time.time() - t
print(json.dumps(dict(deg=deg, n=n, target=target, read_s=round(t_read, 1), build_s=round(t_build, 1), export_s=round(t_exp, 1), x3d_mb=round(os.path.getsize(xo) / 1e6, 1), ply_mb=round(os.path.getsize(ply) / 1e6, 1), peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2))))
os.remove(xo); os.remove(ply)
