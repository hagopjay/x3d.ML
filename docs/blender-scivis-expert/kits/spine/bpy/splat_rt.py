import sys, os, json, time, tempfile, logging, io, contextlib
ROOT='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/clone/x3d-blender-io'
sys.path.insert(0,'/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/deps')
import numpy as np, bpy
from lxml import etree
tmp=tempfile.mkdtemp(prefix='x3dreg_'); os.symlink(ROOT+'/source', tmp+'/io_scene_x3d'); sys.path.insert(0,tmp)
import importlib; mod=importlib.import_module('io_scene_x3d'); mod.register()
items=json.load(open('items_splat.json'))
P=etree.XMLParser(huge_tree=True,resolve_entities=False,no_network=True)
def arrs(path):
    r=etree.parse(path,P).getroot()
    out=[]
    for g in r.iter('GaussianSplats'):
        d={}
        for k,v in g.attrib.items():
            if k in('positions','scales','orientations','opacities') or k.startswith('sphericalHarmonics'):
                d[k]=np.array(v.split(),dtype=np.float64)
        out.append(d)
    return out
res=[]
for it in items:
    row={'id':it['id'][:8],'bytes':it['bytes']}
    a=arrs(it['path']); row['in_nodes']=len(a); row['in_splats']=[len(x.get('positions',[]))//3 for x in a]
    row['in_attrs']=sorted(set(k for x in a for k in x))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0=time.time()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bpy.ops.import_scene.x3d(filepath=it['path'])
    except Exception as e:
        row['import_exc']=str(e)[-200:]; res.append(row); continue
    row['import_s']=round(time.time()-t0,2)
    row['objs']={o.type:sum(1 for x in bpy.data.objects if x.type==o.type) for o in bpy.data.objects}
    row['mesh_verts']=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH')
    row['attrs']=sorted({a.name for o in bpy.data.objects if o.type=='MESH' for a in o.data.attributes if a.name.startswith(('splat','x3d'))})[:20]
    outp=f"splat_{it['id'][:8]}_x41.x3d"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bpy.ops.export_scene.x3d(filepath=outp,x3d_version='X3D41',meta_license='CC0_1.0',meta_creator='spine-splat-rt')
        row['export_bytes']=os.path.getsize(outp)
    except Exception as e:
        row['export_exc']=str(e)[-200:]; res.append(row); continue
    b=arrs(outp); row['out_nodes']=len(b); row['out_splats']=[len(x.get('positions',[]))//3 for x in b]
    row['out_attrs']=sorted(set(k for x in b for k in x))
    # compare node 0 arrays elementwise (concatenate all nodes)
    errs={}
    cin={k:np.concatenate([x[k] for x in a if k in x]) for k in set(k for x in a for k in x)}
    cout={k:np.concatenate([x[k] for x in b if k in x]) for k in set(k for x in b for k in x)}
    for k in sorted(cin):
        if k in cout and cin[k].shape==cout[k].shape:
            e=np.abs(cin[k]-cout[k]); errs[k]=float(e.max()) if e.size else 0.0
        else: errs[k]='missing' if k not in cout else f'shape {cin[k].shape}->{cout[k].shape}'
    row['max_abs_err']=errs
    # quaternion sign-insensitive
    if 'orientations' in cin and 'orientations' in cout and cin['orientations'].shape==cout['orientations'].shape:
        qi=cin['orientations'].reshape(-1,4); qo=cout['orientations'].reshape(-1,4)
        qi=qi/np.maximum(np.linalg.norm(qi,axis=1,keepdims=True),1e-12); qo=qo/np.maximum(np.linalg.norm(qo,axis=1,keepdims=True),1e-12)
        row['quat_abs_dot_min']=float(np.min(np.abs(np.sum(qi*qo,axis=1))))
    # reimport
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bpy.ops.import_scene.x3d(filepath=outp)
        row['reimport_mesh_verts']=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH')
    except Exception as e: row['reimport_exc']=str(e)[-200:]
    res.append(row)
print(json.dumps(res,indent=1))
json.dump(res,open('splat_rt_result.json','w'))
