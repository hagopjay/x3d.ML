"""Cycles stills of the hall, from the hall's own X3D through the Blender bridge (x3d-blender-io): the round trip the Library is about.

The X3D is first frozen at the film instant (src/freeze_x3d.py), then imported with the bridge, then given the light and materials the
X3D cannot carry (design/BRIEF.md sections 4 and 6, "Recipes"), and rendered:
- the real sun(s) as Sun lamps from the frozen DirectionalLights, a physical sky for the oculus and lunettes, haze in the well and the
  cube (homogeneous volume) so the light through the ports and lunettes is seen as shafts; the X_ITE stand-ins are switched off
  (PaneGlow point lights, the crypt's LensLight cones, the alpha-card beams), and the cube's three lamps reach only the cube (light linking = X3D global FALSE);
- the panes are thin-walled glass over their own emissive render atlas; stone, oak and bronze get bump and the brief's values; the pool
  is a still mirror that lets light through to its bed; the sky domes stay visible to the camera but do not light the hall.
Every render prints a RENDERSTAT line (engine, device, samples reached, time) for the log.

usage: python cycles_hall.py --bridge <x3d-blender-io/source> --x3d frozen.x3d --camera ViewMeridian --out out.png
          [--res 1440 1080] [--samples 512] [--threshold 0.01] [--time-limit 0] [--device auto|CPU|GPU]
          [--haze 0.006] [--cube-haze 0.02] [--exposure 0.0] [--pane-glow 3.0] [--sun 4.0] [--sky 0.25] [--bloom 0.15]
          [--blend scene.blend] [--no-volume]"""
import sys, os, re, math, time, json, argparse
from pathlib import Path
import xml.etree.ElementTree as ET

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
P = argparse.ArgumentParser()
P.add_argument("--bridge", required=True); P.add_argument("--x3d", required=True); P.add_argument("--camera", required=True)
P.add_argument("--out", required=True); P.add_argument("--res", type=int, nargs=2, default=[1440, 1080])
P.add_argument("--samples", type=int, default=512); P.add_argument("--threshold", type=float, default=0.01)
P.add_argument("--time-limit", type=float, default=0.0); P.add_argument("--device", default="auto")
P.add_argument("--haze", type=float, default=0.006); P.add_argument("--cube-haze", type=float, default=0.02)
P.add_argument("--sky-site", default="Blacksburg", help="whose sun drives the world sky (the hall stands in Blacksburg)")
P.add_argument("--keep-domes", action="store_true", help="keep X3D's painted sky domes (default: hidden, the physical sky shows instead)")
P.add_argument("--exposure", type=float, default=0.0); P.add_argument("--pane-glow", type=float, default=3.0)
P.add_argument("--tier4-glow", type=float, default=5.0); P.add_argument("--sun", type=float, default=4.0)
P.add_argument("--sky", type=float, default=0.25); P.add_argument("--bloom", type=float, default=0.15)
P.add_argument("--blend"); P.add_argument("--no-volume", action="store_true"); P.add_argument("--look", default="AgX - Medium High Contrast")
P.add_argument("--cube-light", type=float, default=1.0, help="v1_7: a factor on the cube's three lamps and its twilight fill; Cycles carries the light around the closed cube (bounces) where X_ITE 16.5.0 draws direct light only")
P.add_argument("--lamp-blockers", default="cube", choices=("cube", "triplet"), help="v1_7: what may shadow the cube's three lamps: the whole cube "
               "(v1_6, so a lamp reached the room only through its own port) or the trip-let and its rope alone (the X3D: only the block casts)")
P.add_argument("--lamp-direct", action="store_true", help="v1_7d (FILM v1.8): the cube's three lamps light directly only (max bounces 0), as X_ITE draws "
               "them, so the twilight, not the lamps' bounce off the lit stone, fills the letters (in v1_7c the letters read warmer than the light)")
P.add_argument("--cube-lamp-light", type=float, default=None, help="v1_7d: a factor on the three lamps alone (default: --cube-light), to re-level once they light directly only")
P.add_argument("--twilight-bounces", type=int, default=-1, help="v1_7d: max bounces of the cube's twilight lights (-1: Cycles' default). The closed cube "
               "carries the twilight round its warm stone, which turns it grey; 0 keeps it slate blue on the waiting walls, as X_ITE draws it")
P.add_argument("--lampglass-light", default="on", choices=("on", "off"), help="v1_7d: on (to v1_7c), the lamp glass (emission 8) lights the cube from frame 0, "
               "before any lamp rises, and greyed the waiting walls; off: it glows to the camera only, as an X_ITE UnlitMaterial does")
