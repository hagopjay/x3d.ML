"""T4: can a Blender-rendered figure carry the x3dprov chain head, and can the chain record the figure? bpy 5.2.3 headless, Cycles CPU.
Inputs: out_t2/B2.x3d (stamped, Blender-round-tripped scene from t2). Everything in scratch."""
import sys, os, json, hashlib, importlib, re, struct, time, zlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S, S + "/fork/src"]
import bpy, mathutils
import x3dprov as P

OUT = S + "/out_t4"; os.makedirs(OUT, exist_ok=True)
pkg = os.path.join(OUT, "pkg"); os.makedirs(pkg, exist_ok=True)
if not os.path.exists(pkg + "/io_scene_x3d"): os.symlink(S + "/bio/source", pkg + "/io_scene_x3d")
sys.path.insert(0, pkg)
importlib.import_module("io_scene_x3d").register()

src = S + "/out_t2/B2.x3d"
xml = open(src, encoding="utf-8").read()
steps = P.read_steps(xml)
head_hash = hashlib.sha256(steps[-1][1].encode()).hexdigest()   # what the next step's `prev` will be
script_sha = hashlib.sha256(open(__file__, "rb").read()).hexdigest()

bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.x3d(filepath=src) == {"FINISHED"}
sc = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.location = (6, -6, 4); cam.rotation_euler = mathutils.Euler((1.1, 0, 0.8)); sc.camera = cam
lt = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(lt); lt.rotation_euler = (0.6, 0.2, 0.4)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 4; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 128; sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"

note = ("x3dprov head=%s steps=%d script=%s bpy=%s/%s engine=%s samples=%d view=%s device=CPU"
        % (head_hash, len(steps), script_sha[:16], bpy.app.version_string, bpy.app.build_hash.decode(), sc.render.engine,
           sc.cycles.samples, sc.view_settings.view_transform))
r = sc.render
r.use_stamp_note = True; r.stamp_note_text = note
for flag in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_camera", "use_stamp_lens",
             "use_stamp_scene", "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(r, flag): setattr(r, flag, True)
r.use_stamp = False   # metadata only, no burn-in

res = {"bpy": bpy.app.version_string, "bpy_hash": bpy.app.build_hash.decode(), "note_len": len(note), "stamp_flags_present": [f for f in dir(r) if f.startswith("use_stamp") or f.startswith("stamp")]}
t = time.time()
exr = OUT + "/fig.exr"; png = OUT + "/fig.png"
r.image_settings.file_format = "OPEN_EXR"; r.image_settings.color_depth = "32"; r.filepath = exr
bpy.ops.render.render(write_still=True)
res["cycles_render_s"] = round(time.time() - t, 1)
r.image_settings.file_format = "PNG"; r.image_settings.color_depth = "8"; r.filepath = png
bpy.ops.render.render(write_still=True)

# EXR: parse header attributes (name\0 type\0 int32 size value) until empty name
def exr_header(path):
    b = open(path, "rb").read(65536)
    assert b[:4] == b"v/1\x01", b[:4]
    i = 8; attrs = {}
    while b[i] != 0:
        j = b.index(b"\0", i); name = b[i:j].decode(); i = j + 1
        j = b.index(b"\0", i); typ = b[i:j].decode(); i = j + 1
        size = struct.unpack("<i", b[i:i + 4])[0]; i += 4
        val = b[i:i + size]; i += size
        attrs[name] = (typ, val[:400].decode("latin1") if typ == "string" else "<%s %d B>" % (typ, size))
    return attrs
h = exr_header(exr)
res["exr_header_string_attrs"] = {k: v[1] for k, v in h.items() if v[0] == "string"}
res["exr_has_note_with_head"] = any(head_hash in v[1] for v in h.values() if v[0] == "string")

# PNG: tEXt/iTXt/zTXt chunks
def png_text(path):
    b = open(path, "rb").read(); i = 8; out = {}
    while i < len(b):
        n, typ = struct.unpack(">I4s", b[i:i + 8]); data = b[i + 8:i + 8 + n]; i += 12 + n
        if typ == b"tEXt":
            k, v = data.split(b"\0", 1); out[k.decode()] = v.decode("latin1")
        elif typ == b"zTXt":
            k, rest = data.split(b"\0", 1); out[k.decode()] = zlib.decompress(rest[1:]).decode("latin1")
        elif typ == b"iTXt":
            k, rest = data.split(b"\0", 1); out[k.decode()] = rest[4:].split(b"\0", 2)[-1].decode("utf8", "replace") if False else rest[:60].decode("latin1")
    return out
pt = png_text(png)
res["png_text_chunks"] = {k: v[:260] for k, v in pt.items()}
res["png_has_note_with_head"] = any(head_hash in v for v in pt.values())

# chain: record the figure (render step), verify; image hash binds back to chain
fig_sha = hashlib.sha256(open(exr, "rb").read()).hexdigest()
x2 = P.add_step(xml, {"op": "render", "renderer": "blender-cycles", "agent": "blender", "agent_ref": bpy.app.version_string + " " + bpy.app.build_hash.decode(),
                      "engine": "CYCLES", "samples": 4, "device": "CPU", "view_transform": "Standard", "resolution": "128x128",
                      "script_sha256": script_sha, "output_file": "fig.exr", "output_file_sha256": fig_sha, "embedded_chain_head": head_hash})
res["chain_verify_after_render_step"] = P.verify(x2)
last = json.loads(P.read_steps(x2)[-1][1])
res["render_step_prev_equals_embedded_head"] = last["prev"] == head_hash
res["render_step_output_equals_input"] = last["input_sha256"] == last["output_sha256"]
open(OUT + "/scene_with_render_step.x3d", "w", encoding="utf-8").write(x2)
print(json.dumps(res, indent=1)); json.dump(res, open(OUT + "/t4_result.json", "w"), indent=1)
