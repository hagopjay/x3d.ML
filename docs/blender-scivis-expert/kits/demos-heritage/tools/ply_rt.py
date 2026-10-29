import sys, os, tempfile, time
from pathlib import Path
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs')
import bpy
tmp=tempfile.mkdtemp(prefix='x3dio_'); (Path(tmp)/'io_scene_x3d').symlink_to(Path(S+'/x3d-blender-io/source'),target_is_directory=True); sys.path.insert(0,tmp)
import importlib; ext=importlib.import_module('io_scene_x3d'); ext.register()
from io_scene_x3d.import_x3d import _build_splat_object
from io_scene_x3d.splat_io import read_ply
bpy.ops.wm.read_factory_settings(use_empty=True)
t=time.time(); sp=read_ply(sys.argv[1],name='Synth'); print('RES read_ply',round(time.time()-t,1))
obj=_build_splat_object(bpy.context.scene.collection,'Synth',sp)
t=time.time(); r=bpy.ops.export_scene.x3d(filepath=sys.argv[2],x3d_version='X3D41',use_selection=False); print('RES export',r,round(time.time()-t,1),os.path.getsize(sys.argv[2]))
