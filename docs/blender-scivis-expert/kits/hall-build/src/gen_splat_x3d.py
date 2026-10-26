"""Pure-python: synthetic GaussianSplats X3D 4.1 written by the bridge's own emitter (emit_x3d40._splats_xml, bridge main 482741b).
usage: gen_splat_x3d.py <bridge/source> <out.x3d> <N> <sh_degree> [seed]; prints start-tag bytes"""
import sys, importlib.util, os, numpy as np
src, out, N, deg = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
sys.path.insert(0, src)
import ir, emit_x3d40 as E
rng = np.random.default_rng(seed)
S = ir.IRGaussianSplats(name="S")
pos = (rng.normal(0, 3, (N, 3))).astype(np.float32); sc = np.exp(rng.normal(-3.5, 0.5, (N, 3))).astype(np.float32)
q = rng.normal(0, 1, (N, 4)).astype(np.float32); q /= np.linalg.norm(q, axis=1, keepdims=True); op = rng.uniform(0.05, 1, N).astype(np.float32)
S.positions = [tuple(map(float, r)) for r in pos]; S.scales = [tuple(map(float, r)) for r in sc]; S.orientations = [tuple(map(float, r)) for r in q]; S.opacities = [float(v) for v in op]
for d in range(deg + 1):
    for c in range(2 * d + 1):
        S.sh[(d, c)] = [tuple(map(float, r)) for r in (rng.normal(0, 0.3 if d else 1.0, (N, 3))).astype(np.float32)]
class D:   # minimal _DefNames stand-in
    def get(self, kind, name, prefix): return prefix + name
    def first_use(self, kind, name): return True
tag = E._splats_xml(S, D(), "  ", version="4.1")
doc = ("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.1' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.1.xsd'>\n"
       "<head><component name='GaussianSplats' level='1'/></head><Scene>\n<Viewpoint description='v' position='0 0 12'/>\n" + tag + "</Scene></X3D>\n")
open(out, "w").write(doc)
print(len(tag.encode()), len(doc.encode()), round(len(tag.encode()) / N, 1), "bytes per splat (start tag)")
