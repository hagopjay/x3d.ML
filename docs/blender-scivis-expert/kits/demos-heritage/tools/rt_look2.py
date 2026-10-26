import sys, os, tempfile
from pathlib import Path
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs')
import bpy
tmp=tempfile.mkdtemp(prefix='x3dio_')
(Path(tmp)/'io_scene_x3d').symlink_to(Path(S+'/x3d-blender-io/source'),target_is_directory=True)
sys.path.insert(0,tmp)
import importlib
ext=importlib.import_module('io_scene_x3d'); ext.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.x3d(filepath=sys.argv[1])
for me in bpy.data.meshes:
    ca=me.color_attributes
    if len(ca): ca.active_color=ca[0]; ca.render_color_index=0
out=sys.argv[2]
bpy.ops.export_scene.x3d(filepath=out, x3d_version='X3D40', use_selection=False, use_normals=True)
