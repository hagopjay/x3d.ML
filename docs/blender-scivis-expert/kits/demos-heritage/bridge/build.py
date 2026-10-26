"""Build the PBR still life in bpy, render with Cycles (CPU), export to X3D 4.0 with x3d-blender-io.

usage: python build.py OUTDIR [--samples N] [--view Standard] [--noshadow] [--noexport] [--norender] [--tag name]
"""
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage/pylibs")
import sys, os, math, time, json, argparse
import numpy as np
import bpy, bmesh
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--view", default="Standard")
ap.add_argument("--noshadow", action="store_true")
ap.add_argument("--noexport", action="store_true")
ap.add_argument("--norender", action="store_true")
ap.add_argument("--tag", default="cycles")
ap.add_argument("--res", type=float, default=100)
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
OUT = os.path.abspath(args.out); os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "x3d-blender-io")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def srgb2lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat(name, color, metallic=0.0, rough=0.5, tex=None, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    if tex:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(tex)
        n.image.colorspace_settings.name = "sRGB"
        nt.links.new(n.outputs["Color"], b.inputs["Base Color"])
    return m


def smooth(obj):
    for p in obj.data.polygons: p.use_smooth = True


# ---------- marble texture (procedural, numpy, deterministic) ----------
def marble_png(path, n=1024, seed=7):
    rng = np.random.default_rng(seed)
    def vnoise(res):
        g = rng.random((res + 1, res + 1))
        x = np.linspace(0, res, n, endpoint=False); i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
        a = g[i][:, i]; b = g[i][:, i + 1]; c = g[i + 1][:, i]; d = g[i + 1][:, i + 1]
        fx = f[None, :]; fy = f[:, None]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    turb = sum(vnoise(4 * 2 ** k) / 2 ** k for k in range(6))
    yy, xx = np.mgrid[0:n, 0:n] / n
    v = np.sin((xx * 3.0 + yy * 1.6) * math.pi * 2 + turb * 7.0)
    vein = np.abs(v) ** 0.22  # 0 at vein
    fine = sum(vnoise(32 * 2 ** k) / 2 ** k for k in range(3)) / 1.75
    base = np.array([0.93, 0.91, 0.87]); veinc = np.array([0.36, 0.33, 0.31]); gold = np.array([0.80, 0.66, 0.40])
    t = vein[..., None]
    col = veinc * (1 - t) + base * t
    col = col * (0.94 + 0.06 * fine[..., None])
    goldmask = np.clip(1 - np.abs(np.sin((xx * 1.1 - yy * 2.3) * math.pi * 2 + turb * 5.0)) ** 0.08 * 1.0, 0, 1)[..., None] * 0.0
    col = col * (1 - goldmask) + gold * goldmask
    img = (np.clip(col, 0, 1) * 255).astype(np.uint8)
    from PIL import Image
    Image.fromarray(img).save(path)


tex = os.path.join(OUT, "marble.png")
marble_png(tex)

# ---------- materials ----------
GOLD = mat("BrushedGold", (1.0, 0.766, 0.336), metallic=1.0, rough=0.24)
MAROON = mat("HokieMaroon", srgb2lin("#861F41"), rough=0.18)
ORANGE = mat("BurntOrangeCeramic", srgb2lin("#E5751F"), rough=0.32)
MARBLE = mat("Marble", (1, 1, 1), rough=0.22, tex=tex)
PLINTH = mat("Plinth", (0.022, 0.019, 0.017), rough=0.55)
GROUND = mat("Ground", (0.0045, 0.0034, 0.0027), rough=0.9)


def link(o, m):
    o.data.materials.clear(); o.data.materials.append(m)


# ---------- geometry ----------

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.32 - 1.5)); p = bpy.context.object; p.name = "Plinth"
p.scale = (2.7, 1.75, 3.0); bpy.ops.object.transform_apply(scale=True)
bv = p.modifiers.new("bevel", "BEVEL"); bv.width = 0.035; bv.segments = 3; bv.limit_method = "ANGLE"
link(p, PLINTH)
TOP = 0.32

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.33, segments=96, ring_count=48, location=(-0.72, 0.18, TOP + 0.33))
s = bpy.context.object; s.name = "GoldSphere"; smooth(s); link(s, GOLD)

bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.085, major_segments=96, minor_segments=40,
                                 location=(0.02, -0.48, TOP + 0.085), rotation=(0, 0, 0))
t = bpy.context.object; t.name = "MaroonTorus"; smooth(t); link(t, MAROON)

# vase: revolved profile (r, z)
prof = [(0.0, 0.0), (0.17, 0.0), (0.19, 0.02), (0.235, 0.12), (0.27, 0.26), (0.265, 0.38), (0.22, 0.50),
        (0.15, 0.60), (0.105, 0.68), (0.095, 0.76), (0.11, 0.83), (0.135, 0.865), (0.125, 0.875), (0.085, 0.84),
        (0.08, 0.76)]
me = bpy.data.meshes.new("Vase"); bm = bmesh.new()
verts = [bm.verts.new((r, 0, z)) for r, z in prof]
edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=96, use_merge=True)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(me); bm.free()
v = bpy.data.objects.new("OrangeVase", me); sc.collection.objects.link(v); v.location = (0.72, 0.30, TOP)
ss = v.modifiers.new("sub", "SUBSURF"); ss.levels = 1; ss.render_levels = 1
smooth(v); link(v, ORANGE)
# make normals consistent (outward)
bpy.context.view_layer.objects.active = v; v.select_set(True)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
v.select_set(False)

