"""Generate JS conformance vectors from the Python engine (the oracle).
usage: python3 -I -B make_vectors.py <engine_dir> <repos_dir> <conformance.json> <out.json>
Rows: {id, family, kind, source_text, claim:{field,value,quote}, policy:{}, expect:{...}}
Families: gaik (GAIK-derived conformance rows), prose (hand-written), real (real corpus attributes), mutated (real, then edited)
"""
import sys, os, json, random, hashlib, subprocess, re
sys.path.insert(0, sys.argv[1])
import x3dtrace as T
root, conf_path, out_path = sys.argv[2], sys.argv[3], sys.argv[4]
rng = random.Random(20261116)
rows = []

def run(claim, text, kind, policy=None):
    pol = T.TracePolicy(**(policy or {})) if policy else T.TracePolicy()
    r = T.check_claims([dict(claim, source="s")], [T.Source("s", text, kind)], pol)
    it = r.items[0]
    return {"verdict": it.verdict, "status": it.status, "value_status": it.value_status,
            "derivation": list(it.derivation), "occurrences": it.occurrences,
            "span": list(it.span) if it.span else None, "note": it.note}

def add(family, kind, text, claim, policy=None):
    try:
        exp = run(claim, text, kind, policy)
    except Exception as e:
        exp = {"error": repr(e)[:120]}
    rows.append({"id": "%s-%04d" % (family, len(rows)), "family": family, "kind": kind, "source_text": text,
                 "claim": claim, "policy": policy or {}, "expect": exp})

# 1. GAIK-derived rows
conf = json.load(open(conf_path))
for r in conf["value_status"]:
    kind = "x3d" if r.get("mode") in ("x3d", "scene") else "text"
    pol = {k: v for k, v in (r.get("policy") or {}).items() if k in T.TracePolicy.__dataclass_fields__}
    if "conversions" in pol: pol["conversions"] = tuple(pol["conversions"])
    claim = {"field": "//*[@DEF='n']/@" + (r.get("sem") or "other"), "value": r["value"], "quote": r["quote"]}
    add("gaik", kind, "Note: " + r["quote"] + " (end)", claim, pol)

# 2. prose rows
P = [
 ("radius", "2.5", "radius of 2.5 m"), ("radius", "2.5", "radius of 3 m"), ("height", "0.4", "a 40 cm tall post"),
 ("height", "0.0254", "1 inch"), ("height", "0.3048", "one foot high"), ("height", "0.3048", "1 ft high"),
 ("height", "1609.344", "1 mile"), ("height", "1000", "1 km"), ("height", "0.006", "6 mm"),
 ("rotation", "0 1 0 1.5708", "90 degrees about the vertical axis"), ("rotation", "1 0 0 1.5708", "rotate 90 degrees about the x axis"),
 ("rotation", "0 0 1 3.14159", "180° about z"), ("rotation", "0 1 0 0.7854", "45 deg around the y axis"),
 ("rotation", "0 1 0 1.5708", "turn 90 about y"), ("rotation", "0 1 0 1.5708", "turn 1.5708 rad about y"),
 ("rotation", "0 1 0 -1.5708", "turn 90 degrees about y"), ("rotation", "0 1 0 1.5708", "turn 270 degrees about y"),
 ("angle", "1.5708", "an angle of 90 degrees"), ("angle", "90", "an angle of 1.5708 radians"), ("angle", "1.5708", "an angle of 90"),
 ("transparency", "0.5", "50 % transparent"), ("transparency", "0.25", "25 percent see-through"), ("transparency", "0.3", "30%"),
 ("transparency", "50", "50 %"), ("intensity", "0.8", "intensity 80 percent"),
 ("diffuseColor", "1 0 0", "red"), ("diffuseColor", "0 0 1", "red"), ("diffuseColor", "0 1 0", "bright green"),
 ("diffuseColor", "1 0.502 0", "#ff8000"), ("diffuseColor", "1 0.502 0", "rgb(255, 128, 0)"), ("diffuseColor", "0.5 0.5 0.5", "50 % grey"),
 ("diffuseColor", "0.5 0.5 0.5", "grey"), ("diffuseColor", "0.8 0.1 0.1", "a warm red"), ("diffuseColor", "1 1 1", "white"),
 ("diffuseColor", "0 0 0", "black"), ("diffuseColor", "1 1 0", "yellow"), ("diffuseColor", "0.2 0.4 0.8", "colour 0.2 0.4 0.8"),
 ("diffuseColor", "0.2 0.4 0.8", "colour 0.8 0.4 0.2"),
 ("cycleInterval", "3", "three seconds"), ("cycleInterval", "3", "a 3 s loop"), ("cycleInterval", "0.5", "half a second"),
 ("cycleInterval", "120", "2 minutes"), ("cycleInterval", "12", "a dozen seconds"), ("radius", "7", "seven metres"),
 ("radius", "8", "seven metres"), ("size", "2 2 2", "radius 2"), ("size", "3 3 3", "uniform size 3"), ("scale", "3 3 3", "scale 3"),
 ("size", "0.4 6 0.4", "6 m tall on a 0.4 m x 0.4 m footing"), ("size", "0.4 0.4 6", "0.4 0.4 6"), ("size", "1 2 3", "1 2 3"),
 ("size", "1 2 3", "3 2 1"), ("size", "123", "scale 1 2 3"), ("translation", "3.5 0 1.2", "3,5 m east and 1,2 m north"),
 ("translation", "-3.5 0 1.2", "3,5 m east and 1,2 m north"), ("translation", "3.5 0 0", "3.5 m east"),
 ("translation", "0 0 -4", "4 m south"), ("translation", "0 2 0", "2 m up"), ("translation", "0 2 0", "2 m above the floor"),
 ("radius", "1234.5", "1.234,50 EUR"), ("radius", "1234.5", "1,234.50"), ("radius", "1234", "1 234 m"),
 ("radius", "5", "-5"), ("radius", "-5", "5"), ("radius", "1e-05", "1e-5"), ("radius", "0.00001", "1e-5"), ("radius", "100000", "1e5"),
 ("radius", "3.14159", "3.14159265"), ("radius", "3.1416", "3.14 m"), ("radius", "3.14", "3.1416"),
 ("DEF", "Cube1", 'DEF="Cube1"'), ("DEF", "cube1", 'DEF="Cube1"'), ("DEF", "Cube9", 'DEF="Cube1"'), ("DEF", "007", "Part 7"),
 ("name", "main hall", "the main hall"), ("name", "main hall", "the big hall"),
 ("version", "16.7.0", "X_ITE 16.7.0"), ("version", "16.7.0", 'version = "7.16.0"'), ("version", "5.8.4", "ENGINE_VERSION = 4.8.5"),
 ("version", "2.6.4", "blenderizer 2.6.4 (bl_info)"), ("version", "16.7.0", "v16.7.0"), ("date", "11.04.2025", "11.04.2025"),
 ("date", "31.12.1999", "31 December 1999"), ("date", "31.12.99", "due 31.12.99"),
]
for field, value, quote in P:
    for variant in ("exact", "padded"):
        text = quote if variant == "exact" else "As requested: " + quote + ", as before."
        add("prose", "text", text, {"field": "//*[@DEF='n']/@" + field, "value": value, "quote": quote})

