"""T4b: are two Cycles CPU renders of the same scene byte-identical (EXR) with all time-varying stamps off vs on? bpy 5.2.3"""
import sys, os, hashlib, json, importlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S]
import bpy, mathutils
OUT = S + "/out_t4"; sys.path.insert(0, OUT + "/pkg"); importlib.import_module("io_scene_x3d").register()
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.ops.import_scene.x3d(filepath=S + "/out_t2/B2.x3d") == {"FINISHED"}
    sc = bpy.context.scene
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.location = (6, -6, 4); cam.rotation_euler = mathutils.Euler((1.1, 0, 0.8)); sc.camera = cam
    lt = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(lt); lt.rotation_euler = (0.6, 0.2, 0.4)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 8; sc.cycles.use_denoising = False; sc.cycles.seed = 0
    sc.render.resolution_x = sc.render.resolution_y = 96
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
    return sc
def flags(sc, timevarying):
    r = sc.render
    for f in [f for f in dir(r) if f.startswith("use_stamp_")]:
        setattr(r, f, False)
    r.use_stamp_note = True; r.stamp_note_text = "x3dprov head=TEST"
    if timevarying:
        for f in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_hostname", "use_stamp_memory"): setattr(r, f, True)
res = {"bpy": bpy.app.version_string, "bpy_hash": bpy.app.build_hash.decode()}
for tv in (False, True):
    shas = []
    for k in range(2):
        sc = build(); flags(sc, tv); p = f"{OUT}/rep_{int(tv)}_{k}.exr"; sc.render.filepath = p
        bpy.ops.render.render(write_still=True); shas.append(hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
    res["timevarying_stamps_%s" % ("on" if tv else "off")] = {"file_sha256_prefix_run1_run2": shas, "byte_identical": shas[0] == shas[1]}
# pixel identity (always)
import numpy as np
px = []
for k in range(2):
    sc = build(); flags(sc, True); p = f"{OUT}/pix_{k}.exr"; sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p); a = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(a); px.append(hashlib.sha256(a.tobytes()).hexdigest()[:16]); bpy.data.images.remove(img)
res["pixel_hash_two_runs"] = px; res["pixels_identical"] = px[0] == px[1]
print(json.dumps(res, indent=1))
