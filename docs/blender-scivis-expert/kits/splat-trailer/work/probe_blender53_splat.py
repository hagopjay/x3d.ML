#!/usr/bin/env python3
"""Probe for Blender 5.3 native Gaussian splats (run with: blender -b --python-exit-code 1 --python probe_blender53_splat.py -- OUTDIR [ADDON_ROOT]).
Also runs on bpy 5.2.3 (smoke: reports 'no native splat type' and the stock PLY import shape).
Answers the open questions in the splat_native.py docstring that only a real 5.3 build can settle:
  Q1 radiance:base.xyz  = raw SH DC (f_dc) or reconstructed RGB (0.5 + C0*f_dc, clamped)?       -> expected raw (fork assumes it)
  Q2 radiance:base.w    = sigmoid(opacity) 0..1, or something else?                              -> expected sigmoid
  Q3 scale              = exp(scale_i) linear?                                                   -> expected linear
  Q4 rotation           = (w,x,y,z) taken from rot_0..3 and normalised?
  Q5 radiance:sh_i      = f_rest in (degree, coef) order with RGB triples (fork: i = d*d-1+c)?
  Q6 PLY axis           = untouched (Y-down 3DGS frame), or rotated on import?
  Q7 colour space       = any property recording sRGB vs linear?                                  -> 'sRGB assumption' (trade press)
Writes probe_result.json with the attribute dump of the first 4 splats and every comparison above.
"""
import sys, os, json, struct, math
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "probe_out"); os.makedirs(out, exist_ok=True)
C0 = 0.28209479177387814
# four splats with distinctive values (3DGS reference layout, SH degree 3: 45 f_rest)
rows = []
for i, (pos, dc, logit, ln_s, q) in enumerate([
    ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), 0.0, (math.log(0.1), math.log(0.2), math.log(0.3)), (1.0, 0.0, 0.0, 0.0)),
    ((-1.0, 0.5, 2.5), (1.0, -1.0, 0.5), 2.0, (math.log(0.05), math.log(0.05), math.log(0.4)), (0.5, 0.5, 0.5, 0.5)),
    ((0.0, -2.0, 1.0), (-2.0, 2.5, 0.25), -3.0, (math.log(0.3), math.log(0.1), math.log(0.02)), (0.0, 1.0, 0.0, 0.0)),
    ((4.0, 0.0, -1.0), (0.3, 0.2, 0.1), 5.0, (math.log(0.01), math.log(0.01), math.log(0.01)), (0.7071068, 0.0, 0.7071068, 0.0)),
]):
    rest = [round(0.001 * (k + 1) * (1 + 0.1 * i), 6) for k in range(45)]   # f_rest_k = 0.001*(k+1)*(1+0.1*i): every slot distinguishable
    rows.append([*pos, 0, 0, 0, *dc, *rest, logit, *ln_s, *q])
