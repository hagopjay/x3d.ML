#!/usr/bin/env python3
"""Deterministic splat fixture 'S1' (seed 1741): writes a 3DGS PLY (SH1), exports it through the x3d-blender-io add-on (bpy 5.2.3) to X3D 4.1.
usage: python -I fixture_gen.py ADDON_ROOT OUTDIR"""
import os, sys, math, json, importlib, tempfile, re
from pathlib import Path
import numpy as np
addon_root, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
C0 = 0.28209479177387814
rng = np.random.default_rng(1741)

def quat_y(a):  # w,x,y,z rotation about Y
    return np.stack([np.cos(a / 2), 0 * a, np.sin(a / 2), 0 * a], 1)
def rand_quat(n):
    q = rng.normal(size=(n, 4)); return q / np.linalg.norm(q, axis=1, keepdims=True)

P, S, Q, A, RGB, SH1 = [], [], [], [], [], []
# floor: checker of flat splats on y=0
g = np.linspace(-4, 4, 35); X, Z = np.meshgrid(g, g); X = X.ravel(); Z = Z.ravel()
n = len(X); P.append(np.c_[X, np.zeros(n), Z] + rng.normal(0, 0.01, (n, 3))); S.append(np.tile([0.17, 0.02, 0.17], (n, 1))); Q.append(quat_y(rng.uniform(0, 3.14, n)))
A.append(np.full(n, 0.9)); chk = ((np.floor(X / 0.5) + np.floor(Z / 0.5)) % 2).astype(bool)
RGB.append(np.where(chk[:, None], [0.85, 0.80, 0.70], [0.25, 0.30, 0.45])); SH1.append(np.zeros((n, 45)))
# four pillars
for sx in (-2, 2):
    for sz in (-2, 2):
        h = rng.uniform(0, 3, 150); P.append(np.c_[sx + rng.normal(0, 0.15, 150), h, sz + rng.normal(0, 0.15, 150)])
        S.append(np.tile([0.12, 0.25, 0.12], (150, 1))); Q.append(rand_quat(150)); A.append(np.full(150, 0.7))
        RGB.append(np.c_[0.9 - 0.25 * h, 0.35 + 0.2 * h, 0.2 + 0.2 * h].clip(0, 1)); SH1.append(rng.normal(0, 0.06, (150, 45)))
# translucent anisotropic blobs
n = 900; P.append(rng.normal(0, 1.4, (n, 3)) * [1, 0.6, 1] + [0, 1.4, 0]); S.append(np.exp(rng.normal(np.log(0.12), 0.5, (n, 3)))); Q.append(rand_quat(n))
A.append(rng.uniform(0.15, 0.6, n)); RGB.append(rng.uniform(0.1, 1.0, (n, 3))); SH1.append(rng.normal(0, 0.08, (n, 45)))
# small bright opaque points
n = 400; P.append(rng.uniform(-3.5, 3.5, (n, 3)) * [1, 0.8, 1] + [0, 1.5, 0]); S.append(np.full((n, 3), 0.035)); Q.append(rand_quat(n))
A.append(np.full(n, 0.95)); RGB.append(rng.uniform(0.6, 1.0, (n, 3))); SH1.append(np.zeros((n, 45)))
P, S, Q, A, RGB, SH1 = [np.concatenate(v) for v in (P, S, Q, A, RGB, SH1)]
N = len(P)
dc = (RGB - 0.5) / C0
# PLY: f_rest = channel-major: R(c0..c2), G(c0..c2), B(c0..c2); SH1 given as (coef, rgb) = (3,3) -> reshape
sh1 = SH1.reshape(N, 15, 3)              # [splat, coef, rgb]
f_rest = np.concatenate([sh1[:, :, ch] for ch in range(3)], 1)   # [R c0 c1 c2, G..., B...]
names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"] + [f"f_rest_{i}" for i in range(45)] + ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
logit = np.log(A / (1 - A))
arr = np.c_[P, np.zeros((N, 3)), dc, f_rest, logit, np.log(S), Q].astype("<f4")
assert arr.shape[1] == len(names)
ply = out / "S1_sh3.ply"
with open(ply, "wb") as f:
    f.write(("ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % N + "".join(f"property float {k}\n" for k in names) + "end_header\n").encode()); f.write(arr.tobytes())
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_fx_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
importlib.import_module("io_scene_x3d").register()
from io_scene_x3d import splat_io, import_x3d
from bpy_extras.io_utils import axis_conversion
G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()
res = {"N": N, "ply_bytes": os.path.getsize(ply)}
for tag, maxdeg in (("sh3", 3), ("sh2", 2), ("sh1", 1), ("sh0", 0)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = splat_io.read_splats(str(ply), name="S1")
    for k in [k for k in s.sh if k[0] > maxdeg]: del s.sh[k]
    o = import_x3d._build_splat_object(bpy.context.scene.collection, "S1", s); o.matrix_world = G
    xo = out / f"S1_{tag}_bridge.x3d"
    r = bpy.ops.export_scene.x3d(filepath=str(xo), x3d_version="X3D41", use_selection=False)
    res[tag] = dict(x3d=xo.name, bytes=os.path.getsize(xo), result=list(r))
print(json.dumps(res))
