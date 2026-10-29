import sys, os, hashlib, math
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]; br, x3d, out = a[:3]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("bp_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib; m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register(); bpy.ops.import_scene.x3d(filepath=x3d)
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == "LIGHT" and o.data.type == "POINT": o.data.energy = 4 * math.pi * o.data.energy / 1.75
print("LIGHTS", [(o.name, o.data.type, round(o.data.energy, 3), round(o.data.cutoff_distance, 1) if hasattr(o.data, "cutoff_distance") else None, tuple(round(v, 3) for v in o.location)) for o in bpy.data.objects if o.type == "LIGHT"])
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.ortho_scale = 2.0; cam.location = (0, -10, 0); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 200; sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"; sc.render.filepath = out; bpy.ops.render.render(write_still=True)
