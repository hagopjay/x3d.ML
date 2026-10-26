"""Blender-side oracle probe: import X3D via x3d-blender-io (bpy 5.2.3), report objects, visibility, camera, and a Cycles CPU nonblank ratio.
usage: python -I bl_probe.py SRC_DIR OUT_JSON file.x3d ..."""
import sys, os, json, importlib.util, time
import bpy, mathutils
from bpy_extras.io_utils import axis_conversion
SRC, OUT = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg
try: spec.loader.exec_module(pkg)
except Exception as e: print("pkg init:", repr(e)[:200])
imp = importlib.import_module("x3dio.import_x3d")
res = {}
for f in sys.argv[3:]:
    name = os.path.basename(f); t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    r = {}
    try:
        imp.load(bpy.context, f, global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
    except Exception as e:
        r["import_error"] = repr(e)[:300]; res[name] = r; continue
    sc = bpy.context.scene
    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type in ("MESH", "CURVE", "FONT")]
    r["objects"] = len(objs); r["geom_objects"] = len(meshes)
    r["geom_render_visible"] = sum(1 for o in meshes if not o.hide_render and not o.hide_viewport)
    r["lights"] = [o.data.type for o in objs if o.type == "LIGHT"]
    r["cameras"] = len([o for o in objs if o.type == "CAMERA"])
    r["x3d_tags"] = sorted({k for o in objs for k in o.keys() if k.startswith("x3d")})[:8]
    # camera: use imported one or fall back
    cam = next((o for o in objs if o.type == "CAMERA"), None)
    if cam is None:
        cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam)
        cam.location = (0, -10, 3); cam.rotation_euler = (1.35, 0, 0); r["camera_fallback"] = True
    sc.camera = cam
    # emulate headlight: a sun parented to camera (X_ITE default headlight on), unless an imported light exists
    if not r["lights"]:
        sd = bpy.data.lights.new("headlight", "SUN"); sd.energy = 3.0
        so = bpy.data.objects.new("headlight", sd); sc.collection.objects.link(so); so.parent = cam
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.0, 0.0, 0.0, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    sc.world = w
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 8; sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 160, 90, 100
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    p = f"/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/dspy-redteam/work/render_{name}.png"
    sc.render.filepath = p
    try:
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(p); px = list(img.pixels); n = len(px) // 4
        nb = sum(1 for i in range(n) if max(px[4*i:4*i+3]) > 0.02)
        r["nonblank_ratio"] = round(nb / n, 4)
    except Exception as e: r["render_error"] = repr(e)[:200]
    r["secs"] = round(time.time() - t0, 1)
    res[name] = r
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
