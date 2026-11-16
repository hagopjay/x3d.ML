"""M-B: corpus inventory, quote ambiguity by snippet kind, world-box reach.

usage: python3 -I -B m_corpus.py <engine_dir> <repos_dir> <out.json>
Corpus: every tracked *.x3d of the seven repos below at the commit found in the clone, de-duplicated by sha256.
Counting rules are in the code comments; the output names the commit of every repo and the sha256 of x3dtrace.py.
"""
import sys, os, json, hashlib, subprocess, time, bisect, collections, statistics

sys.path.insert(0, sys.argv[1])
import x3dtrace as T

REPOS = ["x3d.ml", "x3d.loom", "x3d.demo", "x3d.docs", "x3d-blender-io", "x3d.lab", "x3d.castle"]
root = sys.argv[2]
out_path = sys.argv[3]
t0 = time.time()

files, commits = [], {}
for r in REPOS:
    d = os.path.join(root, r)
    commits[r] = subprocess.check_output(["git", "-C", d, "rev-parse", "--short=7", "HEAD"], text=True).strip()
    for p in subprocess.check_output(["git", "-C", d, "ls-files", "*.x3d"], text=True).splitlines():
        files.append((r, p))

seen, scenes, dup, notxml, unreadable = {}, [], 0, 0, 0
for r, p in files:
    try:
        raw = open(os.path.join(root, r, p), "rb").read()
        text = raw.decode("utf-8")
    except Exception:
        unreadable += 1
        continue
    h = hashlib.sha256(raw).hexdigest()
    if h in seen:
        dup += 1
        continue
    seen[h] = (r, p)
    if T.sniff_kind(text) != "x3d" or not text.lstrip("﻿ \t\r\n").startswith("<"):
        notxml += 1
        continue
    scenes.append((r, p, h, text))

agg = collections.Counter()
per_repo = collections.Counter()
amb = {k: [] for k in ("value", "attr", "tag", "attr+ctx3", "tag+ctx3")}
amb_by_sem = collections.defaultdict(lambda: {k: [0, 0] for k in amb})   # sem -> kind -> [ambiguous, total]
geom = collections.defaultdict(lambda: [0, 0])  # geometry tag -> [shapes, shapes with a box]
scene_all_boxed = scene_shapes = 0
GEOM_PRIM = {"Box", "Sphere", "Cone", "Cylinder"}
NON_GEOM = {"Appearance", "Metadata", "MetadataSet", "MetadataString", "MetadataDouble", "MetadataFloat",
            "MetadataInteger", "MetadataBoolean", "Material", "ImageTexture", "TextureTransform", "LineProperties",
            "FillProperties", "ComposedShader", "ProgramShader", "PixelTexture", "MovieTexture"}