names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"] + [f"f_rest_{k}" for k in range(45)] + ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
ply = os.path.join(out, "probe4.ply")
with open(ply, "wb") as f:
    f.write(("ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % len(rows) + "".join(f"property float {n}\n" for n in names) + "end_header\n").encode())
    for r in rows: f.write(struct.pack("<" + "f" * len(names), *r))

res = {"bpy": bpy.app.version_string, "rows_input": rows}
pc_type = bpy.types.PointCloud.bl_rna.properties.get("type")
res["pointcloud_type_enum"] = [i.identifier for i in pc_type.enum_items] if pc_type else None
bpy.ops.wm.read_factory_settings(use_empty=True)
res["ply_import_result"] = list(bpy.ops.wm.ply_import(filepath=ply))
objs = []
for o in bpy.data.objects:
    d = {"name": o.name, "type": o.type, "data_type": getattr(o.data, "type", None), "matrix_world": [list(r) for r in o.matrix_world], "attrs": {}}
    for a in o.data.attributes:
        if a.name.startswith("."): continue
        try:
            if a.data_type == "FLOAT":
                v = [0.0] * len(a.data); a.data.foreach_get("value", v); vals = v[:4]
            elif a.data_type in ("FLOAT_VECTOR", "FLOAT4", "QUATERNION", "FLOAT_COLOR"):
                key = {"FLOAT_VECTOR": "vector", "FLOAT4": "vector", "QUATERNION": "value", "FLOAT_COLOR": "color"}[a.data_type]
                w = {"FLOAT_VECTOR": 3, "FLOAT4": 4, "QUATERNION": 4, "FLOAT_COLOR": 4}[a.data_type]
                v = [0.0] * (w * len(a.data)); a.data.foreach_get(key, v); vals = [v[i * w:(i + 1) * w] for i in range(min(4, len(a.data)))]
            else:
                vals = None
        except Exception as e:  # noqa: BLE001 - a probe reports, it does not stop
            vals = f"unreadable: {e}"
        d["attrs"][a.name] = {"data_type": a.data_type, "domain": a.domain, "first4": vals}
    d["custom_props"] = {k: str(o.data[k]) for k in o.data.keys()}
    objs.append(d)
res["objects"] = objs
# answers (only when the native layout is present)
o = next((x for x in objs if "radiance:base" in x["attrs"]), None)
if o:
    A = o["attrs"]; base = A["radiance:base"]["first4"]; exp_dc = [r[6:9] for r in rows]; exp_rgb = [[max(0, min(1, 0.5 + C0 * c)) for c in r[6:9]] for r in rows]
    exp_op = [1 / (1 + math.exp(-r[54 + 0])) for r in rows]
    res["answers"] = {
        "Q1_base_xyz_is_raw_dc": all(all(abs(base[i][k] - exp_dc[i][k]) < 1e-5 for k in range(3)) for i in range(4)),
        "Q1_base_xyz_is_rgb": all(all(abs(base[i][k] - exp_rgb[i][k]) < 1e-5 for k in range(3)) for i in range(4)),
        "Q2_base_w_is_sigmoid": all(abs(base[i][3] - exp_op[i]) < 1e-5 for i in range(4)),
        "Q3_scale_linear": all(all(abs(A["scale"]["first4"][i][k] - math.exp(rows[i][55 + k])) < 1e-5 for k in range(3)) for i in range(4)),
        "Q4_rotation_wxyz_matches_rot0123": all(all(abs(A["rotation"]["first4"][i][k] - rows[i][58 + k]) < 1e-5 for k in range(4)) for i in range(4)),
        "Q5_sh_slot_check": {f"radiance:sh_{j}": A.get(f"radiance:sh_{j}", {}).get("first4", [None])[0] for j in (0, 1, 2, 3, 8, 14)},
        "Q6_positions_untouched": all(all(abs(A["position"]["first4"][i][k] - rows[i][k]) < 1e-5 for k in range(3)) for i in range(4)),
    }
    res["fork_expectation_note"] = "x3d-blender-io splat_native.py assumes Q1 raw DC, Q2 sigmoid 0..1, Q3 linear, Q4 w x y z, Q5 index i = d*d-1+c."
else:
    res["answers"] = "no native splat layout in this Blender (expected on 5.2.x): stock PLY import gives raw f_dc_*, f_rest_*, opacity, scale_*, rot_* float attributes on a Mesh"
# if the add-on root is given, run the fork exporter on whatever object exists and keep the X3D for diffing
if len(argv) > 1:
    import importlib, tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="xbio_probe_")); (tmp / "io_scene_x3d").symlink_to(Path(argv[1]).resolve() / "source", target_is_directory=True); sys.path.insert(0, str(tmp))
    try:
        importlib.import_module("io_scene_x3d").register()
        res["fork_export"] = list(bpy.ops.export_scene.x3d(filepath=os.path.join(out, "probe_fork.x3d"), x3d_version="X3D41", use_selection=False))
    except Exception as e:  # noqa: BLE001
        res["fork_export"] = f"failed: {e}"
json.dump(res, open(os.path.join(out, "probe_result.json"), "w"), indent=1, default=str)
print("wrote", os.path.join(out, "probe_result.json"))
