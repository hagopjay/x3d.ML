import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod=importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
d=os.path.dirname(os.path.abspath(__file__))
bpy.ops.import_scene.x3d(filepath=d+'/defaults_probe.x3d')
for o in sorted(bpy.data.objects,key=lambda o:o.location.x):
    print(o.name, len(o.data.vertices), 'loc x',round(o.location.x,2), 'dims', tuple(round(v,3) for v in o.dimensions), 'scale', tuple(round(v,3) for v in o.scale))
