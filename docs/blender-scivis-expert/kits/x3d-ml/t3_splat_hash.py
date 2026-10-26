"""T3: does x3dprov (as in x3d.ML main 5379a80, copy of research/traceability-2026-10-17/x3dprov.py, 6608 B) cope with text-encoded splat scenes?
Uses synthetic splats (numpy, fixed seed). Fork validator = x3d_mcp main 8dd0d3e, validate_xml (XSD only, default parser)."""
import sys, os, time, json, hashlib
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S, S + "/fork/src"]
import numpy as np
from lxml import etree
import x3dprov as P
from validation import validate as V

rng = np.random.default_rng(7)

def fmt(a):
    return " ".join("%.6f" % v for v in a.ravel())

def splat_scene(n):
    pos = rng.uniform(-20, 40, (n, 3)); sc = rng.uniform(0.003, 0.05, (n, 3))
    q = rng.normal(size=(n, 4)); q /= np.linalg.norm(q, axis=1, keepdims=True)
    op = rng.uniform(0, 1, n); dc = rng.uniform(-1, 2, (n, 3))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<X3D profile="Immersive" version="4.1"><head><component name="GaussianSplats" level="1"/>'
            '<meta name="title" content="synthetic splats %d"/></head><Scene>'
            '<GaussianSplats positions="%s" scales="%s" orientations="%s" opacities="%s" sphericalHarmonicsDegree0Coef0="%s"/>'
            '</Scene></X3D>\n') % (n, fmt(pos), fmt(sc), fmt(q), fmt(op), fmt(dc))

rows = []
for n in (50_000, 75_000, 100_000, 500_000):
    xml = splat_scene(n)
    nbytes = len(xml.encode())
    # which hash path?
    try:
        P._parse(xml); path = "c14n"
    except etree.XMLSyntaxError as e:
        path = "text-fallback (XMLSyntaxError: %s)" % str(e)[:60]
    t = time.time(); s1 = P.add_step(xml, {"op": "ingest", "agent": "t3"}); t_add = time.time() - t
    t = time.time(); v = P.verify(s1); t_ver = time.time() - t
    # tamper: change the last digit of the last opacity (end of file region)
    i = s1.index('opacities="') + len('opacities="'); j = s1.index('"', i)
    ops = s1[i:j]; tampered = s1[:j - 1] + ("1" if ops[-1] != "1" else "2") + s1[j:]
    vt = P.verify(tampered)
    vf = V.validate_xml(xml)
    rows.append({"splats": n, "file_MB": round(nbytes / 1e6, 2), "x3dprov_hash_path": path, "add_step_s": round(t_add, 2), "verify_s": round(t_ver, 2),
                 "verify_status": v["status"], "tamper_last_digit_status": vt["status"],
                 "fork_validate_xml_valid": vf["valid"], "fork_err": (vf["errors"][0][:90] if vf["errors"] else "")})
    print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(S + "/out_t3.json", "w"), indent=1)
