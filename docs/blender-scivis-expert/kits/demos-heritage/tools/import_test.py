import sys, os, time, tempfile, gzip, shutil
from pathlib import Path
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs')
src=Path(S+'/x3d-blender-io/source')
import bpy
tmp=tempfile.mkdtemp(prefix='x3dio_')
(Path(tmp)/'io_scene_x3d').symlink_to(src,target_is_directory=True)
sys.path.insert(0,tmp)
import importlib
ext=importlib.import_module('io_scene_x3d')
ext.register()
paths=sys.argv[1:]
for p in paths:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext.register() if False else None
    f=p
    if p.endswith('.x3dz'):
        f=tmp+'/'+os.path.basename(p)[:-1]
        with gzip.open(p,'rb') as a, open(f,'wb') as b: shutil.copyfileobj(a,b)
    t=time.time()
    r=bpy.ops.import_scene.x3d(filepath=f)
    dt=time.time()-t
    objs=list(bpy.data.objects)
    info=[]
    for o in objs:
        if o.type=='MESH':
            info.append((o.name,'MESH',len(o.data.vertices),sorted(a.name for a in o.data.attributes)[:14]))
        elif o.type=='POINTCLOUD':
            info.append((o.name,'POINTCLOUD',len(o.data.points),sorted(a.name for a in o.data.attributes)[:14]))
        else:
            info.append((o.name,o.type))
    print('IMPORT',os.path.basename(p),os.path.getsize(f),'bytes',r,round(dt,1),'s',info, flush=True)
