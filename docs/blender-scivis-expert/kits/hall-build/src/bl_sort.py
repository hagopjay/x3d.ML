import sys, os, hashlib, math
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]; br, x3d, out = a[:3]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("bs_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib; m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register(); bpy.ops.import_scene.x3d(filepath=x3d)
sc = bpy.context.scene
def eotf(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
for mt in bpy.data.materials:
    p = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if mt.use_nodes else None
    if p and tuple(p.inputs["Base Color"].default_value[:3]) == (0, 0, 0): v = p.inputs["Emission Color"].default_value; p.inputs["Emission Color"].default_value = (eotf(v[0]), eotf(v[1]), eotf(v[2]), 1)
print("OBJ", [(o.name, o.type) for o in bpy.data.objects])
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.angle = 0.8; cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 600; sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"; sc.render.filepath = out; bpy.ops.render.render(write_still=True)
