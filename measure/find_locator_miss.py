"""Find the attribute quotes where the field locator does not land on the right node (m_corpus counted 1)."""
import sys, os, subprocess, hashlib, json
sys.path.insert(0, sys.argv[1])
import x3dtrace as T
root = sys.argv[2]
REPOS = ["x3d.ml", "x3d.loom", "x3d.demo", "x3d.docs", "x3d-blender-io", "x3d.lab", "x3d.castle"]
seen = set(); found = []
for r in REPOS:
    d = os.path.join(root, r)
    for p in subprocess.check_output(["git", "-C", d, "ls-files", "*.x3d"], text=True).splitlines():
        try:
            raw = open(os.path.join(d, p), "rb").read(); text = raw.decode("utf-8")
        except Exception:
            continue
        h = hashlib.sha256(raw).hexdigest()
        if h in seen: continue
        seen.add(h)
        if T.sniff_kind(text) != "x3d" or not text.lstrip("﻿ \t\r\n").startswith("<"): continue
        sc = T.SceneIndex(text)
        if not sc.ok: continue
        src = T.Source("scene", text, "x3d")
        byfield = {}
        for e in sc.elements:
            for a in T.INVENTORY_ATTRS:
                if a in e.attrs and not e.use:
                    byfield["%s/@%s" % (sc.xpath(e), a)] = e
        for row in T.inventory(text):
            e = byfield[row["field"]]
            a, (v, vs, ve) = row["attr"], e.attrs[row["attr"]]
            s_attr = text.rfind(a, e.start, vs)
            q = text[s_attr:ve + 1]
            if len(src.occurrences(T.lex(q, "x3d").norms)) <= 1: continue
            it = T.check_claims([{"field": row["field"], "value": v, "quote": q, "source": "scene"}], [src]).items[0]
            if it.span is None or it.span[0] != s_attr:
                found.append({"repo": r, "path": p, "field": row["field"], "attr_start": s_attr, "span": it.span, "disamb": it.disambiguated_by, "occ": it.occurrences})
                print(json.dumps(found[-1]), flush=True)
print("done", len(found))
