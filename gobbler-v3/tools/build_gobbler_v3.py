#!/usr/bin/env python3
"""Build the PolyXandria gobbler (v3): the bird whose network is the knowledge graph. Standard X3D 4.0, no Script.

v3 keeps v2's head, shaders, dissolve and eye byte for byte (the generator below is v2's, patched) and changes four things:
  * the network the bird trails into is now the PolyXandria knowledge graph (graph.json, built by kg/): one star per entity,
    one ribbon per typed relation, colour by class, brightness by grade and provenance, one wheel (a ring with a faint disc)
    per flywheel loop, with light pulses that circle each wheel;
  * four coloured point lights move on sinusoidal paths (PositionInterpolators, one TimeSensor each); their positions are
    routed into the facet, ribbon and star shaders as fields light0..light3, so they wash colour across the head and the graph;
  * viewpoints are rebuilt for scale (Wide is v2's, unchanged; Colossus, Eye, Flywheel, Behind and Crown are new), sized in
    metres so the head stands about 7.5 m tall in a headset (X_ITE WebXR);
  * only the standard build is written (no X_ITE-only nodes), so the file passes the XSD and the fork validator as is.

v2 docstring follows (still true of the head, the dissolve and the shaders):

Build the PolyXandria gobbler (v2): two live X3D scenes from one generator, plus a receipt for each.

    python3 tools/build_gobbler.py               # write both builds (and the extras layer), validate them, write both receipts
    python3 tools/build_gobbler.py --out DIR     # write the .x3d files (and receipts) into DIR instead
    python3 tools/build_gobbler.py --no-validate # skip the fork validator (no receipts)
    python3 tools/build_gobbler.py --preview     # also write a 2D projection PNG to the scratch folder
    python3 tools/build_gobbler.py --check-shells  # after writing (with --out, the files in DIR), render the extras
                                                 # build across a sway cycle with the enamel layer on and off, and
                                                 # fail if the layer turns any pixel white (node, Playwright, PIL)

The bird is a low-poly relief. A 2D profile (head, hooked beak, snood, wattle, neck) is sampled into
points, Delaunay-triangulated and inflated into depth, then written as X3D. The geometry is the v1 bird,
byte for byte the same points (fixed seeds), so the Gobbler viewpoint stays in register with the poster.

v2 moves the look and the motion onto the GPU, in standard X3D 4.0:
  * Five GLSL programs (X3D Shaders component, ComposedShader + ShaderPart) draw everything
    (a sixth, 'Hide', only stops the fallback lattice from drawing when the shaders work):
    FacetShader  - gold that reads as metal: flat per-facet normals, a procedural studio reflection,
                   Fresnel and highlights that keep each facet's hue (saturation never below SATMIN),
                   a maroon-to-ember rim, an ember rim on the snood and wattle, per-facet glints, an
                   energy scan, and the click's burn. The burn is per facet: a broad noise front, nape
                   first, reaches each facet as one value (keyed on the facet, not the pixel), so facets
                   char, ignite and burn away one by one with straight edges. A burning facet shrinks to
                   its centre (barycentrics from a three-point TextureCoordinate), with a white-hot rim
                   1.5 px wide at the cut and a ramp from white-hot at the cut through ember to deep red,
                   flickering.
    LineShader   - every edge as a screen-space ribbon with a soft glow; network edges carry light pulses.
                   Head edges burn on the facets' fire: they glow ember as the front passes, then go out
                   one by one, so mid-dissolve the head is a constellation of its points.
                   Ribbon corners are pure indices: coordIndex (this end), texCoordIndex into a
                   TextureCoordinate3D copy of the points (the other end), normalIndex into a 16-entry
                   Normal table that encodes the corner (side, fixed ends).
    PointShader  - sparks, network stars, dust and motes as soft point sprites with depth of field.
    EyeShader    - the eye: iris, pupil, catchlights and rings, drawn on one disc; a single four-point
                   star while the head is apart.
    SkyShader    - a dithered, banding-free sky dome behind the bird.
  * The dissolve: one Phase value (ScalarInterpolator) is routed into the shaders. Each vertex works out
    its own flight path from its rest position (an integer hash, so every shape that holds the same point
    agrees). No CoordinateInterpolator, no per-spark interpolators.
  * Embers: a ParticleSystem with a VolumeEmitter shaped like the head streams sparks into the network
    while the facets burn (createParticles is switched by a BooleanSequencer on Phase; the system itself is
    enabled only while the Dissolve clock runs, so a still bird draws no frames).
  * X3D's own fallback rule keeps the v1 look if the GPU path fails: every ComposedShader shares its
    Appearance with a Material, and a hidden IndexedLineSet ('Hide' shader) draws the lattice only then.

The X_ITE extras build (gobbler-xite.x3d) is the same scene plus X_ITE-only nodes: a BlendMode on every
LineShader and PointShader layer (screen blending: light adds up but rolls off below white instead of
clipping), a DepthMode (no depth writes, so glow layers never cut each other), additive BlendMode on the
embers, a clear-coated cornea over the eye (PhysicalMaterial with the Clearcoat and Specular extensions), and
an enamel layer it Inlines once the head first stands whole (gobbler-xite-shells.x3d, X3D 4.1): thin-film
enamel (Iridescence and Clearcoat extensions) on some of the gold facets (the file's comments give the
count) and velvet (Sheen) on the snood and wattle, lit only by a 16 px studio cube map (EnvironmentLight,
scoped to the layer; the host file's three lights are scoped to the head and network, so they do not reach it:
their sharp highlights on the clearcoat clipped facets to white in round 3) and screen-blended on top. Enamel
goes only on facets that face the camera through the whole sway, and --check-shells renders a sway cycle to
prove the layer turns no pixel white. The layer loads late on purpose: X_ITE fetches its BRDF lookup tables for EnvironmentLight and
Sheen while the scene loads, which cost about a second of load time when the layer was in this file. It
hides while the head burns (Phase 0.1 to 0.95). The facets' gold uses the standard build's tone constants
(the extras build is never dimmer); its glow shaders are tuned for the blending through standard fields and
constants: bloom 1 (wider halos, smaller motes; 0 in the standard build) and softer halos.
It declares <component name='X_ITE' level='1'/> and says so in its head meta. Its receipt records the fork
validator's real verdict for both files and lists every X_ITE-only node type.
(Round 0 also had 85 instanced gems at the network stars; they read as beige flakes at 1x and were removed.)

All motion is declarative: TimeSensors, interpolators, ROUTEs and shader fields, no Script. Receipts are
computed from the written files and from the fork validator's real output. Python 3 standard library only.
"""
import datetime, json, math, os, random, re, struct, subprocess, sys
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TEASER = os.path.dirname(HERE)
OUT_DIR = os.path.join(TEASER, 'site', 'exhibits', 'gobbler')
SCRATCH = os.environ.get('GOBBLER_SCRATCH', '/tmp/claude-0/-home-claude/dae07dfe-133a-572d-8ebf-054b136e7172/scratchpad')
VENV_PY = sys.executable
VALIDATE = os.path.join(HERE, 'validate.py')
# The fork validator that judges both builds: hagopjay/x3d_mcp at commit 7624969, which accepts ROUTEs into a
# shader's declared <field>s (the branch head before it, 8c0a457, flags every such ROUTE as route-invalid-to-field).
# PR 1 merged 7624969 into integration/validator-fixes on 2026-10-11 16:28Z (merge commit c9c9788), so the receipts
# name the branch.
VALIDATOR_BRANCH = 'main'
VALIDATOR_COMMIT = '2b696f5'
COMMIT_ON_BRANCH = True
VALIDATOR_NAME = 'x3d_mcp fork, ' + VALIDATOR_BRANCH if COMMIT_ON_BRANCH else 'x3d_mcp fork'
VALIDATOR_COMMIT_NOTE = None if COMMIT_ON_BRANCH else 'not yet merged into ' + VALIDATOR_BRANCH
# One line the page can show as is (receipt validator.label).
VALIDATOR_LABEL = VALIDATOR_NAME + ', commit ' + VALIDATOR_COMMIT + ('' if COMMIT_ON_BRANCH else ', ' + VALIDATOR_COMMIT_NOTE)

RNG = random.Random(1872)   # fixed seeds everywhere: the bird is reproducible, byte for byte

# ----------------------------------------------------------------------------------------------
# 1. The profile, drawn in design pixels (the raster original's 1536 x 1024 space, facing left)
# ----------------------------------------------------------------------------------------------
RIDGE = [(226, 532), (212, 508), (205, 478), (206, 448), (214, 418), (228, 390), (247, 363), (270, 338), (294, 316), (314, 300)]
CROWN = [(326, 276), (344, 248), (370, 220), (404, 196), (444, 176), (490, 162), (540, 155), (590, 156), (636, 167), (674, 188), (702, 218), (718, 256), (724, 300)]
NAPE = [(727, 350), (731, 400), (738, 450), (751, 500), (771, 550), (799, 600), (833, 646), (870, 690), (905, 736), (934, 786), (956, 840)]
NECK_BASE = [(940, 890), (890, 926), (820, 944), (744, 940), (672, 918), (610, 884)]
THROAT = [(566, 846), (530, 800), (502, 748), (484, 694), (472, 640), (464, 588), (458, 540), (452, 500)]
JAW = [(434, 466), (404, 460), (372, 460), (342, 464), (316, 472)]
UNDERBEAK = [(298, 480), (278, 492), (258, 506), (240, 520)]


