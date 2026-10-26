import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod = importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
d=os.path.dirname(os.path.abspath(__file__))
bpy.ops.import_scene.x3d(filepath=d+'/unit_in.x3d')
sc=bpy.context.scene
for o in bpy.data.objects:
    print('obj', o.name, o.type, tuple(round(v,4) for v in o.location), tuple(round(v,4) for v in o.dimensions))
print('unit_settings', sc.unit_settings.system, sc.unit_settings.scale_length, sc.unit_settings.length_unit)
print('props', {k:(sc[k] if k in sc.keys() else None) for k in sc.keys()})
