import bpy, sys, os, time, json, importlib, tempfile
from pathlib import Path
ROOT=Path(sys.argv[sys.argv.index('--')+1]); X3D=sys.argv[sys.argv.index('--')+2]; OUT=Path(sys.argv[sys.argv.index('--')+3]); OUT.mkdir(exist_ok=True)
pk=OUT/'pk'; pk.mkdir(exist_ok=True)
import shutil
if not (pk/'io_scene_x3d').exists(): shutil.copytree(ROOT/'source',pk/'io_scene_x3d')
sys.path.insert(0,str(pk))
m=importlib.import_module('io_scene_x3d')
try: m.register()
except Exception as e: print("reg",e)
import addon_utils
addon_utils.enable("io_scene_gltf2",default_set=False,persistent=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
t=time.time(); r=bpy.ops.import_scene.x3d(filepath=X3D); print("import",r,round(time.time()-t,2))
nv=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'); print("verts",nv)
import numpy as np
def allpos():
    out=[]
    dg=bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type=='MESH':
            a=np.empty(len(o.data.vertices)*3,np.float32); o.data.vertices.foreach_get('co',a)
            M=np.array(o.matrix_world,np.float64); p=a.reshape(-1,3).astype(np.float64); p=p@M[:3,:3].T+M[:3,3]
            out.append(p)
    return np.concatenate(out)
P0=allpos(); print("bbox diag",np.linalg.norm(P0.max(0)-P0.min(0)))
res={}
def exp(tag,**kw):
    f=str(OUT/f"{tag}.glb"); t=time.time()
    try:
        r=bpy.ops.export_scene.gltf(filepath=f,export_format='GLB',export_apply=False,use_selection=False,export_image_format='NONE',export_normals=False,export_materials='NONE',export_cameras=False,export_lights=False,**kw)
        res[tag]=dict(bytes=os.path.getsize(f),sec=round(time.time()-t,2),result=list(r))
    except Exception as e:
        res[tag]=dict(error=f"{type(e).__name__}: {str(e)[:200]}")
    print(tag,res[tag],flush=True)
exp("raw")
exp("meshopt",export_meshopt_compression_enable=True)
exp("meshopt_filter",export_meshopt_compression_enable=True,export_meshopt_extension=True) if 'export_meshopt_extension' in [p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties] else None
exp("draco",export_draco_mesh_compression_enable=True,export_draco_position_quantization=14)
json.dump(res,open(OUT/'res.json','w'),indent=1)
# re-import each and measure position error
for tag in list(res):
    f=OUT/f"{tag}.glb"
    if not f.exists(): continue
    bpy.ops.wm.read_factory_settings(use_empty=True); addon_utils.enable("io_scene_gltf2",default_set=False,persistent=False)
    try:
        bpy.ops.import_scene.gltf(filepath=str(f)); P1=allpos()
        res[tag]['reimport_verts']=len(P1)
        res[tag]['orig_verts']=len(P0)
        if len(P1)==len(P0):
            res[tag]['max_abs_err']=float(np.abs(P1-P0).max()); res[tag]['rms_err']=float(np.sqrt(((P1-P0)**2).sum(1).mean()))
        else:
            from scipy.spatial import cKDTree
    except Exception as e: res[tag]['reimport_error']=f"{type(e).__name__}: {str(e)[:150]}"
    print(tag,res[tag],flush=True)
json.dump(res,open(OUT/'res.json','w'),indent=1)