# 3. real corpus attributes and mutations
repos = ["x3d.ml", "x3d.loom", "x3d.demo", "x3d.docs", "x3d-blender-io", "x3d.lab", "x3d.castle"]
files = []
for r in repos:
    d = os.path.join(root, r)
    for p in subprocess.check_output(["git", "-C", d, "ls-files", "*.x3d"], text=True).splitlines():
        files.append(os.path.join(d, p))
rng.shuffle(files)
seen, used = set(), 0
def mutate(v):
    nums = list(re.finditer(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", v))
    out = []
    if nums:
        m = nums[0]
        s = m.group(0)
        out.append(("neg", v[:m.start()] + (s[1:] if s.startswith("-") else "-" + s) + v[m.end():]))
        m2 = nums[-1]
        s2 = m2.group(0)
        if s2[-1].isdigit():
            out.append(("digit", v[:m2.end() - 1] + str((int(s2[-1]) + 1) % 10) + v[m2.end():]))
    parts = v.split()
    if len(parts) >= 2 and len(set(parts)) >= 2:
        q = parts[:]
        i, j = 0, len(q) - 1
        while i < j and q[i] == q[j]: j -= 1
        q[i], q[j] = q[j], q[i]
        out.append(("swap", " ".join(q)))
    if len(parts) >= 2:
        out.append(("drop", " ".join(parts[:-1])))
    return out
for fp in files:
    if used >= 110: break
    try:
        raw = open(fp, "rb").read(); text = raw.decode("utf-8")
    except Exception:
        continue
    h = hashlib.sha256(raw).hexdigest()
    if h in seen or len(text) > 400000: continue
    seen.add(h)
    sc = T.SceneIndex(text)
    if not sc.ok: continue
    inv = T.inventory(text)
    if not inv: continue
    used += 1
    byfield = {}
    for e in sc.elements:
        for a in T.INVENTORY_ATTRS:
            if a in e.attrs and not e.use:
                byfield["%s/@%s" % (sc.xpath(e), a)] = e
    pick = rng.sample(inv, min(4, len(inv)))
    for row in pick:
        e = byfield.get(row["field"])
        if e is None: continue
        a = row["attr"]; v, vs, ve = e.attrs[a]
        s_attr = text.rfind(a, e.start, vs)
        w0, w1 = max(0, s_attr - 350), min(len(text), ve + 350)
        win = text[w0:w1]
        quote = text[s_attr:ve + 1]
        claim = {"field": row["field"], "value": v, "quote": quote}
        add("real", "x3d", win, claim)
        for tag, mv in mutate(v)[:3]:
            add("mutated", "x3d", win, {"field": row["field"], "value": mv, "quote": quote})
print(len(rows), "rows;", {f: sum(1 for r in rows if r["family"] == f) for f in ("gaik", "prose", "real", "mutated")})
json.dump({"engine_sha256_16": hashlib.sha256(open(os.path.join(sys.argv[1], "x3dtrace.py"), "rb").read()).hexdigest()[:16],
           "python": sys.version.split()[0], "rows": rows}, open(out_path, "w"))