parse_fail = 0
inv_total = 0
fullscan = []
for r, p, h, text in scenes:
    sc = T.SceneIndex(text)
    if not sc.ok:
        parse_fail += 1
        continue
    per_repo[r] += 1
    els = sc.elements
    agg["scenes"] += 1
    agg["bytes"] += len(text.encode("utf-8"))
    agg["elements"] += len(els)
    agg["attributes"] += sum(len(e.attrs) for e in els)
    agg["DEF"] += sum(1 for e in els if e.def_)
    agg["USE"] += sum(1 for e in els if e.use)
    tags = {e.tag for e in els}
    agg["with_head"] += "head" in tags
    agg["with_meta"] += "meta" in tags
    agg["with_unit"] += "unit" in tags
    agg["with_Inline"] += "Inline" in tags
    agg["with_Proto"] += ("ProtoDeclare" in tags) or ("ProtoInstance" in tags)
    agg["with_Script"] += "Script" in tags
    agg["with_x3dprov"] += any(e.tag == "meta" and e.attrs.get("name", ("",))[0].startswith("x3dprov") for e in els)

    # --- world-box reach per Shape (a Shape written inline, not a USE) ---
    ok_all = True
    ns = 0
    for e in els:
        if e.tag != "Shape" or e.use:
            continue
        g = None
        for c in e.children:
            if els[c].tag not in NON_GEOM:
                g = els[c]
                break
        gt = g.tag if g is not None else "(none)"
        if g is not None and g.use:
            gt = "USE-geometry"
        has = bool(sc.boxes_for(e))
        geom[gt][0] += 1
        geom[gt][1] += has
        ns += 1
        ok_all &= has
    if ns:
        scene_shapes += 1
        scene_all_boxed += ok_all

    # --- quote ambiguity for every inventoried attribute (not USE) ---
    src = T.Source("scene", text, "x3d")
    lx = src.lexed
    inv = T.inventory(text)
    inv_total += len(inv)
    byfield = {}
    for e in els:
        for a in T.INVENTORY_ATTRS:
            if a in e.attrs and not e.use:
                byfield["%s/@%s" % (sc.xpath(e), a)] = e
    for row in inv:
        e = byfield[row["field"]]
        a, (v, vs, ve) = row["attr"], e.attrs[row["attr"]]
        s_attr = text.rfind(a, e.start, vs)
        snippets = {"value": (vs, ve), "attr": (s_attr, ve + 1), "tag": (e.start, e.tag_end)}
        # does "first hit" (the article, GAIK) or "the field names the node" find the right place for attr="value"?
        qa = T.lex(text[s_attr:ve + 1], "x3d")
        occ_a = src.occurrences(qa.norms)
        if len(occ_a) > 1:
            agg["attr_ambiguous"] += 1
            agg["attr_first_hit_wrong"] += lx.starts[occ_a[0]] != s_attr
            rep1 = T.check_claims([{"field": row["field"], "value": v, "quote": text[s_attr:ve + 1], "source": "scene"}], [src]).items[0]
            agg["attr_field_locator_wrong"] += (rep1.span is None) or rep1.span[0] != s_attr
        sem = row["sem"] or "other"
        for kind, (a0, a1) in snippets.items():
            q = T.lex(text[a0:a1], "x3d")
            occ = src.occurrences(q.norms)
            amb[kind].append(len(occ))
            amb_by_sem[sem][kind][0] += len(occ) > 1
            amb_by_sem[sem][kind][1] += 1
            if kind in ("attr", "tag"):
                i = bisect.bisect_left(lx.starts, a0)
                n = len(q.norms)
                if lx.norms[i:i + n] != q.norms:       # lexer boundary effect: fall back to the plain count
                    run = q.norms
                else:
                    run = lx.norms[max(0, i - 3):i + n + 3]
                occ2 = src.occurrences(run)
                k2 = kind + "+ctx3"
                amb[k2].append(len(occ2))
                amb_by_sem[sem][k2][0] += len(occ2) > 1
                amb_by_sem[sem][k2][1] += 1

def stats(xs):
    if not xs:
        return {}
    return {"n": len(xs), "ambiguous": sum(1 for x in xs if x > 1), "share_ambiguous": round(sum(1 for x in xs if x > 1) / len(xs), 4),
            "max_occurrences": max(xs), "median": statistics.median(xs), "p99": sorted(xs)[int(0.99 * (len(xs) - 1))]}

res = {
    "engine_sha256": hashlib.sha256(open(os.path.join(sys.argv[1], "x3dtrace.py"), "rb").read()).hexdigest()[:16],
    "python": sys.version.split()[0],
    "commits": commits,
    "tracked_x3d_files": len(files), "unreadable": unreadable, "duplicates_dropped": dup, "not_xml_text": notxml,
    "unique_scenes_parsed_ok": agg["scenes"], "parse_failures": parse_fail,
    "per_repo_unique_parsed": dict(per_repo),
    "totals": dict(agg),
    "inventory_attributes": inv_total,
    "ambiguity_by_snippet_kind": {k: stats(v) for k, v in amb.items()},
    "ambiguity_by_semantic_class": {s: {k: {"ambiguous": c[0], "n": c[1], "share": round(c[0] / c[1], 4) if c[1] else None}
                                        for k, c in kk.items()} for s, kk in amb_by_sem.items()},
    "shape_box_reach": {g: {"shapes": c[0], "with_box": c[1], "share": round(c[1] / c[0], 4)} for g, c in
                        sorted(geom.items(), key=lambda kv: -kv[1][0])},
    "shapes_total": sum(c[0] for c in geom.values()), "shapes_with_box": sum(c[1] for c in geom.values()),
    "scenes_with_shapes": scene_shapes, "scenes_all_shapes_boxed": scene_all_boxed,
    "seconds": round(time.time() - t0, 1),
}
json.dump(res, open(out_path, "w"), indent=1)
print(json.dumps(res, indent=1))
