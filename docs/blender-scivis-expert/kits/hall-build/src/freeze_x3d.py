"""Freeze a TimeSensor-driven X3D film at one instant: every interpolator ROUTEd (directly or through chained ROUTEs) from the
clock's fraction_changed is evaluated at that fraction the way X_ITE 16.5.0 does it, and the values are written into the target
fields, so any loader (the Blender bridge, a validator, a still renderer) sees the scene as it stands at that moment.

Interpolation follows X_ITE 16.5.0 (src/x_ite/Components/Interpolation): linear for Scalar/Position/Position2D/Coordinate/Normal,
quaternion slerp (shortest arc) for Orientation, HSV for Color (X_ITE's Color3.lerp: hue along the shorter way round), and the
step rule of X3DSequencerNode for IntegerSequencer and BooleanSequencer (the last key at or below the fraction).
The clock's TimeSensor gets enabled="false" and the ROUTEs that carried the film are removed (with --keep-routes they stay).
Every Switch then keeps only its chosen child (none for whichChoice -1) and becomes a Group, because the Blender bridge imports all
of a Switch's children: v1_4-v1_6's Cycles stills showed the heavens (Switch HeavensShown, opened at bar 48.5) over the dome and in
the oculus at every station. A child whose DEFs are USEd outside it is kept, and ROUTEs left naming removed nodes are dropped
(with --keep-switches nothing changes).

usage: python3 freeze_x3d.py <in.x3d> <out.x3d> (--fraction f | --time-s t | --bar b --barmap audio/aria_barmap_provisional.json)
                             [--timesensor Film] [--keep-routes] [--keep-switches] [--report out.json]"""
import sys, json, math, argparse, re
import xml.etree.ElementTree as ET

def floats(s): return [float(x) for x in re.split(r"[\s,]+", (s or "").strip()) if x]
def fmt(v): return " ".join(("true" if x else "false") if isinstance(x, bool) else str(x) if isinstance(x, int) else ("%.6g" % x) for x in v)

def segment(keys, f):
    """-> (i0, i1, w) as X3DInterpolatorNode: clamp outside, binary search inside (keys non-decreasing)"""
    n = len(keys)
    if n == 1 or f <= keys[0]: return 0, 0, 0.0
    if f >= keys[-1]: return n - 1, n - 1, 0.0
    lo, hi = 0, n - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if keys[m] <= f: lo = m
        else: hi = m
    d = keys[hi] - keys[lo]
    return lo, hi, (0.0 if d <= 0 else (f - keys[lo]) / d)

def rgb2hsv(c):   # X_ITE Color3.getHSV (hue in radians)
    r, g, b = c; mx, mn = max(c), min(c); v = mx; d = mx - mn
    if mx != 0 and d != 0:
        s = d / mx
        h = (g - b) / d if r == mx else (2 + (b - r) / d if g == mx else 4 + (r - g) / d)
        h *= math.pi / 3
        if h < 0: h += 2 * math.pi
    else: s = h = 0.0
    return [h, s, v]

def hsv2rgb(h, s, v):   # X_ITE Color3.setHSV
    s = max(s, 0.0); v = max(v, 0.0)
    if s == 0: return [v, v, v]
    w = math.degrees(h % (2 * math.pi)) / 60; i = math.floor(w); f = w - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6]

def hsv_lerp(a, b, t):   # X_ITE Color3.lerp
    ha, sa, va = a; hb, sb, vb = b
    if sa == 0: ha = hb
    if sb == 0: hb = ha
    rng = abs(hb - ha)
    if rng <= math.pi: return [ha + t * (hb - ha), sa + t * (sb - sa), va + t * (vb - va)]
    step = (2 * math.pi - rng) * t; h = ha - step if ha < hb else ha + step
    if h < 0: h += 2 * math.pi
    elif h > 2 * math.pi: h -= 2 * math.pi
    return [h, sa + t * (sb - sa), va + t * (vb - va)]

def aa2q(r):
    x, y, z, a = r; n = math.sqrt(x * x + y * y + z * z) or 1.0; s = math.sin(a / 2)
    return [x / n * s, y / n * s, z / n * s, math.cos(a / 2)]

