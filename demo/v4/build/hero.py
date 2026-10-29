"""HERO and RIGOK for Tether Firehose 4 (SPEC section 1 S1 item 8 hero_pick(); section 5 item 5 rigOk; section 8 step 3).
Reads demo/data/live.json (the 201 recorded chains of 17 Oct, verdicts fork@eb4b4b4, renders X_ITE 16.5.0) and the 16.5.1 pass (demo/data/renders_live_x_ite_16.5.1.json).
  demo/v4/data/hero.json   HERO[12]: hero_pick() = final attempt valid on fork@eb4b4b4, r.nb >= .05, r.nodes >= 20, one per prompt (most nodes wins), cap 12, ordered nb desc;
                           the opening scene sp-09 is moved first regardless. Fields idx (index into live.json items), m, p, c, k, pt, body (final attempt), jpg (its measured
                           192x144 frame), nb, nb151, frames, last, ok, u (chain USD), calls, nodes, codes (first-try codes), finding (first-try finding), fix (the fix the
                           validator named, when it named one), rl (characters of the report the model was sent), vms1 / vmsN (validator ms, first and final attempt), key, text.
  demo/v4/data/rigok.json  RIGOK per final scene, computed STATICALLY from the XML. A headless pass would also need "bbox finite"; without a renderer that is unknown, so
                           rigOk is false only for the static rules: any Geo* node, NavigationInfo type NONE, Viewpoint jump=false, any HAnim* node, ProximitySensor, or a body
                           lxml cannot parse. Each entry records its reasons, whether it has its own Viewpoint and a Text node.
Bodies are model output: run this with python3 -I; lxml parses with resolve_entities=False, no_network=True. Usage: python3 -I demo/v4/build/hero.py"""
import json, os, re
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
D = os.path.join(ROOT, "demo/data"); OUT_H, OUT_R = os.path.join(ROOT, "demo/v4/data/hero.json"), os.path.join(ROOT, "demo/v4/data/rigok.json")
OPENING, CAP, MIN_NB, MIN_NODES = "sp-09", 12, 0.05, 20
live = json.load(open(D + "/live.json")); items = live["items"]; r151 = json.load(open(D + "/renders_live_x_ite_16.5.1.json"))
slug = lambda m: m.replace("/", "_")
key_of = lambda it, k: f"{slug(it['m'])}/{it['p']}_a{k}.x3d"
CODE = re.compile(r"\*\*\[([\w-]+)\]\*\*")


def codes_of(a):      # the page's codesOf: "xsd" when the XSD failed, then each semantic code once
    c = [] if a["x"] else ["xsd"]
    for l in a.get("se") or []:
        m = CODE.search(l)
        if m and m.group(1) not in c: c.append(m.group(1))
    return c


def finding_of(a):    # the page's findingOf: the first finding line, markup and line number stripped, 150 chars
    l = (a.get("xe") or [""])[0] or (a.get("se") or [""])[0] or ""
    l = re.sub(r"^-\s*", "", l).replace("**", ""); l = re.sub(r"^Line \d+:\s*", "", l); l = re.sub(r"\{[^}]*\}", "", l)
    return re.sub(r"\s+", " ", l).strip()[:150]


def fix_of(a):        # the first fix the validator named (semantic "-fix" lines), or None: an XSD-only report names none
    l = (a.get("fx") or [None])[0]
    return re.sub(r"\s+", " ", CODE.sub("", re.sub(r"^-\s*", "", l))).strip()[:200] if l else None


def nb151_of(key):
    rd = r151.get(key) or {}
    if rd.get("err"): return None
    seen = [v for v in (rd.get("nonblank"), rd.get("shot")) if v is not None]
    return max(seen) if seen else 0


# ---- hero_pick()
best = {}
for idx, it in enumerate(items):
    f = it["A"][-1]; r = f["r"]
    if not (f["ok"] and not r.get("err") and (r.get("nb") or 0) >= MIN_NB and (r.get("nodes") or 0) >= MIN_NODES): continue
    if it["p"] not in best or r["nodes"] > items[best[it["p"]]]["A"][-1]["r"]["nodes"]: best[it["p"]] = idx
