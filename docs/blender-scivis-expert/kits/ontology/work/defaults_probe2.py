import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod=importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
d=os.path.dirname(os.path.abspath(__file__))
bpy.ops.import_scene.x3d(filepath=d+'/defaults_probe2.x3d')
for o in sorted(bpy.data.objects,key=lambda o:o.location.x):
    m=o.data.materials[0] if o.data.materials else None
    bc=None
    if m and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type=='BSDF_PRINCIPLED': bc=tuple(round(v,3) for v in n.inputs['Base Color'].default_value[:3]); rough=round(n.inputs['Roughness'].default_value,3); met=round(n.inputs['Metallic'].default_value,3)
            if n.type=='EMISSION': bc=('emission',tuple(round(v,3) for v in n.inputs['Color'].default_value[:3]))
    print(int(o.location.x), 'dims', tuple(round(v,3) for v in o.dimensions), 'colour', bc)
