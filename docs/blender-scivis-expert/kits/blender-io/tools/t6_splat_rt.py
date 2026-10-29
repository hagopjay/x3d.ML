import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
mod = register()
import numpy as np, struct, gzip, time, math, json

N = int(os.environ.get("N", "5000"))
rng = np.random.default_rng(20261024)

def make_ply(path, n, sh_degree):
    rest = {0: 0, 1: 9, 2: 24, 3: 45}[sh_degree]
    names = ["x","y","z","nx","ny","nz","f_dc_0","f_dc_1","f_dc_2"] + [f"f_rest_{i}" for i in range(rest)] + ["opacity","scale_0","scale_1","scale_2","rot_0","rot_1","rot_2","rot_3"]
    data = np.zeros((n, len(names)), dtype=np.float32)
    col = {k: i for i, k in enumerate(names)}
    data[:, 0:3] = rng.uniform(-5, 5, (n, 3))
    data[:, col["f_dc_0"]:col["f_dc_0"]+3] = rng.normal(0, 1.0, (n, 3))
    for i in range(rest): data[:, col[f"f_rest_{i}"]] = rng.normal(0, 0.2, n)
    data[:, col["opacity"]] = rng.normal(0, 3.0, n)            # logit domain, as the reference trainer stores it
    data[:, col["scale_0"]:col["scale_0"]+3] = rng.uniform(-8, -1, (n, 3))   # log domain
    q = rng.standard_normal((n, 4)); q /= np.linalg.norm(q, axis=1, keepdims=True)
    data[:, col["rot_0"]:col["rot_0"]+4] = q.astype(np.float32)           # w x y z
    hdr = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % n + "".join(f"property float {k}\n" for k in names) + "end_header\n"
    with open(path, "wb") as f:
        f.write(hdr.encode()); f.write(data.tobytes())
    return names, data

def read_ply_np(path):
    with open(path, "rb") as f:
        names = []; n = 0
        while True:
            line = f.readline().decode().split()
            if line[:1] == ["element"]: n = int(line[2])
            elif line[:1] == ["property"]: names.append(line[2])
            elif line[:1] == ["end_header"]: break
        arr = np.frombuffer(f.read(), dtype=np.float32).reshape(n, len(names))
    return names, arr

def build_obj_from_ply(path, target):
    import importlib
    sio = importlib.import_module("io_scene_x3d.splat_io")
    imp_mod = importlib.import_module("io_scene_x3d.import_x3d")
    splats = sio.read_splats(path, name="Cloud")
    os.environ["X3D_SPLAT_IMPORT"] = target
    obj = imp_mod._build_splat_object(bpy.context.scene.collection, "Cloud", splats)
    return obj

def extract_ir(obj):
    import importlib
    ex = importlib.import_module("io_scene_x3d.extract")
    sn = importlib.import_module("io_scene_x3d.splat_native")
    if obj.type == "POINTCLOUD": return sn.extract_native_splats(obj.data, name="out")
    return ex.extract_splats(obj.data, name="out")

def stats(a, b):
    d = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return float(d.max()), float(d.mean())

results = []
for deg in (0, 3):
    for target in ("mesh", "pointcloud"):
        reset()
        ply0 = str(TMP / f"in_sh{deg}.ply")
        names, data = make_ply(ply0, N, deg)
        ply_bytes = os.path.getsize(ply0)
        t0 = time.time()
        obj = build_obj_from_ply(ply0, target)
        bpy.context.view_layer.update()
        p41 = str(TMP / f"sh{deg}_{target}.x3d")
        r = exp(p41, "X3D41"); assert r == {"FINISHED"}, r
        t_exp = time.time() - t0
        x3d_bytes = os.path.getsize(p41)
        gz = len(gzip.compress(open(p41, "rb").read(), 6))
        # semantic validator (x3d python package)
        sys.path.insert(0, str(REPO / "source"))
        from validate import validate_with_x3d_py, validate_xml_file
        sem = validate_with_x3d_py(p41)
        # re-import
        reset(); os.environ["X3D_SPLAT_IMPORT"] = target
        t1 = time.time(); imp(p41); t_imp = time.time() - t1
        objs = [o for o in bpy.data.objects if o.type in ("MESH", "POINTCLOUD")]
        o2 = objs[0]
        ir = extract_ir(o2)
        # compare to original arrays
        col = {k: i for i, k in enumerate(names)}
        pos = np.array(ir.positions, dtype=np.float32)
        out = {}
        out["pos_max_abs"] = stats(pos, data[:, 0:3])[0]
        sc = np.log(np.array(ir.scales, dtype=np.float64))
        out["log_scale_max_abs"] = stats(sc, data[:, col["scale_0"]:col["scale_0"]+3])[0]
        op = np.array(ir.opacities, dtype=np.float64)
        sig = 1/(1+np.exp(-data[:, col["opacity"]].astype(np.float64)))
        out["opacity_sigmoid_max_abs"] = stats(op, sig)[0]
        q = np.array(ir.orientations, dtype=np.float64)  # x y z w
        qw = np.stack([q[:,3], q[:,0], q[:,1], q[:,2]], axis=1)
        orig_q = data[:, col["rot_0"]:col["rot_0"]+4].astype(np.float64)
        out["quat_max_abs(after_sign_fix)"] = float(np.minimum(np.abs(qw-orig_q).max(axis=1), np.abs(qw+orig_q).max(axis=1)).max())
        dc = np.array(ir.sh[(0,0)], dtype=np.float64)
        out["sh0_max_abs"] = stats(dc, data[:, col["f_dc_0"]:col["f_dc_0"]+3])[0]
        if deg == 3:
            # rest layout: channel-major, 15 per channel
            err = 0.0
            slots = [(d, c) for d in (1,2,3) for c in range(2*d+1)]
            for si, slot in enumerate(slots):
                arr = np.array(ir.sh[slot], dtype=np.float64)
                for ch in range(3):
                    err = max(err, float(np.abs(arr[:, ch] - data[:, col[f"f_rest_{ch*15+si}"]]).max()))
            out["sh_rest_max_abs"] = err
        # write the PLY back and compare bit-for-bit column-wise
        sio = importlib.import_module("io_scene_x3d.splat_io") if False else None
        import importlib as il
        sio = il.import_module("io_scene_x3d.splat_io")
        ply1 = str(TMP / f"out_sh{deg}_{target}.ply")
        sio.write_ply(ply1, ir)
        n2, d2 = read_ply_np(ply1)
        same_cols = [k for k in names if k in n2]
        exact = {k: bool(np.array_equal(d2[:, n2.index(k)], data[:, col[k]])) for k in same_cols}
        out["ply_cols_bit_exact"] = f"{sum(exact.values())}/{len(exact)}"
        out["ply_cols_not_exact"] = [k for k, v in exact.items() if not v][:12]
        out["ply_out_bytes"] = os.path.getsize(ply1)
        row = dict(sh=deg, target=target, N=N, ply_bytes=ply_bytes, bytes_per_splat_ply=ply_bytes/N, x3d41_bytes=x3d_bytes, bytes_per_splat_x3d=x3d_bytes/N, x3d41_gzip6_bytes=gz,
                   validate_xml=validate_xml_file(p41).valid, x3dpy_valid=(sem.valid if sem else None), x3dpy_warnings=(sem.warnings[:3] if sem else None), x3dpy_errors=(sem.errors[:3] if sem else None),
                   export_s=round(t_exp,2), import_s=round(t_imp,2), obj_type=o2.type, **out)
        results.append(row); print(json.dumps(row))
json.dump(results, open(SCR / f"t6_results_N{N}.json", "w"), indent=1)
