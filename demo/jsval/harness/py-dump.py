"""Python reference dumper (run with python3 -I, never from inside a downloaded directory).

  python3 -I py-dump.py <fork-tree> <out.json> [<dir-of-x3d-files> ...]

Without directories: dumps the 557-body corpus (replay.json + live attempt files) keyed
"replay/<k>" and "live/<model>/<file>". With directories: dumps every *.x3d in them keyed
"<dirname>/<file>" (sorted). Each value = {"validate": validate_xml dict, "semantic": report}.
"""
import sys, os, json, glob
TREE, OUT = sys.argv[1], sys.argv[2]
sys.path[0:0] = [TREE + "/src", TREE]
from validation.validate import validate_xml
from validation.semantic import validate_semantic

bodies = {}
if len(sys.argv) > 3:
    for d in sys.argv[3:]:
        for f in sorted(glob.glob(os.path.join(d, "*.x3d"))):
            bodies[os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f)] = open(f, encoding="utf-8", errors="replace").read()
else:
    for it in json.load(open("/home/user/x3d.ml/demo/data/replay.json")):
        bodies["replay/" + it["k"]] = it["b"]
    for f in sorted(glob.glob("/home/user/x3d.ml/runs/live-2026-10-17/x3d/*/*.x3d")):
        bodies["live/" + "/".join(f.split("/")[-2:])] = open(f, encoding="utf-8", errors="replace").read()

def _call(fn, xml):
    # the fork raises on some inputs (lxml XMLSchemaValidateError for long unmatched pattern facets,
    # OverflowError in _check_gaussian_splats); keep the run going and record it as data
    try:
        return fn(xml)
    except Exception as e:  # noqa: BLE001
        return {"exception": f"{type(e).__name__}: {e}"}

out = {}
for k, xml in bodies.items():
    out[k] = {"validate": _call(validate_xml, xml), "semantic": _call(validate_semantic, xml)}
json.dump(out, open(OUT, "w"), indent=0)
print(len(out))
