import os, sys, json, importlib, tempfile, time, re
from pathlib import Path
addon_root, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
cases = [tuple(int(x) for x in c.split(':')) for c in sys.argv[3:]]   # deg:N
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, rt_test_lib as L
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_big_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
mod = importlib.import_module("io_scene_x3d"); mod.register()
from io_scene_x3d import splat_io, import_x3d
from bpy_extras.io_utils import axis_conversion
G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()
res = []
for deg, n in cases:
    ply = work / f"big_sh{deg}_{n}.ply"; L.make_ply(ply, n, deg, np.random.default_rng(7))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = splat_io.read_splats(str(ply), name="S"); o = import_x3d._build_splat_object(bpy.context.scene.collection, "S", s); o.matrix_world = G
    xo = work / f"big_sh{deg}_{n}.x3d"
    t = time.time(); r = bpy.ops.export_scene.x3d(filepath=str(xo), x3d_version="X3D41", use_selection=False)
    txt = open(xo, encoding="utf-8").read()
    tags = [len(m.group(0)) for m in re.finditer(r"<GaussianSplats\b[^>]*/>", txt)]
    tf = re.search(r"<Transform\b[^>]*>", txt).group(0)
    res.append(dict(deg=deg, n=n, bytes=os.path.getsize(xo), nodes=len(tags), largest_tag=max(tags), export_s=round(time.time()-t,1), transform=tf))
print(json.dumps(res, indent=1))
