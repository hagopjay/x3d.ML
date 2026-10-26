"""Ontology/UOM -> Blender: build an H-Anim LOA<=N armature from X3DUOM hanimJointNameValues (names, parent, loa, rest centre)."""
import sys, os, json
LOA=int(os.environ.get('LOA','1'))
D=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'hanim_uom.json')))['hanimJointNameValues']
by={r['value']:r for r in D}
keep=[r['value'] for r in D if int(r['loa'])<=LOA]
def eff_parent(n):
    p=by[n].get('parent')
    while p and int(by[p]['loa'])>LOA: p=by[p].get('parent')
    return p
missing=[n for n in keep if not by[n].get('default')]
print('LOA',LOA,'joints',len(keep),'without rest centre',missing)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod=importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
arm=bpy.context.active_object; arm.name='HAnimRig'; arm.data.name='HAnimRigData'
eb=arm.data.edit_bones
for b in list(eb): eb.remove(b)
def pos(n):
    x,y,z=[float(v) for v in by[n]['default'].split()]
    return (x,-z,y)            # X3D Y-up -> Blender Z-up (x, -z, y)
bones={}
for n in keep:
    b=eb.new(n); h=pos(n) if by[n].get('default') else (0,0,1); b.head=h; b.tail=(h[0],h[1],h[2]+0.05); bones[n]=b
for n in keep:
    p=eff_parent(n)
    if p: bones[n].parent=bones[p]
bpy.ops.object.mode_set(mode='OBJECT')
out=os.environ.get('OUT','rig.x3d')
bpy.ops.export_scene.x3d(filepath=out, x3d_version='X3D40', use_selection=False, meta_title=f'H-Anim LOA{LOA} from X3DUOM 4.1', meta_creator='bridge probe')
print('exported',out)
