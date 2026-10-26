#!/usr/bin/env python3
"""Anamnesis (design/TRAILER.md v1.1, X3D export): the trained memory as X3D 4.1 GaussianSplats, written by the bridge.

Runs on the bpy wheel with the x3d-blender-io add-on registered from --bridge (a checkout or archive root holding source/):
  1. the PLY is read by the add-on's own reader (splat_io.read_splats: exp scales, sigmoid opacities, x y z w quaternions,
     SH by degree), and the splat object is built by the add-on's own builder (import_x3d._build_splat_object), placed the
     way the importer places a GaussianSplats node at the scene root (its default Y-up to Z-up matrix), so the export
     comes back in the Hall's own X3D frame;
  2. the add-on exports X3D 4.1 (export_scene.x3d, x3d_version X3D41, every other option at its default);
  3. the export is read back as float32 and compared with the PLY's numbers, field by field (exact, or the largest
     difference), so nothing is claimed that was not checked.
--max-sh-degree D leaves SH degrees above D out of the export (the cut's frames are rendered from the PLY with all of them);
the log says so. --roundtrip FILE.x3d also imports FILE with the add-on, exports it again and compares the two as
Splat Park's roundtrip_bpy.py does (orientations up to sign).

usage: python export_splats.py --bridge DIR --ply step_30000.ply --out DIR [--name anamnesis_v1] [--max-sh-degree 1]
       [--roundtrip FILE.x3d]"""
import os, sys, re, json, time, math, struct, argparse, tempfile, importlib, hashlib, subprocess
from pathlib import Path
import numpy as np

SH_FIELDS = [(d, c) for d in range(4) for c in range(2 * d + 1)]


def say(log, *a):
    s = " ".join(str(x) for x in a); log.append(s); print(s, flush=True)


def bridge_rev(root):
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
        if r: return r
    except Exception:
        pass
    p = Path(root) / "REV"
    return p.read_text().strip() if p.exists() else "unknown"


def read_ply_np(path):
    """The PLY's raw float32 columns (binary little endian, float properties only, as the trainer writes)."""
    with open(path, "rb") as f:
        head = b""
        while not head.endswith(b"end_header\n"):
            line = f.readline()
            if not line: raise SystemExit("PLY header has no end_header")
            head += line
        n = int(re.search(rb"element vertex (\d+)", head).group(1))
        props = [p.decode() for p in re.findall(rb"property float (\S+)", head)]
        arr = np.frombuffer(f.read(), dtype="<f4", count=n * len(props)).reshape(n, len(props))
    return {p: arr[:, i] for i, p in enumerate(props)}, n


def expected_from_ply(cols, n, max_deg):
    """What the export must hold, from the PLY's own columns (the same mapping as splat_io, done in numpy)."""
    f64 = lambda k: cols[k].astype(np.float64)
    E = {"positions": np.stack([f64("x"), f64("y"), f64("z")], 1)}
    E["scales"] = np.exp(np.stack([f64(f"scale_{i}") for i in range(3)], 1))
    q = np.stack([f64("rot_1"), f64("rot_2"), f64("rot_3"), f64("rot_0")], 1)
    ln = np.linalg.norm(q, axis=1, keepdims=True); bad = ln[:, 0] < 1e-12
    q = np.where(bad[:, None], np.array([0, 0, 0, 1.0]), q / np.where(ln < 1e-12, 1, ln)); E["orientations"] = q
    o = f64("opacity"); E["opacities"] = np.where(o >= 0, 1 / (1 + np.exp(-o)), np.exp(o) / (1 + np.exp(o)))[:, None]
    rest = sorted([k for k in cols if k.startswith("f_rest_")], key=lambda k: int(k.split("_")[-1])); per = len(rest) // 3
    whole = max(k for k in (0, 3, 8, 15) if k <= per)
    E["sphericalHarmonicsDegree0Coef0"] = np.stack([f64(f"f_dc_{c}") for c in range(3)], 1)
    for slot, (d, c) in enumerate([(d, c) for d in (1, 2, 3) for c in range(2 * d + 1)][:whole]):
        if d > max_deg: break
        E[f"sphericalHarmonicsDegree{d}Coef{c}"] = np.stack([f64(f"f_rest_{ch * per + slot}") for ch in range(3)], 1)
    return E