def q2aa(q):
    x, y, z, w = q; w = max(-1.0, min(1.0, w)); a = 2 * math.acos(w); s = math.sqrt(max(0.0, 1 - w * w))
    return [0.0, 0.0, 1.0, 0.0] if s < 1e-9 else [x / s, y / s, z / s, a]

def slerp(q0, q1, t):
    d = sum(a * b for a, b in zip(q0, q1))
    if d < 0: q1 = [-c for c in q1]; d = -d
    if d > 0.9995: q = [a + t * (b - a) for a, b in zip(q0, q1)]
    else:
        th = math.acos(d); s0 = math.sin((1 - t) * th) / math.sin(th); s1 = math.sin(t * th) / math.sin(th)
        q = [s0 * a + s1 * b for a, b in zip(q0, q1)]
    n = math.sqrt(sum(c * c for c in q)); return [c / n for c in q]

WIDTH = {"ScalarInterpolator": 1, "PositionInterpolator": 3, "PositionInterpolator2D": 2, "ColorInterpolator": 3, "OrientationInterpolator": 4}

def step(keys, f):
    """X3DSequencerNode (X_ITE 16.5.0): the last key <= f, clamped to the first and last keys"""
    if len(keys) == 1 or f <= keys[0]: return 0
    if f >= keys[-1]: return len(keys) - 1
    return max(i for i, k in enumerate(keys) if k <= f)

