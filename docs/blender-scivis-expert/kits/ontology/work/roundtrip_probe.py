import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod = importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
d=os.path.dirname(os.path.abspath(__file__))
bpy.ops.import_scene.x3d(filepath=d+'/bridge_fixture.x3d')
sc=bpy.context.scene
print('objects', sorted((o.name,o.type) for o in bpy.data.objects))
print('collections', [(c.name,len(c.objects)) for c in bpy.data.collections], 'scene root objs', len(sc.collection.objects))
for o in bpy.data.objects:
    if 'x3d_metadata' in o.keys():
        md=o['x3d_metadata']; print('meta on', o.name, json.dumps(md.to_dict() if hasattr(md,'to_dict') else md)[:200])
for o in bpy.data.objects:
    if o.type=='ARMATURE': print('bones', [(b.name,(b.parent.name if b.parent else None)) for b in o.data.bones])
print('head meta', [(m['name'],m['content']) for m in sc.get('x3d_head_meta',[])])
print('custom props on armature objs', [ (o.name, list(o.keys())) for o in bpy.data.objects if o.type=='ARMATURE'])
