#!/usr/bin/env python3
"""Hands-on splat round-trip test on bpy 5.2.3 LTS with the x3d-blender-io fork (clone of hagopjay/x3d-blender-io).

usage: python -I rt_test.py ADDON_ROOT WORKDIR N
Writes synthetic 3DGS PLYs (SH0..SH3) in the reference layout, then for each:
  1. PLY size (bytes/splat) vs the KB arithmetic 68/104/164/248
  2. PLY -> add-on reader -> {mesh | native pointcloud} object -> export X3D 4.1 -> compare to PLY (float32)
  3. X3D -> import -> export again -> compare (X3D -> Blender -> X3D)
  4. Blender object -> IR -> write_ply -> compare to the source PLY columns (Blender -> PLY)
Results as JSON on stdout.
"""
import os, sys, json, re, time, importlib, tempfile, struct
from pathlib import Path
import numpy as np

addon_root, work, N = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), int(sys.argv[3])
work.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_splats_ref as R   # copy of trailer/src/export_splats.py (read_ply_np, expected_from_ply, splat_fields, compare)

rng = np.random.default_rng(1741)


def make_ply(path, n, deg):
    per = {0: 0, 1: 9, 2: 24, 3: 45}[deg]
    names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"] + [f"f_rest_{i}" for i in range(per)] + \
            ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    a = np.zeros((n, len(names)), np.float32)
    col = {k: i for i, k in enumerate(names)}
    a[:, 0:3] = rng.normal(0, 5.0, (n, 3))                        # metres, a hall-sized cloud
    a[:, 3:6] = 0
    a[:, 6:9] = rng.normal(0, 0.8, (n, 3))                        # SH DC
    if per:
        a[:, 9:9 + per] = rng.normal(0, 0.05, (n, per))
    a[:, col["opacity"]] = rng.normal(0.0, 3.0, n)                # logit opacity, a wide tail
    a[:, col["scale_0"]:col["scale_0"] + 3] = rng.normal(np.log(0.03), 0.7, (n, 3))   # ln scale
    q = rng.normal(size=(n, 4)); q /= np.linalg.norm(q, axis=1, keepdims=True)
    a[:, col["rot_0"]:col["rot_0"] + 4] = q                        # w first
    header = ("ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % n + "".join(f"property float {k}\n" for k in names) + "end_header\n").encode()
    with open(path, "wb") as f:
        f.write(header); f.write(a.astype("<f4").tobytes())
    return os.path.getsize(path) - len(header), len(names)


out = {"N": N, "cases": []}
import bpy
tmp = Path(tempfile.mkdtemp(prefix="xbio_rt_")); (tmp / "io_scene_x3d").symlink_to(addon_root / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
mod = importlib.import_module("io_scene_x3d"); mod.register()
from io_scene_x3d import splat_io, import_x3d, splat_native, extract
out["bpy"] = bpy.app.version_string
out["addon_manifest"] = re.search(r'^version = "([^"]+)"', (addon_root / "source" / "blender_manifest.toml").read_text(), re.M).group(1)
out["pointcloud_type_supported"] = splat_native.pointcloud_type_supported()
out["pointcloud_buildable"] = splat_native.pointcloud_buildable()


def allexact(cmp):
    return all(v.get("exact", v.get("exact_tuples")) == v.get("values", v.get("tuples")) for v in cmp.values() if "note" not in v)


def worst(cmp):
    return max((v.get("max_abs_diff", 0.0) for v in cmp.values() if "note" not in v), default=0.0)


for deg in (0, 1, 2, 3):
    ply = work / f"synth_sh{deg}_{N}.ply"
    payload, nprops = make_ply(ply, N, deg)
    size = os.path.getsize(ply)
    case = {"sh_degree": deg, "ply_bytes": size, "floats_per_splat": nprops, "payload_bytes_per_splat": payload / N, "ply_bytes_per_splat_incl_header_amortised": size / N}
    cols, n = R.read_ply_np(str(ply)); E = R.expected_from_ply(cols, n, 3)
    for target in ("mesh", "pointcloud"):
        os.environ["X3D_SPLAT_IMPORT"] = target
        bpy.ops.wm.read_factory_settings(use_empty=True)
        t0 = time.time(); splats = splat_io.read_splats(str(ply), name="S"); t_read = time.time() - t0
        t0 = time.time(); obj = import_x3d._build_splat_object(bpy.context.scene.collection, "S", splats); t_build = time.time() - t0
        rec = {"target": target, "obj_type": obj.type, "data_type_attrs": None, "read_s": round(t_read, 2), "build_s": round(t_build, 2)}
        if obj.type == "POINTCLOUD":
            rec["data_type_attrs"] = {a.name: a.data_type for a in obj.data.attributes if a.name.startswith(("radiance", "position", "scale", "rotation"))}
            rec["is_native_splat_object"] = splat_native.is_native_splat_object(obj)
        xo = work / f"rt_sh{deg}_{target}.x3d"
        t0 = time.time(); r = bpy.ops.export_scene.x3d(filepath=str(xo), x3d_version="X3D41", use_selection=False); rec["export"] = list(r); rec["export_s"] = round(time.time() - t0, 2)
        rec["x3d_bytes"] = os.path.getsize(xo); rec["x3d_bytes_per_splat"] = rec["x3d_bytes"] / N
        F, nodes, tr, txt = R.splat_fields(str(xo)); cmpA = R.compare(E, F)
        rec["ply_to_x3d"] = dict(nodes=nodes, all_exact=allexact(cmpA), worst=worst(cmpA), fields=sorted(F.keys()) if deg == 3 else len(F), transform=tr[:1],
                                 notes={k: v["note"] for k, v in cmpA.items() if "note" in v})
        rec["largest_start_tag"] = max((len(m.group(0)) for m in re.finditer(r"<GaussianSplats\b[^>]*/>", txt)), default=0)
        # X3D -> Blender -> X3D
        bpy.ops.wm.read_factory_settings(use_empty=True)
        t0 = time.time(); r1 = bpy.ops.import_scene.x3d(filepath=str(xo)); t_imp = time.time() - t0
        xo2 = work / f"rt2_sh{deg}_{target}.x3d"
        r2 = bpy.ops.export_scene.x3d(filepath=str(xo2), x3d_version="X3D41", use_selection=False)
        F2, nodes2, tr2, _ = R.splat_fields(str(xo2)); cmpB = R.compare(F, F2)
        rec["x3d_import_s"] = round(t_imp, 2)
        rec["x3d_blender_x3d"] = dict(nodes=nodes2, all_exact=allexact(cmpB), worst=worst(cmpB), notes={k: v["note"] for k, v in cmpB.items() if "note" in v},
                                      objs=[(o.name, o.type) for o in bpy.data.objects], transform_in=tr[:1], transform_out=tr2[:1])
        # Blender -> PLY (add-on writer) vs the source PLY columns
        objs = [o for o in bpy.data.objects if extract.is_splat_mesh(o) or splat_native.is_native_splat_object(o)]
        if objs:
            o = objs[0]
            ir = splat_native.extract_native_splats(o.data, name="S") if o.type == "POINTCLOUD" else extract.extract_splats(o.data, name="S")
            ply2 = work / f"back_sh{deg}_{target}.ply"; splat_io.write_ply(str(ply2), ir)
            cols2, n2 = R.read_ply_np(str(ply2))
            diffs = {}
            for k in cols:
                if k in cols2 and not k.startswith("n"):
                    d = np.abs(cols[k].astype(np.float64) - cols2[k].astype(np.float64))
                    diffs[k] = float(d.max())
                elif k not in cols2 and not k.startswith("n"):
                    diffs[k] = "missing"
            # quaternions sign-free
            qa = np.stack([cols[f"rot_{i}"] for i in range(4)], 1).astype(np.float64); qb = np.stack([cols2[f"rot_{i}"] for i in range(4)], 1).astype(np.float64)
            dq = np.minimum(np.abs(qa - qb).max(1), np.abs(qa + qb).max(1))
            op_a = cols["opacity"].astype(np.float64); op_b = cols2["opacity"].astype(np.float64)
            clamp = int((np.abs(op_a) > 13.8).sum())
            rec["blender_to_ply"] = dict(n=n2, same_n=(n2 == n), max_abs_diff_by_column_summary={
                "xyz": max(diffs[k] for k in ("x", "y", "z")), "f_dc": max(diffs[f"f_dc_{i}"] for i in range(3)),
                "f_rest": max([v for k, v in diffs.items() if k.startswith("f_rest") and v != "missing"] or [0.0]),
                "scale_ln": max(diffs[f"scale_{i}"] for i in range(3)), "opacity_logit": diffs["opacity"], "quat_signfree": float(dq.max())},
                missing=[k for k, v in diffs.items() if v == "missing"], source_logit_beyond_13p8=clamp,
                opacity_logit_worst_when_within_13p8=float(np.abs(op_a - op_b)[np.abs(op_a) <= 13.8].max()),
                ply_bytes=os.path.getsize(ply2))
        case.setdefault("targets", []).append(rec)
    out["cases"].append(case)
print(json.dumps(out, indent=1, default=str))
