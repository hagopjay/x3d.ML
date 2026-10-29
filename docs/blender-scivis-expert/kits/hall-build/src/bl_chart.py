"""bpy: import chart.x3d through a bridge checkout, render with Cycles under a list of view transforms. usage: -- <bridge/source> <chart.x3d> <outdir> [VT|VT:Look ...]"""
import sys, os, json, hashlib, math
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]
br, x3d, outdir, vts = a[0], a[1], a[2], a[3:]
import bpy
tmp = Path(os.environ["TMPDIR"]) / ("bc_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib
m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register()
bpy.ops.import_scene.x3d(filepath=x3d)
sc = bpy.context.scene
lights = [(o.name, o.data.type, round(o.data.energy, 4), tuple(round(v, 3) for v in o.rotation_euler)) for o in bpy.data.objects if o.type == "LIGHT"]
print("LIGHTS", lights)
cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.type = "ORTHO"; cam_d.ortho_scale = 14.0; cam_d.sensor_fit = "HORIZONTAL"
cam.location = (6, -10, -2); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.engine = "CYCLES"; cy = sc.cycles; cy.device = "CPU"; cy.samples = 16; cy.use_denoising = False; cy.use_adaptive_sampling = False
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1400, 600, 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "16"; sc.render.image_settings.color_mode = "RGB"
os.makedirs(outdir, exist_ok=True)
print("VT_ENUM", [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items])
for vt in vts:
    name, _, look = vt.partition(":")
    sc.view_settings.view_transform = name
    try: sc.view_settings.look = look or "None"
    except Exception as e: print("LOOK_ERR", look, e)
    sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
    sc.render.filepath = os.path.join(outdir, (name + ("_" + look if look else "")).replace(" ", "_").replace("-", "") + ".png")
    bpy.ops.render.render(write_still=True)
    print("DONE", sc.render.filepath)
