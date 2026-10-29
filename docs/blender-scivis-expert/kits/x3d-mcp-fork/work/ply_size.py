import sys, os, tempfile, json
sys.path.insert(0, "../x3d-blender-io/source")
sys.dont_write_bytecode = True
import ir, splat_io
res = {}
N = 1000
for d in range(4):
    sp = ir.IRGaussianSplats(name="t")
    for i in range(N):
        sp.positions.append((i * 0.001, 0.0, 0.0)); sp.scales.append((0.01, 0.01, 0.01))
        sp.orientations.append((0, 0, 0, 1)); sp.opacities.append(0.5)
        for dd in range(d + 1):
            for c in range(2 * dd + 1):
                sp.sh.setdefault((dd, c), []).append((0.1, 0.2, 0.3))
    p = os.path.join(tempfile.mkdtemp(), f"t{d}.ply")
    splat_io.write_ply(p, sp)
    raw = open(p, "rb").read()
    hdr_end = raw.index(b"end_header\n") + len(b"end_header\n")
    props = [l for l in raw[:hdr_end].decode().splitlines() if l.startswith("property")]
    res[f"SH{d}"] = {"file_bytes": len(raw), "header_bytes": hdr_end, "per_splat_bytes": (len(raw) - hdr_end) / N, "properties": len(props),
                     "formula_bytes": 4 * (17 + 3 * ((d + 1) ** 2 - 1)), "ten_million_GB": round(10_000_000 * (len(raw) - hdr_end) / N / 1e9, 3)}
print(json.dumps(res, indent=1))
