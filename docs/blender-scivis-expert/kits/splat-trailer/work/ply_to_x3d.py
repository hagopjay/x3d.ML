import os, sys, importlib, tempfile
from pathlib import Path
addon_root, ply, out, maxdeg = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3], int(sys.argv[4])
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_p2x_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
importlib.import_module("io_scene_x3d").register()
from io_scene_x3d import splat_io, import_x3d
from bpy_extras.io_utils import axis_conversion
G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()
bpy.ops.wm.read_factory_settings(use_empty=True)
s = splat_io.read_splats(ply, name="S1")
for k in [k for k in s.sh if k[0] > maxdeg]: del s.sh[k]
o = import_x3d._build_splat_object(bpy.context.scene.collection, "S1", s); o.matrix_world = G
print(bpy.ops.export_scene.x3d(filepath=out, x3d_version="X3D41", use_selection=False))
