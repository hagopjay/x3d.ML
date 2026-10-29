"""bpy worker: import each X3D, export X3D 4.0, reimport, record stats. Usage: worker.py <items.json> <out.jsonl> <exports_dir> [mode]
mode: rt (import+export+reimport, default) | imp (import only)"""
import sys, os, json, time, traceback, logging, io, contextlib, tempfile
ROOT='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/clone/x3d-blender-io'
items=json.load(open(sys.argv[1])); OUT=sys.argv[2]; EXP=sys.argv[3]; MODE=sys.argv[4] if len(sys.argv)>4 else 'rt'
os.makedirs(EXP,exist_ok=True)
import bpy
tmp=tempfile.mkdtemp(prefix='x3dreg_')
os.symlink(ROOT+'/source', tmp+'/io_scene_x3d')
sys.path.insert(0,tmp)
import importlib
mod=importlib.import_module('io_scene_x3d')
mod.register()

class Cap(logging.Handler):
    def __init__(s): super().__init__(); s.recs=[]
    def emit(s,r): s.recs.append((r.levelname, r.getMessage()[:200]))
cap=Cap(); logging.getLogger().addHandler(cap); logging.getLogger().setLevel(logging.WARNING)

def stats():
    from mathutils import Vector
    o={'objects':len(bpy.data.objects)}
    types={}
    nv=nf=ne=0; mn=[1e30]*3; mx=[-1e30]*3
    for ob in bpy.data.objects:
        types[ob.type]=types.get(ob.type,0)+1
        if ob.type=='MESH':
            me=ob.data; nv+=len(me.vertices); nf+=len(me.polygons); ne+=len(me.edges)
            if len(me.vertices)<=300000:
                mw=ob.matrix_world
                for v in me.vertices:
                    p=mw@v.co
                    for i in range(3):
                        mn[i]=min(mn[i],p[i]); mx[i]=max(mx[i],p[i])
    o['types']=types; o['verts']=nv; o['faces']=nf; o['edges']=ne
    o['bbox']=[mn,mx] if nv else None
    o['materials']=len(bpy.data.materials); o['images']=len(bpy.data.images)
    o['actions']=len(bpy.data.actions); o['anim_objects']=sum(1 for ob in bpy.data.objects if ob.animation_data and ob.animation_data.action); o['frame_end']=max([a.frame_range[1] for a in bpy.data.actions] or [0])
    o['shape_keys']=sum(1 for k in bpy.data.shape_keys)
    o['lights']=len(bpy.data.lights); o['cameras']=len(bpy.data.cameras); o['armatures']=len(bpy.data.armatures)
    o['pointclouds']=len(getattr(bpy.data,'pointclouds',[]))
    return o

def do_import(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cap.recs.clear()
    ret=bpy.ops.import_scene.x3d(filepath=path)
    return ret, list(cap.recs)

done=set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)['id'])
        except: pass
fo=open(OUT,'a')
for it in items:
    if it['id'] in done: continue
    row={'id':it['id'],'path':it['path'],'bytes':it.get('bytes')}
    t0=time.time()
    sout=io.StringIO()
    try:
        with contextlib.redirect_stdout(sout):
            ret,recs=do_import(it['path'])
        row['import_ret']=sorted(ret)
        row['import_s']=round(time.time()-t0,3)
        row['log_levels']={}
        for lv,m in recs: row['log_levels'][lv]=row['log_levels'].get(lv,0)+1
        row['log_first']=[m for lv,m in recs if lv in('ERROR','CRITICAL')][:3] or [m for lv,m in recs][:2]
        row['stats1']=stats()
        row['stdout_err_lines']=sum(1 for l in sout.getvalue().splitlines() if 'rror' in l or 'xception' in l)
    except Exception as e:
        row['import_exc']=f"{type(e).__name__}: {str(e)[:300]}"
        row['import_s']=round(time.time()-t0,3)
        row['tb']=traceback.format_exc()[-600:]
        fo.write(json.dumps(row)+'\n'); fo.flush(); continue
    if MODE=='rt' and row['stats1']['objects']>0:
        outp=os.path.join(EXP,it['id'][:12]+'.x3d')
        t1=time.time()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                r2=bpy.ops.export_scene.x3d(filepath=outp, x3d_version=it.get('xv','X3D40'), use_animation=True, meta_license='CC0_1.0', meta_creator='spine-roundtrip')
            row['export_ret']=sorted(r2); row['export_s']=round(time.time()-t1,3)
            row['export_bytes']=os.path.getsize(outp) if os.path.exists(outp) else None
            row['export_path']=outp
        except Exception as e:
            row['export_exc']=f"{type(e).__name__}: {str(e)[:300]}"
        if row.get('export_bytes'):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    ret2,recs2=do_import(outp)
                row['stats2']=stats(); row['reimport_ret']=sorted(ret2)
            except Exception as e:
                row['reimport_exc']=f"{type(e).__name__}: {str(e)[:300]}"
    fo.write(json.dumps(row)+'\n'); fo.flush()
