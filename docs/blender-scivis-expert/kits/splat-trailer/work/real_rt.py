import os, sys, json, re, time, importlib, tempfile, resource
from pathlib import Path
import numpy as np
addon_root, ply, out = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve(); target = sys.argv[4]
os.environ["X3D_SPLAT_IMPORT"] = target; out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_splats_ref as R
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_real_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
importlib.import_module("io_scene_x3d").register()
from io_scene_x3d import splat_io, import_x3d, splat_native, extract
from bpy_extras.io_utils import axis_conversion
G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()
cols, n = R.read_ply_np(ply); E = R.expected_from_ply(cols, n, 3)
rep = dict(ply=os.path.basename(ply), n=n, ply_bytes=os.path.getsize(ply), target=target)
op = cols["opacity"].astype(np.float64); rep["logit_range"] = [float(op.min()), float(op.max())]; rep["logit_beyond_13p8155"] = int((np.abs(op) > 13.8155).sum())
sc = np.stack([cols[f"scale_{i}"] for i in range(3)], 1).astype(np.float64); rep["ln_scale_range"] = [float(sc.min()), float(sc.max())]
q = np.stack([cols[f"rot_{i}"] for i in range(4)], 1).astype(np.float64); lead = np.bincount(np.abs(q).argmax(1), minlength=4); rep["quat_largest_component_counts_w_first_layout"] = lead.tolist()
rep["quat_norm_off_gt_1e-3"] = int((np.abs(np.linalg.norm(q, axis=1) - 1) > 1e-3).sum())
bpy.ops.wm.read_factory_settings(use_empty=True)
t = time.time(); s = splat_io.read_splats(ply, name="S"); rep["read_s"] = round(time.time() - t, 1); rep["sh_degree"] = s.sh_degree()
t = time.time(); o = import_x3d._build_splat_object(bpy.context.scene.collection, "S", s); o.matrix_world = G; rep["build_s"] = round(time.time() - t, 1); rep["obj"] = o.type
xo = out / f"real_{Path(ply).stem}_{target}.x3d"
t = time.time(); bpy.ops.export_scene.x3d(filepath=str(xo), x3d_version="X3D41", use_selection=False); rep["export_s"] = round(time.time() - t, 1)
rep["x3d_bytes"] = os.path.getsize(xo); rep["x3d_bytes_per_splat"] = round(rep["x3d_bytes"] / n, 1)
F, nodes, tr, txt = R.splat_fields(str(xo)); cmp = R.compare(E, F)
rep["ply_to_x3d_all_exact"] = all(v.get("exact", v.get("exact_tuples")) == v.get("values", v.get("tuples")) for v in cmp.values() if "note" not in v)
rep["fields"] = sorted(F.keys()); rep["largest_start_tag"] = max(len(m.group(0)) for m in re.finditer(r"<GaussianSplats\b[^>]*/>", txt)); rep["transform"] = tr[:1]
objs = [x for x in bpy.data.objects]
ir = splat_native.extract_native_splats(o.data, name="S") if o.type == "POINTCLOUD" else extract.extract_splats(o.data, name="S")
ply2 = out / "back.ply"; splat_io.write_ply(str(ply2), ir); cols2, n2 = R.read_ply_np(str(ply2))
d = {}
for k in cols:
    if k.startswith("n") and k != "nx" and False: continue
    if k in ("nx", "ny", "nz"): continue
    if k in cols2: d[k] = float(np.abs(cols[k].astype(np.float64) - cols2[k].astype(np.float64)).max())
op2 = cols2["opacity"].astype(np.float64)
a1 = 1 / (1 + np.exp(-op)); a2 = 1 / (1 + np.exp(-op2))
rep["bl_to_ply"] = dict(xyz=max(d["x"], d["y"], d["z"]), f_dc=max(d[f"f_dc_{i}"] for i in range(3)), scale_ln=max(d[f"scale_{i}"] for i in range(3)), opacity_logit=d["opacity"], alpha_max_abs=float(np.abs(a1 - a2).max()),
                        quat_signfree=float(np.minimum(np.abs(q - np.stack([cols2[f"rot_{i}"] for i in range(4)], 1)).max(1), np.abs(q + np.stack([cols2[f"rot_{i}"] for i in range(4)], 1)).max(1)).max()))
rep["peak_rss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)
os.remove(ply2); print(json.dumps(rep, indent=1))
