import sys, os, time, tempfile, re, json
from pathlib import Path
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs')
import bpy
tmp=tempfile.mkdtemp(prefix='x3dio_')
(Path(tmp)/'io_scene_x3d').symlink_to(Path(S+'/x3d-blender-io/source'),target_is_directory=True)
sys.path.insert(0,tmp)
import importlib
ext=importlib.import_module('io_scene_x3d'); ext.register()
src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir,exist_ok=True)
ver = sys.argv[3] if len(sys.argv)>3 else 'X3D40'
bpy.ops.wm.read_factory_settings(use_empty=True)
r=bpy.ops.import_scene.x3d(filepath=src); print('import',r)
for o in bpy.data.objects: 
    pass
print('objects',len(bpy.data.objects),'materials',len(bpy.data.materials),'images',len(bpy.data.images),'meshes',len(bpy.data.meshes))
out=os.path.join(outdir,'rt.x3d')
r=bpy.ops.export_scene.x3d(filepath=out, x3d_version=ver, use_selection=False)
print('export',r, os.path.getsize(out))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir,'rt.blend'))
