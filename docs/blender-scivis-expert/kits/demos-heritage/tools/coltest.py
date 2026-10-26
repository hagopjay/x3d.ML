import sys,tempfile
from pathlib import Path
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs')
import bpy
tmp=tempfile.mkdtemp(); (Path(tmp)/'io_scene_x3d').symlink_to(Path(S+'/x3d-blender-io/source'),target_is_directory=True); sys.path.insert(0,tmp)
import importlib; ext=importlib.import_module('io_scene_x3d'); ext.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.x3d(filepath=S+'/colortest/color.x3d')
for m in bpy.data.meshes:
    for a in m.color_attributes:
        print('RES',m.name,a.name,a.data_type,a.domain,[round(c,4) for c in a.data[0].color])