def splat_fields(path):
    """Every GaussianSplats array in an X3D file, concatenated over nodes, as float64 parsed from the text."""
    txt = open(path, encoding="utf-8").read()
    out, nodes, tr = {}, 0, []
    for m in re.finditer(r"(<Transform\b[^>]*>)?\s*<GaussianSplats\b([^>]*)/>", txt):
        nodes += 1; tr.append(m.group(1) or "")
        for k, v in re.findall(r'\s([A-Za-z0-9]+)="([^"]*)"', m.group(2)):
            if re.match(r"^(positions|scales|orientations|opacities|sphericalHarmonics)", k):
                out.setdefault(k, []).append(np.array(v.split(), dtype=np.float64))
    w = lambda k: 4 if k == "orientations" else 1 if k == "opacities" else 3
    return {k: np.concatenate(v).reshape(-1, w(k)) for k, v in out.items()}, nodes, tr, txt


def compare(E, F):
    res = {}
    for k in sorted(set(E) | set(F)):
        a, b = E.get(k), F.get(k)
        if a is None or b is None:
            res[k] = dict(note="missing in the export" if b is None else "not expected (above the SH cap?)"); continue
        if a.shape != b.shape:
            res[k] = dict(note=f"shape {a.shape} vs {b.shape}"); continue
        # the export writes float32-exact text (the shortest decimal that reads back as the float32): compare as float32
        a32 = a.astype(np.float32).astype(np.float64); b = b.astype(np.float32).astype(np.float64)
        if k == "orientations":
            d = np.minimum(np.abs(a32 - b).max(1), np.abs(a32 + b).max(1))
            res[k] = dict(tuples=int(len(a)), exact_tuples=int((d == 0).sum()), max_abs_diff=float(d.max()), sign_free=True)
        else:
            d = np.abs(a32 - b)
            res[k] = dict(values=int(a.size), exact=int((d == 0).sum()), max_abs_diff=float(d.max()))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge", required=True); ap.add_argument("--ply", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="anamnesis_v1"); ap.add_argument("--max-sh-degree", type=int, default=3)
    ap.add_argument("--roundtrip", default="")
    A = ap.parse_args(); os.makedirs(A.out, exist_ok=True); log = []; t0 = time.time()
    root = Path(A.bridge).resolve(); rev = bridge_rev(root)
    tmp = Path(tempfile.mkdtemp(prefix="xbio_export_")); (tmp / "io_scene_x3d").symlink_to(root / "source", target_is_directory=True)
    sys.path.insert(0, str(tmp))
    import bpy
    say(log, "bpy", bpy.app.version_string, "python", sys.version.split()[0], "bridge", rev)
    mod = importlib.import_module("io_scene_x3d"); mod.register()
    from io_scene_x3d import splat_io, import_x3d
    rep = dict(bridge=rev, bpy=bpy.app.version_string, tool="trailer/src/export_splats.py")
    if A.ply:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cols, n = read_ply_np(A.ply)
        t1 = time.time(); splats = splat_io.read_splats(A.ply, name=A.name); t_read = time.time() - t1
        deg_in = splats.sh_degree()
        dropped = sorted({d for (d, c) in splats.sh if d > A.max_sh_degree})
        for key in [k for k in splats.sh if k[0] > A.max_sh_degree]: del splats.sh[key]
        say(log, f"read {n:,} splats from {os.path.basename(A.ply)} in {t_read:.1f} s with the add-on's reader; SH degree {deg_in}"
            + (f"; degrees {dropped} left out of the export (--max-sh-degree {A.max_sh_degree}); the cut renders the PLY with all of them" if dropped else ""))
        from bpy_extras.io_utils import axis_conversion
        G = axis_conversion(from_forward="-Z", from_up="Y").to_4x4()   # the importer's default (axis_forward -Z, axis_up Y)
        t2 = time.time(); obj = import_x3d._build_splat_object(bpy.context.scene.collection, A.name, splats); obj.matrix_world = G
        t_build = time.time() - t2
        say(log, f"built {obj.name} ({obj.type}, {len(obj.data.vertices) if obj.type == 'MESH' else '?'} points) in {t_build:.1f} s with the add-on's builder")
        del splats
        out = os.path.join(A.out, A.name + "_bridge.x3d")
        t3 = time.time(); r = bpy.ops.export_scene.x3d(filepath=out, x3d_version="X3D41", use_selection=False); t_exp = time.time() - t3
        say(log, "export", r, f"in {t_exp:.1f} s ->", out, os.path.getsize(out), "bytes")
        t4 = time.time(); F, nodes, tr, txt = splat_fields(out); E = expected_from_ply(cols, n, A.max_sh_degree); cmp = compare(E, F)
        say(log, f"read back {nodes} GaussianSplats node(s) in {time.time() - t4:.1f} s; Transform: {tr[:1]}")
        for k, v in cmp.items(): say(log, " ", k, json.dumps(v))
        exact = all(v.get("exact", v.get("exact_tuples")) == v.get("values", v.get("tuples")) for v in cmp.values() if "note" not in v)
        tv = {k: [float(x) for x in v.split()] for k, v in re.findall(r'\s(translation|rotation|scale)="([^"]*)"', tr[0] if tr else "")}
        ident = bool(tv) and max(map(abs, tv.get("translation", [1]))) < 1e-6 and abs(tv.get("rotation", [0, 0, 1, 1])[3]) < 1e-6 \
            and max(abs(x - 1) for x in tv.get("scale", [0])) < 1e-6
        rep.update(ply=os.path.basename(A.ply), splats=n, sh_degree_in=deg_in, sh_degrees_left_out=dropped, out=os.path.basename(out),
                   out_bytes=os.path.getsize(out), sha256=hashlib.sha256(open(out, "rb").read()).hexdigest(), nodes=nodes, transform=tr[:1],
                   compare_to_ply=cmp, all_exact_float32=exact, read_s=round(t_read, 2), build_s=round(t_build, 2), export_s=round(t_exp, 2),
                   metas=re.findall(r'<meta name="([^"]*)" content="([^"]*)"', txt[:20000]))
        say(log, "every field float32-exact against the PLY" if exact else "NOT every field exact: see compare_to_ply", "| Transform identity:", ident)
    if A.roundtrip:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        t5 = time.time(); r1 = bpy.ops.import_scene.x3d(filepath=A.roundtrip); t_imp = time.time() - t5
        rt = os.path.join(A.out, Path(A.roundtrip).stem + "_roundtrip.x3d")
        t6 = time.time(); r2 = bpy.ops.export_scene.x3d(filepath=rt, x3d_version="X3D41", use_selection=False); t_exp2 = time.time() - t6
        Fa, na, _, _ = splat_fields(A.roundtrip); Fb, nb, _, _ = splat_fields(rt); cmp2 = compare(Fa, Fb)
        say(log, f"round trip: import {r1} {t_imp:.1f} s, export {r2} {t_exp2:.1f} s; nodes {na} -> {nb}")
        for k, v in cmp2.items(): say(log, " ", k, json.dumps(v))
        rep["roundtrip"] = dict(src=os.path.basename(A.roundtrip), out=os.path.basename(rt), nodes_src=na, nodes_out=nb, import_s=round(t_imp, 2),
                               export_s=round(t_exp2, 2), compare=cmp2,
                               all_exact=all(v.get("exact", v.get("exact_tuples")) == v.get("values", v.get("tuples")) for v in cmp2.values() if "note" not in v))
        try: os.remove(rt)   # the round trip's own export is only compared, not kept
        except OSError: pass
    rep["total_s"] = round(time.time() - t0, 1); rep["log"] = log
    name = A.name + ("_export" if A.ply else "") + ("_roundtrip" if A.roundtrip else "")
    json.dump(rep, open(os.path.join(A.out, name + ".json"), "w"), indent=1)
    say(log, "total", rep["total_s"], "s")


if __name__ == "__main__":
    main()