bpy.ops.mesh.primitive_cube_add(size=0.42, location=(-0.05, 0.50, TOP + 0.21), rotation=(0, 0, math.radians(28)))
c = bpy.context.object; c.name = "MarbleCube"; link(c, MARBLE)
cb = c.modifiers.new("bevel", "BEVEL"); cb.width = 0.012; cb.segments = 2

# ---------- lights: suns only (the exporter maps SUN -> DirectionalLight; strength <= 1 maps 1:1) ----------
def sun(name, energy, rot_deg, color=(1, 1, 1), angle_deg=2.0):
    bpy.ops.object.light_add(type="SUN", rotation=tuple(math.radians(a) for a in rot_deg))
    o = bpy.context.object; o.name = name; d = o.data; d.energy = energy; d.color = color
    d.angle = math.radians(angle_deg)
    if args.noshadow: d.use_shadow = False
    return o

key = sun("KeySun", 1.0, (48, 0, -38), color=(1.0, 0.93, 0.82))
fill = sun("FillSun", 0.30, (62, 0, 120), color=(0.80, 0.86, 1.0), angle_deg=8)
rim = sun("RimSun", 0.75, (68, 0, 200), color=(1.0, 0.85, 0.65), angle_deg=3)

# X3D DirectionalLight is scoped (global FALSE): it lights only its parent group's subtree, and the exporter
# wraps every light in its own Transform. Blender-side fix: chain the suns as parents so every mesh sits
# inside all three light Transforms (Rim > Fill > Key > meshes). World placement is unchanged.
def parent(child, par):
    mw = child.matrix_world.copy(); child.parent = par; child.matrix_world = mw
bpy.context.view_layer.update()
parent(fill, rim); parent(key, fill)
bpy.context.view_layer.update()
for o in (p, s, t, v, c):
    parent(o, key)
bpy.context.view_layer.update()

# ---------- world (very dark, warm) ----------
w = bpy.data.worlds.new("World"); sc.world = w
wc = (0.004, 0.0032, 0.0026)
w.color = wc  # PR #8 exporter reads the node-tree Background colour; Cycles uses it too
w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (*wc, 1)

# ---------- camera, 3/4 view; vertical sensor fit so Blender's angle == X3D fieldOfView (min dimension) ----------
cam_d = bpy.data.cameras.new("Camera"); cam_d.sensor_fit = "VERTICAL"; cam_d.lens = 62; cam_d.sensor_height = 24
cam = bpy.data.objects.new("Camera", cam_d); sc.collection.objects.link(cam)
cam.location = (3.35, -3.75, 1.85)
target = Vector((0.0, 0.0, 0.50))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

# ---------- render ----------
sc.render.resolution_x = 960; sc.render.resolution_y = 600; sc.render.resolution_percentage = int(args.res)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.render.threads_mode = "FIXED"; sc.render.threads = 4
sc.cycles.samples = args.samples; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.01
sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 8
sc.render.film_transparent = False
sc.view_settings.view_transform = args.view
sc.view_settings.look = "None"
# Cycles sun of strength S lights a white Lambertian at S/pi; a glTF-style rasteriser (X_ITE) at S.
# Exposure +log2(pi) puts both on the same photometric scale. Blender-side change only.
sc.view_settings.exposure = math.log2(math.pi)
sc.view_settings.gamma = 1.0
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
sc.render.filepath = os.path.join(OUT, args.tag + ".png")

info = {"blender": bpy.app.version_string, "view_transform": args.view, "exposure_stops": sc.view_settings.exposure,
        "samples": args.samples, "adaptive_threshold": 0.01, "denoiser": "OpenImageDenoise", "threads": 4,
        "resolution": [960, 600], "world_background_linear": wc, "shadows": not args.noshadow, "camera_fov_vertical_rad": cam_d.angle}
if not args.norender:
    t0 = time.time(); bpy.ops.render.render(write_still=True); info["render_seconds"] = round(time.time() - t0, 1)

if not args.noexport:
    sys.path.insert(0, HERE + "/pkg"); sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage/pylibs")
    pk = os.path.join(HERE, "pkg", "io_scene_x3d")
    os.makedirs(os.path.dirname(pk), exist_ok=True)
    if not os.path.exists(pk): os.symlink(os.path.join(REPO, "source"), pk)
    import importlib; mod = importlib.import_module("io_scene_x3d"); mod.register()
    xp = os.path.join(OUT, "stilllife-x3d40.x3d")
    t0 = time.time()
    r = bpy.ops.export_scene.x3d(filepath=xp, x3d_version="X3D40", use_normals=True, use_selection=False,
                                 use_mesh_modifiers=True, use_hierarchy=True, path_mode="RELATIVE",
                                 meta_title="One scene, two renderers: PBR still life",
                                 meta_description="Exported from Blender by x3d-blender-io (X3D 4.0 PhysicalMaterial path)")
    info["export_result"] = list(r); info["export_seconds"] = round(time.time() - t0, 2)
json.dump(info, open(os.path.join(OUT, (args.tag if not args.norender else "export") + ".info.json"), "w"), indent=1)
print("INFO", json.dumps(info))
