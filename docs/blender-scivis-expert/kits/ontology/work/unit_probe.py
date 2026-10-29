import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib, re
bpy.ops.wm.read_factory_settings(use_empty=True)
mod = importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001; sc.unit_settings.length_unit='MILLIMETERS'
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(10,0,0))
res = {}
for label, kw in [('default', {}), ('file_unit=MM', {'file_unit':'MM'}), ('global_scale=1000', {'file_unit':'CUSTOM','global_scale':1000.0})]:
    p = f'/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/ontology/work/unit_{abs(hash(label))%9999}.x3d'
    try:
        bpy.ops.export_scene.x3d(filepath=p, x3d_version='X3D40', **kw)
        t = open(p).read()
        m = re.search(r'<Transform DEF="OB_Cube" translation="([^"]+)"', t)
        res[label] = (m.group(1) if m else None, '<unit' in t)
    except Exception as e:
        res[label] = ('ERR ' + str(e)[:100], None)
for k,v in res.items(): print(k, v)
