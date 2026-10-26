import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
mod = register()
import numpy as np, importlib, math, json, struct
sio = importlib.import_module("io_scene_x3d.splat_io")
imp_mod = importlib.import_module("io_scene_x3d.import_x3d")
ex = importlib.import_module("io_scene_x3d.extract")
import x3d.x3d as X
print("x3d package has GaussianSplats class:", hasattr(X, "GaussianSplats"), "| AlphaMode etc.")

# 1. opacity logit sweep through splat_io read -> write
logits = np.array([-20,-16.7,-14,-13.9,-12,-8,-4,0,4,8,12,13.9,14,16.7,20], dtype=np.float32)
n = len(logits)
names = ["x","y","z","nx","ny","nz","f_dc_0","f_dc_1","f_dc_2","opacity","scale_0","scale_1","scale_2","rot_0","rot_1","rot_2","rot_3"]
data = np.zeros((n, len(names)), dtype=np.float32); data[:, 9] = logits; data[:, 13] = 1.0
data[:, 10:13] = -3.0
p = str(TMP / "sweep.ply")
with open(p, "wb") as f:
    f.write(("ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % n + "".join(f"property float {k}\n" for k in names) + "end_header\n").encode()); f.write(data.tobytes())
reset(); os.environ["X3D_SPLAT_IMPORT"] = "mesh"
obj = imp_mod._build_splat_object(bpy.context.scene.collection, "Sweep", sio.read_splats(p, name="Sweep"))
q = str(TMP / "sweep41.x3d"); exp(q, "X3D41")
print("X3D opacities text:", [ (m.group(1)) for m in [__import__('re').search(r'opacities="([^"]*)"', open(q).read())]][0][:200])
reset(); imp(q)
o2 = [o for o in bpy.data.objects][0]
ir = ex.extract_splats(o2.data, name="o")
p2 = str(TMP / "sweep_out.ply"); sio.write_ply(p2, ir)
with open(p2, "rb") as f:
    hdr = []; 
    while True:
        l = f.readline().decode().split(); hdr.append(l)
        if l[:1] == ["end_header"]: break
    cols = [h[2] for h in hdr if h[:1] == ["property"]]
    arr = np.frombuffer(f.read(), dtype=np.float32).reshape(n, len(cols))
out = arr[:, cols.index("opacity")]
print("opacity logit in -> out (X3D opacity float32 in between):")
for a, b, s in zip(logits, out, ir.opacities): print(f"   {a:8.2f} -> {b:9.4f}   opacity01={s:.9f}  err={abs(a-b):.4f}")