def _bumpy(path, amp, first, last):
    """Push every other point of path[first:last] outward (to the left of travel on screen)."""
    out = list(path)
    for i in range(first, last):
        if i % 2 == 1:
            a, b = path[i - 1], path[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
            out[i] = (path[i][0] + dy / L * amp, path[i][1] - dx / L * amp)
    return out


THROAT = _bumpy(THROAT, 9, 1, len(THROAT) - 1)            # caruncles along the front of the neck
SILHOUETTE = RIDGE + CROWN + NAPE + NECK_BASE + THROAT + JAW + UNDERBEAK

BEAK_BASE = [(314, 300), (324, 330), (340, 358), (364, 380), (396, 394), (430, 400), (456, 402)]
GAPE = [(456, 402), (424, 406), (390, 414), (356, 426), (326, 440), (300, 458)]
BEAK = RIDGE + BEAK_BASE + GAPE[1:] + UNDERBEAK          # upper beak region (crease-bounded)
MANDIBLE = GAPE + JAW[::-1][1:]                            # the thin lower jaw strip
EYE = (452, 292)

# Snood: from the forehead, over the top of the beak, hanging across it and past its tip.
SNOOD_SPINE = [(324, 284), (318, 306), (309, 332), (299, 360), (291, 390), (286, 420), (284, 450), (286, 480), (291, 510), (298, 538), (306, 564), (314, 586)]
SNOOD_WIDTH = [9, 11, 13, 15, 16, 17, 18, 19, 21, 25, 30, 34]
# Wattle: the dewlap under the throat, long and narrowing, lobed along its free edge.
WATTLE = [(418, 468), (446, 474), (470, 488), (482, 520), (488, 560), (488, 600), (484, 640), (476, 684), (464, 724), (448, 760), (430, 790), (412, 806), (398, 796), (390, 764), (388, 728), (390, 690), (394, 650), (398, 610), (402, 570), (406, 530), (410, 500)]
# Bare red skin (caruncles) down the throat and the front of the neck.
SKIN = [(436, 336), (500, 320), (570, 332), (630, 390), (652, 470), (680, 560), (730, 650), (790, 740), (830, 840), (760, 900), (660, 880), (580, 820), (520, 740), (484, 650), (466, 560), (446, 486), (424, 424), (424, 372)]

PX_ORIGIN = (480, 420)


def U(p):
    """Design pixels -> scene units: 1 unit = 100 px, y up."""
    return ((p[0] - PX_ORIGIN[0]) / 100.0, (PX_ORIGIN[1] - p[1]) / 100.0)


# ----------------------------------------------------------------------------------------------
# 2. Geometry kit: point in polygon, distances, resampling, Poisson darts, Delaunay
# ----------------------------------------------------------------------------------------------
def inside(pt, poly):
    x, y = pt; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(p, poly, closed=True):
    n = len(poly); m = n if closed else n - 1
    return min(seg_dist(p, poly[i], poly[(i + 1) % n]) for i in range(m))


def resample(path, spacing_fn, closed=False):
    pts = list(path) + ([path[0]] if closed else [])
    out = [pts[0]]; carry = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = math.dist(a, b); t = 0.0
        if L == 0:
            continue
        while True:
            need = spacing_fn(out[-1]) - carry
            if t * L + need > L:
                carry += L - t * L; break
            t += need / L; carry = 0.0
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    if closed:
        if len(out) > 1 and math.dist(out[-1], out[0]) < 0.5 * spacing_fn(out[0]):
            out.pop()
    elif math.dist(out[-1], pts[-1]) > 0.4 * spacing_fn(pts[-1]):
        out.append(pts[-1])
    else:
        out[-1] = pts[-1]
    return out


def subdivide(poly, h):
    """Keep every corner of a closed polygon and split long edges into near-equal steps."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        k = max(1, int(round(math.dist(a, b) / h)))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    return out


def poisson_fill(poly, spacing_fn, fixed, tries=7000, margin=0.6, rng=RNG):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pts = list(fixed); new = []
    for _ in range(tries):
        c = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if not inside(c, poly):
            continue
        h = spacing_fn(c)
        if poly_dist(c, poly) < margin * h:
            continue
        if any((c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2 < (0.85 * h) ** 2 for q in pts):
            continue
        pts.append(c); new.append(c)
    return new


def delaunay(points):
    """Bowyer-Watson; triangles come back counter-clockwise in y-up space."""
    pts = list(points)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    R = 20 * max(max(xs) - min(xs), max(ys) - min(ys)); n = len(pts)
    pts += [(cx - R, cy - R), (cx + R, cy - R), (cx, cy + R)]
    tris = [(n, n + 1, n + 2)]

    def circ(t):
        (ax, ay), (bx, by), (qx, qy) = pts[t[0]], pts[t[1]], pts[t[2]]
        d = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
        if abs(d) < 1e-12:
            return (0, 0, float('inf'))
        a2, b2, q2 = ax * ax + ay * ay, bx * bx + by * by, qx * qx + qy * qy
        ux = (a2 * (by - qy) + b2 * (qy - ay) + q2 * (ay - by)) / d
        uy = (a2 * (qx - bx) + b2 * (ax - qx) + q2 * (bx - ax)) / d
        return (ux, uy, (ax - ux) ** 2 + (ay - uy) ** 2)
    cache = {tris[0]: circ(tris[0])}
    for i in range(n):
        px, py = pts[i]
        bad = [t for t in tris if (px - cache[t][0]) ** 2 + (py - cache[t][1]) ** 2 < cache[t][2]]
        count = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = tuple(sorted(e)); count[k] = count.get(k, 0) + 1
        bset = set(bad); tris = [t for t in tris if t not in bset]
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                if count[tuple(sorted(e))] == 1:
                    nt = (e[0], e[1], i); tris.append(nt); cache[nt] = circ(nt)
    out = []
    for t in tris:
        if max(t) >= n:
            continue
        (ax, ay), (bx, by), (qx, qy) = pts[t[0]], pts[t[1]], pts[t[2]]
        if (bx - ax) * (qy - ay) - (by - ay) * (qx - ax) < 0:
            t = (t[0], t[2], t[1])
        out.append(t)
    return out


def triangulate_region(poly, xy):
    """Delaunay of xy, keeping triangles that lie inside poly."""
    keep = []
    for t in delaunay(xy):
        a, b, c = (xy[i] for i in t)
        cen = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3)
        mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2),
                ((c[0] + a[0]) / 2, (c[1] + a[1]) / 2)]
        if inside(cen, poly) and all(inside(m, poly) or poly_dist(m, poly) < 1.5 for m in mids):
            keep.append(t)
    return keep


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def mix(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


# ----------------------------------------------------------------------------------------------
# 3. Head, beak, snood and wattle: points with depth
# ----------------------------------------------------------------------------------------------
def spacing_head(p):
    x, y = p
    base = 20 + 0.085 * max(0.0, x - 300) + 0.06 * max(0.0, y - 420)
    d_eye = math.hypot(x - EYE[0], y - EYE[1])
    if d_eye < 110:
        base = min(base, 16 + 0.09 * d_eye)
    if x < 340:
        base = min(base, 18)
    return base


def thickness(p):
    """Half-thickness of the head in units: slim at the beak tip, full at the skull and neck."""
    return lerp(0.2, 1.0, smooth((p[0] - 250) / 240.0))


def height(p, sign=1.0):
    d = poly_dist(p, SILHOUETTE) if inside(p, SILHOUETTE) else 0.0
    t = min(1.0, d / 105.0)
    return sign * thickness(p) * math.sqrt(1 - (1 - t) ** 2)


class Mesh:
    """Every head vertex lives in one list; that list becomes the shared Coordinate node."""
    def __init__(self):
        self.pts = []

    def add(self, px, z, part, glow=True):
        x, y = U(px)
        self.pts.append({'px': px, 'xyz': [x, y, z], 'part': part, 'glow': glow})
        return len(self.pts) - 1


def tube_polygon(spine, widths, lump=0.0, seed=3):
    """Outline of a fleshy tube along a spine, with optional lumps (caruncle bumps)."""
    rng = random.Random(seed); left = []; right = []
    for i, p in enumerate(spine):
        a = spine[max(0, i - 1)]; b = spine[min(len(spine) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        wl = widths[i] / 2 * (1 + lump * rng.uniform(-1, 1)); wr = widths[i] / 2 * (1 + lump * rng.uniform(-1, 1))
        left.append((p[0] + nx * wl, p[1] + ny * wl)); right.append((p[0] - nx * wr, p[1] - ny * wr))
    end = spine[-1]; d = (spine[-1][0] - spine[-2][0], spine[-1][1] - spine[-2][1]); L = math.hypot(*d)
    tip = (end[0] + d[0] / L * widths[-1] * 0.55, end[1] + d[1] / L * widths[-1] * 0.55)
    return left + [tip] + right[::-1]


def lobed(poly, first, last, amp=7):
    """Insert outward lobes between consecutive outline points first..last (clockwise on screen)."""
    out = []; n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        out.append(a)
        if first <= i <= last:
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
            out.append((mx + dy / L * amp, my - dx / L * amp))
    return out


def build_head(mesh):
    faces = {'beak': [], 'mandible': [], 'head': [], 'back': [], 'snood': [], 'wattle': []}
    outline = resample(SILHOUETTE, spacing_head, closed=True)
    crumble = random.Random(31)
    def frayed(p):             # 0 on the head, rising toward the neck base, where it frays into network
        return max(0.0, min(1.0, (p[1] - 700) / 240.0 + (p[0] - 760) / 500.0))
    outline = [(p[0] + crumble.gauss(0, 16 * frayed(p)), p[1] + crumble.gauss(0, 16 * frayed(p))) for p in outline]
    front_px = list(outline)
    crease_lines = []
    for path, k in ((BEAK_BASE, 0.85), (GAPE, 0.8)):
        line = []
        for p in resample(path, lambda q: k * spacing_head(q)):
            if poly_dist(p, SILHOUETTE) > 7 and all(math.dist(p, q) > 8 for q in front_px):
                front_px.append(p); line.append(len(front_px) - 1)
            else:
                line.append(min(range(len(front_px)), key=lambda i: math.dist(front_px[i], p)))
        crease_lines.append(line)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.25
        front_px.append((EYE[0] + 48 * math.cos(a), EYE[1] + 43 * math.sin(a)))
    front_px += poisson_fill(SILHOUETTE, lambda q: 30 if inside(q, BEAK) else spacing_head(q), front_px)
    n_outline = len(outline)
    ids = [mesh.add(p, 0.0 if i < n_outline else height(p), 'front') for i, p in enumerate(front_px)]
    for t in triangulate_region(SILHOUETTE, front_px):
        a, b, c = (front_px[i] for i in t)
        cen = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3)
        part = 'beak' if inside(cen, BEAK) else 'mandible' if inside(cen, MANDIBLE) else 'head'
        if crumble.random() < 0.75 * frayed(cen):
            continue                                   # facets fall away where the neck frays
        faces[part].append(tuple(ids[i] for i in t))
    # Back shell: its own coarser sampling, the same outline, mirrored depth. No glow nodes.
    back_px = list(outline)
    back_px += poisson_fill(SILHOUETTE, lambda p: 1.6 * spacing_head(p), back_px, tries=4000, rng=random.Random(9))
    bids = [ids[i] if i < n_outline else mesh.add(p, 0.8 * height(p, -1.0), 'back', glow=False)
            for i, p in enumerate(back_px)]
    for t in triangulate_region(SILHOUETTE, back_px):
        cen = tuple(sum(back_px[i][k] for i in t) / 3 for k in range(2))
        if crumble.random() < 0.9 * frayed(cen):
            continue
        faces['back'].append(tuple(bids[i] for i in (t[0], t[2], t[1])))
    # Snood: a single sheet over the near side of the beak, hanging past its tip.
    sn = tube_polygon(SNOOD_SPINE, SNOOD_WIDTH, lump=0.16, seed=4)
    sn_out = subdivide(sn, 20)
    sn_px = sn_out + poisson_fill(sn, lambda p: 21, sn_out, tries=3000, margin=0.45)
    sids = []
    for k, p in enumerate(sn_px):
        s = min(1.0, poly_dist(p, sn) / 12.0) if inside(p, sn) else 0.0
        over = max(height(p), 0.0) if inside(p, SILHOUETTE) else 0.0
        z = max(over + 0.12, 0.3) + 0.12 * math.sqrt(s)
        sids.append(mesh.add(p, z, 'snood', glow=(k < len(sn_out) and k % 2 == 0)))
    for t in triangulate_region(sn, sn_px):
        faces['snood'].append(tuple(sids[i] for i in t))
    # Wattle: a lobed flap hanging under the throat, in front of the midline.
    wp = lobed(WATTLE, 3, 19, amp=10)
    w_out = subdivide(wp, 24)
    w_px = w_out + poisson_fill(wp, lambda p: 28, w_out, tries=3000, margin=0.45)
    wids = []
    for k, p in enumerate(w_px):
        s = min(1.0, poly_dist(p, wp) / 30.0) if inside(p, wp) else 0.0
        over = max(height(p), 0.0) if inside(p, SILHOUETTE) else 0.0
        z = max(over + 0.1, 0.1 + 0.06 * max(0.0, (p[1] - 460) / 270.0)) + 0.18 * math.sqrt(s)
        wids.append(mesh.add(p, z, 'wattle', glow=(k < len(w_out) and k % 2 == 0)))
    for t in triangulate_region(wp, w_px):
        faces['wattle'].append(tuple(wids[i] for i in t))
    def keep(px):              # no contour where the neck dissolves into the network
        return px[0] < 600 or px[1] < 230    # front and crown only: the back of the head stays open mesh
    contours = []
    run = []
    order = list(range(n_outline)) + [0]
    for i in order:
        if keep(front_px[i]):
            run.append(ids[i])
        else:
            if len(run) > 1:
                contours.append((run, 'gold'))
            run = []
    if len(run) > 1:
        contours.append((run, 'gold'))
    for line in crease_lines:
        contours.append(([ids[i] for i in line], 'gold'))
    contours.append((sids[:len(sn_out)] + [sids[0]], 'red'))
    contours.append((wids[:len(w_out)] + [wids[0]], 'red'))
    return faces, ids[:n_outline], contours


# ----------------------------------------------------------------------------------------------
# 4. The network that trails right and down
# ----------------------------------------------------------------------------------------------
GRAPH_PATH = os.environ.get('GOBBLER_GRAPH', os.path.join(os.path.dirname(HERE), 'graph.json'))
KG = None


def load_graph():
    global KG
    if KG is None:
        KG = json.load(open(GRAPH_PATH, encoding='utf-8'))
    return KG


def node_rgb(nd):
    """Star colour: the class's hue, dimmed and greyed by provenance and grade (a model's recall or a simulation is fainter)."""
    c = CLASS_COLOUR.get(nd['cls'], (0.98, 0.8, 0.45))
    k = {'data': 1.0, 'doc': 0.96, 'model_recall': 0.78, 'simulated': 0.62}.get(nd.get('prov'), 0.9) * {'Confirmed': 1.0, 'Likely': 0.92, 'Suspected': 0.8}.get(nd.get('grade'), 0.9)
    grey = sum(c) / 3
    sat = 1.0 if nd.get('prov') in ('data', 'doc') else 0.8
    return tuple(max(0.0, min(1.0, (grey + (x - grey) * sat) * k)) for x in c)


def build_network(mesh, outline_ids):
    """The graph in place of v2's random network. Nodes keep the graph's own 3D layout (kg/layout.py); the head joins it through
    bridge ribbons from its right-hand outline points to the nodes nearest the neck (the tether)."""
    G = load_graph()
    rng = random.Random(42)
    nodes = []
    for i, nd in enumerate(G['nodes']):
        sz = 1.5 + 1.8 * nd['w'] ** 0.6 + (0.3 if nd.get('loops') else 0.0)
        if nd.get('tier') == 2: sz = 1.05 + 1.0 * nd['w'] ** 0.6      # the star tier of a deep build: smaller, dimmer stars
        nodes.append({'px': (480 + nd['xyz'][0] * 100, 420 - nd['xyz'][1] * 100), 'xyz': list(nd['xyz']), 'size': sz, 'sz': sz, 'group': 0,
                      'cls': nd['cls'], 'rgb': node_rgb(nd), 'label': nd['label'], 'w': nd['w'], 'loops': nd.get('loops', [])})
    na = len(nodes)
    anchors = [i for i in outline_ids if mesh.pts[i]['px'][0] > 600 and mesh.pts[i]['px'][1] < 840]
    anchors = sorted(anchors, key=lambda i: mesh.pts[i]['px'][1])
    step_ = max(1, len(anchors) // 14)
    anchors = anchors[::step_][:14]
    # bridge each chosen head point to the heaviest node near the neck that is not yet tethered
    neck = (4.1, -3.7, 0.0)
    cand = sorted(range(na), key=lambda i: (math.dist(nodes[i]['xyz'][:2], neck[:2]) - 2.2 * nodes[i]['w']))[:60]
    tethered, edges = set(), []
    for j, a in enumerate(anchors):
        ax_, ay_ = U(mesh.pts[a]['px'])
        best = min((c for c in cand if c not in tethered), key=lambda c: math.dist(nodes[c]['xyz'][:2], (ax_, ay_)))
        tethered.add(best); edges.append((best, na + j))
    keep = set()
    for e in G['edges']:
        if e['loop'] >= 0:
            continue
        a, b = e['s'], e['t']
        if a != b and math.dist(nodes[a]['xyz'], nodes[b]['xyz']) <= (6.0 if e.get('faint') else 3.8):
            keep.add((min(a, b), max(a, b)))
    net_edges = sorted(keep) + edges
    dust = []
    for _ in range(5000):
        c = (rng.gauss(760, 70), rng.gauss(330, 150))
        if inside(c, SILHOUETTE) or poly_dist(c, SILHOUETTE) < 14 or len(dust) >= 46:
            continue
        if any(math.dist(c, q) < 22 for q in dust):
            continue
        dust.append(c)
    dust = [{'xyz': list(U(c)) + [rng.gauss(0, 0.5)], 'size': rng.uniform(0.35, 0.6), 'group': rng.randrange(4)} for c in dust]
    return nodes, anchors, net_edges, [], na, dust




# ----------------------------------------------------------------------------------------------
# 5. Motion on the GPU: the dissolve, written once in GLSL (and once in Python for the eye's path)
# ----------------------------------------------------------------------------------------------
DISSOLVE_FROM = (0.45, -0.75)     # head centre, units
DISSOLVE_TO = (2.5, -0.9)         # centre of the star cloud the head bursts into, over the network
EYE_KEYS = [0, 0.1, 0.16, 0.22, 0.28, 0.34, 0.4, 0.46, 0.52, 0.6, 0.66, 0.72, 0.78, 0.84, 0.9, 0.96, 1]
M32 = 0xFFFFFFFF


def pcg3(x, y, z):
    """pcg3d (Jarzynski and Olano), uint32 arithmetic: the same integer hash as the GLSL."""
    x = (x * 1664525 + 1013904223) & M32; y = (y * 1664525 + 1013904223) & M32; z = (z * 1664525 + 1013904223) & M32
    x = (x + y * z) & M32; y = (y + z * x) & M32; z = (z + x * y) & M32
    x ^= x >> 16; y ^= y >> 16; z ^= z >> 16
    x = (x + y * z) & M32; y = (y + z * x) & M32; z = (z + x * y) & M32
    return x, y, z


def rnd3(p, o=(0, 0, 0)):
    q = [int(math.floor(p[k] * 100.0 + 0.5)) + o[k] + 4096 for k in range(3)]
    return [v / 4294967296.0 for v in pcg3(*q)]


def f32(v):
    return struct.unpack('f', struct.pack('f', v))[0]


def scatter_py(p, ph, xmin, xmax):
    """Python twin of the GLSL scatter() (without the time-based breathing): position at Phase ph."""
    r = rnd3(p); g = [(v - 0.5) * 3.4 for v in rnd3(p, (37, 71, 13))]
    x, y, z = p
    u = max(0.0, min(1.0, (x - xmin) / (xmax - xmin)))
    jit = (r[0] - 0.5) * 0.04
    l0 = 0.14 + 0.16 * (1 - u) + jit; l1 = l0 + 0.2
    b0 = 0.6 + 0.12 * u + jit; b1 = min(0.95, b0 + 0.2)
    if ph <= l0 or ph >= b1:
        return list(p)
    if ph < l1:
        e = smooth((ph - l0) / (l1 - l0)); hold = 0.0
    elif ph <= b0:
        e = 1.0; hold = (ph - l1) / max(1e-4, b0 - l1)
    else:
        e = 1 - smooth((ph - b0) / (b1 - b0)); hold = 1.0
    s = math.sin(math.pi * e) if e < 1 else 0.0
    c, sn = math.cos(-0.2443), math.sin(-0.2443)
    dx, dy = (x - DISSOLVE_FROM[0]) * 1.6, (y - DISSOLVE_FROM[1]) * 1.5
    tgt = [DISSOLVE_TO[0] + dx * c - dy * sn + g[0] * 0.36, DISSOLVE_TO[1] + dx * sn + dy * c + g[1] * 0.36, 1.2 * z + g[2] * 0.9]
    curl = [0.0, 0.6 * math.sin(2.1 * x + 0.5), 0.6 * math.cos(1.7 * y)]
    drift = [0.3 + 0.1 * math.sin(3 * y), 0.12 * math.sin(2 * x), 0.15 * math.cos(2 * y)]
    return [p[k] + (tgt[k] - p[k]) * e + curl[k] * s + drift[k] * hold * e for k in range(3)]


GLSL_HASH = """uvec3 pcg3(uvec3 v) {
  v = v * 1664525u + 1013904223u;
  v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
  v ^= v >> 16u;
  v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
  return v;
}
vec3 rnd3i(ivec3 q) { return vec3(pcg3(uvec3(q + 4096))) * (1.0 / 4294967296.0); }
ivec3 qpos(vec3 p) { return ivec3(floor(p * 100.0 + 0.5)); }
"""

# scatter(p): where a head vertex is at the current phase (xyz) and how far it has flown (w, 0..1).
# The nape leaves first and the beak comes home first; a curl and a drift keep neighbours together.
GLSL_SCATTER = """vec4 scatter(vec3 p) {
  ivec3 q = qpos(p);
  vec3 r = rnd3i(q);
  vec3 g = (rnd3i(q + ivec3(37, 71, 13)) - 0.5) * 3.4;
  float u = clamp((p.x - XMIN) / (XMAX - XMIN), 0.0, 1.0);
  float jit = (r.x - 0.5) * 0.04;
  float l0 = 0.14 + 0.16 * (1.0 - u) + jit, l1 = l0 + 0.2;
  float b0 = 0.6 + 0.12 * u + jit, b1 = min(0.95, b0 + 0.2);
  if (phase <= l0 || phase >= b1) return vec4(p, 0.0);
  float e, hold;
  if (phase < l1) { e = smoothstep(l0, l1, phase); hold = 0.0; }
  else if (phase <= b0) { e = 1.0; hold = (phase - l1) / max(1e-4, b0 - l1); }
  else { e = 1.0 - smoothstep(b0, b1, phase); hold = 1.0; }
  float s = e < 1.0 ? sin(3.14159265 * e) : 0.0;
  const float c = 0.97030, sn = -0.24188;
  vec2 d = vec2((p.x - 0.45) * 1.6, (p.y + 0.75) * 1.5);
  vec3 tgt = vec3(2.5 + d.x * c - d.y * sn + g.x * 0.36, -0.9 + d.x * sn + d.y * c + g.y * 0.36, 1.2 * p.z + g.z * 0.9);
  vec3 curl = vec3(0.0, 0.6 * sin(2.1 * p.x + 0.5), 0.6 * cos(1.7 * p.y));
  vec3 drift = vec3(0.3 + 0.1 * sin(3.0 * p.y), 0.12 * sin(2.0 * p.x), 0.15 * cos(2.0 * p.y));
  vec3 live = 0.07 * e * vec3(sin(time * 0.9 + r.y * 6.283), cos(time * 0.7 + r.z * 6.283), sin(time * 0.5 + r.x * 6.283));
  return vec4(p + (tgt - p) * e + curl * s + drift * hold * e + live, e);
}
"""

GLSL_VNOISE = """float h1(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(h1(i), h1(i + vec3(1, 0, 0)), f.x), mix(h1(i + vec3(0, 1, 0)), h1(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(h1(i + vec3(0, 0, 1)), h1(i + vec3(1, 0, 1)), f.x), mix(h1(i + vec3(0, 1, 1)), h1(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
"""

GLSL_LIGHTS = """uniform vec3 light0;
uniform vec3 light1;
uniform vec3 light2;
uniform vec3 light3;
"""
# poolAt: the colour the four lights leave on a point, a soft pool round each light (object space)
GLSL_POOL = """vec3 poolAt(vec3 p) {
  vec3 d0 = p - light0, d1 = p - light1, d2 = p - light2, d3 = p - light3;
  return (LC0 * exp(-dot(d0, d0) * POOLK) + LC1 * exp(-dot(d1, d1) * POOLK) + LC2 * exp(-dot(d2, d2) * POOLK) + LC3 * exp(-dot(d3, d3) * POOLK)) * POOLG;
}
"""

GLSL_HEAD = """#version 300 es
precision highp float;
precision highp int;
"""

# Shader fields (uniforms) each program declares; the ROUTEs feed them.
FACET_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform float phase;
uniform float time;
""" + GLSL_LIGHTS + """in vec4 x3d_Vertex;
in vec4 x3d_Color;
in vec4 x3d_TexCoord0;
out vec3 vView;
out vec3 vObj;
flat out vec3 vL0;
flat out vec3 vL1;
flat out vec3 vL2;
flat out vec3 vL3;
flat out vec3 vFacet;
out vec4 vColor;
out vec3 vBary;
""" + GLSL_HASH + GLSL_SCATTER + """void main() {
  vec4 s = scatter(x3d_Vertex.xyz);
  vec4 mv = x3d_ModelViewMatrix * vec4(s.xyz, 1.0);
  vView = mv.xyz;
  vL0 = (x3d_ModelViewMatrix * vec4(light0, 1.0)).xyz;
  vL1 = (x3d_ModelViewMatrix * vec4(light1, 1.0)).xyz;
  vL2 = (x3d_ModelViewMatrix * vec4(light2, 1.0)).xyz;
  vL3 = (x3d_ModelViewMatrix * vec4(light3, 1.0)).xyz;
  vObj = x3d_Vertex.xyz;
  vFacet = x3d_Vertex.xyz;                                      // flat: one corner's rest position for the whole facet
  vColor = x3d_Color;
  vBary = vec3(1.0 - x3d_TexCoord0.x - x3d_TexCoord0.y, x3d_TexCoord0.xy);   // corners (0 0) (1 0) (0 1): barycentrics
  gl_Position = x3d_ProjectionMatrix * mv;
}
"""

# The burn front, shared by FacetShader (per pixel) and LineShader (per edge, so the lattice burns on the same fire).
# burnD is how far the fire has gone (0 to 1); burnEdge(p) > 0 is unburnt, < 0 burnt. Broad value noise (2.5 and 6
# per unit, the finer one licking upward with time) bends the front into a few wide arcs across the head, nape first.
GLSL_BURN = """float burnD() { return phase < 0.6 ? clamp((phase - 0.07) / 0.2, 0.0, 1.0) : 1.0 - clamp((phase - 0.77) / 0.2, 0.0, 1.0); }
float burnEdge(vec3 p, float d) {
  float u = clamp((p.x - XMIN) / (XMAX - XMIN), 0.0, 1.0);
  float n = vnoise(p * BURNF1 + 1.7) * BURNW1 + vnoise(p * BURNF2 + vec3(3.1, 3.1 - time * 0.6, 3.1)) * BURNW2;
  return (phase < 0.6 ? 1.0 - u : u) * BURNU + n - d * 1.55 + 0.1;
}
"""

FACET_FS = GLSL_HEAD + """uniform float phase;
uniform float time;
uniform float scan;
uniform float glow;
in vec3 vView;
in vec3 vObj;
flat in vec3 vL0;
flat in vec3 vL1;
flat in vec3 vL2;
flat in vec3 vL3;
flat in vec3 vFacet;
in vec4 vColor;
in vec3 vBary;
out vec4 x3d_FragColor;
""" + GLSL_HASH + GLSL_VNOISE + GLSL_BURN + """float mx3(vec3 c) { return max(max(c.r, c.g), c.b); }
float mn3(vec3 c) { return min(min(c.r, c.g), c.b); }
// One coloured point light on a gold facet: a soft diffuse wash in the facet's own hue, and a highlight that keeps the light's colour.
vec3 pointLit(vec3 Lp, vec3 LC, vec3 N, vec3 R, vec3 tint) {
  vec3 Lv = Lp - vView;
  float dl = length(Lv);
  vec3 Ld = Lv / dl;
  float att = LATT / (1.0 + 0.0075 * dl * dl);
  float dif = max(dot(N, Ld), 0.0), rd = max(dot(R, Ld), 0.0);
  float sp = pow(rd, 30.0) * 1.7 + pow(rd, 7.0) * 0.28;
  return LC * att * (tint * dif * 0.55 + mix(tint, vec3(1.0), 0.5) * sp);
}
void main() {
  vec3 N = normalize(cross(dFdx(vView), dFdy(vView)));      // flat, per facet
  vec3 V = normalize(-vView);
  float NdV = dot(N, V);
  if (NdV < 0.0) { N = -N; NdV = -NdV; }
  // One set of random numbers per facet, keyed on the facet's own colour (constant across the facet).
  ivec4 cq = ivec4(floor(vColor * 1000.0 + 0.5));
  vec3 fr = rnd3i(cq.xyz + ivec3(cq.w, 2 * cq.w, 3 * cq.w));
  vec3 fr2 = rnd3i(cq.zxy + ivec3(91, 17, 53));
  float fid = fr.x;
  // The click: a fire front crosses the head in a few broad arcs, nape first. It reaches each facet as ONE value
  // (keyed on the facet's corner vFacet plus a per-facet jitter, not on the pixel), so facets go one by one with
  // straight edges: gold, then charred dark, then ignited (deep red to ember, flickering), then the facet burns
  // down to its centre. The cut is an inset copy of the facet (barycentrics), so it stays a straight-edged triangle,
  // with a white-hot rim RIMPX pixels wide and a ramp from white-hot at the cut through ember to deep red inside.
  float d = burnD(), edge = 1.0, cut = 1.0, rimHot = 0.0, inner = 1.0;
  if (d > 0.0) {
    edge = burnEdge(vFacet, d) + (fr2.y - 0.5) * BURNJIT;
    float inset = smoothstep(0.0, -BURNSPAN, edge) * 0.3334;
    if (inset > 0.0) {
      float bmin = min(min(vBary.x, vBary.y), vBary.z);
      float px = (bmin - inset) / max(fwidth(bmin), 1e-5);     // pixels inside the cut
      if (px < 0.0 || inset > 0.333) discard;
      cut = clamp(px, 0.0, 1.0);
      rimHot = 1.0 - smoothstep(RIMPX * 0.6, RIMPX, px);
      inner = clamp((bmin - inset) / max(0.3334 - inset, 1e-3), 0.0, 1.0);   // 0 at the cut, 1 at the centre
    }
  }
  float charW = smoothstep(CHAR0, CHAR1, edge), heat = clamp(1.0 - edge / CHAR1, 0.0, 1.0);
  float coreW = smoothstep(0.0, 0.25, heat);
  // Gold: Fresnel over a procedural studio (key softbox, strip light, horizon line, top fill).
  vec3 base = vColor.rgb;
  vec3 tint = base / max(mx3(base), 1e-3);                      // the facet's own hue at full value
  vec3 hiHue = mix(tint, vec3(1.0, 0.86, 0.58), 0.5);           // highlights stay in hue, never white or grey
  float flesh = clamp((base.r - base.g - 0.22) * 3.0, 0.0, 1.0);
  vec3 Ne = normalize(N + (fr - 0.5) * 0.22);                   // a mosaic of facets
  vec3 R = reflect(-V, Ne);
  float key = smoothstep(0.62, 0.96, dot(R, normalize(vec3(-0.45, 0.6, 0.66))));
  float key2 = smoothstep(0.82, 0.98, dot(R, normalize(vec3(0.55, 0.5, 0.67))));
  float strip = exp(-pow((R.x - 0.72) * 5.0, 2.0)) * smoothstep(-0.4, 0.4, R.y);
  float fill = smoothstep(0.55, 1.0, dot(R, normalize(vec3(0.25, -0.25, 0.93))));
  float hor = exp(-pow(R.y * 5.5 + 0.35, 2.0));
  float top = smoothstep(0.3, 1.0, R.y);
  vec3 env = vec3(1.0, 0.88, 0.66) * (key * 2.1 + key2 * 1.3) + vec3(1.0, 0.7, 0.4) * (strip * 0.9 + fill * 0.28)
           + vec3(0.95, 0.6, 0.3) * hor * 0.5 + vec3(0.5, 0.4, 0.3) * top * 0.25 + vec3(0.035, 0.026, 0.02);
  vec3 F0 = clamp(base * vec3(1.2, 1.0, 0.72) * (0.75 + 0.5 * fid), 0.0, 1.0);
  vec3 F = F0 + (hiHue - F0) * pow(1.0 - NdV, 5.0);            // grazing light goes to the facet's hue, not to white
  vec3 metal = F * env;
  vec3 L = normalize(vec3(-0.5, 0.6, 0.62));
  float dif = max(dot(N, L), 0.0);
  float spec = pow(max(dot(N, normalize(L + V)), 0.0), 70.0);
  vec3 skin = base * (0.3 + 0.7 * dif) + mix(base, vec3(1.0, 0.86, 0.58), 0.5) * spec * 0.7 + base * strip * 0.45
            + vec3(0.9, 0.3, 0.15) * pow(1.0 - NdV, 2.5) * 0.9;  // snood and wattle: lit from within, an ember rim
  vec3 col = mix(metal, skin, flesh);
  vec3 lit = pointLit(vL0, LC0, N, R, hiHue) + pointLit(vL1, LC1, N, R, hiHue) + pointLit(vL2, LC2, N, R, hiHue) + pointLit(vL3, LC3, N, R, hiHue);
  col += lit * LITK * (1.0 - 0.35 * flesh);
  float rim = pow(1.0 - NdV, 3.0);                             // Hokie maroon to ember at the edges
  col += mix(vec3(0.55, 0.08, 0.17), vec3(1.0, 0.46, 0.12), clamp(0.55 + vObj.y * 0.28, 0.0, 1.0)) * rim * 0.85;
  vec3 Np = normalize(N + (fr2 - 0.5) * 0.3);
  float glint = pow(max(dot(reflect(-V, Np), normalize(vec3(-0.45, 0.65, 0.6))), 0.0), 160.0);
  float flash = step(0.9, fid) * pow(0.5 + 0.5 * sin(time * (1.1 + 2.0 * fid) + fid * 40.0), 40.0);
  col += mix(hiHue, vec3(1.0, 0.95, 0.85), 0.35) * (glint * 1.5 + flash * 1.3) * (1.0 - 0.6 * flesh) * glow;
  float sc = exp(-pow((vObj.x * 0.85 + vObj.y * 0.3 - scan) * 2.4, 2.0));   // the energy scan
  col += (vec3(1.0, 0.66, 0.26) * 0.45 + vec3(1.0, 0.86, 0.6) * rim * 0.9) * sc * glow;
  // No facet goes dead: saturation stays at SATMIN or more, along the facet's own hue, at the same value.
  float vmax = mx3(col), sat = (vmax - mn3(col)) / max(vmax, 1e-4), st = 1.0 - mn3(tint);
  vec3 floorCol = vmax * (1.0 - min(1.0, SATMIN / max(st, SATMIN)) * (1.0 - tint));
  col = mix(col, floorCol, clamp((SATMIN - sat) / SATMIN, 0.0, 1.0));
  // The fire, per facet: charred near-black ahead of the front, then the facet ignites. Its colour runs char, deep
  // red, ember, white-hot toward the cut, with a fine fast flicker inside, and a white-hot rim at the cut itself.
  col = mix(col, vec3(0.07, 0.012, 0.012) + col * 0.08, charW * 0.92);
  if (heat > 0.0) {
    float fl = 0.7 + 0.7 * vnoise(vObj * 31.0 + vec3(fid * 40.0, -time * 7.0, time * 3.0));   // fine, fast flicker
    float hot = heat * heat * (1.0 - 0.75 * smoothstep(0.0, 0.85, inner));   // hotter toward the cut, cooler at the centre
    vec3 fire = mix(vec3(0.42, 0.03, 0.025), vec3(1.0, 0.34, 0.06) * 1.6, smoothstep(0.0, 0.55, hot));
    fire = mix(fire, vec3(1.0, 0.8, 0.45) * 1.9, smoothstep(0.55, 1.0, hot));
    col = mix(col, fire * fl, coreW);
  }
  col = mix(col, vec3(1.0, 0.94, 0.8) * 2.2, rimHot);
  // Highlights roll off without a hue shift: clipping each channel on its own turned bright gold lime.
  float m = mx3(col);
  col /= 1.0 + m * KNEE;
  m = mx3(col);
  if (m > 1.0) col = mix(col / m, vec3(1.0, 0.86, 0.58), clamp((m - 1.0) * 0.45, 0.0, 0.55));
  col *= FGAIN;
  float a = clamp(vColor.a + rim * 0.2 + sc * 0.15, 0.0, 1.0);
  a = max(a, coreW);
  x3d_FragColor = vec4(col, a * cut);
}
"""

# A ribbon corner: x3d_Vertex is this end, x3d_TexCoord0 the other end, x3d_Normal's angle a 4-bit code
# (bit 0 side, bit 1 second end, bit 2 this end fixed, bit 3 other end fixed). The colour's alpha sets the width.
LINE_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform ivec4 x3d_Viewport;
uniform float phase;
uniform float time;
uniform float scan;
uniform float bloom;
""" + GLSL_LIGHTS + """in vec4 x3d_Vertex;
in vec3 x3d_Normal;
in vec4 x3d_TexCoord0;
in vec4 x3d_Color;
out vec4 vColor;
out float vX;
out float vS;
out float vPulse;
out float vSeed;
out float vFade;
out float vScan;
out float vBloom;
out float vHeat;
out float vHot;
out vec3 vPool;
out float vLoop;
out float vPh;
out float vDel;
""" + GLSL_HASH + GLSL_SCATTER + GLSL_VNOISE + GLSL_BURN + GLSL_POOL + """void main() {
  int code = (int(floor(atan(x3d_Normal.y, x3d_Normal.x) / 0.39269908 + 0.5)) + 16) % 16;
  float side = (code & 1) == 1 ? 1.0 : -1.0;
  vec3 a = x3d_Vertex.xyz, b = x3d_TexCoord0.xyz;
  vec4 sa = (code & 4) != 0 ? vec4(a, 0.0) : scatter(a);
  vec4 sb = (code & 8) != 0 ? vec4(b, 0.0) : scatter(b);
  mat4 PM = x3d_ProjectionMatrix * x3d_ModelViewMatrix;
  vec4 ca = PM * vec4(sa.xyz, 1.0), cb = PM * vec4(sb.xyz, 1.0);
  vec2 vp = vec2(x3d_Viewport.zw);
  vec2 dir = cb.xy / cb.w * vp - ca.xy / ca.w * vp;
  float len = length(dir);
  dir = len > 1e-5 ? dir / len : vec2(1.0, 0.0);
  float bl = bloom * ((code & 12) != 0 ? 1.0 : LATB);           // less bloom on the head's dense lattice
  // v3: a colour alpha of 0.7 or more marks a flywheel ribbon: alpha = 0.7 + 0.3 * (phase_q + 100 * span_q) / 400, where phase_q (0 to 99)
  // is where this edge starts round its loop (hundredths) and span_q (0 to 3) is how much of the loop it covers (0.06 + 0.04 * span_q).
  float cal = x3d_Color.a;
  vLoop = step(0.699, cal);
  float idx = vLoop > 0.5 ? floor((cal - 0.7) / 0.3 * 400.0 + 0.5) : 0.0;
  float dq = floor(idx / 100.0);
  vPh = (idx - 100.0 * dq) / 100.0;
  vDel = 0.06 + 0.04 * dq;
  float aw = vLoop > 0.5 ? LOOPW : cal;
  float w = (0.6 + 2.8 * aw) * (1.0 + 1.6 * bl) * vp.y / 640.0;   // half width in pixels, scaled with the canvas
  ca.xy += vec2(-dir.y, dir.x) * side * w * 2.0 / vp * ca.w;
  ca.z -= 0.002 * ca.w;                                         // sit just in front of the facets
  gl_Position = ca;
  vBloom = bl;
  vX = (code & 2) != 0 ? -side : side;                          // across the ribbon, the same sign at both ends
  vColor = x3d_Color;
  vS = vLoop > 0.5 ? ((code & 2) != 0 ? 1.0 : 0.0) : (a.x >= b.x ? 0.0 : 1.0);   // pulses run from the far end toward the head; round a wheel, from edge start to end
  vPool = poolAt((a + b) * 0.5);
  vPulse = (code & 12) != 0 ? 1.0 : 0.0;
  vSeed = rnd3i(qpos(a) + qpos(b)).x;
  vFade = 1.0 - 0.55 * max(sa.w, sb.w);
  // The lattice burns on the facets' fire: an edge glows ember as the front crosses its middle, holds a moment
  // (its own random delay), then goes out. Only the head's points stay, a constellation. Network edges never burn.
  vHeat = 0.0; vHot = 0.0;
  float d = burnD();
  if (d > 0.0 && (code & 12) != 12) {
    float e = burnEdge((a + b) * 0.5, d), delay = 0.03 + 0.2 * vSeed;
    vHeat = smoothstep(0.09, 0.02, e) * smoothstep(-delay - 0.06, -delay * 0.4, e);
    vHot = exp(-pow(e / 0.035, 2.0));                           // white-hot as the cut crosses the edge
    vFade *= smoothstep(-delay - 0.06, -delay, e);
  }
  if (vFade < 0.001) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);    // a burnt-out edge costs no fill
  vScan = (code & 12) != 0 ? 0.0 : exp(-pow(((a.x + b.x) * 0.425 + (a.y + b.y) * 0.15 - scan) * 2.4, 2.0));
}
"""

LINE_FS = GLSL_HEAD + """uniform float time;
uniform float glow;
in float vBloom;
in vec4 vColor;
in float vX;
in float vS;
in float vPulse;
in float vSeed;
in float vFade;
in float vScan;
in float vHeat;
in float vHot;
in vec3 vPool;
in float vLoop;
in float vPh;
in float vDel;
out vec4 x3d_FragColor;
void main() {
  if (vFade < 0.003) discard;
  float b = 1.0 + 1.6 * vBloom;                                 // bloom widens the ribbon, the core keeps its width
  float core = exp(-vX * vX * 9.0 * b * b);
  float halo = (exp(-vX * vX * 2.2 * b) * (0.3 - 0.12 * vBloom) + exp(-vX * vX * 3.0) * 0.1 * vBloom) * HALO;
  float pk = 0.0;
  if (vPulse > 0.5) {
    float t = fract(time * (0.09 + 0.13 * vSeed) + vSeed * 17.0) * 1.8 - 0.4;
    float dd = vS - t;
    pk = exp(-dd * dd * 60.0) * glow;
  }
  float lk = 0.0;
  if (vLoop > 0.5) {                                            // a wheel: two comets circle it, each trailing behind its head
    float u = fract(time / LOOPT);
    float pos = vPh + vS * vDel;
    float d1 = fract(u - pos), d2 = fract(u + 0.5 - pos);
    lk = (exp(-d1 * 11.0) + exp(-d2 * 11.0)) * glow;
    pk = max(pk * 0.2, (exp(-d1 * 70.0) + exp(-d2 * 70.0)) * glow);
  }
  vec3 hc = pow(vColor.rgb, vec3(1.0 + HSAT * vBloom)) * (1.0 + 0.6 * vBloom);   // bloom: a deeper gold halo round a pale core
  vec3 pulseC = vLoop > 0.5 ? mix(vColor.rgb, vec3(1.0, 0.96, 0.86), 0.5) : vec3(1.0, 0.85, 0.55);
  vec3 em = vColor.rgb * core * LCORE * (1.0 + 0.7 * vLoop + 1.6 * lk) + hc * halo * (1.0 + 1.2 * lk) + pulseC * pk * (core * 1.7 + halo * PULSEH)
          + vec3(1.0, 0.74, 0.38) * vScan * (core + halo) * 1.3 * glow
          + vPool * (core * 0.9 + halo * 1.1) * POOLE;            // v3: the moving lights tint the ribbons they pass
  em = mix(em, vec3(1.0, 0.45, 0.12) * (core * 1.6 + halo * 2.2) + vec3(1.0, 0.9, 0.7) * core * 0.4, vHeat);
  em += vec3(1.0, 0.9, 0.74) * core * vHot * 0.9;
  em *= vFade * (vPulse > 0.5 ? 1.0 : HEADK);                   // HEADK: the head's dense lattice, dimmer when additive
  float a = clamp(max(max(em.r, em.g), em.b), 0.0, 1.0);
  if (a < 0.004) discard;
  x3d_FragColor = GLOWOUT;
}
"""

# A point sprite. The X3D 4.0 XSD gives PointSet no attrib field, so the colour's alpha carries the sprite's
# kind and size: alpha = kind / 4 + size / 16. Kind 0 head spark (flies with the dissolve), 1 network star,
# 2 drifting dust, 3 mote. Out-of-focus points grow and fade (depth of field).
POINT_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform ivec4 x3d_Viewport;
uniform float phase;
uniform float time;
uniform float glow;
uniform float bloom;
""" + GLSL_LIGHTS + """in vec4 x3d_Vertex;
in vec4 x3d_Color;
out vec4 vColor;
out float vB;
out float vBloom;
out float vSpike;
""" + GLSL_HASH + GLSL_SCATTER + GLSL_POOL + """void main() {
  vec3 p = x3d_Vertex.xyz;
  vec3 r = rnd3i(qpos(p) + ivec3(11, 5, 3));
  float kind = floor(x3d_Color.a * 4.0 + 0.001), size = (x3d_Color.a - kind * 0.25) * 16.0, e = 0.0;
  if (kind < 0.5) { vec4 s = scatter(p); p = s.xyz; e = s.w; }
  else if (kind < 2.5 && kind > 1.5) {
    p += vec3(sin(time * (0.05 + 0.06 * r.x) + r.y * 6.283) * 0.7, sin(time * (0.04 + 0.05 * r.y) + r.z * 6.283) * 0.5,
              sin(time * (0.03 + 0.04 * r.z) + r.x * 6.283) * 0.6);
  }
  vec4 mv = x3d_ModelViewMatrix * vec4(p, 1.0);
  float k = float(x3d_Viewport.w) / 640.0;
  float dist = max(0.2, -mv.z);
  if (kind > 2.5) size *= 1.0 - 0.45 * bloom;                  // motes: bloom draws them wider, so it draws them smaller
  float px = size * length(x3d_ModelViewMatrix[0].xyz) * 0.16 * x3d_ProjectionMatrix[1][1] * float(x3d_Viewport.w) * 0.5 / dist;
  float tw = 0.62 + 0.38 * sin(time * (0.7 + 1.9 * r.y) + r.x * 6.283);
  if (kind < 0.5) tw = 0.88 + 0.12 * tw;
  float coc = abs(dist - FOCUS) * (kind > 0.5 ? 0.9 : 0.25) * k;
  float s = clamp(px * (0.85 + 0.3 * tw) * (1.0 + 0.9 * bloom) + coc, 1.0, 110.0 * k);
  gl_PointSize = s;
  vB = tw * (1.0 + 0.9 * e) * clamp(px * (1.0 + 0.9 * bloom) / s, 0.2, 1.0) * mix(1.0, glow, 0.5);
  vBloom = bloom;
  vSpike = size > SPIKEMIN && kind > 0.5 && kind < 1.5 ? 1.0 : 0.0;   // only the few brightest hubs
  vec3 pool = (kind > 0.5 && kind < 2.5) ? poolAt(p) : vec3(0.0);
  vColor = vec4(clamp(x3d_Color.rgb + pool * 0.8, 0.0, 1.0), 1.0);
  vB *= 1.0 + 0.9 * min(1.0, length(pool));
  gl_Position = size <= 0.01 ? vec4(2.0, 2.0, 2.0, 1.0) : x3d_ProjectionMatrix * mv;
  gl_Position.z -= 0.003 * gl_Position.w;
}
"""

POINT_FS = GLSL_HEAD + """in vec4 vColor;
in float vB;
in float vBloom;
in float vSpike;
out vec4 x3d_FragColor;
void main() {
  vec2 d = gl_PointCoord * 2.0 - 1.0;
  float r2 = dot(d, d);
  if (r2 > 1.0) discard;
  float bb = 1.0 + 0.9 * vBloom;
  float core = exp(-r2 * 16.0 * bb * bb);
  float halo = (exp(-r2 * 3.5 * bb) * (0.62 - 0.2 * vBloom) * (1.0 - r2) + exp(-r2 * 2.5) * 0.16 * vBloom * (1.0 - r2)) * HALO;
  float sp = vSpike * (exp(-abs(d.x) * 28.0) + exp(-abs(d.y) * 28.0)) * max(0.0, 1.0 - sqrt(r2) / 0.7) * 0.7;
  vec3 hc = pow(vColor.rgb, vec3(1.0 + HSAT * vBloom)) * (1.0 + 0.6 * vBloom);   // bloom: a deeper halo round a pale core
  vec3 em = (hc * (halo + sp) + mix(vColor.rgb, vec3(1.0), CORW) * core * CORG) * vB;
  float a = clamp(max(max(em.r, em.g), em.b), 0.0, 1.0);
  if (a < 0.004) discard;
  x3d_FragColor = GLOWOUT;
}
"""

EYE_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec2 vP;
void main() {
  vP = x3d_Vertex.xy;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
  gl_Position.z -= 0.004 * gl_Position.w;
}
"""

EYE_FS = GLSL_HEAD + """uniform float time;
uniform float phase;
in vec2 vP;
out vec4 x3d_FragColor;
float ring(float r, float R, float w, float aa) { return 1.0 - smoothstep(w * 0.5, w * 0.5 + aa, abs(r - R)); }
void main() {
  float r = length(vP);
  float aa = fwidth(r) * 1.2 + 1e-4;
  float ang = atan(vP.y, vP.x);
  float iris = 1.0 - smoothstep(0.2 - aa, 0.2 + aa, r);
  float fib = 0.5 + 0.5 * sin(ang * 27.0 + sin(ang * 5.0) * 2.5);
  vec3 ic = mix(vec3(1.0, 0.6, 0.14), vec3(0.6, 0.24, 0.04), smoothstep(0.1, 0.2, r)) * (0.7 + 0.3 * fib);
  ic = mix(ic, vec3(0.16, 0.05, 0.015), smoothstep(0.165, 0.2, r));
  ic = mix(ic, vec3(0.018, 0.011, 0.008), 1.0 - smoothstep(0.105 - aa, 0.105 + aa, r));
  vec2 c1 = vP - vec2(-0.055, 0.065), c2 = vP - vec2(0.06, -0.045);
  ic += vec3(1.0, 0.97, 0.9) * (exp(-dot(c1, c1) * 1100.0) + 0.45 * exp(-dot(c2, c2) * 3000.0));
  float rg = ring(r, 0.26, 0.012, aa) + 0.8 * ring(length(vP * vec2(1.0, 1.111)), 0.36, 0.01, aa)
           + 0.6 * ring(length(vP * vec2(1.0, 1.25)), 0.46, 0.008, aa);
  float gw = exp(-pow((r - 0.2) * 14.0, 2.0)) * 0.4 * (1.0 - iris);
  vec3 em = ic * iris + vec3(0.95, 0.85, 0.6) * rg * (1.0 - iris) + vec3(1.0, 0.58, 0.18) * gw;
  float a = clamp(iris + rg + gw, 0.0, 1.0);
  // While the head is apart the eye stays as one star: the iris goes out as the fire reaches it, a four-point
  // glint takes its place, rides the flight and twinkles, and the iris comes back as the head reassembles.
  float st = smoothstep(0.17, 0.24, phase) * (1.0 - smoothstep(0.84, 0.93, phase));
  float tw = 0.8 + 0.2 * sin(time * 2.3);
  float core = exp(-r * r * 260.0), spk = (exp(-abs(vP.y) * 90.0) * exp(-abs(vP.x) * 6.0) + exp(-abs(vP.x) * 90.0) * exp(-abs(vP.y) * 6.0)) * 1.1;
  float star = clamp((core * 1.2 + spk + exp(-r * r * 28.0) * 0.35) * tw, 0.0, 1.0);
  vec3 sc = mix(vec3(1.0, 0.62, 0.22), vec3(1.0, 0.95, 0.82), clamp(core * 1.5 + spk * 0.6, 0.0, 1.0));
  em = mix(em, sc * star, st);
  a = mix(a, star, st);
  if (a < 0.004) discard;
  x3d_FragColor = vec4(min(em / max(a, 1e-3), vec3(1.0)), a);
}
"""

# The sky: a sphere around the camera's start, coloured by direction. Ground colour at the edges (it meets
# the page), a warm glow behind the head, a maroon haze behind the network, faint nebula, dithered.
SKY_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec3 vDir;
void main() {
  vDir = x3d_Vertex.xyz;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
"""

SKY_FS = GLSL_HEAD + """in vec3 vDir;
out vec4 x3d_FragColor;
""" + GLSL_VNOISE + """float h2(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
void main() {
  vec3 d = normalize(vDir);
  float f = smoothstep(0.0, 0.4, -d.z);
  vec2 q = d.xy / max(-d.z, 0.1);
  vec2 a = (q - vec2(QHX, QHY)) * vec2(1.0, 1.3), b = q - vec2(QNX, QNY);
  float n = vnoise(d * 9.0) * 0.6 + vnoise(d * 21.0) * 0.4;
  vec3 col = vec3(0.057, 0.050, 0.047)
           + f * vec3(0.15, 0.095, 0.045) * exp(-dot(a, a) / 0.03) * (0.8 + 0.4 * n)
           + f * vec3(0.085, 0.022, 0.032) * exp(-dot(b, b) / 0.05) * (0.7 + 0.6 * n)
           + f * vec3(0.03, 0.02, 0.012) * smoothstep(0.55, 0.9, n) * exp(-dot(q, q) / 0.12);
  col += (h2(gl_FragCoord.xy) + h2(gl_FragCoord.yx + 17.0) - 1.0) / 255.0;
  x3d_FragColor = vec4(col, 1.0);
}
"""

# Hidden unless the GPU path fails: then X3D's fallback rule shows this line set's Material instead.
HIDE_VS = GLSL_HEAD + """uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
void main() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); }
"""
HIDE_FS = GLSL_HEAD + """out vec4 x3d_FragColor;
// The output must stay live: a shader that only discards gets x3d_FragColor optimised away, and
// WebGL then warns about a draw buffer with no fragment output. No fragment survives anyway.
void main() { if (gl_FragCoord.x > -1.0) discard; x3d_FragColor = vec4(0.0); }
"""



# ----------------------------------------------------------------------------------------------
# 6. Number formatting, palette, small maths
# ----------------------------------------------------------------------------------------------
def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def f3(v):
    s = ('%.3f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def vec(v):
    return ' '.join(f(x) for x in v)


def col(c):
    return ' '.join(f3(max(0.0, min(1.0, x))) for x in c)


GOLD = (0.839, 0.702, 0.355)        # the Library's palette: gold oklch(78% .115 88)
GOLD_SOFT = (0.936, 0.854, 0.603)   # gold-soft oklch(89% .085 92)
GOLD_MUTED = (0.608, 0.513, 0.313)  # gold-muted oklch(62% .075 85)
MAROON = (0.52, 0.145, 0.227)       # maroon oklch(42% .13 12)
EMBER = (0.91, 0.449, 0.112)        # ember oklch(68% .17 50)
GROUND = (0.057, 0.050, 0.047)      # ground oklch(16% .004 60) = #0f0d0c, the page background

# ---- v3: the lights. Each moves on a sinusoid per axis (one period), centre c + amplitude a * sin(2 pi t / T + phase).
# Positions are in scene units (the head is 7.5 tall; in a headset 1 unit is 1 metre). Colours are linear-ish display RGB.
LIGHTS = [
    dict(name='LightGold',   color=(1.00, 0.80, 0.42), c=(0.0, -0.6, 7.5),  a=(4.6, 3.1, 1.8), T=17.0, ph=(0.0, 1.6, 0.4), k=1.00),
    dict(name='LightEmber',  color=(1.00, 0.36, 0.09), c=(3.2, -5.6, 4.6),  a=(5.2, 1.9, 2.2), T=23.0, ph=(2.1, 0.3, 1.1), k=0.95),
    dict(name='LightCyan',   color=(0.12, 0.78, 1.00), c=(8.5, -1.2, 5.8),  a=(6.8, 4.0, 3.4), T=29.0, ph=(0.7, 2.4, 3.6), k=1.00),
    dict(name='LightViolet', color=(0.66, 0.28, 1.00), c=(3.6, 2.6, -2.4),  a=(6.2, 2.4, 3.0), T=37.0, ph=(4.0, 0.9, 2.2), k=1.05),
]
LIGHT_KEYS = 48


def light_pos(L, t):
    return [L['c'][i] + L['a'][i] * math.sin(2 * math.pi * t / L['T'] + L['ph'][i]) for i in range(3)]


# class -> star colour (display RGB). Brand gold stays for the standards; every other family gets its own hue.
FAMILY = {
    'spec':   ((0.98, 0.80, 0.45), ('Standard', 'Component', 'NodeType')),
    'tool':   ((0.34, 0.86, 0.96), ('Tool', 'Validator', 'Repo')),
    'people': ((0.96, 0.46, 0.66), ('Org', 'Person', 'Event')),
    'work':   ((1.00, 0.62, 0.26), ('Workstream', 'Document', 'Dataset', 'Scene')),
    'learn':  ((0.62, 0.95, 0.46), ('Experiment', 'Finding', 'Metric')),
    'rule':   ((0.68, 0.52, 1.00), ('Rule', 'Decision')),
    'loop':   ((1.00, 0.95, 0.80), ('Loop',)),
}
CLASS_COLOUR = {c: rgb for rgb, cs in FAMILY.values() for c in cs}
# relation -> ribbon colour family
REL_COLOUR = {'structure': (0.80, 0.66, 0.38), 'technical': (0.30, 0.78, 0.90), 'social': (0.90, 0.42, 0.62), 'knowledge': (0.58, 0.88, 0.42), 'loop': (1.0, 0.9, 0.7)}
REL_FAMILY = {'part_of': 'structure', 'contains': 'structure', 'version_of': 'structure', 'supersedes': 'structure', 'forked_from': 'structure', 'depends_on': 'structure', 'appears_in': 'structure',
              'implements': 'technical', 'reads': 'technical', 'writes': 'technical', 'converts_to': 'technical', 'validates': 'technical', 'renders': 'technical', 'uses': 'technical', 'co_used_with': 'technical',
              'authored_by': 'social', 'maintained_by': 'social', 'member_of': 'social', 'works_with': 'social', 'hosts': 'social', 'presented_at': 'social'}


def glow_texture(n=16):
    rows = []
    for j in range(n):
        row = []
        for i in range(n):
            x = (i + 0.5) / n * 2 - 1; y = (j + 0.5) / n * 2 - 1; r = math.hypot(x, y)
            a = min(1.0, 0.7 * max(0.0, 1 - r) ** 2.3 + math.exp(-(r / 0.2) ** 2))
            row.append('0xFF%02X' % int(round(a * 255)))
        rows.append(' '.join(row))
    return '%d %d 2\n' % (n, n) + '\n'.join(rows)


def axis_angle(q):
    w, x, y, z = q
    w = max(-1.0, min(1.0, w)); a = 2 * math.acos(w); s = math.sqrt(max(0.0, 1 - w * w))
    if s < 1e-6:
        return (0, 1, 0, 0)
    return (x / s, y / s, z / s, a)


def qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qaxis(ax, ang):
    s = math.sin(ang / 2); return (math.cos(ang / 2), ax[0] * s, ax[1] * s, ax[2] * s)


def wrap(items, per, indent):
    return ('\n' + ' ' * indent).join(' '.join(items[i:i + per]) for i in range(0, len(items), per))



# ----------------------------------------------------------------------------------------------
# 7. Assemble the model
# ----------------------------------------------------------------------------------------------
def ear_clip(poly):
    """Triangulate a simple polygon (counter-clockwise, y up)."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def in_tri(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
    idx = list(range(len(poly))); tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(in_tri(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2)); idx.pop(k); break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def head_hull():
    """A closed prism around the head's silhouette: the volume the burning facets shed embers from."""
    pts = [U(p) for p in resample(SILHOUETTE, lambda q: 55, closed=True)]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts = pts[::-1]
    n = len(pts); zh = 0.5
    coords = [(x, y, zh) for x, y in pts] + [(x, y, -zh) for x, y in pts]
    tris = []
    for a, b, c in ear_clip(pts):
        tris.append((a, b, c)); tris.append((n + a, n + c, n + b))
    for i in range(n):
        j = (i + 1) % n
        tris.append((i, n + i, n + j)); tris.append((i, n + j, j))
    return coords, tris


def build():
    mesh = Mesh()
    faces, outline_ids, contours = build_head(mesh)
    nodes, anchors, net_edges, net_tris, na, dust = build_network(mesh, outline_ids)
    # Network points that touch the head join the head's point list (and never move), so the bridge
    # edges stretch from the flying head to the still network.
    bridge, anchor_slot = [], {}
    for a, b in net_edges:
        if (a >= na) != (b >= na):
            n_i, h_i = (a, b) if a < na else (b, a)
            if n_i not in anchor_slot:
                mesh.pts.append({'px': nodes[n_i]['px'], 'xyz': list(nodes[n_i]['xyz']), 'part': 'anchor', 'glow': False})
                anchor_slot[n_i] = len(mesh.pts) - 1
            bridge.append((anchors[h_i - na], anchor_slot[n_i]))
    net_edges = [(a, b) for a, b in net_edges if a < na and b < na]

    P = mesh.pts
    xs = [q['xyz'][0] for q in P if q['part'] != 'anchor']
    xmin, xmax = min(xs), max(xs)
    rng = random.Random(7)

    def neck_fade(px):
        """1 on the head, falling toward 0 at the neck base, where the bird turns into network."""
        return 1 - smooth((px[1] - 700) / 240.0 + (px[0] - 760) / 500.0) * 0.85

    def face_rgba(t, part):
        """Base colour and opacity per facet. v2 facets are metal, so the head reads nearly solid."""
        cen = [sum(P[i]['px'][k] for i in t) / 3 for k in range(2)]
        j = rng.uniform(-0.08, 0.08)
        if part in ('beak', 'mandible'):
            c = mix(GOLD, GOLD_SOFT, 0.55 + j); a = 0.97 if part == 'beak' else 0.92
        elif part == 'back':
            c = mix(GOLD_MUTED, MAROON, 0.3 + j); a = 0.2
        else:
            c = mix(GOLD, GOLD_SOFT, 0.1 + j); a = 0.95
            if inside(cen, SKIN):
                k = min(1.0, poly_dist(cen, SKIN) / 45.0)
                c = mix(c, (0.62, 0.12, 0.2), 0.35 + 0.6 * k); a = 0.9
        return c, a * neck_fade(cen) ** 1.7

    def flesh_rgba(t, part):
        j = rng.uniform(-0.07, 0.07)
        cy = sum(P[i]['px'][1] for i in t) / 3
        if part == 'snood':
            c = mix((0.8, 0.18, 0.24), (0.56, 0.1, 0.17), smooth((cy - 300) / 300.0))
        else:
            c = mix((0.74, 0.15, 0.22), (0.47, 0.08, 0.15), smooth((cy - 470) / 260.0))
        return [x + j for x in c], 0.9

    gold_faces = faces['head'] + faces['beak'] + faces['mandible'] + faces['back']
    gold_parts = (['head'] * len(faces['head']) + ['beak'] * len(faces['beak']) +
                  ['mandible'] * len(faces['mandible']) + ['back'] * len(faces['back']))
    red_faces = faces['snood'] + faces['wattle']
    red_parts = ['snood'] * len(faces['snood']) + ['wattle'] * len(faces['wattle'])

    def point_colour(q):
        part = q['part']; px = q['px']
        if part == 'back':
            return mix(GOLD_MUTED, GROUND, 0.45)
        if part in ('snood', 'wattle'):
            return (0.97, 0.44, 0.27)
        if part == 'anchor':
            return mix(GOLD_MUTED, GROUND, 0.2)
        c = mix(GOLD, GOLD_SOFT, 0.35) if inside(px, BEAK) else mix(GOLD, GOLD_SOFT, 0.2)
        if inside(px, SKIN) and poly_dist(px, SKIN) > 18:
            c = mix(c, (1.0, 0.4, 0.3), 0.62)
        return mix(GROUND, c, 0.12 + 0.88 * neck_fade(px) ** 1.5)

    # Ribbons on the head: contour segments (bright, wide), facet edges, bridges into the network.
    contour_segs = {}
    for line, kind in contours:
        for a, b in zip(line, line[1:]):
            if a != b:
                contour_segs[(min(a, b), max(a, b))] = kind
    edge_set = set()
    for t in gold_faces + red_faces:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edge_set.add((min(a, b), max(a, b)))
    fixed = {i for i, q in enumerate(P) if q['part'] == 'anchor'}
    head_ribbons = []
    for a, b in sorted(edge_set - set(contour_segs)):
        back = P[a]['part'] == 'back' or P[b]['part'] == 'back'
        c = mix(point_colour(P[a]), point_colour(P[b]), 0.5)
        head_ribbons.append((a, b, c, 0.1 if back else 0.28))
    for (a, b), kind in sorted(contour_segs.items()):
        fade = neck_fade(mix(list(P[a]['px']) + [0], list(P[b]['px']) + [0], 0.5)[:2])
        c = mix(GROUND, GOLD_SOFT if kind == 'gold' else (0.96, 0.46, 0.28), 0.15 + 0.85 * fade)
        head_ribbons.append((a, b, c, 0.62))
    for h, an in bridge:
        head_ribbons.append((h, an, mix(point_colour(P[h]), mix(GOLD_MUTED, GROUND, 0.2), 0.5), 0.22))

    glow_ids = [i for i, q in enumerate(P) if q['glow'] and neck_fade(q['px']) > 0.45 and
                (q['part'] != 'front' or random.Random(i * 7919).random() < 0.62 or poly_dist(q['px'], SILHOUETTE) < 2)]
    gset = set(glow_ids)
    spark = []
    for i, q in enumerate(P):
        if i in gset:
            base = point_colour(q)
            spark.append((mix(base, (1, 0.9, 0.66), 0.55), 1.25 if q['part'] in ('snood', 'wattle') else 1.45))
        else:
            spark.append(((0, 0, 0), 0.0))

    g = {
        'P': P, 'nodes': nodes, 'dust': dust, 'net_edges': net_edges, 'net_tris': net_tris, 'na': na,
        'bridge': bridge, 'anchor_slot': anchor_slot, 'gold_faces': gold_faces, 'red_faces': red_faces,
        'gold_rgba': [face_rgba(t, p) for t, p in zip(gold_faces, gold_parts)],
        'red_rgba': [flesh_rgba(t, p) for t, p in zip(red_faces, red_parts)],
        'head_ribbons': head_ribbons, 'fixed': fixed, 'edges': sorted(edge_set) + bridge,
        'glow_ids': glow_ids, 'spark': spark, 'xmin': xmin, 'xmax': xmax,
    }
    hx = [q['xyz'][0] for q in P if q['part'] == 'front']; hy = [q['xyz'][1] for q in P if q['part'] == 'front']
    g['pivot'] = [(min(hx) + max(hx)) / 2 - 0.3, (min(hy) + max(hy)) / 2 + 0.6, 0]
    g['eye'] = list(U(EYE)) + [height(EYE) + 0.05]
    ex, ey = U(EYE)
    near = sorted((i for i, q in enumerate(P) if q['part'] == 'front'), key=lambda i: math.dist(P[i]['xyz'][:2], (ex, ey)))[:4]
    # The eye rides the mean flight of its four nearest vertices, computed with the GLSL's own hash.
    pts = [[float(f(v)) for v in P[i]['xyz']] for i in near]
    g['eye_path'] = []
    for k in EYE_KEYS:
        moved = [scatter_py(p, k, float(f(xmin)), float(f(xmax))) for p in pts]
        g['eye_path'].append([g['eye'][j] + sum(m[j] - p[j] for m, p in zip(moved, pts)) / 4 for j in range(3)])
    g['hull'] = head_hull()
    g['kg'] = load_graph()
    order = sorted(range(len(nodes)), key=lambda i: -nodes[i]['w'])
    g['hub_ids'] = order[:12]
    for i in g['hub_ids']:
        nodes[i]['sz'] = 3.4
    return g


def plan_motes(g):
    """Paths along network edges that end on the head outline: sparks flowing into the bird."""
    nodes = g['nodes']; na = len(nodes)
    adj = {i: set() for i in range(na)}
    for a, b in g['net_edges']:
        adj[a].add(b); adj[b].add(a)
    anchored = set(g['anchor_slot'])
    rng = random.Random(5)
    starts = sorted(range(na), key=lambda i: -nodes[i]['px'][0])
    motes, used = [], set()
    for name, cycle, size in (('MoteA', 6.5, 2.2), ('MoteB', 8.3, 1.8), ('MoteC', 10.9, 2.5)):
        for s in starts:
            if s in used or rng.random() < 0.6:
                continue
            prev = {s: None}; q = [s]; hit = None
            while q:
                v = q.pop(0)
                if v in anchored and v != s:
                    hit = v; break
                for w_ in sorted(adj[v]):
                    if w_ not in prev:
                        prev[w_] = v; q.append(w_)
            if hit is None:
                continue
            path = []; v = hit
            while v is not None:
                path.append(v); v = prev[v]
            path = path[::-1]
            if len(path) < 4:
                continue
            used.update(path[:3])
            pts = [nodes[i]['xyz'] for i in path]
            hid = next(h for (h, a) in g['bridge'] if a == g['anchor_slot'][hit])
            pts.append(g['P'][hid]['xyz'])
            d = [0.0]
            for i in range(1, len(pts)):
                d.append(d[-1] + math.dist(pts[i - 1], pts[i]))
            motes.append({'name': name, 'cycle': cycle, 'size': size,
                          'key': ' '.join(f3(x / d[-1]) for x in d), 'kv': ', '.join(vec(p) for p in pts)})
            break
    return motes


def look_at(pos, tgt):
    """Orientation that looks from pos to tgt with y up (X3D cameras look down -z)."""
    fx, fy, fz = (tgt[i] - pos[i] for i in range(3)); L = math.sqrt(fx * fx + fy * fy + fz * fz); fx, fy, fz = fx / L, fy / L, fz / L
    yaw = math.atan2(-fx, -fz); pitch = math.asin(max(-1.0, min(1.0, fy)))
    return list(axis_angle(qmul(qaxis((0, 1, 0), yaw), qaxis((1, 0, 0), pitch))))


def frame_viewpoints(g):
    P = g['P']
    head = [q['xyz'] for q in P if q['part'] in ('front', 'snood', 'wattle')]
    hx0 = min(p[0] for p in head)
    hy0 = min(p[1] for p in head); hy1 = max(p[1] for p in head)
    fov = 0.7
    t = math.tan(fov / 2)
    vps = []
    # Wide: v2's, unchanged (16:9, fieldOfView spans the height; head on the left third, network to the right edge).
    span_h = (hy1 - hy0) * 1.42
    dist = span_h / 2 / t
    half_w = span_h / 2 * 16 / 9
    cx = hx0 - 0.11 * 2 * half_w + half_w
    cy = (hy0 + hy1) / 2 + 0.05
    vps.append({'def': 'Wide', 'name': 'Wide', 'position': [cx, cy, dist], 'orientation': [0, 0, 1, 0], 'center': g['pivot'], 'fov': fov})
    ex, ey, _ = g['eye']
    # Colossus: a low, close, upward view. The head is 7.5 m tall in a headset; here it fills the frame and the graph rises behind it.
    tgt = [2.6, 1.4, 0.0]; pos = [-3.4, -8.2, 3.6]
    vps.append({'def': 'Colossus', 'name': 'Colossus', 'position': pos, 'orientation': look_at(pos, tgt), 'center': tgt, 'fov': 1.22})
    # Eye: eye to eye, from just below and in front; the graph melts into bokeh behind.
    pos = [ex - 2.2, ey - 0.9, 4.4]; tgt = [ex, ey, 0.0]
    vps.append({'def': 'EyeToEye', 'name': 'Eye', 'position': pos, 'orientation': look_at(pos, tgt), 'center': tgt, 'fov': 0.62})
    # Inside: from within the graph, looking back at the bird. The graph is the foreground, the head a gold monument at its far end.
    pos = [8.4, -2.6, 4.4]; tgt = [0.4, -0.2, 0.0]
    vps.append({'def': 'Inside', 'name': 'Inside the graph', 'position': pos, 'orientation': look_at(pos, tgt), 'center': tgt, 'fov': 0.95})
    # Flywheel: along the axis of the first wheel, looking through it at the head.
    rings = g['kg'].get('loops', [])
    if rings and rings[0].get('ring'):
        rg = rings[0]['ring']; c = rg['center']; nrm = rg['normal']
        sgn = 1.0 if nrm[2] >= 0 else -1.0
        pos = [c[0] + sgn * nrm[0] * rg['radius'] * 2.6, c[1] + sgn * nrm[1] * rg['radius'] * 2.6 + 0.4, c[2] + sgn * nrm[2] * rg['radius'] * 2.6]
        vps.append({'def': 'Flywheel', 'name': 'Flywheel', 'position': pos, 'orientation': look_at(pos, c), 'center': c, 'fov': 0.9})
    # Crown: high above, looking down on the head and the spiral of wheels.
    pos = [4.0, 12.5, 7.0]; tgt = [4.8, -2.4, 0.0]
    vps.append({'def': 'Crown', 'name': 'Crown', 'position': pos, 'orientation': look_at(pos, tgt), 'center': tgt, 'fov': 1.0})
    return vps


# ----------------------------------------------------------------------------------------------
# 8. Write X3D (one writer, two builds)
# ----------------------------------------------------------------------------------------------
RIBBON_CODES = ' '.join('%s %s 0' % (f3(math.cos(k * math.pi / 8)), f3(math.sin(k * math.pi / 8))) for k in range(16))
XITE_ONLY = {'BlendMode', 'DepthMode', 'InstancedShape', 'IridescenceMaterialExtension', 'ClearcoatMaterialExtension',
             'SheenMaterialExtension', 'TransmissionMaterialExtension', 'VolumeMaterialExtension', 'DispersionMaterialExtension',
             'AnisotropyMaterialExtension', 'SpecularMaterialExtension', 'IORMaterialExtension', 'EmissiveStrengthMaterialExtension',
             'DiffuseTransmissionMaterialExtension', 'VolumeScatterMaterialExtension', 'RetroreflectionMaterialExtension',
             'SpecularGlossinessMaterial'}


def bbox_attrs(g, dz):
    """A bounding box that holds the head at rest and in flight, centred dz in front of it."""
    if 'flight_box' not in g:
        pts = [q['xyz'] for q in g['P']]
        pts += [scatter_py([float(f(v)) for v in q['xyz']], 0.5, float(f(g['xmin'])), float(f(g['xmax']))) for q in g['P']]
        lo = [min(p[k] for p in pts) - 0.6 for k in range(3)]; hi = [max(p[k] for p in pts) + 0.6 for k in range(3)]
        g['flight_box'] = (lo, hi)
    lo, hi = g['flight_box']
    head = [q['xyz'] for q in g['P'] if q['part'] != 'anchor']
    c = [(min(p[k] for p in head) + max(p[k] for p in head)) / 2 for k in range(3)]
    c[2] += dz
    sz = [2 * max(hi[k] - c[k], c[k] - lo[k]) for k in range(3)]
    return "bboxCenter='%s' bboxSize='%s'" % (vec(c), vec(sz))


def sprite_alpha(kind, size):
    """PointShader reads a sprite's kind and size from its colour's alpha (see POINT_VS)."""
    if size <= 0:
        return '0'
    return '%.4f' % (kind * 0.25 + min(size, 3.9) / 16.0)


def ribbon_faces(segs, fixed):
    """coordIndex / texCoordIndex / normalIndex for one quad per segment (see LineShader)."""
    ci, ti, ni = [], [], []
    for a, b in segs:
        fa = 4 if a in fixed else 0; fb = 4 if b in fixed else 0
        ci.append('%d %d %d %d -1' % (a, a, b, b))
        ti.append('%d %d %d %d -1' % (b, b, a, a))
        ni.append('%d %d %d %d -1' % (0 | fa | fb * 2, 1 | fa | fb * 2, 2 | fb | fa * 2, 3 | fb | fa * 2))
    return ci, ti, ni


def shader_xml(defname, vs, fs, fields, ind, consts=None):
    s = ' ' * ind
    for k, v in (consts or {}).items():
        vs = vs.replace(k, v); fs = fs.replace(k, v)
    out = [s + "<ComposedShader DEF='%s' language='GLSL'>" % defname]
    for name, typ, val in fields:
        out.append(s + "  <field name='%s' type='%s' accessType='inputOutput' value='%s'/>" % (name, typ, val))
    out.append(s + "  <ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex," + vs + "]]></ShaderPart>")
    out.append(s + "  <ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment," + fs + "]]></ShaderPart>")
    out.append(s + "</ComposedShader>")
    return '\n'.join(out)


def glow_rgba_texture(n=24):
    rows = []
    for j in range(n):
        row = []
        for i in range(n):
            x = (i + 0.5) / n * 2 - 1; y = (j + 0.5) / n * 2 - 1; r = math.hypot(x, y)
            a = min(1.0, 0.55 * max(0.0, 1 - r) ** 2 + math.exp(-(r / 0.22) ** 2))
            row.append('0xFF%02X' % int(round(a * 255)))
        rows.append(' '.join(row))
    return '%d %d 2\n' % (n, n) + '\n'.join(rows)


# Round 4: the key softbox is gold (it was 1 0.86 0.62 at strength 1.6, which overflowed the 8-bit texels to near
# white), and overflowing texels keep their hue (HUECLAMP), so the studio holds no white light for the enamel to mirror.
KEYC = tuple(json.loads(os.environ.get('GOBBLER_KEYC', '[1.0, 0.8, 0.48]'))); HUECLAMP = os.environ.get('GOBBLER_HUECLAMP', '1') == '1'
GRAD = float(os.environ.get('GOBBLER_GRAD', '0.9')); ROSE = tuple(json.loads(os.environ.get('GOBBLER_ROSE', '[1.0, 0.3, 0.4]'))); GOLDL = (1.0, 0.8, 0.45)


def studio_faces(n=16):
    """A tiny warm studio for the extras build's EnvironmentLight: six n x n PixelTextures (front -Z, back +Z, left -X,
    right +X, top +Y, bottom -Y; PixelTexture rows run bottom to top). Near-black ground; a warm key softbox high left,
    a rose softbox right, an ember strip low, all on the viewer's side, where the facets' reflections look."""
    def norm(v):
        l = math.sqrt(sum(x * x for x in v)); return [x / l for x in v]
    boxes = [(norm((-0.45, 0.55, 0.7)), 0.86, KEYC, 1.6), (norm((0.65, 0.05, 0.75)), 0.9, (1.0, 0.5, 0.42), 1.3),
             (norm((0.1, -0.55, 0.83)), 0.93, (1.0, 0.55, 0.2), 1.1), (norm((-0.2, 0.95, -0.2)), 0.8, (0.9, 0.7, 0.4), 0.7)]
    faces = {'front': lambda u, v: (u, v, -1), 'back': lambda u, v: (-u, v, 1), 'left': lambda u, v: (-1, v, -u),
             'right': lambda u, v: (1, v, u), 'top': lambda u, v: (u, 1, v), 'bottom': lambda u, v: (u, -1, -v)}
    out = {}
    for name, fn in faces.items():
        px = []
        for k in range(n):
            v = -1 + (k + 0.5) / n * 2
            for i in range(n):
                u = -1 + (i + 0.5) / n * 2
                d = norm(fn(u, v))
                c = [0.02, 0.016, 0.013]
                if d[2] > 0:                                   # the viewer's hemisphere: gold high left, rose low right
                    h = max(0.0, min(1.0, 0.5 + 0.55 * (d[1] - d[0])))
                    k = d[2] ** 1.5 * GRAD
                    c = [c[j] + k * (ROSE[j] + (GOLDL[j] - ROSE[j]) * h) for j in range(3)]
                for bd, cosr, bc, kk in boxes:
                    t = sum(a * b for a, b in zip(d, bd))
                    e = max(0.0, min(1.0, (t - cosr) / 0.04)) * kk + max(0.0, t - 0.4) ** 3 * 0.25 * kk
                    c = [c[j] + bc[j] * e for j in range(3)]
                if HUECLAMP and max(c) > 1.0:          # keep the hue where a softbox overflows: gold stays gold, not white
                    c = [x / max(c) for x in c]
                px.append('0x%02X%02X%02X' % tuple(max(0, min(255, int(round(x * 255)))) for x in c))
        out[name] = '%d %d 3 ' % (n, n) + ' '.join(px)
    return out


# The extras build's thin-film shell: base colour, roughness and resting transparency.
# Round 4. The round-3 white facet was not the studio: the scene's three DirectionalLights reached the layer, and their
# punctual highlights on a 0.08-roughness clearcoat clipped whole facets to white (with the lights off, the same layer
# at round-3 strength draws no white pixel). The lights are now scoped to the head and the network, outside the layer.
# What is left is tuned so the layer adds light without clipping, over gold that is brighter than in round 3:
#   FILMBLEND 'dscreen': BlendMode ONE_MINUS_DST_COLOR, ONE (screen blending, d + s(1 - d)). A channel can reach 1 only
#     if the layer or the gold under it is already 1 there, so enamel brightens gold toward gold, never past it to white
#     or lemon. Transparency (FILMT) no longer weights it and stays 0. 'add' is round 3's SRC_ALPHA, ONE.
#   FILMBASE: a brighter warm metal (round 3: 0.25 0.18 0.1), so facing tiles read too, not only grazing ones.
#   FILMENVI 1.6 (round 3: 2.4), and the studio's key softbox is gold and hue-clamped (KEYC, HUECLAMP).
#   FILMNDV: an enamel facet must face the camera (N.V at least this) at every angle of the sway, from the Gobbler and
#     Wide viewpoints; the round-3 white facet (N.V 0.16 at worst) and other grazing ones are left out.
#   FILMFRAC 0.42 seeds more facets (round 3: 0.3) so the count stays near round 3's after the cull.
# Measured over a sway cycle at dpr 2 (--check-shells): no pixel the layer turns white (R, G, B >= 0.92).
FILM = {'FILMBASE': '0.6 0.42 0.2', 'FILMROUGH': '0.15', 'FILMT': '0', 'FILMTHK': '320', 'FILMTMIN': '250', 'FILMIRI': '1', 'FILMCC': '0.6', 'FILMENVI': '1.6', 'FILMENVN': '16', 'FILMFRAC': '0.42', 'FILMNDV': '0.25', 'FILMBLEND': 'dscreen', 'FILMVMAX': '1', 'VELT': '0.1', 'VELBASE': '0.15 0.02 0.04', 'VELSHEEN': '0.5 0.08 0.15', 'VELSR': '0.5'}
FILM.update(json.loads(os.environ.get('GOBBLER_FILM', '{}')))


SHELLS_FILE = 'gobbler-xite-shells.x3d'
# The burn front's shape (GLSL_BURN): weight of the nape-to-beak sweep, and frequency and weight of the two noises.
# Per facet (FacetShader): the char band runs from burnEdge CHAR0 down to CHAR1, the facet ignites from CHAR1 to 0,
# then shrinks to its centre over BURNSPAN; BURNJIT spreads neighbours apart; RIMPX is the white-hot rim in pixels.
BURN = {'SATMIN': '0.42', 'BURNU': '0.75', 'BURNF1': '1.1', 'BURNW1': '0.32', 'BURNF2': '3.0', 'BURNW2': '0.1',
        'CHAR0': '0.13', 'CHAR1': '0.05', 'BURNSPAN': '0.2', 'BURNJIT': '0.07', 'RIMPX': '1.6'}
BURN.update(json.loads(os.environ.get('GOBBLER_BURN', '{}')))


SWAY_KEYS = 32


def sway_rotation(t):
    """The Sway clock's rotation at fraction t (the same curve SwayTurn samples), as a quaternion."""
    return qmul(qaxis((0, 1, 0), math.radians(12) * math.sin(2 * math.pi * t)), qaxis((1, 0, 0), math.radians(2.5) * math.sin(4 * math.pi * t)))


def qrot(q, v):
    r = qmul(qmul(q, (0.0, v[0], v[1], v[2])), (q[0], -q[1], -q[2], -q[3]))
    return r[1:]


def min_facing(g, tri):
    """The smallest N.V of a facet (double-sided) over the whole sway, seen from the Gobbler and Wide viewpoints."""
    P = g['P']; c0 = g['pivot']; worst = 1.0
    cams = [vp['position'] for vp in g['viewpoints'] if vp['def'] in ('Gobbler', 'Wide')]
    for k in range(SWAY_KEYS):
        q = sway_rotation(k / SWAY_KEYS)
        w = [[a + b for a, b in zip(qrot(q, [P[i]['xyz'][j] - c0[j] for j in range(3)]), c0)] for i in tri]
        e1 = [w[1][j] - w[0][j] for j in range(3)]; e2 = [w[2][j] - w[0][j] for j in range(3)]
        n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        ln = math.sqrt(sum(x * x for x in n)) or 1.0
        cen = [sum(p[j] for p in w) / 3 for j in range(3)]
        for cam in cams:
            v = [cam[j] - cen[j] for j in range(3)]; lv = math.sqrt(sum(x * x for x in v))
            worst = min(worst, abs(sum(n[j] * v[j] for j in range(3))) / (ln * lv))
    return worst


def write_shells(g):
    """The extras build's enamel layer, Inlined by gobbler-xite.x3d: X3D 4.1 (EnvironmentLight) plus X_ITE-only nodes."""
    P = g['P']; out = []; w = out.append
    frac = float(FILM['FILMFRAC']); ndv = float(FILM['FILMNDV'])
    seeded = [(t, (c, a)) for k, (t, (c, a)) in enumerate(zip(g['gold_faces'], g['gold_rgba'])) if a > 0.3 and random.Random(k * 7907 + 3).random() < frac]
    vmax = float(FILM['FILMVMAX'])
    film_faces = [t for t, (c, a) in seeded if max(c) <= vmax and min_facing(g, t) >= ndv]
    g['film_faces'] = len(film_faces); g['film_seeded'] = len(seeded)
    g['film_opaque'] = sum(1 for c, a in g['gold_rgba'] if a > 0.3)
    fc = studio_faces(int(FILM['FILMENVN']))
    w("<?xml version='1.0' encoding='UTF-8'?>")
    w("<X3D profile='Immersive' version='4.1' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.1.xsd'>")
    w("  <head>")
    w("    <component name='Shape' level='2'/>")
    w("    <component name='CubeMapTexturing' level='1'/>")
    w("    <component name='Lighting' level='3'/>")
    w("    <component name='X_ITE' level='1'/>")
    w("    <meta name='title' content='%s'/>" % SHELLS_FILE)
    w("    <meta name='description' content='The enamel layer of the PolyXandria gobbler, X_ITE extras build. gobbler-xite.x3d Inlines it over the shader-drawn bird: thin-film enamel on %d of the %d gold facets and velvet on the snood and wattle, lit only by a small studio cube map (EnvironmentLight) and blended on top of the gold.'/>" % (len(film_faces), len(g['gold_faces'])))
    w("    <meta name='x3d-build' content='X_ITE extras layer. X3D 4.1 for EnvironmentLight, plus X_ITE-only nodes (the glTF-style Iridescence, Clearcoat and Sheen material extensions, BlendMode, DepthMode) under the X_ITE component, so it does not pass the X3D 4.1 XSD. The standard build, gobbler.x3d, does not use it.'/>")
    w("    <meta name='creator' content='HagopJay'/>")
    w("    <meta name='created' content='26 October 2026 (v3; v1 and v2 of the gobbler stay as they were)'/>")
    w("  </head>")
    w("  <Scene>")
    w("    <WorldInfo title='PolyXandria gobbler, enamel layer'/>")
    w("    <Group>")
    w("      <!-- A tiny warm studio (16 px faces): gold high left, rose low right, ember below, on the viewer's side. global false:")
    w("           it lights only this Group, so the shader-drawn bird keeps its own look. The host file's lights do not reach here. -->")
    w("      <EnvironmentLight global='false' intensity='%s'>" % FILM['FILMENVI'])
    w("        <ComposedCubeMapTexture containerField='specularTexture'>")
    for face in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        w("          <PixelTexture containerField='%sTexture' image='%s'/>" % (face, fc[face]))
    w("        </ComposedCubeMapTexture>")
    w("      </EnvironmentLight>")
    w("      <!-- Velvet on the snood and wattle: a maroon sheen at the grazing edges, added on top. -->")
    w("      <Shape %s>" % bbox_attrs(g, 1.8))
    w("        <Appearance alphaMode='BLEND'>")
    w("          <PhysicalMaterial baseColor='%s' metallic='0' roughness='0.7' transparency='%s'>" % (FILM['VELBASE'], FILM['VELT']))
    w("            <SheenMaterialExtension sheenColor='%s' sheenRoughness='%s'/>" % (FILM['VELSHEEN'], FILM['VELSR']))
    w("          </PhysicalMaterial>")
    w("          <BlendMode%s sourceColorFactor='SRC_ALPHA' sourceAlphaFactor='ONE' destinationColorFactor='ONE' destinationAlphaFactor='ONE'/>" % (
        " DEF='Additive'" if FILM['FILMBLEND'] == 'add' else ''))
    w("          <DepthMode DEF='ShellDepth' depthMask='false' polygonOffset='-1 -4'/>")
    w("        </Appearance>")
    w("        <IndexedFaceSet solid='false' coordIndex='" + wrap(['%d %d %d -1' % t for t in g['red_faces']], 10, 10) + "'>")
    w("          <Coordinate DEF='HeadPoints' point='" + wrap([vec(q['xyz']) for q in P], 8, 10) + "'/>")
    w("        </IndexedFaceSet>")
    w("      </Shape>")
    w("      <!-- Thin-film enamel on %d of the %d gold facets: a seeded %d%% of the %d opaque ones (%d), less the %d that turn to a" % (
        len(film_faces), len(g['gold_faces']), round(frac * 100), g['film_opaque'], len(seeded), len(seeded) - len(film_faces)))
    w("           grazing angle somewhere in the sway. A warm metal under a %s nm film, so the studio comes back gold or rose by" % FILM['FILMTHK'])
    w("           angle, and the tiles change as the bird sways. Screen-blended over the shader's gold (ONE_MINUS_DST_COLOR, ONE):")
    w("           it brightens the gold and rolls off below white. -->")
    w("      <Shape %s>" % bbox_attrs(g, 0.6))
    w("        <Appearance alphaMode='BLEND'>")
    w("          <PhysicalMaterial baseColor='%s' metallic='1' roughness='%s' transparency='%s'>" % (FILM['FILMBASE'], FILM['FILMROUGH'], FILM['FILMT']))
    w("            <IridescenceMaterialExtension iridescence='%s' iridescenceIndexOfRefraction='1.3' iridescenceThicknessMinimum='%s' iridescenceThicknessMaximum='%s'/>" % (FILM['FILMIRI'], FILM['FILMTMIN'], FILM['FILMTHK']))
    w("            <ClearcoatMaterialExtension clearcoat='%s' clearcoatRoughness='0.08'/>" % FILM['FILMCC'])
    w("          </PhysicalMaterial>")
    if FILM['FILMBLEND'] == 'dscreen':
        w("          <BlendMode sourceColorFactor='ONE_MINUS_DST_COLOR' sourceAlphaFactor='ONE' destinationColorFactor='ONE' destinationAlphaFactor='ONE'/>")
    else:
        w("          <BlendMode USE='Additive'/>")
    w("          <DepthMode USE='ShellDepth'/>")
    w("        </Appearance>")
    w("        <IndexedFaceSet solid='false' coordIndex='" + wrap(['%d %d %d -1' % t for t in film_faces], 10, 10) + "'>")
    w("          <Coordinate USE='HeadPoints'/>")
    w("        </IndexedFaceSet>")
    w("      </Shape>")
    w("    </Group>")
    w("  </Scene>")
    w("</X3D>")
    return '\n'.join(out) + '\n'


def write_x3d(g, extras):
    P = g['P']; out = []; w = out.append
    consts = {'XMIN': f(g['xmin']) + ('.0' if '.' not in f(g['xmin']) else ''),
              'XMAX': f(g['xmax']) + ('.0' if '.' not in f(g['xmax']) else ''), 'FOCUS': '14.0',
              'QHX': '-0.075', 'QHY': '0.03', 'QNX': '0.2', 'QNY': '-0.05', 'SPIKEMIN': '2.75'}
    consts.update(BURN)
    consts.update({'LC%d' % i: 'vec3(%s)' % ', '.join(f3(x) for x in L['color']) for i, L in enumerate(LIGHTS)})
    consts.update({'POOLK': '0.05', 'POOLG': '0.9', 'POOLE': '0.8', 'LATT': '1.2', 'LITK': '0.5', 'LOOPW': '0.3', 'LOOPT': '14.0'})
    LIGHT_FIELDS = [('light%d' % i, 'SFVec3f', vec(light_pos(L, 0.0))) for i, L in enumerate(LIGHTS)]
    # Glow tuning per build. The extras build blends its glow layers (screen blending), so it keeps their halos softer
    # and the head lattice's bloom lower. The facets' gold uses the same tone constants in both builds (KNEE 0.12,
    # FGAIN 1): round 3 dimmed the extras gold (0.25, 0.93) to make room for the enamel, and the extras head read
    # duller than the standard one. The enamel layer now takes that headroom out of itself instead.
    consts.update({'KNEE': '0.12', 'LATB': '0.3', 'HALO': '0.7', 'PULSEH': '1.4', 'HEADK': '1.0', 'CORW': '0.35', 'HSAT': '2.0', 'CORG': '1.25', 'LCORE': '1.15',
                   'GLOWOUT': 'vec4(min(em, vec3(1.0)), a)', 'FGAIN': '1.0'}
                  if extras else
                  {'KNEE': '0.12', 'LATB': '0.45', 'HALO': '1.0', 'HSAT': '0.0', 'PULSEH': '2.2', 'HEADK': '1.0', 'CORW': '0.6', 'CORG': '1.3', 'LCORE': '1.1',
                   'GLOWOUT': 'vec4(min(em / max(a, 1e-3), vec3(1.0)), a)', 'FGAIN': '1.0'})
    name = 'gobbler-xite.x3d' if extras else 'gobbler.x3d'
    point_str = [vec(q['xyz']) for q in P]
    net_str = [vec(nd['xyz']) for nd in g['nodes']] + [vec(d['xyz']) for d in g['dust']]

    def additive(ind, first=False, mode='ScreenGlow'):
        """Extras only. 'ScreenGlow' (LineShader and PointShader layers) is screen blending, src + dst * (1 - src) with the
        shaders writing premultiplied colour: light adds up like additive glow but rolls off below 1 instead of
        clipping where gold lines cross gold facets. 'Additive' (embers, cornea) is plain SRC_ALPHA + ONE."""
        if not extras:
            return []
        s = ' ' * ind
        if first and mode == 'ScreenGlow':
            return [s + "<BlendMode DEF='ScreenGlow' sourceColorFactor='ONE' sourceAlphaFactor='ONE' destinationColorFactor='ONE_MINUS_SRC_COLOR' destinationAlphaFactor='ONE'/>",
                    s + "<DepthMode DEF='GlowDepth' depthMask='false'/>"]
        if first:
            return [s + "<BlendMode DEF='Additive' sourceColorFactor='SRC_ALPHA' sourceAlphaFactor='ONE' destinationColorFactor='ONE' destinationAlphaFactor='ONE'/>"]
        return [s + "<BlendMode USE='%s'/>" % mode, s + "<DepthMode USE='GlowDepth'/>"]
    w("<?xml version='1.0' encoding='UTF-8'?>")
    w("<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>")
    w("  <head>")
    w("    <component name='Shaders' level='1'/>")
    w("    <component name='Shape' level='2'/>")
    w("    <component name='ParticleSystems' level='3'/>")
    w("    <component name='Texturing3D' level='1'/>")
    if extras:
        w("    <component name='X_ITE' level='1'/>")
    w("    <meta name='title' content='%s'/>" % name)
    w("    <meta name='x3d-kg' content='nodes %d, edges %d, loops %d; graph.json built by kg/ (see GRAPH-v3.md in the release)'/>" % (len(g['nodes']), len(g['kg']['edges']), len(g['kg']['loops'])))
    w("    <meta name='description' content='The PolyXandria gobbler, version 3: the golden turkey head trails off into the PolyXandria knowledge graph. Every star is an entity, every ribbon a typed relation, every wheel a flywheel loop whose light pulses circle it. Four coloured lights move on sinusoidal paths. GLSL shaders (ComposedShader) draw the metal, the edges and the stars; TimeSensors, interpolators and ROUTEs drive their fields. No Script.'/>")
    if extras:
        w("    <meta name='x3d-build' content='X_ITE extras build. This file uses X_ITE-only nodes (BlendMode, DepthMode and the glTF-style Clearcoat and Specular material extensions, under the X_ITE component), so it is not standard X3D 4.0 and does not pass the X3D 4.0 XSD. After the intro it Inlines %s, an enamel layer in X3D 4.1 with more X_ITE-only nodes (Iridescence, Clearcoat and Sheen material extensions, BlendMode, DepthMode) and an X3D 4.1 EnvironmentLight. The standard build, gobbler.x3d, is the same scene without these nodes and without the layer; this build also tunes its glow shaders for that blending through standard fields and constants: bloom 1 (wider halos in a deeper gold, smaller motes) and softer halo constants.'/>" % SHELLS_FILE)
    else:
        w("    <meta name='x3d-build' content='Standard X3D 4.0 build. The X_ITE extras build, gobbler-xite.x3d, is the same scene plus X_ITE-only nodes and the standard switches, triggers and ROUTEs that drive them.'/>")
    w("    <meta name='creator' content='HagopJay'/>")
    w("    <meta name='created' content='26 October 2026 (v3; v1 and v2 of the gobbler stay as they were)'/>")
    w("  </head>")
    w("  <Scene>")
    w("    <WorldInfo title='PolyXandria gobbler 3' info='\"The knowledge graph of PolyXandria and the global X3D community, with its flywheel loops.\" \"Real entities carry provenance data or doc; model-recalled and simulated entities are dimmer and tagged in graph.json.\"'/>")
    w("    <Background skyColor='%s'/>" % col(GROUND))
    w("    <NavigationInfo type='\"EXAMINE\" \"FLY\" \"WALK\" \"ANY\"' headlight='false' speed='3' avatarSize='0.25 1.6 0.75' transitionType='\"ANIMATE\"' transitionTime='1.8'/>")
    w("    <!-- Wide (the default, unchanged from v2) frames the head on the left third and the graph to the right edge. Colossus, Eye, Behind,")
    w("         Flywheel and Crown are the v3 views, in metres: in a headset the head stands about 7.5 m tall. Binding any plays the assembly (see Intro). -->")
    for vp in g['viewpoints']:
        w("    <Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'/>" % (
            vp['def'], vp['name'], vec(vp['position']), ' '.join(f3(x) for x in vp['orientation']), vec(vp['center']), f3(vp['fov'])))
    w("    <Viewpoint DEF='Probe' description='Probe' position='4 -2 14' orientation='0 0 1 0' fieldOfView='0.9'/>")
    w("    <!-- The pick marker: the page moves it onto the selected node (translation), and flies the Probe viewpoint to it. Parked far below the scene until then. -->")
    w("    <Transform DEF='PickMarker' translation='0 -900 0'>")
    w("      <PointLight color='1 0.95 0.8' intensity='0.9' radius='6' attenuation='1 0 0.4'/>")
    w("      <Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='1 0.92 0.7'/></Appearance><Sphere radius='0.045'/></Shape>")
    w("      <Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='1 0.8 0.3' transparency='0.82'/></Appearance><Sphere radius='0.2' solid='false'/></Shape>")
    w("    </Transform>")
    w("")
    w("    <!-- v3: four coloured point lights on sinusoidal paths. Each has its own TimeSensor and PositionInterpolator (48 keys per period,")
    w("         centre + amplitude * sin(2 pi t / T + phase) per axis); the same value is routed to the PointLight and into the shaders as light0..3,")
    w("         so the facets, ribbons and stars are lit by exactly the lights that move. -->")
    for L in LIGHTS:
        w("    <PointLight DEF='%s' location='%s' color='%s' intensity='%s' radius='40' attenuation='1 0 0.02'/>" % (L['name'], vec(light_pos(L, 0.0)), col(L['color']), f(L['k'])))
    w("")
    w("    <!-- The sky: a sphere around the camera, coloured by direction in SkyShader (dithered, so no banding). -->")
    w("    <Transform translation='1.5 -0.8 12'>")
    w("      <Shape>")
    w("        <Appearance>")
    w("          <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GROUND))
    w(shader_xml('SkyShader', SKY_VS, SKY_FS, [], 10, consts))
    w("        </Appearance>")
    w("        <Sphere radius='60' solid='false'/>")
    w("      </Shape>")
    w("    </Transform>")
    # drifting dust
    drng = random.Random(23); dust_pts = []; dust_col = []; dust_pt = []
    for k in range(300):
        if k < 8:
            p = (drng.uniform(-3, 8), drng.uniform(-5, 3), drng.uniform(4, 8.5))
        else:
            p = (drng.uniform(-8, 11), drng.uniform(-7, 5), drng.uniform(-10, 3))
        dust_pts.append(vec(p))
        dust_col.append(col(mix(GOLD_MUTED, EMBER if drng.random() < 0.3 else GOLD_SOFT, drng.uniform(0.2, 0.7))) +
                        ' ' + sprite_alpha(2, drng.uniform(0.35, 0.8)))
    w("    <!-- Dust: 300 points that drift slowly on the GPU (PointShader, kind 2), out of focus near and far. -->")
    w("    <Shape>")
    w("      <Appearance alphaMode='BLEND'>")
    w("        <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GOLD_MUTED))
    w(shader_xml('PointShader', POINT_VS, POINT_FS, [('phase', 'SFFloat', '1'), ('time', 'SFTime', '0'), ('glow', 'SFFloat', '1'),
                                                      ('bloom', 'SFFloat', '1' if extras else '0')] + LIGHT_FIELDS, 8, consts))
    out.extend(additive(8, first=True))
    w("      </Appearance>")
    w("      <PointSet>")
    w("        <ColorRGBA color='" + wrap(dust_col, 6, 10) + "'/>")
    w("        <Coordinate point='" + wrap(dust_pts, 8, 10) + "'/>")
    w("      </PointSet>")
    w("    </Shape>")
    w("")
    # the light orbs: a glowing sprite at each light, so you can watch them move
    for L in LIGHTS:
        w("    <Transform DEF='%sOrb' translation='%s'>" % (L['name'], vec(light_pos(L, 0.0))))
        w("      <Shape>")
        w("        <Appearance alphaMode='BLEND'>")
        w("          <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(L['color']))
        w("          <ComposedShader USE='PointShader'/>")
        w("        </Appearance>")
        w("        <PointSet>")
        w("          <ColorRGBA color='%s %s'/>" % (col(L['color']), sprite_alpha(3, 3.2)))
        w("          <Coordinate point='0 0 0'/>")
        w("        </PointSet>")
        w("      </Shape>")
        w("    </Transform>")
    w("")
    w("    <Transform DEF='Bird' center='%s'>" % vec(g['pivot']))
    w("      <!-- Gobble: a short head shake at the start of a click (see GobbleShake). -->")
    w("      <Transform DEF='Gobble' center='2.2 -3.4 0'>")
    w("        <Group>")
    w("          <!-- A click on the head starts the Dissolve clock (v3: the graph is not clickable through this sensor, so a page can pick its stars). -->")
    w("          <TouchSensor DEF='Touch' description='Dissolve and reassemble'/>")
    w("          <!-- Three lights, scoped (global false) to the head here and to the network below (USE). They reach only the")
    w("               Materials (the fallback) and the cornea's PhysicalMaterial; the shaders carry their own studio.%s -->" % (
        " The enamel\n               layer sits outside their scope: their sharp highlights on its clearcoat clipped facets to white." if extras else ""))
    w("          <DirectionalLight DEF='KeyLight' global='false' direction='0.55 -0.5 -0.67' color='1 0.86 0.62' intensity='1'/>")
    w("          <DirectionalLight DEF='WarmLight' global='false' direction='-0.75 0.3 -0.6' color='1 0.48 0.2' intensity='0.6'/>")
    w("          <DirectionalLight DEF='RoseLight' global='false' direction='-0.2 0.85 0.5' color='0.75 0.2 0.3' intensity='0.45'/>")
    w("          <!-- Gold facets. HeadPoints is the one Coordinate the head's shapes share; FacetShader moves and shades them. -->")
    w("          <Shape>")
    w("            <Appearance alphaMode='BLEND'>")
    w("              <Material DEF='Facets' diffuseColor='%s' emissiveColor='0.07 0.05 0.025' specularColor='0.6 0.48 0.3' shininess='0.35' transparency='0.75'/>" % col(GOLD))
    w(shader_xml('FacetShader', FACET_VS, FACET_FS, [('phase', 'SFFloat', '1'), ('time', 'SFTime', '0'), ('scan', 'SFFloat', '-9'), ('glow', 'SFFloat', '1')] + LIGHT_FIELDS, 14, consts))
    w("            </Appearance>")
    w("            <IndexedFaceSet solid='false' colorPerVertex='false'")
    w("              coordIndex='" + wrap(['%d %d %d -1' % t for t in g['gold_faces']], 10, 16) + "'")
    w("              texCoordIndex='" + wrap(['0 1 2 -1'] * len(g['gold_faces']), 16, 16) + "'>")
    w("              <ColorRGBA color='" + wrap([col(c) + ' ' + f3(a) for c, a in g['gold_rgba']], 6, 16) + "'/>")
    w("              <Coordinate DEF='HeadPoints' point='" + wrap(point_str, 8, 16) + "'/>")
    w("              <!-- Bary: every facet's corners get (0 0), (1 0), (0 1), so FacetShader knows where it is inside its facet. -->")
    w("              <TextureCoordinate DEF='Bary' point='0 0 1 0 0 1'/>")
    w("            </IndexedFaceSet>")
    w("          </Shape>")
    w("          <!-- Snood and wattle, the turkey's maroon, on the same points and the same shader. Their bbox sits in front")
    w("               of the gold lattice's, so X_ITE draws them after it: the snood reads as one red stroke over the beak. -->")
    w("          <Shape %s>" % bbox_attrs(g, 1.75))
    w("            <Appearance alphaMode='BLEND'>")
    w("              <Material DEF='Flesh' diffuseColor='0.6 0.13 0.2' emissiveColor='0.24 0.035 0.06' specularColor='0.5 0.3 0.25' shininess='0.3' transparency='0.5'/>")
    w("              <ComposedShader USE='FacetShader'/>")
    w("            </Appearance>")
    w("            <IndexedFaceSet solid='false' colorPerVertex='false'")
    w("              coordIndex='" + wrap(['%d %d %d -1' % t for t in g['red_faces']], 10, 16) + "'")
    w("              texCoordIndex='" + wrap(['0 1 2 -1'] * len(g['red_faces']), 16, 16) + "'>")
    w("              <ColorRGBA color='" + wrap([col(c) + ' ' + f3(a) for c, a in g['red_rgba']], 6, 16) + "'/>")
    w("              <Coordinate USE='HeadPoints'/>")
    w("              <TextureCoordinate USE='Bary'/>")
    w("            </IndexedFaceSet>")
    w("          </Shape>")
    is_red = lambda r: P[r[0]]['part'] in ('snood', 'wattle') and P[r[1]]['part'] in ('snood', 'wattle')
    hr = [r for r in g['head_ribbons'] if not is_red(r)]
    rr = [r for r in g['head_ribbons'] if is_red(r)]
    rci, rti, rni = ribbon_faces([(a, b) for a, b, _, _ in rr], g['fixed'])
    ci, ti, ni = ribbon_faces([(a, b) for a, b, _, _ in hr], g['fixed'])
    w("          <!-- Edges as glowing ribbons, one quad per edge: coordIndex is this end, texCoordIndex (into a copy of")
    w("               HeadPoints) the other end, normalIndex picks the corner's code from RibbonCodes. LineShader widens them. -->")
    w("          <!-- bboxCenter sits in front of the facets' centre so X_ITE draws the glow layers after the gold. -->")
    w("          <Shape %s>" % bbox_attrs(g, 1.5))
    w("            <Appearance alphaMode='BLEND'>")
    w("              <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GOLD))
    w(shader_xml('LineShader', LINE_VS, LINE_FS, [('phase', 'SFFloat', '1'), ('time', 'SFTime', '0'), ('scan', 'SFFloat', '-9'), ('glow', 'SFFloat', '1'),
                                                  ('bloom', 'SFFloat', '1' if extras else '0')] + LIGHT_FIELDS, 14, consts))
    out.extend(additive(14))
    w("            </Appearance>")
    w("            <IndexedFaceSet solid='false' colorPerVertex='false' normalPerVertex='true'")
    w("              coordIndex='" + wrap(ci, 8, 16) + "'")
    w("              texCoordIndex='" + wrap(ti, 8, 16) + "'")
    w("              normalIndex='" + wrap(ni, 8, 16) + "'>")
    w("              <ColorRGBA color='" + wrap([col(c) + ' ' + f3(wd) for _, _, c, wd in hr], 6, 16) + "'/>")
    w("              <Coordinate USE='HeadPoints'/>")
    w("              <Normal DEF='RibbonCodes' vector='" + RIBBON_CODES + "'/>")
    w("              <TextureCoordinate3D DEF='EndPoints' point='" + wrap(point_str, 8, 16) + "'/>")
    w("            </IndexedFaceSet>")
    w("          </Shape>")
    w("          <!-- The snood's and wattle's own lattice, drawn after their facets (bbox further forward), so it glows on them. -->")
    w("          <Shape %s>" % bbox_attrs(g, 1.9))
    w("            <Appearance alphaMode='BLEND'>")
    w("              <Material diffuseColor='0 0 0' emissiveColor='0.96 0.46 0.28'/>")
    w("              <ComposedShader USE='LineShader'/>")
    out.extend(additive(14))
    w("            </Appearance>")
    w("            <IndexedFaceSet solid='false' colorPerVertex='false' normalPerVertex='true'")
    w("              coordIndex='" + wrap(rci, 8, 16) + "'")
    w("              texCoordIndex='" + wrap(rti, 8, 16) + "'")
    w("              normalIndex='" + wrap(rni, 8, 16) + "'>")
    w("              <ColorRGBA color='" + wrap([col(c) + ' ' + f3(wd) for _, _, c, wd in rr], 6, 16) + "'/>")
    w("              <Coordinate USE='HeadPoints'/>")
    w("              <Normal USE='RibbonCodes'/>")
    w("              <TextureCoordinate3D USE='EndPoints'/>")
    w("            </IndexedFaceSet>")
    w("          </Shape>")
    w("          <!-- The first edition's lattice as plain lines. Hide discards it; if the GPU path fails, X3D's fallback shows its Material. -->")
    w("          <Shape>")
    w("            <Appearance>")
    w("              <Material DEF='Lattice' diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GOLD))
    w(shader_xml('Hide', HIDE_VS, HIDE_FS, [], 14))
    w("            </Appearance>")
    w("            <IndexedLineSet coordIndex='" + wrap(['%d %d -1' % e for e in g['edges']], 12, 16) + "'>")
    w("              <Coordinate USE='HeadPoints'/>")
    w("            </IndexedLineSet>")
    w("          </Shape>")
    w("          <!-- Sparks: a point sprite on every glowing vertex (PointShader, kind 0: they fly with the dissolve). -->")
    w("          <Shape %s>" % bbox_attrs(g, 2.0))
    w("            <Appearance alphaMode='BLEND'>")
    w("              <Material diffuseColor='0 0 0' emissiveColor='1 0.88 0.62'/>")
    w("              <ComposedShader USE='PointShader'/>")
    out.extend(additive(14))
    w("            </Appearance>")
    w("            <PointSet>")
    w("              <ColorRGBA color='" + wrap([col(c) + ' ' + sprite_alpha(0, s) for c, s in g['spark']], 6, 16) + "'/>")
    w("              <Coordinate USE='HeadPoints'/>")
    w("            </PointSet>")
    w("          </Shape>")
    w("          <!-- The eye: iris, pupil, catchlights and three rings, drawn by EyeShader on one disc. -->")
    w("          <Transform DEF='Eye' translation='%s'>" % vec(g['eye']))
    w("            <Transform DEF='Lid'>")
    n = 32
    fan = ' '.join('0 %d %d -1' % (k + 1, (k + 1) % n + 1) for k in range(n))
    circle = ' '.join('%s %s 0' % (f3(0.5 * math.cos(2 * math.pi * k / n)), f3(0.5 * math.sin(2 * math.pi * k / n))) for k in range(n))
    # The eye sorts after the glow layers (bbox pulled forward), so lattice glow never washes over the iris.
    w("              <Shape bboxCenter='0 0 3' bboxSize='0.6 0.6 6.2'>")
    w("                <Appearance alphaMode='BLEND'>")
    w("                  <Material diffuseColor='0 0 0' emissiveColor='0.5 0.24 0.05' transparency='0.5'/>")
    w(shader_xml('EyeShader', EYE_VS, EYE_FS, [('phase', 'SFFloat', '1'), ('time', 'SFTime', '0')], 18))
    w("                </Appearance>")
    w("                <IndexedFaceSet solid='false' coordIndex='%s'>" % fan)
    w("                  <Coordinate point='0 0 0 %s'/>" % circle)
    w("                </IndexedFaceSet>")
    w("              </Shape>")
    if extras:
        w("              <!-- X_ITE extras: the cornea, a lacquered dome. It adds only light (additive BlendMode): a clearcoat")
        w("                   and a warm specular layer catch the three lights over the shader-drawn iris. Switched on when")
        w("                   Intro ends (ExtrasGate), so the first frame costs what the standard build's does. -->")
        w("              <Switch DEF='CorneaOn' whichChoice='-1'>")
        w("              <Transform translation='0 0 0.02' scale='1 1 0.32'>")
        w("                <Shape bboxCenter='0 0 10' bboxSize='0.5 0.5 20'>")
        w("                  <Appearance alphaMode='BLEND'>")
        w("                    <PhysicalMaterial baseColor='0 0 0' metallic='0' roughness='0.14'>")
        w("                      <ClearcoatMaterialExtension clearcoat='1' clearcoatRoughness='0.03'/>")
        w("                      <SpecularMaterialExtension specular='1' specularColor='1 0.88 0.66'/>")
        w("                    </PhysicalMaterial>")
        out.extend(additive(20, first=True, mode='Additive'))
        w("                  </Appearance>")
        w("                  <Sphere radius='0.215'/>")
        w("                </Shape>")
        w("              </Transform>")
        w("              </Switch>")
    w("            </Transform>")
    w("          </Transform>")
    hull_c, hull_t = g['hull']
    tex = glow_rgba_texture().replace('\n', '\n' + ' ' * 20)
    w("          <!-- Embers: while the facets burn, sparks stream out of the head's volume toward the network. -->")
    w("          <ParticleSystem DEF='Embers' geometryType='SPRITE' maxParticles='900' particleLifetime='2.4' lifetimeVariation='0.4'")
    w("            particleSize='0.24 0.24' colorKey='0 0.1 0.5 1' createParticles='false' enabled='false'>")
    w("            <Appearance alphaMode='BLEND'>")
    w("              <UnlitMaterial emissiveColor='1 1 1'/>")
    w("              <PixelTexture repeatS='false' repeatT='false'")
    w("                image='" + tex + "'/>")
    out.extend(additive(14, mode='Additive'))
    w("            </Appearance>")
    w("            <ColorRGBA color='1 0.96 0.82 0.4, 1 0.78 0.36 1, 1 0.42 0.12 0.85, 0.5 0.07 0.13 0'/>")
    w("            <VolumeEmitter direction='0.92 -0.3 0.25' speed='1.8' variation='0.55'")
    w("              coordIndex='" + wrap(['%d %d %d -1' % t for t in hull_t], 10, 16) + "'>")
    w("              <Coordinate point='" + wrap([vec(c) for c in hull_c], 8, 16) + "'/>")
    w("            </VolumeEmitter>")
    w("          </ParticleSystem>")
    w("        </Group>")
    w("      </Transform>")
    if extras:
        w("      <!-- X_ITE extras: the enamel layer (gobbler-xite-shells.x3d), thin-film enamel on %d of the %d gold facets and" % (g['film_faces'], len(g['gold_faces'])))
        w("           velvet on the snood and wattle, lit only by its own small studio (EnvironmentLight). It sits beside Gobble, outside")
        w("           the head lights' scope, and shakes with it (ShellShake, from GobbleShake). It loads only when the head first stands")
        w("           whole (ShellGate), so this file loads as fast as before, and it steps aside while the head burns.")
        w("           ShellsAllowed is a handle for a host page on a slow GPU: whichChoice -1 keeps the layer off. -->")
        w("      <Transform DEF='ShellShake' center='2.2 -3.4 0'>")
        w("        <Switch DEF='ShellsAllowed' whichChoice='0'>")
        w("          <Switch DEF='ShellsOn' whichChoice='-1'>")
        w("            <Inline DEF='Shells' url='\"%s\"' load='false'/>" % SHELLS_FILE)
        w("          </Switch>")
        w("        </Switch>")
        w("      </Transform>")
    # ---- network: the knowledge graph ------------------------------------------------------------
    nodes = g['nodes']; kg = g['kg']
    n_nodes = len(nodes)
    GRADE_W = {'Confirmed': 0.21, 'Likely': 0.16, 'Suspected': 0.11}
    einfo = {}
    for e in kg['edges']:
        if e['loop'] >= 0:
            continue
        k_ = (min(e['s'], e['t']), max(e['s'], e['t']))
        if k_ not in einfo or (not e.get('faint') and einfo[k_].get('faint')) or GRADE_W.get(e['grade'], 0) > GRADE_W.get(einfo[k_]['grade'], 0) and not (e.get('faint') and not einfo[k_].get('faint')):
            einfo[k_] = e
    # points: nodes, dust, then (hidden) wheel arc points and wheel centres
    net_str = [vec(nd['xyz']) for nd in nodes] + [vec(d['xyz']) for d in g['dust']]
    n_base = len(net_str)
    wheels = []                                      # per loop: arc point ids, centre id, colour
    LOOP_RGB = [(1.0, 0.86, 0.45), (0.45, 0.92, 1.0), (1.0, 0.52, 0.72), (0.70, 1.0, 0.52), (0.78, 0.62, 1.0), (1.0, 0.66, 0.34), (0.5, 1.0, 0.85), (1.0, 0.95, 0.5)]
    for li, L in enumerate(kg['loops']):
        r = L.get('ring')
        if not r or len(L['steps']) < 3:
            continue
        c = r['center']; u = r['u']; v = r['v']; R = r['radius']
        ang = []
        for sid in L['steps']:
            d_ = [nodes[sid]['xyz'][k] - c[k] for k in range(3)]
            ang.append(math.atan2(sum(d_[k] * v[k] for k in range(3)), sum(d_[k] * u[k] for k in range(3))))
        pts_id = []                                  # ring points in cycle order, including the sub-steps between nodes
        SUB = 4
        for k in range(len(L['steps'])):
            a0 = ang[k]; a1 = ang[(k + 1) % len(L['steps'])]
            while a1 <= a0:
                a1 += 2 * math.pi
            pts_id.append(L['steps'][k])
            for j in range(1, SUB + 1):
                a = a0 + (a1 - a0) * j / (SUB + 1)
                net_str.append(vec([c[q] + R * (math.cos(a) * u[q] + math.sin(a) * v[q]) for q in range(3)])); pts_id.append(len(net_str) - 1)
        net_str.append(vec(c)); cid = len(net_str) - 1
        wheels.append({'li': li, 'ids': pts_id, 'centre': cid, 'rgb': LOOP_RGB[li % len(LOOP_RGB)], 'name': L['name']})
    nci, nti, nni = ribbon_faces(g['net_edges'], set(range(len(net_str))))
    def ecol(a, b):
        e = einfo.get((min(a, b), max(a, b)))
        fam = REL_FAMILY.get(e['p'], 'knowledge') if e else 'structure'
        c = mix(REL_COLOUR[fam], mix(nodes[a]['rgb'], nodes[b]['rgb'], 0.5), 0.4)
        k = {'data': 1.0, 'doc': 0.95, 'model_recall': 0.72, 'simulated': 0.55}.get(e['prov'] if e else 'doc', 0.9)
        far = min(1.0, max(0.0, (nodes[a]['xyz'][0] + nodes[b]['xyz'][0]) / 2 - 5.0) / 12.0)
        if e and e.get('faint'):                       # star-tier tether: thin and dim
            return col(mix(c, GROUND, 0.62 + 0.2 * far)), 0.075
        return col(mix(c, GROUND, 0.3 + 0.25 * far + (1 - k) * 0.5)), GRADE_W.get(e['grade'] if e else 'Likely', 0.16)
    w("      <!-- The graph the bird trails into: one ribbon per typed relation, coloured by relation family and dimmed by provenance;")
    w("           alpha is the ribbon's width (grade). Ribbons carry light pulses toward the head; the four lights tint them as they pass. -->")
    w("      <Group>")
    w("        <DirectionalLight USE='KeyLight'/>")
    w("        <DirectionalLight USE='WarmLight'/>")
    w("        <DirectionalLight USE='RoseLight'/>")
    w("        <Shape>")
    w("          <Appearance alphaMode='BLEND'>")
    w("            <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GOLD_MUTED))
    w("            <ComposedShader USE='LineShader'/>")
    w("          </Appearance>")
    w("          <IndexedFaceSet solid='false' colorPerVertex='false' normalPerVertex='true'")
    w("            coordIndex='" + wrap(nci, 8, 14) + "'")
    w("            texCoordIndex='" + wrap(nti, 8, 14) + "'")
    w("            normalIndex='" + wrap(nni, 8, 14) + "'>")
    ecs = [ecol(a, b) for a, b in g['net_edges']]
    w("            <ColorRGBA color='" + wrap([c_ + ' ' + f3(a_) for c_, a_ in ecs], 6, 14) + "'/>")
    w("            <Coordinate DEF='NetPoints' point='" + wrap(net_str, 8, 14) + "'/>")
    w("            <Normal USE='RibbonCodes'/>")
    w("            <TextureCoordinate3D DEF='NetEnds' point='" + wrap(net_str, 8, 14) + "'/>")
    w("          </IndexedFaceSet>")
    w("        </Shape>")
    w("        <Shape>")
    w("          <Appearance>")
    w("            <Material diffuseColor='0 0 0' emissiveColor='%s'/>" % col(GOLD_MUTED))
    w("            <ComposedShader USE='Hide'/>")
    w("          </Appearance>")
    w("          <IndexedLineSet coordIndex='" + wrap(['%d %d -1' % e for e in g['net_edges']], 12, 14) + "'>")
    w("            <Coordinate USE='NetPoints'/>")
    w("          </IndexedLineSet>")
    w("        </Shape>")
    # the wheels: a ribbon per arc segment (alpha packs the loop phase, see LINE_VS), and a faint disc
    lsegs, lcols = [], []
    for wh in wheels:
        ids = wh['ids']; m = len(ids)
        for k in range(m):
            lsegs.append((ids[k], ids[(k + 1) % m]))
            q = int(100 * k / m)
            lcols.append(col(wh['rgb']) + ' %.5f' % (0.7 + 0.3 * (q + 100 * 0) / 400.0))
    if lsegs:
        lci, lti, lni = ribbon_faces(lsegs, set(range(len(net_str))))
        w("        <!-- Flywheel loops: each wheel is a ring of its steps. Its ribbons' alpha packs where each starts round the loop (LineShader decodes it),")
        w("             so two comets circle every wheel in step order. -->")
        w("        <Shape>")
        w("          <Appearance alphaMode='BLEND'>")
        w("            <Material diffuseColor='0 0 0' emissiveColor='1 0.9 0.7'/>")
        w("            <ComposedShader USE='LineShader'/>")
        w("          </Appearance>")
        w("          <IndexedFaceSet solid='false' colorPerVertex='false' normalPerVertex='true'")
        w("            coordIndex='" + wrap(lci, 8, 14) + "'")
        w("            texCoordIndex='" + wrap(lti, 8, 14) + "'")
        w("            normalIndex='" + wrap(lni, 8, 14) + "'>")
        w("            <ColorRGBA color='" + wrap(lcols, 4, 14) + "'/>")
        w("            <Coordinate USE='NetPoints'/>")
        w("            <Normal USE='RibbonCodes'/>")
        w("            <TextureCoordinate3D USE='NetEnds'/>")
        w("          </IndexedFaceSet>")
        w("        </Shape>")
        fan, fcol = [], []
        for wh in wheels:
            ids = wh['ids']
            for k in range(len(ids)):
                fan.append('%d %d %d -1' % (wh['centre'], ids[k], ids[(k + 1) % len(ids)]))
                fcol.append(col(wh['rgb']) + ' 0.045')
        w("        <!-- A faint disc in each wheel's plane. -->")
        w("        <Shape>")
        w("          <Appearance alphaMode='BLEND'>")
        w("            <UnlitMaterial emissiveColor='1 1 1'/>")
        w("          </Appearance>")
        w("          <IndexedFaceSet solid='false' colorPerVertex='false' coordIndex='" + wrap(fan, 8, 14) + "'>")
        w("            <ColorRGBA color='" + wrap(fcol, 4, 14) + "'/>")
        w("            <Coordinate USE='NetPoints'/>")
        w("          </IndexedFaceSet>")
        w("        </Shape>")
    hubs = set(g['hub_ids']); g['hubs'] = len(hubs)
    star_pt, star_col = [], []
    for k, nd in enumerate(nodes):
        star_pt.append(sprite_alpha(1, nd['sz'])); star_col.append(col(nd['rgb']))
    tw_cols = {0: (0.98, 0.8, 0.45), 1: (1, 0.92, 0.68), 2: (1, 0.58, 0.24), 3: (0.96, 0.4, 0.42)}
    for d in g['dust']:
        star_pt.append(sprite_alpha(1, d['size'] * 2.2)); star_col.append(col(tw_cols[d['group']]))
    for _ in range(n_base, len(net_str)):
        star_pt.append('0'); star_col.append('0 0 0')
    w("        <!-- Stars: one per entity (PointShader, kind 1), coloured by class, sized by weight; the %d heaviest carry spikes. Hidden points (size 0) are wheel geometry. -->" % g['hubs'])
    w("        <Shape>")
    w("          <Appearance alphaMode='BLEND'>")
    w("            <Material diffuseColor='0 0 0' emissiveColor='0.98 0.8 0.45'/>")
    w("            <ComposedShader USE='PointShader'/>")
    w("          </Appearance>")
    w("          <PointSet>")
    w("            <ColorRGBA color='" + wrap([c + ' ' + a for c, a in zip(star_col, star_pt)], 6, 14) + "'/>")
    w("            <Coordinate USE='NetPoints'/>")
    w("          </PointSet>")
    w("        </Shape>")
    w("        <!-- Motes: bright sprites that run along graph edges into the head. -->")
    for k, m in enumerate(g['motes']):
        if k == 0:
            w("        <Transform DEF='%s' scale='0 0 0'>" % m['name'])
            w("          <Shape DEF='MoteSprite'>")
            w("            <Appearance alphaMode='BLEND'>")
            w("              <Material diffuseColor='0 0 0' emissiveColor='1 0.88 0.62'/>")
            w("              <ComposedShader USE='PointShader'/>")
            w("            </Appearance>")
            w("            <PointSet>")
            w("              <ColorRGBA color='1 0.9 0.66 %s'/>" % sprite_alpha(3, 1.6))
            w("              <Coordinate point='0 0 0'/>")
            w("            </PointSet>")
            w("          </Shape>")
            w("        </Transform>")
        else:
            w("        <Transform DEF='%s' scale='0 0 0'><Shape USE='MoteSprite'/></Transform>" % m['name'])
    w("      </Group>")
    w("    </Transform>")
    w("")
    # ---- clocks and wiring ---------------------------------------------------------------------------
    w("    <!-- Ambient sway: a slow turn about y, 12 degrees each way, with a slight nod. -->")
    w("    <TimeSensor DEF='Sway' cycleInterval='32' loop='true'/>")
    sk, sv = [], []
    for k in range(17):
        t = k / 16
        q = qmul(qaxis((0, 1, 0), math.radians(12) * math.sin(2 * math.pi * t)),
                 qaxis((1, 0, 0), math.radians(2.5) * math.sin(4 * math.pi * t)))
        sk.append(f3(t)); sv.append(' '.join(f3(x) for x in axis_angle(q)))
    w("    <OrientationInterpolator DEF='SwayTurn' key='%s'" % ' '.join(sk))
    w("      keyValue='%s'/>" % ', '.join(sv))
    w("    <ROUTE fromNode='Sway' fromField='fraction_changed' toNode='SwayTurn' toField='set_fraction'/>")
    w("    <ROUTE fromNode='SwayTurn' fromField='value_changed' toNode='Bird' toField='set_rotation'/>")
    w("")
    w("    <!-- Blink: every few seconds the eye closes for a moment. -->")
    w("    <TimeSensor DEF='Blink' cycleInterval='7.3' loop='true'/>")
    w("    <PositionInterpolator DEF='LidScale' key='0 0.955 0.97 0.985 1' keyValue='1 1 1, 1 1 1, 1 0.08 1, 1 1 1, 1 1 1'/>")
    w("    <ROUTE fromNode='Blink' fromField='fraction_changed' toNode='LidScale' toField='set_fraction'/>")
    w("    <ROUTE fromNode='LidScale' fromField='value_changed' toNode='Lid' toField='set_scale'/>")
    w("")
    w("    <!-- Twinkle's running time is every shader's clock: star twinkle, network pulses, facet glints, dust drift. -->")
    w("    <TimeSensor DEF='Twinkle' cycleInterval='7' loop='true'/>")
    for sh in ('FacetShader', 'LineShader', 'PointShader', 'EyeShader'):
        w("    <ROUTE fromNode='Twinkle' fromField='elapsedTime' toNode='%s' toField='time'/>" % sh)
    w("")
    w("    <!-- Scan: every 10 seconds a band of energy sweeps the head from beak to nape. -->")
    w("    <TimeSensor DEF='Scan' cycleInterval='10' loop='true'/>")
    w("    <ScalarInterpolator DEF='ScanSweep' key='0 0.5 1' keyValue='-4 -4 4.2'/>")
    w("    <ROUTE fromNode='Scan' fromField='fraction_changed' toNode='ScanSweep' toField='set_fraction'/>")
    w("    <ROUTE fromNode='ScanSweep' fromField='value_changed' toNode='FacetShader' toField='scan'/>")
    w("    <ROUTE fromNode='ScanSweep' fromField='value_changed' toNode='LineShader' toField='scan'/>")
    w("")
    w("    <!-- Glow: effect intensity 0 to 1 (default 1). A host page may lower it on a slow GPU: Glow.set_fraction. -->")
    w("    <ScalarInterpolator DEF='Glow' key='0 1' keyValue='0 1'/>")
    for sh in ('FacetShader', 'LineShader', 'PointShader'):
        w("    <ROUTE fromNode='Glow' fromField='value_changed' toNode='%s' toField='glow'/>" % sh)
    w("")
    w("    <!-- Motes: each runs its path, growing in and shrinking out. -->")
    for m in g['motes']:
        # The same sizes in both builds. PointShader's bloom (1 in the extras build) draws motes smaller (x0.55), since its
        # blending makes them brighter: a drifting ember, not a lens blob.
        s3 = ' '.join([f(m['size'])] * 3)
        w("    <TimeSensor DEF='%sClock' cycleInterval='%s' loop='true'/>" % (m['name'], f(m['cycle'])))
        w("    <PositionInterpolator DEF='%sPath' key='%s' keyValue='%s'/>" % (m['name'], m['key'], m['kv']))
        w("    <PositionInterpolator DEF='%sSize' key='0 0.08 0.9 1' keyValue='0 0 0, %s, %s, 0 0 0'/>" % (m['name'], s3, s3))
        w("    <ROUTE fromNode='%sClock' fromField='fraction_changed' toNode='%sPath' toField='set_fraction'/>" % (m['name'], m['name']))
        w("    <ROUTE fromNode='%sClock' fromField='fraction_changed' toNode='%sSize' toField='set_fraction'/>" % (m['name'], m['name']))
        w("    <ROUTE fromNode='%sPath' fromField='value_changed' toNode='%s' toField='set_translation'/>" % (m['name'], m['name']))
        w("    <ROUTE fromNode='%sSize' fromField='value_changed' toNode='%s' toField='set_scale'/>" % (m['name'], m['name']))
    w("")
    w("    <!-- Two clocks drive one Phase. Dissolve (a click) plays 0 to 1: burn, burst into the network, return.")
    w("         Intro (binding a viewpoint, so also at load) holds 0.5, then plays 0.5 to 1: stars assemble into the bird. -->")
    w("    <TimeSensor DEF='Dissolve' cycleInterval='6.5'/>")
    w("    <TimeSensor DEF='Intro' cycleInterval='4.4'/>")
    w("    <ScalarInterpolator DEF='IntroPhase' key='0 0.3 1' keyValue='0.5 0.5 1'/>")
    w("    <ScalarInterpolator DEF='Phase' key='0 1' keyValue='0 1'/>")
    w("    <BooleanFilter DEF='WhileAssembling'/>")
    w("    <ROUTE fromNode='Touch' fromField='touchTime' toNode='Dissolve' toField='set_startTime'/>")
    for vp in g['viewpoints']:
        w("    <ROUTE fromNode='%s' fromField='bindTime' toNode='Intro' toField='set_startTime'/>" % vp['def'])
    w("    <ROUTE fromNode='Intro' fromField='isActive' toNode='WhileAssembling' toField='set_boolean'/>")
    w("    <ROUTE fromNode='WhileAssembling' fromField='inputNegate' toNode='Touch' toField='set_enabled'/>")
    if extras:
        w("    <!-- X_ITE extras: the cornea joins when Intro ends, so the first frame compiles no PhysicalMaterial. IntroEnd")
        w("         passes only that TRUE, and ExtrasGate turns it into whichChoice 0. -->")
        w("    <BooleanFilter DEF='IntroEnd'/>")
        w("    <IntegerTrigger DEF='ExtrasGate' integerKey='0'/>")
        w("    <ROUTE fromNode='WhileAssembling' fromField='inputNegate' toNode='IntroEnd' toField='set_boolean'/>")
        w("    <ROUTE fromNode='IntroEnd' fromField='inputTrue' toNode='ExtrasGate' toField='set_boolean'/>")
        w("    <ROUTE fromNode='ExtrasGate' fromField='triggerValue' toNode='CorneaOn' toField='whichChoice'/>")
        w("    <!-- The enamel layer shows while the head is whole: off when the burn starts (Phase 0.1), back when the facets")
        w("         are home (0.95). The first TRUE also loads it, at the end of Intro (or at once if a host page sets Phase 1). -->")
        w("    <BooleanSequencer DEF='ShellPhase' key='0 0.1 0.95' keyValue='true false true'/>")
        w("    <BooleanFilter DEF='ShellGate'/>")
        w("    <IntegerTrigger DEF='ShellsShow' integerKey='0'/>")
        w("    <IntegerTrigger DEF='ShellsHide' integerKey='-1'/>")
        w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='ShellPhase' toField='set_fraction'/>")
        w("    <ROUTE fromNode='ShellPhase' fromField='value_changed' toNode='ShellGate' toField='set_boolean'/>")
        w("    <ROUTE fromNode='ShellGate' fromField='inputTrue' toNode='Shells' toField='set_load'/>")
        w("    <ROUTE fromNode='ShellGate' fromField='inputTrue' toNode='ShellsShow' toField='set_boolean'/>")
        w("    <ROUTE fromNode='ShellGate' fromField='inputNegate' toNode='ShellsHide' toField='set_boolean'/>")
        w("    <ROUTE fromNode='ShellsShow' fromField='triggerValue' toNode='ShellsOn' toField='whichChoice'/>")
        w("    <ROUTE fromNode='ShellsHide' fromField='triggerValue' toNode='ShellsOn' toField='whichChoice'/>")
    w("    <ROUTE fromNode='Dissolve' fromField='fraction_changed' toNode='Phase' toField='set_fraction'/>")
    w("    <ROUTE fromNode='Intro' fromField='fraction_changed' toNode='IntroPhase' toField='set_fraction'/>")
    w("    <ROUTE fromNode='IntroPhase' fromField='value_changed' toNode='Phase' toField='set_fraction'/>")
    w("")
    w("    <!-- Phase is the one number the GPU needs: each vertex computes its own flight from it, each facet its burn. -->")
    for sh in ('FacetShader', 'LineShader', 'PointShader', 'EyeShader'):
        w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='%s' toField='phase'/>" % sh)
    w("    <!-- Embers stream while the facets burn (EmberWindow). The system itself runs only while Dissolve runs: the last")
    w("         ember dies (lifetime 2.4 s plus 40%) well before the 6.5 s clock ends, and a still bird draws no frames. -->")
    w("    <BooleanSequencer DEF='EmberWindow' key='0 0.09 0.42' keyValue='false true false'/>")
    w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='EmberWindow' toField='set_fraction'/>")
    w("    <ROUTE fromNode='EmberWindow' fromField='value_changed' toNode='Embers' toField='set_createParticles'/>")
    w("    <ROUTE fromNode='Dissolve' fromField='isActive' toNode='Embers' toField='set_enabled'/>")
    w("    <!-- Fallback only (a valid shader replaces the Material): the facets fade out and back. -->")
    w("    <ScalarInterpolator DEF='FacetFade' key='0 0.08 0.18 0.84 0.95 1' keyValue='0.75 0.75 1 1 0.75 0.75'/>")
    w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='FacetFade' toField='set_fraction'/>")
    w("    <ROUTE fromNode='FacetFade' fromField='value_changed' toNode='Facets' toField='set_transparency'/>")
    w("    <ROUTE fromNode='FacetFade' fromField='value_changed' toNode='Flesh' toField='set_transparency'/>")
    keys = ' '.join(f3(k) for k in EYE_KEYS)
    w("    <PositionInterpolator DEF='EyePath' key='%s' keyValue='%s'/>" % (keys, ', '.join(vec(v) for v in g['eye_path'])))
    w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='EyePath' toField='set_fraction'/>")
    w("    <ROUTE fromNode='EyePath' fromField='value_changed' toNode='Eye' toField='set_translation'/>")
    w("    <!-- Gobble: the click first shakes the head (Phase 0 to 0.09), then the burn begins. -->")
    w("    <OrientationInterpolator DEF='GobbleShake' key='0 0.015 0.03 0.045 0.06 0.075 0.09' keyValue='0 0 1 0, 0 0 1 0.14, 0 0 1 -0.12, 0 0 1 0.09, 0 0 1 -0.05, 0 0 1 0.02, 0 0 1 0'/>")
    w("    <ROUTE fromNode='Phase' fromField='value_changed' toNode='GobbleShake' toField='set_fraction'/>")
    w("    <ROUTE fromNode='GobbleShake' fromField='value_changed' toNode='Gobble' toField='set_rotation'/>")
    if extras:
        w("    <ROUTE fromNode='GobbleShake' fromField='value_changed' toNode='ShellShake' toField='set_rotation'/>")
    w("")
    w("    <!-- v3 lights: one clock and one path each. The path's value goes to the PointLight, to the glowing orb, and to the three shaders. -->")
    for i, L in enumerate(LIGHTS):
        keys = [f3(k / LIGHT_KEYS) for k in range(LIGHT_KEYS + 1)]
        vals = [vec(light_pos(L, L['T'] * k / LIGHT_KEYS)) for k in range(LIGHT_KEYS + 1)]
        w("    <TimeSensor DEF='%sClock' cycleInterval='%s' loop='true'/>" % (L['name'], f(L['T'])))
        w("    <PositionInterpolator DEF='%sPath' key='%s'" % (L['name'], ' '.join(keys)))
        w("      keyValue='%s'/>" % ', '.join(vals))
        w("    <ROUTE fromNode='%sClock' fromField='fraction_changed' toNode='%sPath' toField='set_fraction'/>" % (L['name'], L['name']))
        w("    <ROUTE fromNode='%sPath' fromField='value_changed' toNode='%s' toField='set_location'/>" % (L['name'], L['name']))
        w("    <ROUTE fromNode='%sPath' fromField='value_changed' toNode='%sOrb' toField='set_translation'/>" % (L['name'], L['name']))
        for sh in ('FacetShader', 'LineShader', 'PointShader'):
            w("    <ROUTE fromNode='%sPath' fromField='value_changed' toNode='%s' toField='light%d'/>" % (L['name'], sh, i))
    w("  </Scene>")
    w("</X3D>")
    return '\n'.join(out) + '\n'


# ----------------------------------------------------------------------------------------------
# 9. Count, validate, receipt
# ----------------------------------------------------------------------------------------------
NOT_NODES = {'ROUTE', 'field', 'fieldValue', 'IS', 'connect'}


def count_scene(xml_text):
    root = ET.fromstring(xml_text.encode('utf-8'))
    scene = root.find('Scene')
    elems = [e for e in scene.iter() if e is not scene]
    nodes = [e for e in elems if e.tag not in NOT_NODES]      # node elements, USE references included
    declared = [e for e in nodes if not e.get('USE')]         # a USE is the same node again, so it is not a new node
    xite = {}
    for e in nodes:
        if e.tag in XITE_ONLY:
            d = xite.setdefault(e.tag, {'node': e.tag, 'count': 0, 'uses': 0})
            d['uses' if e.get('USE') else 'count'] += 1
    return {
        'profile': root.get('profile'), 'x3dVersion': root.get('version'),
        'components': [{'name': c.get('name'), 'level': int(c.get('level'))} for c in root.iter('component')],
        'nodeCount': len(declared), 'defCount': sum(1 for e in nodes if e.get('DEF')),
        'useCount': sum(1 for e in nodes if e.get('USE')), 'routeCount': sum(1 for e in elems if e.tag == 'ROUTE'),
        'interpolatorCount': sum(1 for e in nodes if e.tag.endswith('Interpolator') and not e.get('USE')),
        'shaderCount': sum(1 for e in declared if e.tag == 'ComposedShader'),
        'sensors': sorted({e.tag for e in nodes if e.tag.endswith('Sensor')}),
        'xiteOnlyNodes': sorted(xite.values(), key=lambda d: d['node']),
    }


def validate(path):
    r = subprocess.run([VENV_PY, VALIDATE, path], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise SystemExit('validator failed: ' + r.stderr[-2000:])
    data = json.loads(r.stdout)
    sem = data['semantic']
    m = re.search(r'Found (\d+) error\(s\), (\d+) warning\(s\), (\d+) info\(s\)', sem)
    if m:
        errs, warns, infos = (int(x) for x in m.groups())
    elif 'All Clear' in sem and 'No semantic issues found' in sem:
        errs = warns = infos = 0
    else:
        errs = warns = infos = None
    return data, errs, warns, infos


def add_layer(r, layer):
    """The extras build Inlines its enamel layer. The card's lists and counts cover both files; each file keeps its own
    validator verdict (the layer's under 'inline')."""
    r['inline'] = layer
    merged = {}
    for src, lst in ((r['file'], r.get('xiteOnlyNodes', [])), (layer['file'], layer.get('xiteOnlyNodes', []))):
        for d in lst:
            m = merged.setdefault(d['node'], {'node': d['node'], 'count': 0, 'uses': 0, 'files': []})
            m['count'] += d['count']; m['uses'] += d['uses']; m['files'].append(src)
    r['xiteOnlyNodes'] = sorted(merged.values(), key=lambda d: d['node'])
    r['xiteOnlyNodesNote'] = 'Every X_ITE-only node type in this build, across ' + r['file'] + ' and the layer it Inlines, ' + layer['file'] + '.'
    unk = list(r['validator'].get('profile_unknown', []))
    for n in layer['validator'].get('profile_unknown', []):
        if n not in unk:
            unk.append(n)
    r['profileUnknownAllFiles'] = unk
    r['totals'] = {k: r[k] + layer[k] for k in ('bytes', 'nodeCount', 'defCount', 'useCount', 'routeCount', 'interpolatorCount', 'shaderCount')}
    r['totalsNote'] = 'Both files of the extras build: ' + r['file'] + ' and ' + layer['file'] + '.'


def receipt_for(name, text, stats, data, errs, warns, infos, extras, layer=False):
    v = {'name': VALIDATOR_NAME, 'commit': VALIDATOR_COMMIT, 'label': VALIDATOR_LABEL}
    if VALIDATOR_COMMIT_NOTE:
        v['commitNote'] = VALIDATOR_COMMIT_NOTE
    v.update({
         'xsd_valid': data['xsd_valid'], 'profile_ok': data['profile_ok'],
         'semantic_errors': errs, 'semantic_warnings': warns, 'semantic_infos': infos,
         'checks': ['X3D ' + stats['x3dVersion'] + ' XSD', 'profile and component', 'DEF/USE/ROUTE wiring']})
    if not data['xsd_valid']:
        v['xsd_errors'] = data['xsd_errors']
        # libxml2 stops at the first unexpected child under each parent, so the list is a sample whatever its length.
        # The validator wrapper also keeps at most 10 lines; say so only when this list is at that cap.
        v['xsd_errors_note'] = ('libxml2 names only the first unexpected child under each parent, so this list is a sample' +
                                (', and the validator wrapper keeps its first 10 lines' if len(data['xsd_errors']) >= 10 else '') +
                                '. xiteOnlyNodes lists every X_ITE-only node type in the file.')
    m = re.search(r'unknown=\[([^\]]*)\]', data.get('profile') or '')
    if m:
        v['profile_unknown'] = re.findall(r"'([^']+)'", m.group(1))
    sem_errs = [ln.strip() for ln in (data.get('semantic') or '').splitlines() if 'ERROR' in ln.upper() and '[' in ln]
    if errs:
        v['semantic_error_lines'] = sem_errs[:10]
    r = {
        'file': name, 'build': 'X_ITE extras' if extras else 'standard',
        'bytes': len(text.encode('utf-8')), 'x3dVersion': stats['x3dVersion'],
        'profile': stats['profile'], 'components': stats['components'], 'nodeCount': stats['nodeCount'],
        'defCount': stats['defCount'], 'useCount': stats['useCount'], 'routeCount': stats['routeCount'],
        'interpolatorCount': stats['interpolatorCount'], 'shaderCount': stats['shaderCount'], 'sensors': stats['sensors'],
        'validator': v, 'renderedWith': 'X_ITE 16.5.1', 'generated': datetime.date.today().isoformat(),
    }
    if layer:
        r['build'] = 'X_ITE extras layer'
        r['xiteOnlyNodes'] = stats['xiteOnlyNodes']
        r['inlinedBy'] = 'gobbler-xite.x3d'
    elif extras:
        r['xiteOnlyNodes'] = stats['xiteOnlyNodes']
        r['standardBuild'] = 'gobbler.x3d'
    else:
        r['extrasBuild'] = 'gobbler-xite.x3d'
    return r


def main():
    """python3 build_gobbler_v3.py --graph graph.json --out DIR [--no-validate]: writes gobbler3.x3d and its receipt."""
    global KG, GRAPH_PATH
    out_dir = OUT_DIR
    if '--out' in sys.argv:
        out_dir = os.path.abspath(sys.argv[sys.argv.index('--out') + 1])
    if '--graph' in sys.argv:
        GRAPH_PATH = os.path.abspath(sys.argv[sys.argv.index('--graph') + 1]); KG = None
    g = build()
    g['motes'] = plan_motes(g)
    g['viewpoints'] = frame_viewpoints(g)
    os.makedirs(out_dir, exist_ok=True)
    name = 'gobbler3.x3d'
    text = write_x3d(g, False)
    path = os.path.join(out_dir, name)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    stats = count_scene(text)
    print('wrote', name, len(text.encode('utf-8')), 'bytes;', json.dumps({k: v for k, v in stats.items() if k != 'components'}))
    print('head points', len(g['P']), 'graph nodes', len(g['nodes']), 'graph edges drawn', len(g['net_edges']), 'wheels', len(g['kg']['loops']),
          'dust', len(g['dust']), 'motes', len(g['motes']), 'spiked hubs', g['hubs'], 'viewpoints', [v['def'] for v in g['viewpoints']])
    if '--no-validate' in sys.argv:
        return
    data, errs, warns, infos = validate(path)
    print(name, 'validator:', json.dumps({'xsd_valid': data['xsd_valid'], 'profile_ok': data['profile_ok'], 'errors': errs, 'warnings': warns, 'infos': infos}))
    if not (data['xsd_valid'] and data['profile_ok'] and errs == 0 and warns == 0):
        print(data['semantic'][:3000]); print(data['xsd_errors']); print(data['profile'][:800])
        raise SystemExit('v3 build not clean: no receipt written')
    receipt = receipt_for(name, text, stats, data, errs, warns, infos, False)
    receipt['graph'] = {'nodes': len(g['nodes']), 'edges': len(g['kg']['edges']), 'loops': len(g['kg']['loops']), 'meta': g['kg'].get('meta', {})}
    receipt['extrasBuild'] = None
    with open(os.path.join(out_dir, 'gobbler3-receipt.json'), 'w', encoding='utf-8') as fh:
        json.dump(receipt, fh, indent=2); fh.write('\n')
    print('receipt written; validator', VALIDATOR_LABEL)


# --check-shells: a render check for the enamel layer (round 4). It serves the site with exhibits/gobbler/ taken from DIR,
# loads the extras build in one x3d-canvas with the hero's renderer settings (contentScale 2, multisampling 4,
# toneMapping NONE, exposure 1), freezes every clock but Sway's curve, and captures the bird at 16 points of the sway
# cycle (fraction 0 is also the reduced-motion pose) with the layer on and then off. A pixel fails when the layer makes
# it white: R, G and B all at 0.92 or more with the layer, at least 30/255 brighter in sum, and, without the layer, not
# already a light core (lowest channel under 0.8): spark and lattice cores over an enamel facet are near white anyway.
CHECK_JS = r"""
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs'; import path from 'path'; import http from 'http';
const [port, site, gob, out] = process.argv.slice(2);
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'text/plain', '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.jpg': 'image/jpeg', '.ttf': 'font/ttf', '.woff2': 'font/woff2' };
const page0 = '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0f0d0c}x3d-canvas{display:block;width:640px;height:600px}</style>' +
  '<script src="vendor/x_ite/x_ite.min.js"></script></head><body><x3d-canvas id="bird" splashScreen="false" notifications="false" contextMenu="false" cache="false" ' +
  'contentScale="2" multisampling="4" toneMapping="NONE" exposure="1" src="exhibits/gobbler/gobbler-xite.x3d"></x3d-canvas></body></html>';
const srv = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/check.html') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(page0); }
  const f = p.startsWith('/exhibits/gobbler/') ? path.join(gob, p.slice(18)) : path.join(site, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': mime[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
}).listen(+port);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await (await browser.newContext({ viewport: { width: 640, height: 600 }, deviceScaleFactor: 2 })).newPage();
page.setDefaultTimeout(300000);
await page.goto('http://127.0.0.1:' + port + '/check.html');
for (let i = 0; i < 600; i++) { if (await page.evaluate(() => { try { return !!document.getElementById('bird').browser.currentScene.getNamedNode('Phase'); } catch (e) { return false; } })) break; await page.waitForTimeout(100); }
await page.waitForTimeout(7000);
const set = (sw, on) => page.evaluate(([sw, on]) => { const sc = document.getElementById('bird').browser.currentScene, N = n => sc.getNamedNode(n);
  for (const n of ['Intro', 'Dissolve', 'Sway', 'Twinkle', 'Scan', 'Blink', 'MoteAClock', 'MoteBClock', 'MoteCClock']) N(n).enabled = false;
  N('Phase').set_fraction = 1; N('LidScale').set_fraction = 0; N('ScanSweep').set_fraction = 0; N('SwayTurn').set_fraction = sw;
  for (const s of ['FacetShader', 'LineShader', 'PointShader', 'EyeShader']) N(s).time = 3;
  N('ShellsAllowed').whichChoice = on ? 0 : -1; if (on) { N('Shells').load = true; N('ShellsOn').whichChoice = 0; } }, [sw, on]);
for (let k = 0; k < 16; k++) for (const on of [true, false]) {
  await set(k / 16, on); await page.waitForTimeout(1200);
  await page.locator('#bird').screenshot({ path: path.join(out, 'sway' + String(k).padStart(2, '0') + (on ? '-on' : '-off') + '.png') });
}
await browser.close(); srv.close();
"""


def check_shells(gob_dir):
    """Render the extras build across a sway cycle, with and without its enamel layer; fail if the layer turns any pixel white."""
    from PIL import Image
    out = os.path.join(SCRATCH, 'v2', 'gobbler-check'); os.makedirs(out, exist_ok=True)
    js = os.path.join(out, 'check.mjs')
    with open(js, 'w') as fh:
        fh.write(CHECK_JS)
    port = os.environ.get('GOBBLER_CHECK_PORT', '58914')
    r = subprocess.run(['node', js, port, os.path.join(TEASER, 'site'), os.path.abspath(gob_dir), out], capture_output=True, text=True, timeout=1500)
    if r.returncode != 0:
        raise SystemExit('check-shells: render failed: ' + r.stderr[-2000:])
    worst = 0; report = []
    for k in range(16):
        on = Image.open(os.path.join(out, 'sway%02d-on.png' % k)).convert('RGB')
        off = Image.open(os.path.join(out, 'sway%02d-off.png' % k)).convert('RGB')
        n = 0; changed = 0
        for (a, b, c), (a2, b2, c2) in zip(on.getdata(), off.getdata()):
            if (a + b + c) - (a2 + b2 + c2) > 30:
                changed += 1
                if a >= 235 and b >= 235 and c >= 235 and min(a2, b2, c2) < 204:
                    n += 1
        worst = max(worst, n); report.append({'sway': k / 16, 'layerPixels': changed, 'whiteByLayer': n})
    print('check-shells:', json.dumps(report))
    if worst:
        raise SystemExit('check-shells FAILED: the enamel layer turns %d pixels white in its worst frame (renders in %s)' % (worst, out))
    print('check-shells passed: across 16 sway poses at dpr 2, the layer turns no pixel white (frames in %s)' % out)


def preview(g):
    from PIL import Image, ImageDraw
    P = g['P']; S = 100
    im = Image.new('RGB', (1536, 1024), tuple(int(c * 255) for c in GROUND)); d = ImageDraw.Draw(im, 'RGBA')

    def px(v):
        return (v[0] * S + PX_ORIGIN[0], PX_ORIGIN[1] - v[1] * S)
    for t in g['gold_faces']:
        d.polygon([px(P[i]['xyz']) for i in t], fill=(214, 179, 90, 25 if P[t[0]]['part'] == 'back' else 50))
    for t in g['red_faces']:
        d.polygon([px(P[i]['xyz']) for i in t], fill=(150, 30, 50, 170))
    for a, b, c, wd in g['head_ribbons']:
        d.line([px(P[a]['xyz']), px(P[b]['xyz'])], fill=tuple(int(x * 255) for x in c) + (220,), width=1 + int(wd * 3))
    for a, b in g['net_edges']:
        d.line([px(g['nodes'][a]['xyz']), px(g['nodes'][b]['xyz'])], fill=(180, 140, 70, 120), width=1)
    for i in g['glow_ids']:
        x, y = px(P[i]['xyz']); d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 230, 170, 255))
    x, y = px(g['eye']); d.ellipse([x - 19, y - 19, x + 19, y + 19], fill=(200, 110, 30, 255)); d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=(10, 5, 4, 255))
    os.makedirs(os.path.join(SCRATCH, 'v2', 'gobbler'), exist_ok=True)
    im.save(os.path.join(SCRATCH, 'v2', 'gobbler', 'preview.png'))


if __name__ == '__main__':
    main()
