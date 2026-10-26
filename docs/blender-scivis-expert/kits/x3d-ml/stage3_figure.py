"""Stage 3 (bpy 5.2.3, Cycles CPU): render a tiny still and see which render-stamp metadata Blender writes into PNG and OpenEXR files,
and whether a free-text note can carry an x3dprov head hash. Then list the text chunks / header attributes."""
import sys, os, struct, zlib, json
import bpy
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
head = sys.argv[2]            # a fake-but-real head hash, e.g. the last output_sha256 of the chain
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"; sc.cycles.samples = 4; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 64; sc.render.resolution_percentage = 100
bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
cam.location = (0, -4, 0); cam.rotation_euler = (1.5707963, 0, 0); sc.camera = cam
light = bpy.data.objects.new("L", bpy.data.lights.new("L", "SUN")); sc.collection.objects.link(light); light.rotation_euler = (0.6, 0.2, 0.3)
sc.view_settings.view_transform = "Standard"
note = "x3dprov:head=%s;chain=splats-stamped.x3d;validator=x3d_mcp@8dd0d3e;blender=%s;build=%s" % (head, bpy.app.version_string, bpy.app.build_hash.decode())
r = sc.render
for k in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_camera", "use_stamp_scene",
          "use_stamp_filename", "use_stamp_note", "use_stamp_lens", "use_stamp_memory", "use_stamp_hostname", "use_stamp_marker"):
    if hasattr(r, k): setattr(r, k, True)
r.stamp_note_text = note
r.use_stamp = False            # no burn-in; metadata only
print("note length", len(note), "stamp_note_text readback length", len(r.stamp_note_text))
print("RenderSettings stamp-ish props:", sorted(p for p in dir(r) if "stamp" in p))
for fmt, ext, depth in (("PNG", "png", "16"), ("OPEN_EXR", "exr", "32"), ("JPEG", "jpg", "8"), ("TIFF", "tif", "16")):
    r.image_settings.file_format = fmt
    try: r.image_settings.color_depth = depth
    except Exception: pass
    r.filepath = os.path.join(out, "fig." + ext)
    bpy.ops.render.render(write_still=True)
    print("wrote", r.filepath, os.path.getsize(r.filepath))
# persist: custom props and an embedded script text on the .blend
sc["x3dprov_head"] = head
t = bpy.data.texts.new("agent_script.py"); t.write("# the agent-written script, saved with the scene (KB v1 section 7)\nprint('hello')\n")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "fig.blend"))
print("saved blend")
