"""bpy: import chart through a bridge, optionally apply two post-import parity fixes, render Cycles (Standard / Khronos PBR Neutral / AgX).
usage: -- <bridge/source> <chart.x3d> <outdir> <fixes: none|unlit|world|both> <VT[:Look]>..."""
import sys, os, json, hashlib, math
from pathlib import Path
a = sys.argv[sys.argv.index("--") + 1:]
br, x3d, outdir, fixes, vts = a[0], a[1], a[2], a[3], a[4:]
import bpy, mathutils
tmp = Path(os.environ["TMPDIR"]) / ("bf_" + hashlib.sha1(br.encode()).hexdigest()[:8]); tmp.mkdir(exist_ok=True)
if not (tmp / "io_scene_x3d").exists(): (tmp / "io_scene_x3d").symlink_to(br, target_is_directory=True)
sys.path.insert(0, str(tmp)); import importlib
m = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True); m.register()
bpy.ops.import_scene.x3d(filepath=x3d)
sc = bpy.context.scene
def eotf(c):  # sRGB number -> scene linear (piecewise), so Standard shows the number back
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
changed = 0
if fixes in ("unlit", "both"):
    for mt in bpy.data.materials:
        if not mt.use_nodes: continue
        p = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p is None: continue
        bc = p.inputs["Base Color"].default_value
        if tuple(bc[:3]) == (0.0, 0.0, 0.0) and p.inputs["Emission Strength"].default_value == 1.0:   # the importer's UnlitMaterial signature
            ec = p.inputs["Emission Color"]
            if not ec.is_linked:
                v = ec.default_value; ec.default_value = (eotf(v[0]), eotf(v[1]), eotf(v[2]), 1.0); changed += 1
print("UNLIT_FIX materials changed:", changed)
bg = sc.get("x3d_background"); print("x3d_background:", bg.to_dict() if bg else None)
if fixes in ("world", "both") and bg:
    c = list(bg["skyColor"])[:3]
    w = bpy.data.worlds.new("X3DBackground"); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); mix = nt.nodes.new("ShaderNodeMixShader"); lp = nt.nodes.new("ShaderNodeLightPath")
    dark = nt.nodes.new("ShaderNodeBackground"); dark.inputs["Color"].default_value = (0, 0, 0, 1)
    sky = nt.nodes.new("ShaderNodeBackground"); sky.inputs["Color"].default_value = (eotf(c[0]), eotf(c[1]), eotf(c[2]), 1.0)
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(dark.outputs[0], mix.inputs[1]); nt.links.new(sky.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs["Surface"])
cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.type = "ORTHO"; cam_d.ortho_scale = 14.0; cam_d.sensor_fit = "HORIZONTAL"; cam.location = (6, -10, -3.5); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.engine = "CYCLES"; cy = sc.cycles; cy.device = "CPU"; cy.samples = 16; cy.use_denoising = False; cy.use_adaptive_sampling = False
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1400, 1100, 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "16"; sc.render.image_settings.color_mode = "RGB"
os.makedirs(outdir, exist_ok=True)
for vt in vts:
    name, _, look = vt.partition(":"); sc.view_settings.view_transform = name; sc.view_settings.look = look or "None"
    sc.render.filepath = os.path.join(outdir, (name + ("_" + look if look else "")).replace(" ", "_").replace("-", "") + ".png"); bpy.ops.render.render(write_still=True); print("DONE", sc.render.filepath)