def evaluate(node, f):
    tag = node.tag
    if tag == "BooleanSequencer":
        keys = floats(node.get("key")); kv = (node.get("keyValue") or "").split()
        return None if not keys or not kv else [kv[min(step(keys, f), len(kv) - 1)].lower() == "true"]
    keys = floats(node.get("key")); kv = floats(node.get("keyValue"))
    if not keys: return None
    if tag == "IntegerSequencer": return [int(round(kv[min(step(keys, f), len(kv) - 1)]))]
    if tag in ("CoordinateInterpolator", "NormalInterpolator", "CoordinateInterpolator2D"):
        per = len(kv) // len(keys); i0, i1, w = segment(keys, f)
        a, b = kv[i0 * per:(i0 + 1) * per], kv[i1 * per:(i1 + 1) * per]
        return [x + w * (y - x) for x, y in zip(a, b)]
    k = WIDTH.get(tag)
    if k is None: return None
    vals = [kv[i * k:(i + 1) * k] for i in range(len(kv) // k)]
    i0, i1, w = segment(keys, f); a, b = vals[i0], vals[i1]
    if tag == "OrientationInterpolator": return a if i0 == i1 else q2aa(slerp(aa2q(a), aa2q(b), w))
    if tag == "ColorInterpolator": return a if i0 == i1 else hsv2rgb(*hsv_lerp(rgb2hsv(a), rgb2hsv(b), w))
    return [x + w * (y - x) for x, y in zip(a, b)]

def field_name(f):
    if f.startswith("set_"): f = f[4:]
    if f.endswith("_changed"): f = f[:-8]
    return f

def resolve_switches(root):
    """Keep only each Switch's chosen child and make the Switch a Group (see the module note); -> one record per Switch"""
    uses = {}
    for e in root.iter():
        if e.get("USE"): uses.setdefault(e.get("USE"), []).append(e)
    out = []
    for sw in list(root.iter("Switch")):
        k = int(float((sw.get("whichChoice") or "-1").split()[0]))
        kids = [c for c in sw if c.tag not in ("IS", "ROUTE") and not c.tag.startswith("Metadata") and c.get("containerField", "children") == "children"]
        dropped, kept = [], []
        for i, c in enumerate(kids):
            if i == k: continue
            inside = {id(e) for e in c.iter()}
            used_out = sorted(d for d in {e.get("DEF") for e in c.iter() if e.get("DEF")} if any(id(u) not in inside for u in uses.get(d, [])))
            if used_out: kept.append({"child": i, "defs_used_outside": used_out[:5]}); continue
            sw.remove(c); dropped.append(i)
        sw.tag = "Group"; sw.attrib.pop("whichChoice", None)
        out.append({"switch": sw.get("DEF"), "whichChoice": k, "children": len(kids), "dropped": dropped, "kept_for_use": kept})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--fraction", type=float); ap.add_argument("--time-s", type=float); ap.add_argument("--bar", type=float)
    ap.add_argument("--barmap"); ap.add_argument("--timesensor", default="Film"); ap.add_argument("--keep-routes", action="store_true")
    ap.add_argument("--keep-switches", action="store_true"); ap.add_argument("--report")
    a = ap.parse_args()
    tree = ET.parse(a.inp); root = tree.getroot()
    parent = {c: p for p in root.iter() for c in p}
    defs = {e.get("DEF"): e for e in root.iter() if e.get("DEF")}
    ts = defs.get(a.timesensor)
    if ts is None or ts.tag != "TimeSensor": sys.exit(f"no TimeSensor DEF={a.timesensor}")
    cyc = float(ts.get("cycleInterval", "1"))
    if a.fraction is not None: f = a.fraction
    elif a.time_s is not None: f = a.time_s / cyc
    elif a.bar is not None:                 # build_hall_v1.u_bar: played bar b of 64, linear within a bar
        bm = json.load(open(a.barmap)); T = [float(x["t"]) for x in sorted(bm["bars"], key=lambda x: x["index"])]
        T = T + [2 * T[-1] - T[-2]]; b = a.bar
        if b < 1: t = T[0] * max(b, 0.0)
        else:
            i = min(int(math.floor(b)) - 1, len(T) - 2); t = T[i] + (b - (i + 1)) * (T[i + 1] - T[i])
        f = t / cyc
    else: sys.exit("give --fraction, --time-s or --bar")
    f = max(0.0, min(1.0, f))
    routes = [e for e in root.iter("ROUTE")]
    out_of = {}
    for r in routes: out_of.setdefault((r.get("fromNode"), r.get("fromField")), []).append(r)
    report = {"in": a.inp, "timesensor": a.timesensor, "cycleInterval": cyc, "fraction": round(f, 6), "time_s": round(f * cyc, 3), "set": []}
    used = set(); queue = [(a.timesensor, "fraction_changed", [f])]; guard = 0
    while queue and guard < 100000:
        guard += 1; src, sf, val = queue.pop(0)
        for r in out_of.get((src, sf), []):
            used.add(r); dst = defs.get(r.get("toNode")); df = r.get("toField")
            if dst is None: continue
            if df == "set_fraction" and (dst.tag.endswith(("Interpolator", "Interpolator2D")) or dst.tag.endswith("Sequencer")):   # 2D: fixed 22:58Z 16 Oct (before, CoordinateInterpolator2D got a bare fraction attribute and its targets kept their first keys)
                v = evaluate(dst, val[0])
                if v is not None: queue.append((dst.get("DEF"), "value_changed", v))
                continue
            name = field_name(df); old = dst.get(name); dst.set(name, fmt(val))
            report["set"].append({"node": dst.get("DEF"), "type": dst.tag, "field": name, "value": [x if isinstance(x, (bool, int)) else round(x, 6) for x in val], "was": old})
    ts.set("enabled", "false"); ts.set("loop", "false")
    if not a.keep_routes:
        for r in used: parent[r].remove(r)
    report["routes_removed"] = 0 if a.keep_routes else len(used)
    if not a.keep_switches:
        report["switches"] = resolve_switches(root)
        live = {e.get("DEF") for e in root.iter() if e.get("DEF")}
        parent = {c: p for p in root.iter() for c in p}
        stale = [r for r in root.iter("ROUTE") if r.get("fromNode") not in live or r.get("toNode") not in live]
        for r in stale: parent[r].remove(r)
        report["routes_to_removed_nodes"] = len(stale)
    tree.write(a.out, encoding="UTF-8", xml_declaration=True)
    if a.report: json.dump(report, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("set", "switches")} | {"fields_set": len(report["set"]),
                     "switches": [(s["switch"], s["whichChoice"], s["dropped"], len(s["kept_for_use"])) for s in report.get("switches", [])]}))

if __name__ == "__main__":
    main()
