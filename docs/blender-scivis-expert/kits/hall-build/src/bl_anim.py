import sys, os, hashlib
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]; br, x3d = a[:2]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("ba_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib; m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register(); bpy.ops.import_scene.x3d(filepath=x3d)
def fc(ad):
    if not ad or not ad.action: return None
    acts = [ad.action]
    out = []
    try:
        for l in ad.action.layers:
            for s in l.strips:
                for cb in s.channelbags: out += [f.data_path for f in cb.fcurves]
    except Exception: pass
    try: out += [f.data_path for f in ad.action.fcurves]
    except Exception: pass
    return sorted(set(out))
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, "anim:", fc(o.animation_data), "| data anim:", fc(getattr(o.data, "animation_data", None)) if o.data else None)
for mt in bpy.data.materials:
    print("MAT", mt.name, "node_tree anim:", fc(mt.node_tree.animation_data) if mt.node_tree else None, "| mat anim:", fc(mt.animation_data))
