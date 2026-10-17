import sys, json, re, glob, os
tree = sys.argv[1]; sys.path[0:0] = [tree + "/src", tree]
from validation.validate import validate_xml
from validation.semantic import validate_semantic
G = "/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11/results/x3d"
out = {}
for f in sorted(glob.glob(G + "/*/*/*.x3d")):
    xml = open(f, encoding="utf-8").read(); key = "/".join(f.split("/")[-3:])
    try:
        x = validate_xml(xml); sem = validate_semantic(xml)
        errs = re.findall(r"- \*\*\[([\w-]+)\]\*\*", sem.split("## Warnings")[0].split("## Info")[0]) if "## Errors" in sem else []
        out[key] = {"valid": bool(x.get("valid")) and not errs, "codes": sorted(set(errs))}
    except Exception as e:
        out[key] = {"valid": None, "codes": ["EXC:" + type(e).__name__]}
json.dump(out, open(sys.argv[2], "w"))
