"""Blender as contact oracle for the parts/contact check: AABB (step 4 method) vs exact mesh distance (mathutils BVH)."""
import sys, os, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib, mathutils
from mathutils.bvhtree import BVHTree
bpy.ops.wm.read_factory_settings(use_empty=True)
mod=importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
HERE=os.path.dirname(os.path.abspath(__file__))
def mk(kind,name,loc=(0,0,0),rot=(0,0,0),**kw):
    if kind=='sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=kw.get('r',1.0),location=loc)
    elif kind=='cube': bpy.ops.mesh.primitive_cube_add(size=kw.get('s',2.0),location=loc)
    elif kind=='rod': bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=kw.get('r',0.1),depth=kw.get('l',6.0),location=loc)
    ob=bpy.context.active_object; ob.name=name; ob.rotation_euler=rot
    bpy.context.view_layer.update()
    m=bpy.data.materials.new('M_'+name); m.diffuse_color=(0.5,0.5,0.5,1); ob.data.materials.append(m)
    return ob
def export(path):
    bpy.ops.export_scene.x3d(filepath=path,x3d_version='X3D40',use_selection=False)
def exact_distance(a,b):
    def tree(o):
        verts=[tuple(o.matrix_world@v.co) for v in o.data.vertices]
        polys=[tuple(p.vertices) for p in o.data.polygons]
        return BVHTree.FromPolygons(verts,polys,epsilon=0.0)
    ta=tree(a); tb=tree(b)
    if ta.overlap(tb): return 0.0
    d=1e9
    for src,dst,tree in ((a,b,tb),(b,a,ta)):
        for v in src.data.vertices:
            res=tree.find_nearest(src.matrix_world@v.co)
            if res[0] is not None: d=min(d,res[3])
    # also nearest from dst vertices to src surface handled by loop above
    return d
cases={}
# S1 sphere + cube resting on the pole (tangent point)
bpy.ops.wm.read_factory_settings(use_empty=True)
try: mod.register()
except Exception: pass
a=mk('sphere','Ball'); b=mk('cube','Block',loc=(0,0,2.0)); 
export(HERE+'/contact_S1.x3d'); cases['S1_tangent']=(exact_distance(a,b))
# S2 two parallel diagonal rods, 2.0 apart (centreline), AABBs overlap
bpy.ops.wm.read_factory_settings(use_empty=True)
try: mod.register()
except Exception: pass
r1=mk('rod','RodA',loc=(0,0,0),rot=(math.pi/2,0,math.pi/4)); r1.rotation_euler=(math.pi/2,0,math.pi/4)
off=2.0/math.sqrt(2)
# axis of a rod after Euler(90deg,0,45deg) is (-sin45,cos45,0)... place B perpendicular to that axis, 2.0 away
r2=mk('rod','RodB',loc=(off,off,0),rot=(math.pi/2,0,math.pi/4)); r2.rotation_euler=(math.pi/2,0,math.pi/4)
bpy.context.view_layer.update()
export(HERE+'/contact_S2.x3d'); cases['S2_parallel_rods']=(exact_distance(r1,r2))
# S3 sphere and cube corner: cube corner pointing at sphere with AABB gap 0 but exact gap > 0
bpy.ops.wm.read_factory_settings(use_empty=True)
try: mod.register()
except Exception: pass
a=mk('sphere','Ball'); c=mk('cube','Block',loc=(2.0,2.0,0.0),s=2.0)   # cube spans [1,3]^2: AABB touches sphere AABB corner at (1,1), but sphere surface at that corner is 0.414 away
export(HERE+'/contact_S3.x3d'); cases['S3_corner']=(exact_distance(a,c))
json.dump(cases,open(HERE+'/contact_exact.json','w')); print(json.dumps({k:round(v,4) for k,v in cases.items()}))
