"""Inject known science-vis defects into REAL scenes from the project drive and ask:
  (1) does the fork at 8dd0d3e (XSD + semantic) still call the mutant clean?   -> 'valid but wrong'
  (2) do the prototype sci checks fire on the mutant, and stay silent on the unmutated original?"""
import sys, os, re, json, math, random
SRC = sys.argv[1]
sys.path.insert(0, SRC); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lxml import etree
import sci_checks
sci_checks._bind(SRC)
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics, _PARSER

ROOT = "/mnt/project-files/"
C0 = 0.28209479177387814
splat_files = """polyxandria/landing-v2/gifts/repros/quaternion-xyzw.x3d
polyxandria/planet-scale/scenes/stage-stars-splats.x3d
polyxandria/giza/sphinx/trained/sub-restored.x3d
polyxandria/giza/sphinx/trained/sub-today.x3d
polyxandria/exhibits/heritage-pantheon/pantheon-subset-50k-x3d41.x3d
polyxandria/splat-park/v1/roundtrip/drillfield-roundtrip-mesh.x3d""".split()
nums = lambda s: [float(x) for x in re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", s)]
fmtv = lambda vs, nd=6: " ".join(f"{x:.{nd}g}" for x in vs)

def mut_sh0_rgb(gs):
    v = nums(gs.get("sphericalHarmonicsDegree0Coef0"))
    gs.set("sphericalHarmonicsDegree0Coef0", fmtv([min(1.0, max(0.0, 0.5 + C0 * x)) for x in v]))
def mut_opacity(gs):
    v = nums(gs.get("opacities")); gs.set("opacities", fmtv([x * 0.003 for x in v]))
def mut_scale_exp(gs):   # exp() applied to scales that are already linear (double conversion)
    v = nums(gs.get("scales")); gs.set("scales", fmtv([math.exp(min(x, 50.0)) for x in v]))
def mut_offset(gs):      # float64 text writer adds a UTM-like origin
    v = nums(gs.get("positions"))
    gs.set("positions", " ".join(f"{x + o:.6f}" for x, o in zip(v, [500000.0, 4100000.0, 100.0] * (len(v) // 3))))
MUTS = {"sh0_as_rgb": (mut_sh0_rgb, "splat-sh0-looks-rgb"), "opacity_x0.003": (mut_opacity, "splat-invisible-opacity"),
        "scale_exp_double": (mut_scale_exp, "splat-scale-huge"), "utm_offset_float64": (mut_offset, "float32-precision-loss")}

def checks(text):
    x = validate_xml(text)
    sem = [d for d in semantic_diagnostics(text) if d.level in ("error", "warning")]
    sci = [d for d in sci_checks.run(text, SRC) if d.level in ("error", "warning")]
    return x["valid"], sorted({d.check for d in sem}), sorted({d.check for d in sci})

rows = []
for rel in splat_files:
    text = open(ROOT + rel, encoding="utf-8").read()
    base = checks(text)
    row = {"file": rel, "bytes": len(text), "base": {"xsd": base[0], "fork_sem": base[1], "sci": base[2]}}
    for name, (fn, want) in MUTS.items():
        root = etree.fromstring(text.encode(), _PARSER)
        gs = next(root.iter("GaussianSplats", "{*}GaussianSplats"))
        fn(gs)
        mt = etree.tostring(root, encoding="unicode", xml_declaration=False)
        x, sem, sci = checks(mt)
        row[name] = {"xsd_valid": x, "fork_sem": sem, "sci": sci, "fired": want in sci}
    rows.append(row)
    print(json.dumps({k: (v if k in ("file", "bytes") else v) for k, v in row.items()})[:1400], flush=True)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutation_eval_splats.json"), "w"), indent=1)
