"""Mutate real mesh scenes (Color/ColorRGBA/Normal on IndexedFaceSet/PointSet etc.):
  color_short: drop the last quarter of a Color array to a whole number of tuples
  normal_x2:   scale every Normal vector by 2
For each mutant: XSD valid? fork 8dd0d3e semantic clean (no error/warning)? prototype fires?"""
import sys, os, re, json, random
SRC = sys.argv[1]
sys.path.insert(0, SRC); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lxml import etree
import sci_checks
sci_checks._bind(SRC)
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics, _PARSER
ROOT = "/mnt/project-files/"
rows = [json.loads(l) for l in open(sys.argv[2])]
cand = [r for r in rows if "error" not in r and r["bytes"] < 6_000_000 and ("attribute-count" in r.get("elig", {}) or "normal-not-unit" in r.get("elig", {}))]
seen, picked = set(), []
for r in sorted(cand, key=lambda r: r["path"]):
    if r["sha256_16"] in seen: continue
    seen.add(r["sha256_16"]); picked.append(r)
random.Random(7).shuffle(picked)
picked = picked[:60]
nums = lambda s: re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", s)
def find_color(root):
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.split("}")[-1] in ("Color", "ColorRGBA") and el.get("color") and not el.get("USE"):
            w = 4 if el.tag.endswith("RGBA") else 3
            if len(nums(el.get("color"))) >= 8 * w:
                p = el.getparent()
                if p is not None and p.tag.split("}")[-1] in ("IndexedFaceSet", "IndexedLineSet", "PointSet", "TriangleSet", "IndexedTriangleSet") and not p.get({"IndexedFaceSet":"colorIndex","IndexedLineSet":"colorIndex"}.get(p.tag.split("}")[-1], "_x"), "").strip():
                    return el, w
    return None, 0
def find_normal(root):
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.split("}")[-1] == "Normal" and el.get("vector") and not el.get("USE") and len(nums(el.get("vector"))) >= 9:
            return el
    return None
def chk(text):
    x = validate_xml(text)["valid"]
    sem = sorted({d.check for d in semantic_diagnostics(text) if d.level in ("error", "warning")})
    sci = sorted({d.check for d in sci_checks.run(text, SRC) if d.level in ("error", "warning")})
    return x, sem, sci
out = {"color_short": [], "normal_x2": [], "unmutated_flagged": 0, "files": len(picked)}
for r in picked:
    text = open(ROOT + r["path"], encoding="utf-8").read()
    base = chk(text)
    if base[2]: out["unmutated_flagged"] += 1
    root = etree.fromstring(text.encode(), _PARSER)
    el, w = find_color(root)
    if el is not None:
        v = nums(el.get("color")); keep = (len(v) * 3 // 4) // w * w
        el.set("color", " ".join(v[:keep]))
        x, sem, sci = chk(etree.tostring(root, encoding="unicode"))
        out["color_short"].append({"file": r["path"], "xsd_valid": x, "fork_flags_it": any(s in ("tuple-count","index-out-of-range","array-count") for s in sem), "sci_fires": "attribute-count" in sci})
    root = etree.fromstring(text.encode(), _PARSER)
    n = find_normal(root)
    if n is not None:
        v = [float(t) * 2 for t in nums(n.get("vector"))]
        n.set("vector", " ".join(f"{t:.6g}" for t in v))
        x, sem, sci = chk(etree.tostring(root, encoding="unicode"))
        out["normal_x2"].append({"file": r["path"], "xsd_valid": x, "fork_clean": not sem, "sci_fires": "normal-not-unit" in sci})
summ = {"files": out["files"], "unmutated_flagged": out["unmutated_flagged"],
        "color_short": {"n": len(out["color_short"]), "xsd_valid": sum(c["xsd_valid"] for c in out["color_short"]), "fork_flags": sum(c["fork_flags_it"] for c in out["color_short"]), "sci_fires": sum(c["sci_fires"] for c in out["color_short"])},
        "normal_x2": {"n": len(out["normal_x2"]), "xsd_valid": sum(c["xsd_valid"] for c in out["normal_x2"]), "fork_clean": sum(c["fork_clean"] for c in out["normal_x2"]), "sci_fires": sum(c["sci_fires"] for c in out["normal_x2"])}}
json.dump(out, open("mutation_eval_mesh.json", "w"), indent=1)
print(json.dumps(summ))