P.add_argument("--lampglass-glow", type=float, default=8.0, help="v1_7d: the lamp glass's emission strength (8 to v1_7c). Under AgX 8 reads near white "
               "(sRGB 254 248 240) where X_ITE draws the glass's own amber (213 161 103); once it lights nothing (--lampglass-light off) it can take its colour")
P.add_argument("--lampglass-tint", action="store_true", help="v1_7d: the lamp glass shows its texture times its X3D emissiveColor, as X_ITE draws it; "
               "the bridge (5da2707, import_x3d.py UnlitMaterial) links the emissiveTexture into Emission Color and so drops the colour")
P.add_argument("--shadow-fill", type=float, default=-1.0, help="v1_7d: Cycles' shadows are whole, where X_ITE lets (1 - shadowIntensity) of a lamp "
               "into its shadow (FILM: each letter at an eighth of its lamp). A shadowless twin of each lamp takes this share of it and the lamp the rest "
               "(-1: none). The X3D's 1 - shadowIntensity is 0.12, but under AgX the twilight reads brighter against the lamps than under X_ITE's tone "
               "map, so at 0.12 the letters read warmer and lighter than X_ITE's; 0.06 matches them")
P.add_argument("--poses", default="", help="Anamnesis (design/TRAILER.md v1): render every view of a poses JSON (trailer/src/poses_v1.py) "
               "in one session, each to --out/<name>.png; --camera names a viewpoint of the X3D whose imported camera calibrates the X3D-to-Blender frame")
P.add_argument("--skip-existing", action="store_true", help="with --poses: leave views whose PNG exists (a preempted job resumes)")
P.add_argument("--transparent-film", action="store_true", help="Anamnesis (TRAILER.md v1.1, the sky is not in the memory): the world reads empty "
               "to the camera (alpha 0), through glass too (transparent glass); RGBA PNG (straight alpha); bloom off, so the alpha is the film's own")
P.add_argument("--hide-outside", action="store_true", help="Anamnesis (TRAILER.md v1.1): every object of the X3D's Group World (plaza, causeway, water "
               "plain, sky domes, sun discs and glows, the dawn shell), the cube's outside walls and the clerestory panes' outer faces are hidden from "
               "camera, glossy and transmission rays; they still light, shade and scatter, so the hall's light stays as it is")