picked = sorted(best.values(), key=lambda i: -items[i]["A"][-1]["r"]["nb"])[:CAP]
assert any(items[i]["p"] == OPENING for i in picked), f"the opening scene {OPENING} did not make the pick"
picked.sort(key=lambda i: (items[i]["p"] != OPENING, -items[i]["A"][-1]["r"]["nb"]))
HERO = []
for idx in picked:
    it = items[idx]; a1, f = it["A"][0], it["A"][-1]; r = f["r"]; key = key_of(it, len(it["A"]))
    HERO.append({"idx": idx, "m": it["m"], "p": it["p"], "c": it["c"], "k": it["k"], "pt": it["pt"], "body": it["B"][-1], "jpg": r["jpg"], "nb": r["nb"], "nb151": nb151_of(key), "frames": r["frames"], "last": r["last"],
                 "ok": f["ok"], "u": round(sum(a["u"] for a in it["A"]), 6), "calls": len(it["A"]), "nodes": r["nodes"], "codes": codes_of(a1), "finding": finding_of(a1), "fix": fix_of(a1), "rl": a1["rl"],
                 "vms1": a1["vms"], "vmsN": f["vms"], "key": key, "text": "<Text" in it["B"][-1]})
json.dump({"rule": f"final attempt valid on fork@eb4b4b4, nb >= {MIN_NB}, nodes >= {MIN_NODES}, one per prompt (most nodes), cap {CAP}, nb desc; {OPENING} first", "items": HERO}, open(OUT_H, "w"), separators=(",", ":"), ensure_ascii=False)

# ---- RIGOK: static rules over every final body
RIG = {}; P = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, recover=False)
for idx, it in enumerate(items):
    body = it["B"][-1]; reasons = []; vp = False; text = False
    try:
        root = etree.fromstring(body.encode("utf-8"), P)
        for el in root.iter():
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag.startswith("Geo") and "Geo* node" not in reasons: reasons.append("Geo* node")
            elif tag.startswith("HAnim") and "HAnim node" not in reasons: reasons.append("HAnim node")
            elif tag == "ProximitySensor" and "ProximitySensor" not in reasons: reasons.append("ProximitySensor")
            elif tag == "NavigationInfo" and re.search(r'\bNONE\b', el.get("type", "")) and "NavigationInfo type NONE" not in reasons: reasons.append("NavigationInfo type NONE")
            elif tag in ("Viewpoint", "OrthoViewpoint"):
                vp = True
                if el.get("jump", "true").strip().lower() == "false" and "Viewpoint jump=false" not in reasons: reasons.append("Viewpoint jump=false")
            elif tag == "Text": text = True
    except etree.XMLSyntaxError as e:
        reasons.append("not well-formed XML")
    RIG[key_of(it, len(it["A"]))] = {"idx": idx, "m": it["m"], "p": it["p"], "rigOk": not reasons, "reasons": reasons, "viewpoint": vp, "text": text, "bbox": None}
json.dump({"rule": "static XML rules only (Geo*, HAnim*, ProximitySensor, NavigationInfo type NONE, Viewpoint jump=false, unparsable); bbox finiteness needs a renderer and is left null",
           "n": len(RIG), "ok": sum(1 for v in RIG.values() if v["rigOk"]), "items": RIG}, open(OUT_R, "w"), separators=(",", ":"))

print("HERO:", ", ".join(f"{h['p']} ({h['m'].split('/')[-1].split('-')[1] if '-' in h['m'] else h['m']} {h['nodes']}, {h['nb']:.2f})" for h in HERO))
op = HERO[0]; print(f"opening {op['p']}: {op['m']} nodes {op['nodes']} nb {op['nb']} nb151 {op['nb151']} calls {op['calls']} usd {op['u']} codes {op['codes']} finding '{op['finding']}' fix {op['fix']!r} rl {op['rl']} vms {op['vms1']}/{op['vmsN']}")
rc = {}
for v in RIG.values():
    for r in v["reasons"]: rc[r] = rc.get(r, 0) + 1
print(f"RIGOK: {sum(1 for v in RIG.values() if v['rigOk'])} of {len(RIG)} finals pass the static rules; reasons {rc}; own Viewpoint {sum(1 for v in RIG.values() if v['viewpoint'])}; Text nodes {sum(1 for v in RIG.values() if v['text'])}; heroes with Text {sum(1 for h in HERO if h['text'])}")
print(OUT_H, os.path.getsize(OUT_H), "B;", OUT_R, os.path.getsize(OUT_R), "B")
