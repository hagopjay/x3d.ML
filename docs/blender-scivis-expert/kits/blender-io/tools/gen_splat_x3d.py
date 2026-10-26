import sys, io
sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/repo/source")
import numpy as np
from ir import IRScene, IRInstance, IRGaussianSplats
import emit_x3d40
def gen(path, n, deg):
    rng = np.random.default_rng(1)
    s = IRGaussianSplats(name="S")
    s.positions = [tuple(map(float, p)) for p in rng.uniform(-5,5,(n,3)).astype(np.float32)]
    s.scales = [tuple(map(float, p)) for p in np.exp(rng.uniform(-8,-1,(n,3))).astype(np.float32)]
    q = rng.standard_normal((n,4)); q /= np.linalg.norm(q,axis=1,keepdims=True)
    s.orientations = [tuple(map(float, p)) for p in q.astype(np.float32)]
    s.opacities = [float(x) for x in rng.uniform(0,1,n).astype(np.float32)]
    for d in range(deg+1):
        for c in range(2*d+1):
            s.sh[(d,c)] = [tuple(map(float, p)) for p in rng.normal(0,.5,(n,3)).astype(np.float32)]
    sc = IRScene(name="t"); sc.splats.append(s)
    inst = IRInstance(source_key="SPLATS:S", object_name="S", object_type="MESH"); inst.splats_name = "S"; sc.instances.append(inst); sc.object_names.append("S")
    with open(path, "w", encoding="utf-8") as f:
        emit_x3d40.export_ir_scene(f, sc, generator="gen", version="4.1")
if __name__ == "__main__":
    for spec in sys.argv[2:]:
        n, d = map(int, spec.split(":"))
        p = f"{sys.argv[1]}/gen_n{n}_sh{d}.x3d"; gen(p, n, d)
        import os; print(p, os.path.getsize(p))