A = P.parse_args(argv)
T0 = time.time()

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- import through the bridge
# one package folder per bridge path, so --bridge is always the bridge imported (a single shared folder kept the first one it linked)
import hashlib
BRIDGE = Path(A.bridge).resolve()
tmp = Path(os.environ.get("TMPDIR", "/tmp")) / ("xbio_pkg_" + hashlib.sha1(str(BRIDGE).encode()).hexdigest()[:10]); tmp.mkdir(exist_ok=True)
pkg = tmp / "io_scene_x3d"
if not pkg.exists(): pkg.symlink_to(BRIDGE, target_is_directory=True)
try: BRIDGE_REV = __import__("subprocess").run(["git", "-C", str(BRIDGE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or "not a git checkout"
except Exception: BRIDGE_REV = "unknown"
sys.path.insert(0, str(tmp))
import importlib
bridge = importlib.import_module("io_scene_x3d")
bpy.ops.wm.read_factory_settings(use_empty=True)
bridge.register()
t_imp = time.time(); bpy.ops.import_scene.x3d(filepath=str(Path(A.x3d).resolve())); t_imp = time.time() - t_imp
sc = bpy.context.scene
OB = bpy.data.objects
X = ET.parse(A.x3d).getroot()
XDEF = {e.get("DEF"): e for e in X.iter() if e.get("DEF")}
def f3(s): return [float(v) for v in s.split()]
def x2b(v): return Vector((v[0], -v[2], v[1]))                     # X3D (x, y, z), +Y up, +Z south -> Blender (x, y, z), +Z up

# ---------------------------------------------------------------- node helpers
def tree(m):
    m.use_nodes = True; return m.node_tree
def node(nt, typ, **inputs):
    n = nt.nodes.new(typ)
    for k, v in inputs.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n
def principled(m):
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED": return n
def tex_of(m):
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image: return n
def out_of(m):
    for n in m.node_tree.nodes:
        if n.type == "OUTPUT_MATERIAL": return n
def mats_of(o): return [s.material for s in o.material_slots if s.material]
def rgba(c, a=1.0): return (c[0], c[1], c[2], a)

def add_bump(m, strength=0.2, distance=0.01):
    nt = m.node_tree; p = principled(m); t = tex_of(m)
    if not (p and t): return
    bw = node(nt, "ShaderNodeRGBToBW"); nt.links.new(t.outputs["Color"], bw.inputs[0])
    bu = node(nt, "ShaderNodeBump", Strength=strength, Distance=distance); nt.links.new(bw.outputs[0], bu.inputs["Height"])
    nt.links.new(bu.outputs["Normal"], p.inputs["Normal"])

def set_p(m, **kv):
    p = principled(m)
    if not p: return
    for k, v in kv.items():
        if k in p.inputs and not p.inputs[k].is_linked: p.inputs[k].default_value = v

def glass_pane(m, glow, gamma=1.15, coat=1.0):
    """thin-walled low-iron glass over the pane's own render (the atlas, as light); BRIEF 4 Recipes, Cycles"""
    nt = m.node_tree; p = principled(m); t = tex_of(m)
    if not (p and t): return
    for l in list(p.inputs["Emission Color"].links): nt.links.remove(l)
    g = node(nt, "ShaderNodeGamma", Gamma=gamma); nt.links.new(t.outputs["Color"], g.inputs["Color"])
    nt.links.new(g.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = glow
    p.inputs["Base Color"].default_value = (0.02, 0.022, 0.022, 1.0)
    p.inputs["Roughness"].default_value = 0.04
    p.inputs["Coat Weight"].default_value = coat; p.inputs["Coat Roughness"].default_value = 0.015; p.inputs["Coat IOR"].default_value = 1.52
    p.inputs["Specular IOR Level"].default_value = 0.5

def water(m, tint=(0.80, 0.90, 0.90)):
    """a still pool: Fresnel mirror over clear water that lets the sun reach the bed (shadow rays pass)"""
    nt = tree(m); nt.nodes.clear()
    o = node(nt, "ShaderNodeOutputMaterial"); fr = node(nt, "ShaderNodeFresnel", IOR=1.333)
    gl = node(nt, "ShaderNodeBsdfGlossy", Roughness=0.0); gl.inputs["Color"].default_value = (1, 1, 1, 1)
    tr = node(nt, "ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = rgba(tint)
    mx = node(nt, "ShaderNodeMixShader"); nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], o.inputs["Surface"])

def emission_only(m, strength, use_alpha=True):
    nt = m.node_tree; p = principled(m)
    if p: p.inputs["Emission Strength"].default_value = strength

def haze(name, density, aniso=0.55, color=(1.0, 0.98, 0.95)):
    m = bpy.data.materials.new(name); nt = tree(m); nt.nodes.clear()
    o = node(nt, "ShaderNodeOutputMaterial"); v = node(nt, "ShaderNodeVolumePrincipled", Density=density, Anisotropy=aniso)
    v.inputs["Color"].default_value = rgba(color); nt.links.new(v.outputs[0], o.inputs["Volume"])
    return m

def box(name, center, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center); o = bpy.context.active_object; o.name = name
    o.scale = size; o.data.materials.append(mat)
    for k in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow"): pass
    return o

def vis(o, camera=True, diffuse=True, glossy=True, transmission=True, scatter=True, shadow=True):
    o.visible_camera, o.visible_diffuse, o.visible_glossy = camera, diffuse, glossy
    o.visible_transmission, o.visible_volume_scatter, o.visible_shadow = transmission, scatter, shadow

notes = []
# ---------------------------------------------------------------- materials (by the hall's DEF names)
done = set()
for o in OB:
    for m in mats_of(o):
        if m.name in done or not m.use_nodes: continue
        done.add(m.name); n = m.name
        if n in ("Stone", "CubeStone", "CryptStone"):
            set_p(m, Roughness=0.86, **{"Specular IOR Level": 0.35}); add_bump(m, 0.25, 0.012)
        elif n == "Coffers": set_p(m, Roughness=0.8); add_bump(m, 0.3, 0.02)
        elif n in ("PlazaStone", "FloorStone"): set_p(m, **{"Specular IOR Level": 0.4}); add_bump(m, 0.12, 0.006)
        elif n == "Oak": set_p(m, Roughness=0.42, **{"Coat Weight": 0.25, "Coat Roughness": 0.25}); add_bump(m, 0.1, 0.004)
        elif n in ("Bronze",):            # v1_6: the X3D's own metal and roughness (FILM v1.6, bronze reads as bronze: 0.75 and 0.5); v1_5 and before 1.0 and 0.3
            fe = XDEF.get(n); met = float(fe.get("metallic", "1")) if fe is not None else 1.0; rou = float(fe.get("roughness", "0.3")) if fe is not None else 0.3
            set_p(m, Metallic=met, Roughness=max(0.3, rou), **{"Base Color": (0.55, 0.40, 0.22, 1)})
        elif n == "BronzeWall":
            fe = XDEF.get(n); met = float(fe.get("metallic", "0.85")) if fe is not None else 0.85; rou = float(fe.get("roughness", "0.42")) if fe is not None else 0.42
            set_p(m, Metallic=met, Roughness=max(0.42, rou)); add_bump(m, 0.15, 0.005)
        elif n == "SunShield":            # v1_6: the cube's sun shield, an opaque caster seen by shadow rays only (visibility below)
            nt = tree(m); nt.nodes.clear(); o_ = node(nt, "ShaderNodeOutputMaterial"); df = node(nt, "ShaderNodeBsdfDiffuse")
            df.inputs["Color"].default_value = (0, 0, 0, 1); nt.links.new(df.outputs[0], o_.inputs["Surface"])
        elif re.fullmatch(r"PaneGlass\d", n) or n == "FirstPaneGlass": glass_pane(m, A.pane_glow)
        elif re.fullmatch(r"TierIVGlass\d", n):
            fe = XDEF.get(n); daylight = f3(fe.get("emissiveColor", "1 1 1")) if fe is not None else [1, 1, 1]
            glass_pane(m, A.tier4_glow * max(daylight) , gamma=1.05)
        elif re.fullmatch(r"ClerestoryOutside\d", n): glass_pane(m, 1.2, gamma=1.0, coat=0.6)
        elif n == "VersoGlass": set_p(m, Roughness=0.05, **{"Coat Weight": 1.0, "Emission Strength": 0.6})
        elif n in ("StillWater",): water(m)
        elif n == "StillWaterPlainMaterial": set_p(m, Roughness=0.03, **{"Base Color": (0.01, 0.012, 0.014, 1), "Specular IOR Level": 0.6})
        elif n == "RailGlassMaterial": water(m, tint=(0.93, 0.97, 0.96))
        elif n == "LampGlass":
            emission_only(m, A.lampglass_glow)
            p_ = principled(m); fe = XDEF.get(n)
            fn_ = p_.inputs["Emission Color"].links[0].from_node if p_ and p_.inputs["Emission Color"].is_linked else None
            if A.lampglass_tint and fn_ is not None and fn_.label == "X3D colour":
                notes.append("lamp glass: the bridge already multiplies its texture by emissiveColor (x3d-blender-io PR #19, 342c8c5 on); no tint added")
            elif A.lampglass_tint and p_ and fe is not None and p_.inputs["Emission Color"].is_linked:
                ec_ = f3(fe.get("emissiveColor", "1 1 1")); nt_ = m.node_tree
                vm_ = node(nt_, "ShaderNodeVectorMath", operation="MULTIPLY"); vm_.inputs[1].default_value = ec_
                nt_.links.new(p_.inputs["Emission Color"].links[0].from_socket, vm_.inputs[0]); nt_.links.new(vm_.outputs["Vector"], p_.inputs["Emission Color"])
                notes.append(f"lamp glass: its texture x emissiveColor {ec_}, strength {A.lampglass_glow}")
        elif n == "LensGlow": emission_only(m, 4.0)
        elif n.startswith("Rite") and n != "RiteEdge": emission_only(m, A.pane_glow)
        elif n == "SunDiscGilt": set_p(m, Metallic=1.0, Roughness=0.18, **{"Base Color": (0.88, 0.70, 0.30, 1)})
        elif n in ("SkyBlacksburg", "SkyDoha"): emission_only(m, 1.0)
for o in OB:
    n = o.name
    if n.endswith("Sky") or n.endswith("Glow") and n.startswith("Sun"): vis(o, camera=True, diffuse=False, glossy=True, transmission=True, scatter=False, shadow=False)
    if n in ("DohaSky", "BlacksburgSky") and not A.keep_domes: o.hide_render = True; notes.append(f"{n} hidden (physical sky)")
    if n in ("DawnBeamCard", "BeamBlacksburgCard", "BeamDohaCard") and not A.no_volume: o.hide_render = True; notes.append(f"{n} hidden (real shafts)")
    if n.startswith("SunPatch") and not A.no_volume: o.hide_render = True; notes.append(f"{n} hidden (the real sun lands through the ports)")   # v1_5 stand-ins
    if n.startswith("LunettePatch"): o.hide_render = True; notes.append(f"{n} hidden (the real suns light the glass through the lunettes)")   # v1_6 stand-ins
    if any(s_.material is not None and s_.material.name.startswith("SunBlacksburgDawn") for s_ in getattr(o, "material_slots", [])):
        o.hide_render = True; notes.append(f"{n} hidden (v1_8's dawn belongs to X_ITE's painted sky; the bridge drops its texture alpha)")
    if n == "CubeSunShield": vis(o, camera=False, diffuse=False, glossy=False, transmission=False, scatter=False, shadow=True); notes.append("CubeSunShield casts the suns' shadow only")
    if n == "StillWaterPlain": vis(o, shadow=False)
if A.hide_outside:
    outside = {"World", "CubeWallsOutside"} | {f"Face{k}ClerestoryOutside" for k in range(8)}
    if XDEF.get("World") is not None: outside |= {e.get("DEF") for e in XDEF["World"].iter() if e.get("DEF")}
    hid_ = []
    for o in OB:
        if o.type in ("LIGHT", "CAMERA") or re.sub(r"\.\d{3}$", "", o.name) not in outside: continue
        o.visible_camera, o.visible_glossy, o.visible_transmission = False, False, False; hid_.append(o.name)
    notes.append(f"outside hidden from camera, glossy and transmission rays (still lighting and shading): {sorted(hid_)}")

# ---------------------------------------------------------------- fonts (the inscriptions are cut in the hall's own faces)
FONTS = Path(A.x3d).resolve().parent / "fonts"
def font(f):
    p = FONTS / f
    return bpy.data.fonts.load(str(p), check_existing=True) if p.exists() else None
for o in OB:
    if o.type != "FONT": continue
    body = o.data.body
    f = font("CormorantSC-Medium.ttf") if body.isupper() or body.startswith("<X3D") else font("JetBrainsMono[wght].ttf")
    if f: o.data.font = f
    else: notes.append(f"font missing for {o.name}")

# ---------------------------------------------------------------- light
for o in OB:
    if o.type == "LIGHT" and o.name.startswith(("PaneGlow", "LensLight")): o.hide_render = True    # X_ITE stand-ins; the glass and the lenses emit for real
if A.lampglass_light == "off":
    lg_ = [o for o in OB if o.type == "MESH" and re.sub(r"\.\d{3}$", "", o.name) == "LampOpenings"]
    for o in lg_: vis(o, camera=True, diffuse=False, glossy=False, transmission=False, scatter=False, shadow=False)
    notes.append(f"lamp glass glows to the camera only: {[o.name for o in lg_]}")
suns = {}
for city in ("Blacksburg", "Doha"):
    o = OB.get(f"Sun{city}"); e = XDEF.get(f"Sun{city}")
    if not (o and e is not None): continue
    d = x2b(f3(e.get("direction"))).normalized(); inten = float(e.get("intensity", "1")); col = f3(e.get("color", "1 1 1"))
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    o.data.energy = A.sun * inten / 2.4; o.data.color = col; o.data.angle = math.radians(0.53)
    el = math.degrees(math.asin(max(-1.0, min(1.0, -d.z)))); az = (math.degrees(math.atan2(-d.x, -d.y)) + 360) % 360
    suns[city] = {"elev_deg": round(el, 2), "az_deg_from_north": round(az, 2), "strength": round(o.data.energy, 3), "color": [round(c, 3) for c in col]}
    if el < -0.5: o.hide_render = True
CUBE = ["Triplet", "TripletFrame", "CubeWalls", "CubeFloor", "LampOpenings", "Descent", "DescentRail", "Inscriptions", "Inscriptions.001"]
# v1_7b (--cube-inside): the X3D's CubeInside group is the room the cube's lights reach (global FALSE lights its whole group), so the
# receivers are exactly the shapes in it, each named by the bridge after its own DEF or its nearest DEF'd ancestor: the walls' outside
# faces (CubeWallsOutside), the lamp openings and the outer inscription stay out, the inner inscription (InscriptionsInside) comes in
if XDEF.get("CubeInside") is not None:
    inside = {e.get("DEF") for e in XDEF["CubeInside"].iter() if e.get("DEF")}
    CUBE = sorted(o.name for o in OB if o.type not in ("LIGHT", "CAMERA", "EMPTY") and re.sub(r"\.\d{3}$", "", o.name) in inside)
    notes.append(f"cube receivers follow the X3D's CubeInside group: {CUBE}")
cube_coll = bpy.data.collections.new("CubeReceivers")
for n in CUBE:
    if OB.get(n): cube_coll.objects.link(OB[n])
def kin(o): return [c for c_ in o.children for c in [c_] + kin(c_)]
# v1_7 (design's review of v1_6): the X3D says that in the Cube group only the block casts (the walls and the shield have castShadow
# FALSE), so each lamp's blockers are the trip-let and its rope alone: with the cube's walls among them (v1_6) a lamp reached the room
# only through its own port, and the X and the 3 never showed
tri_blk = bpy.data.collections.new("TripletBlockers")
for o in ([OB["Triplet"]] if OB.get("Triplet") else []) + ([c for c in kin(OB["TripletFrame"]) if c.type == "MESH"] if OB.get("TripletFrame") else []):
    if o.name not in tri_blk.objects: tri_blk.objects.link(o)
LAMP_K = A.cube_light if A.cube_lamp_light is None else A.cube_lamp_light
for n in ("LampSkylight", "LampSouthPort", "LampWestPort"):
    if OB.get(n):
        OB[n].light_linking.receiver_collection = cube_coll; OB[n].data.angle = math.radians(2.0); OB[n].data.energy *= LAMP_K
        if A.lamp_blockers == "triplet": OB[n].light_linking.blocker_collection = tri_blk
        elif OB.get("CubeSunShield"): OB[n].light_linking.blocker_collection = cube_coll     # v1_6: the lamps' shadows come from the cube alone, never the shield
        if A.lamp_direct: OB[n].data.cycles.max_bounces = 0
        if A.shadow_fill > 0:
            # v1_7d: X_ITE lets (1 - shadowIntensity) of a lamp into its shadow; Cycles' shadow is whole, so a share goes to a shadowless twin
            si_ = float(XDEF[n].get("shadowIntensity", "1")) if XDEF.get(n) is not None else 1.0
            tw_ = OB[n].copy(); tw_.data = OB[n].data.copy(); tw_.name = f"{n}ShadowFill"
            for c_ in OB[n].users_collection: c_.objects.link(tw_)
            tw_.data.energy = OB[n].data.energy * A.shadow_fill; OB[n].data.energy *= 1.0 - A.shadow_fill
            if hasattr(tw_.data, "use_shadow"): tw_.data.use_shadow = False
            else: tw_.data.cycles.cast_shadow = False
            tw_.light_linking.receiver_collection = cube_coll; tw_.light_linking.blocker_collection = None
            notes.append(f"{n}: {A.shadow_fill} of it in a shadowless twin ({round(tw_.data.energy, 3)}), the lamp {round(OB[n].data.energy, 3)} (X3D shadowIntensity {si_})")
if A.lamp_blockers == "triplet": notes.append(f"lamp blockers: {sorted(o.name for o in tri_blk.objects)}")
if A.lamp_direct: notes.append("cube lamps light directly only (max bounces 0)")
if A.cube_lamp_light is not None: notes.append(f"cube lamps x {A.cube_lamp_light}, twilight x {A.cube_light}")
elif A.cube_light != 1.0: notes.append(f"cube lamps and twilight x {A.cube_light}")
# v1_7 (FILM v1.7): the twilight of the cube's skylight, a cool light that casts no shadow, reaching only the cube (X3D global FALSE)
for o in OB:
    if o.type == "LIGHT" and o.name.startswith("CubeTwilight"):
        o.light_linking.receiver_collection = cube_coll; o.data.angle = math.radians(10.0); o.data.energy *= A.cube_light
        if hasattr(o.data, "use_shadow"): o.data.use_shadow = False
        else: o.data.cycles.cast_shadow = False
        if A.twilight_bounces >= 0: o.data.cycles.max_bounces = A.twilight_bounces
        notes.append(f"{o.name}: shadowless, cube only, strength {round(o.data.energy, 3)}" + (f", max bounces {A.twilight_bounces}" if A.twilight_bounces >= 0 else ""))
# the world: a physical sky with the higher sun, seen through the oculus and lunettes
w = bpy.data.worlds.new("Sky"); sc.world = w; nt = tree(w); nt.nodes.clear()
wo = node(nt, "ShaderNodeOutputWorld"); bg = node(nt, "ShaderNodeBackground", Strength=A.sky); sky = node(nt, "ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING"
hi = (A.sky_site, suns[A.sky_site]) if A.sky_site in suns else (max(suns.items(), key=lambda kv: kv[1]["elev_deg"]) if suns else None)
if hi:
    notes.append(f"world sky: {hi[0]}'s sun at {hi[1]['elev_deg']} deg")
    sky.sun_elevation = math.radians(max(hi[1]["elev_deg"], -6.0)); sky.sun_rotation = math.radians((90.0 - hi[1]["az_deg_from_north"]) % 360)
    sky.sun_disc = True; sky.altitude = 600.0
nt.links.new(sky.outputs[0], bg.inputs["Color"]); nt.links.new(bg.outputs[0], wo.inputs["Surface"])
# haze: the well (inside the stacks, up to the oculus ring) and the cube
if not A.no_volume:
    box("HazeWell", (0, 0, 21.0), (27.6, 27.6, 41.6), haze("HazeWell", A.haze))
    c = OB.get("CubeWalls")
    if c:
        bb = [c.matrix_world @ Vector(v) for v in c.bound_box]; lo = Vector([min(p[i] for p in bb) for i in range(3)]); hi_ = Vector([max(p[i] for p in bb) for i in range(3)])
        box("HazeCube", (lo + hi_) / 2, (hi_ - lo) * 0.97, haze("HazeCube", A.cube_haze))
    for n in ("HazeWell", "HazeCube"):
        if OB.get(n): vis(OB[n], camera=True, diffuse=False, glossy=False, transmission=True, scatter=True, shadow=False)

# ---------------------------------------------------------------- camera (X3D fieldOfView is the smaller of the two angles)
cam = OB.get(A.camera)
if cam is None or cam.type != "CAMERA": sys.exit(f"no camera {A.camera}; cameras: {[o.name for o in OB if o.type == 'CAMERA']}")
sc.camera = cam
ve = XDEF.get(A.camera); fov = float(ve.get("fieldOfView", "0.785398")) if ve is not None else 0.785398
W, H = A.res; cam.data.sensor_fit = "VERTICAL" if W >= H else "HORIZONTAL"
if W >= H: cam.data.angle_y = fov
else: cam.data.angle_x = fov
cam.data.clip_start = 0.05; cam.data.clip_end = 5000.0

# ---------------------------------------------------------------- render settings
sc.render.engine = "CYCLES"; cy = sc.cycles
dev = "CPU"
if A.device in ("auto", "GPU"):
    cp = bpy.context.preferences.addons["cycles"].preferences
    for k in ("OPTIX", "CUDA"):
        try:
            cp.compute_device_type = k; cp.refresh_devices()
            gpus = [d for d in cp.devices if d.type == k]
            if gpus:
                for d in cp.devices: d.use = d.type == k
                dev = k; break
        except Exception as ex: notes.append(f"{k}: {ex}")
cy.device = "GPU" if dev != "CPU" else "CPU"
cy.samples = A.samples; cy.use_adaptive_sampling = True; cy.adaptive_threshold = A.threshold; cy.adaptive_min_samples = 32
cy.time_limit = A.time_limit; cy.use_denoising = True; cy.denoiser = "OPENIMAGEDENOISE"
cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"; cy.denoising_prefilter = "ACCURATE"
try: cy.denoising_use_gpu = dev != "CPU"
except Exception: pass
cy.use_light_tree = True
for k, v in dict(max_bounces=12, diffuse_bounces=3, glossy_bounces=4, transmission_bounces=8, volume_bounces=0, transparent_max_bounces=24).items(): setattr(cy, k, v)
cy.caustics_reflective = False; cy.caustics_refractive = False; cy.blur_glossy = 0.5
cy.sample_clamp_direct = 0.0; cy.sample_clamp_indirect = 8.0
cy.volume_step_rate = 1.0
sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.color_depth = "8"
if A.transparent_film:
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = "RGBA"
    try: cy.film_transparent_glass = True; cy.film_transparent_roughness = 0.1
    except Exception as ex: notes.append(f"transparent glass: {ex}")
    if A.bloom > 0: notes.append(f"bloom {A.bloom} off for the transparent film"); A.bloom = 0.0
    notes.append("transparent film: the world reads alpha 0, through glass too; RGBA PNG")
sc.view_settings.view_transform = "AgX"
try: sc.view_settings.look = A.look
except Exception as ex: notes.append(f"look: {ex}")
sc.view_settings.exposure = A.exposure
if A.bloom > 0:
    ct = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    ct.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ct.nodes.new("CompositorNodeRLayers"); gl = ct.nodes.new("CompositorNodeGlare")
    for k, v in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", 1.0), ("Smoothness", 0.4), ("Strength", A.bloom), ("Size", 0.6), ("Saturation", 1.0)):
        try: gl.inputs[k].default_value = v
        except Exception as ex: notes.append(f"glare {k}: {ex}")
    ct.links.new(rl.outputs["Image"], gl.inputs["Image"]); go = ct.nodes.new("NodeGroupOutput"); ct.links.new(gl.outputs["Image"], go.inputs[0])
    sc.compositing_node_group = ct; sc.render.use_compositing = True
sc.render.compositor_device = "CPU"                                  # the GPU compositor wants an EGL context; headless machines have none
try: sc.render.compositor_precision = "FULL"
except Exception: pass
stat = {}
def on_stats(scene, *a):
    if a and isinstance(a[0], str) and "Sample" in a[0]: stat["last"] = a[0][-120:]
bpy.app.handlers.render_stats.append(lambda *a: stat.__setitem__("last", str(a[-1])[-160:]) if a else None)
if A.blend: bpy.ops.wm.save_as_mainfile(filepath=str(Path(A.blend).resolve()))
if A.poses:
    # every view through the same calibrated frame: C maps the X3D world to Blender's, read off the imported camera of --camera
    import mathutils
    def x3d_matrix(pos, ori):
        M = mathutils.Matrix.Rotation(ori[3], 4, mathutils.Vector(ori[:3]).normalized()) if abs(ori[3]) > 1e-12 else mathutils.Matrix.Identity(4)
        M.translation = mathutils.Vector(pos); return M
    ref = x3d_matrix([float(x) for x in (ve.get("position") or "0 0 10").split()], [float(x) for x in (ve.get("orientation") or "0 0 1 0").split()])
    C = cam.matrix_world @ ref.inverted()
    PJ = json.load(open(A.poses)); os.makedirs(A.out, exist_ok=True); sc.render.use_persistent_data = True; done = []
    for v in PJ["views"]:
        png = os.path.join(A.out, v["name"] + ".png")
        if A.skip_existing and os.path.exists(png): continue
        cam.matrix_world = C @ x3d_matrix(v["position"], v["orientation"])
        if W >= H: cam.data.angle_y = v["fieldOfView"]
        else: cam.data.angle_x = v["fieldOfView"]
        sc.render.filepath = str(Path(png).resolve())
        t_r = time.time(); bpy.ops.render.render(write_still=True); t_r = time.time() - t_r
        done.append({"name": v["name"], "render_s": round(t_r, 1)})
        print("POSESTAT " + json.dumps({"name": v["name"], "n": len(done), "render_s": round(t_r, 1), "reached": stat.get("last")}), flush=True)
    info = {"poses": os.path.basename(A.poses), "views": len(done), "calibrated_on": A.camera, "C": [list(r) for r in C], "res": [W, H], "engine": "Cycles",
            "blender": bpy.app.version_string, "device": dev, "samples_max": A.samples, "threshold": A.threshold, "import_s": round(t_imp, 1),
            "total_s": round(time.time() - T0, 1), "suns": suns, "haze": None if A.no_volume else [A.haze, A.cube_haze], "exposure": A.exposure,
            "look": A.look, "notes": notes, "x3d": os.path.basename(A.x3d), "bridge": BRIDGE_REV, "renders": done}
    print("RENDERSTAT " + json.dumps({k: info[k] for k in info if k not in ("renders", "C")}))
    json.dump(info, open(os.path.join(A.out, "cycles_poses.json"), "w"), indent=1)
    sys.exit(0)
sc.render.filepath = str(Path(A.out).resolve())
t_r = time.time(); bpy.ops.render.render(write_still=True); t_r = time.time() - t_r
info = {"camera": A.camera, "fov_rad": fov, "res": [W, H], "engine": "Cycles", "blender": bpy.app.version_string, "device": dev,
        "samples_max": A.samples, "threshold": A.threshold, "reached": stat.get("last"), "import_s": round(t_imp, 1), "render_s": round(t_r, 1),
        "total_s": round(time.time() - T0, 1), "suns": suns, "haze": None if A.no_volume else [A.haze, A.cube_haze], "exposure": A.exposure,
        "look": A.look, "pane_glow": A.pane_glow, "tier4_glow": A.tier4_glow, "sun": A.sun, "sky": A.sky, "bloom": A.bloom, "notes": notes,
        "objects": len(OB), "x3d": os.path.basename(A.x3d), "bridge": BRIDGE_REV, "out": A.out}
print("RENDERSTAT " + json.dumps(info))
json.dump(info, open(os.path.splitext(A.out)[0] + ".json", "w"), indent=1)
