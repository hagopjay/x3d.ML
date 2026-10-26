import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy, importlib
bpy.ops.wm.read_factory_settings(use_empty=True)
mod = importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception: pass
d=os.path.dirname(os.path.abspath(__file__))
bpy.ops.import_scene.x3d(filepath=d+'/bridge_fixture.x3d')
lint=json.load(open(d+'/lint.json'))
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
n=0
for key,items in lint.items():
    kind,name=key.split(':',1)
    if kind=='bone' and name in arm.data.bones:
        arm.data.bones[name]['x3d_lint']=' | '.join(f"{i['severity']} {i['message']}" for i in items); n+=1
txt=bpy.data.texts.new('X3D_lint_report'); txt.write(json.dumps(lint,indent=1))
bpy.context.scene['x3d_lint_summary']={'bones_flagged':n,'rules':sorted({i['rule'] for v in lint.values() for i in v})}
out=d+'/bridge_fixture_linted.blend'; bpy.ops.wm.save_as_mainfile(filepath=out)
# read back
bpy.ops.wm.open_mainfile(filepath=out)
a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
print('flagged bones in saved .blend:', {b.name:b['x3d_lint'][:70] for b in a.data.bones if 'x3d_lint' in b.keys()})
print('scene summary', bpy.context.scene['x3d_lint_summary'].to_dict(), 'text blocks', [t.name for t in bpy.data.texts])
