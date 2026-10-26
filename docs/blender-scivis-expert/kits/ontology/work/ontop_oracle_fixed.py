"""Second instrument for step 4: import each gpt-4o 'sphere with a cube on top' scene into Blender 5.2.3 and measure exact contact."""
import sys, os, json, math, re, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg_fixed'))
import bpy, importlib
from mathutils.bvhtree import BVHTree
HERE=os.path.dirname(os.path.abspath(__file__))
mod=importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
res=json.load(open('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/steps-2-to-4/step4-parts-contact/parts-results.json'))
rows={(r['strategy'],r['conv']):r for r in res if r['model']=='gpt-4o' and r['prompt']==2}
def tree(o):
    verts=[tuple(o.matrix_world@v.co) for v in o.data.vertices]; polys=[tuple(p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(verts,polys,epsilon=0.0), verts
def zrange(verts): zs=[v[2] for v in verts]; return min(zs),max(zs)
out=[]
for f in sorted(glob.glob(HERE+'/step3/x3d_final/gpt-4o__*__p2_c*.x3d')):
    m=re.search(r'gpt-4o__(\w+)__p2_c(\d+)\.x3d',f); strat,conv=m.group(1),int(m.group(2))
    r=rows.get((strat,conv))
    if r is None or not r['xsd_valid']: continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try: mod.register()
    except Exception: pass
    txt=open(f,encoding='utf-8').read(); txt=re.sub(r'<!DOCTYPE[^>]*>\s*','',txt)
    tmp=HERE+'/_ontop_tmp.x3d'; open(tmp,'w',encoding='utf-8').write(txt)
    try: bpy.ops.import_scene.x3d(filepath=tmp)
    except Exception as e:
        out.append(dict(f=os.path.basename(f),err=str(e)[:80])); continue
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)>0]
    cubes=[o for o in meshes if len(o.data.vertices)==8 and len(o.data.polygons)==6]
    sph=[o for o in meshes if len(o.data.vertices)>8]
    if len(cubes)!=1 or len(sph)!=1:
        out.append(dict(f=os.path.basename(f),err=f'cubes={len(cubes)} spheres={len(sph)}')); continue
    c,s=cubes[0],sph[0]
    tc,vc=tree(c); ts,vs=tree(s)
    ov=bool(tc.overlap(ts))
    d=0.0 if ov else min(min((ts.find_nearest(v)[3] for v in vc)), min((tc.find_nearest(v)[3] for v in vs)))
    cz0,cz1=zrange(vc); sz0,sz1=zrange(vs)
    size=lambda v: max(max(p[i] for p in v)-min(p[i] for p in v) for i in range(3))
    tol=0.05*min(size(vc),size(vs))+1e-3
    sunk=sz1-cz0       # >0: cube bottom below sphere top
    cls='sunk' if (ov and sunk>tol) else ('rest' if (d<=tol and abs(sunk)<=tol) or (ov and abs(sunk)<=tol) else ('gap' if d>tol else 'rest'))
    # cube must be above sphere centre
    above = (cz0+cz1)/2 > (sz0+sz1)/2
    out.append(dict(f=os.path.basename(f),strat=strat,conv=conv,exact_class=cls,dist=round(d,4),sunk=round(sunk,4),above=above,
                    aabb_strict=bool(r['relations_ok']),aabb_loose=bool(r['relations_ok_loose']),aabb_verdict=r['verdict']=='pass'))
json.dump(out,open(HERE+'/ontop_oracle_fixed.json','w'),indent=0)
ok=[o for o in out if 'exact_class' in o]
print('scenes measured',len(ok),'errors',len(out)-len(ok))
import collections
print('exact classes',collections.Counter(o['exact_class'] for o in ok))
print('confusion (AABB strict pass? x exact class)',collections.Counter((o['aabb_strict'],o['exact_class']) for o in ok))
agree=sum(1 for o in ok if o['aabb_strict']==(o['exact_class']=='rest' and o['above']))
print('agreement strict-vs-exact(rest & above):',agree,'/',len(ok))
print([o for o in out if 'err' in o][:5])
