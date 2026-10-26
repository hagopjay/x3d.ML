import sys, os, hashlib
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]; br, x3d = a[:2]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("bn_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib; m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register(); bpy.ops.import_scene.x3d(filepath=x3d)
for mt in bpy.data.materials:
    print("MAT", mt.name, "method", mt.surface_render_method, "blend_method?", getattr(mt, "blend_method", None))
    for l in mt.node_tree.links: print("  LINK", l.from_node.name, l.from_socket.name, "->", l.to_node.name, l.to_socket.name)
    p = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"); print("  alpha default", p.inputs["Alpha"].default_value, "emission strength", p.inputs["Emission Strength"].default_value)
    for n in mt.node_tree.nodes:
        if n.type == "TEX_IMAGE": print("  IMG", n.image.name, n.image.alpha_mode, n.image.colorspace_settings.name, n.image.channels, n.image.depth)
