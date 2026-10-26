"""T10: size of the CURRENT exporter's X3D 4.1 GaussianSplats text (float32-exact %g, x3d-blender-io 482741b) for the 133k trained set at SH0..SH3
vs PLY/SPZ/SOG. Pure Python (no bpy): ir + splat_io + emit_x3d40 from the add-on source."""
import sys, os, json, time, gzip, lzma
S = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/x3d-ml"
sys.path[:0] = [S + "/pylib", S + "/bio/source"]
import brotli
import splat_io, emit_x3d40 as E
splats = splat_io.read_ply(S + "/npm/synth133k.ply", name="S")
n = len(splats.positions)
res = {"n": n, "addon": "x3d-blender-io 482741b", "sh_degree_in_file": splats.sh_degree(), "rows": []}
for D in (0, 1, 2, 3):
    sh = {k: v for k, v in splats.sh.items() if k[0] <= D}
    class Sx:  # shallow copy with fewer SH bands
        pass
    import copy
    sp = copy.copy(splats); sp.sh = sh
    defs = E._DefNames()
    el = E._splats_xml(sp, defs, "", version="4.1")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<X3D version="4.1" profile="Immersive"><head><component name="GaussianSplats" level="1"/></head><Scene>\n'
           + el + '</Scene></X3D>\n').encode()
    t = time.time(); gz = len(gzip.compress(xml, 9)); t_gz = time.time() - t
    t = time.time(); br = len(brotli.compress(xml, quality=11, lgwin=24)); t_br = time.time() - t
    row = {"sh_degree": D, "text_raw": len(xml), "gzip9": gz, "brotli11": br, "brotli_s": round(t_br, 1), "text_B_per_splat": round(len(xml) / n, 1)}
    res["rows"].append(row); print(json.dumps(row), flush=True)
    json.dump(res, open(S + "/out_t10.json", "w"), indent=1)
