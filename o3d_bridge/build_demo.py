"""Build the Open3D-ML bridge demo data: real CPU inference -> labelled X3D, and the measurements behind every number.

Usage:  python build_demo.py OUT_DIR --ckpt randlanet_s3dis_*.pth --cfg randlanet_s3dis.yml --fork /path/to/x3d_mcp [--index 20]
Input:  Redwood living-room fragment (Choi, Zhou, Koltun, CVPR 2015) fetched by open3d.data.LivingRoomPointClouds.
Writes: OUT_DIR/open3d-segmentation.x3d, stats.json, validate-receipt.json, semantics.jsonld
Needs LD_LIBRARY_PATH to hold a CUDA 12 libcudart if the Open3D torch ops wheel is the CUDA build (see README).
"""
import argparse, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import x3do3d as B  # noqa: E402
import x3dprov  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--ckpt", required=True)
ap.add_argument("--cfg", required=True)
ap.add_argument("--fork", required=True)
ap.add_argument("--index", type=int, default=20)
ap.add_argument("--max-points", type=int, default=50000)
ap.add_argument("--data-root", default="o3ddata")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

import open3d as o3d, torch  # noqa: E402
data = o3d.data.LivingRoomPointClouds(data_root=a.data_root)
src = data.paths[a.index]
src_sha = B.sha256_file(src)
pc = o3d.io.read_point_cloud(src)
pts, col = np.asarray(pc.points), np.asarray(pc.colors)
Pm, off = B.ml_frame_from_source(pts, "-y")
t0 = time.time()
lab, sc = B.run_randlanet_s3dis(Pm, col, a.ckpt, a.cfg)
t_inf = time.time() - t0

lab_rep, _ = B.run_randlanet_s3dis(Pm, col, a.ckpt, a.cfg)  # repeat run, same input: the pipeline samples centre points at random
# frame ablation: the same model, same points, floor NOT at z = 0 (the shift is the finding)
Pn, _ = B.ml_frame_from_source(pts, "-y", floor_to_zero=False)
lab_noshift, _ = B.run_randlanet_s3dis(Pn, col, a.ckpt, a.cfg)

X = B.ml_to_x3d(Pm)
sel = np.sort(np.random.default_rng(0).choice(len(X), a.max_points, replace=False))
metas = [("x3do3d.model", "Open3D-ML RandLANet torch, S3DIS (checkpoint randlanet_s3dis_202201071330utc.pth)"),
         ("x3do3d.ckpt_sha256", B.sha256_file(a.ckpt)), ("x3do3d.open3d", o3d.__version__), ("x3do3d.torch", torch.__version__),
         ("x3do3d.device", "cpu"), ("x3do3d.source", "Redwood living-room fragment %d (Choi, Zhou, Koltun, CVPR 2015) via open3d.data" % a.index),
         ("x3do3d.source_sha256", src_sha), ("x3do3d.points_inferred", len(pts)), ("x3do3d.points_shown", a.max_points)]
xml, st = B.segmentation_to_x3d(X[sel], lab[sel], B.S3DIS_NAMES, B.S3DIS_COLORS, rgb=col[sel], scores=sc[sel],
                                title="Open3D-ML segmentation carried into X3D (Redwood fragment %d)" % a.index, metas=metas)
step = {"kind": "ml-inference", "tool": "Open3D-ML RandLANet S3DIS", "open3d": o3d.__version__, "torch": torch.__version__,
        "ckpt_sha256": B.sha256_file(a.ckpt), "input_sha256": src_sha, "device": "cpu", "seconds": round(t_inf, 2),
        "points_in": int(len(pts)), "points_out": a.max_points, "rounding": "3 decimals"}
step.pop("input_sha256")  # chain input = scene content hash; the source file hash is recorded below
step["source_file_sha256"] = src_sha
xml = x3dprov.add_step(xml, step)
(out / "open3d-segmentation.x3d").write_text(xml, encoding="utf-8")
prov = x3dprov.verify(xml)

# validators
sys.path.insert(0, str(Path(a.fork) / "src"))
from validation.validate import validate_xml  # noqa: E402
v = validate_xml(xml, "4.0")
fork_commit = subprocess.run(["git", "-C", a.fork, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()

# loop closure 1: read the X3D back (X3D -> Open3D) and compare with what was written
rd = B.read_x3d(xml)
tot = sum(len(p["points"]) for p in rd["pointclouds"])
seg = B.read_segmentation(xml)
sel_lab = lab[sel]
count_ok = all(seg[B.S3DIS_NAMES[k]]["count"] == int((sel_lab == k).sum()) for k in range(13) if (sel_lab == k).any())
allpts = np.concatenate([s["points"] for s in seg.values()])
# every written position must be within rounding (5e-4) of an original position (after the frame change)
from scipy.spatial import cKDTree
d, _ = cKDTree(X[sel]).query(allpts)
# loop closure 2: ML inference on the X3D-carried points, in the frame the bridge defines (class lens = shape 0, RGB lens = shape 1)
import lxml.etree as ET
root = ET.fromstring(xml.encode())
pts_b, rgb_b, lab_b = [], [], []
for g in root.iter("{*}Group"):
    if not (g.get("DEF") or "").startswith("class_"):
        continue
    meta = {m.get("name"): B._mfs1(m.get("value")) for m in g.find("{*}MetadataSet")}
    sw = g.find("{*}Switch")
    shapes = sw.findall("{*}Shape")
    co = shapes[0].find(".//{*}Coordinate")
    P_ = B._floats(co.get("point")).reshape(-1, 3)
    c_ = B._floats(shapes[1].find(".//{*}Color").get("color")).reshape(-1, 3)
    pts_b.append(P_); rgb_b.append(c_); lab_b += [int(meta["classId"])] * len(P_)
pts_b, rgb_b, lab_b = np.concatenate(pts_b), np.concatenate(rgb_b), np.array(lab_b)
Pb, _ = B.ml_frame_from_source(B.x3d_to_ml(pts_b), "z")
t1 = time.time()
lab2, sc2 = B.run_randlanet_s3dis(Pb, rgb_b, a.ckpt, a.cfg)
t_inf2 = time.time() - t1

# control: the same 50k points sent to the model directly (no X3D, no rounding), to separate density loss from bridge loss
Pd, _ = B.ml_frame_from_source(B.x3d_to_ml(X[sel]), "z")
lab_direct, _ = B.run_randlanet_s3dis(Pd, col[sel], a.ckpt, a.cfg)
# replicates (5 each): the pipeline samples centre points at random, so one run per arm cannot separate bridge from noise
REP = 5
dir_runs = [float((B.run_randlanet_s3dis(Pd, col[sel], a.ckpt, a.cfg)[0] == lab[sel]).mean()) for _ in range(REP)]
brg_runs = [float((B.run_randlanet_s3dis(Pb, rgb_b, a.ckpt, a.cfg)[0] == lab_b).mean()) for _ in range(REP)]
full_runs = [float((B.run_randlanet_s3dis(Pm, col, a.ckpt, a.cfg)[0] == lab).mean()) for _ in range(REP)]
names = B.S3DIS_NAMES
stats = {
    "schema": B.SCHEMA, "reference": B.REFERENCE,
    "source": {"name": "Redwood living-room fragment %d" % a.index, "file": os.path.basename(src), "sha256": src_sha,
               "points": int(len(pts)), "bbox_min": [round(float(x), 3) for x in pts.min(0)], "bbox_max": [round(float(x), 3) for x in pts.max(0)]},
    "model": {"name": "RandLANet", "dataset": "S3DIS", "ckpt": os.path.basename(a.ckpt), "ckpt_sha256": B.sha256_file(a.ckpt),
              "published_miou_torch": 70.9, "published_miou_source": "Open3D-ML README model zoo table"},
    "env": {"open3d": o3d.__version__, "torch": torch.__version__, "python": platform.python_version(), "device": "cpu",
            "cpu": platform.processor() or platform.machine()},
    "inference": {"seconds_full": round(t_inf, 2), "points": int(len(pts)), "seconds_bridged_subset": round(t_inf2, 2), "points_bridged": int(len(pts_b))},
    "classes": {n: {**{k: v for k, v in s.items()}, "full_count": int((lab == s["id"]).sum()), "full_share": round(float((lab == s["id"]).mean()), 4)} for n, s in st.items()},
    "repeat_agreement_same_input": round(float((lab == lab_rep).mean()), 4),
    "replicates": {"n_each": REP,
                   "direct_subset": {"runs": [round(x, 4) for x in dir_runs], "mean": round(float(np.mean(dir_runs)), 4), "sd": round(float(np.std(dir_runs, ddof=1)), 4)},
                   "bridged_subset": {"runs": [round(x, 4) for x in brg_runs], "mean": round(float(np.mean(brg_runs)), 4), "sd": round(float(np.std(brg_runs, ddof=1)), 4)},
                   "full_repeat": {"runs": [round(x, 4) for x in full_runs], "mean": round(float(np.mean(full_runs)), 4), "sd": round(float(np.std(full_runs, ddof=1)), 4)},
                   "note": "agreement with the first full-cloud run's labels; subset arms see 50,000 of 315,723 points"},
    "confidence": {"mean": round(float(sc.mean()), 4), "p10": round(float(np.percentile(sc, 10)), 4), "p90": round(float(np.percentile(sc, 90)), 4)},
    "frame_ablation": {"with_floor_at_zero": {names[k]: int((lab == k).sum()) for k in names},
                       "without_shift": {names[k]: int((lab_noshift == k).sum()) for k in names},
                       "agreement_between_the_two": round(float((lab == lab_noshift).mean()), 4)},
    "loop": {
        "x3d_pointsets_read": len(rd["pointclouds"]), "x3d_points_read": int(tot), "skipped": rd["skipped"],
        "class_counts_recovered_exactly": bool(count_ok),
        "max_position_error_m": round(float(d.max()), 5), "rounding_bound_m": 0.00087,
        "ml_on_direct_subset_agreement_with_original_labels": round(float((lab_direct == lab[sel]).mean()), 4),
        "ml_on_bridged_subset_agreement_with_original_labels": round(float((lab2 == lab_b).mean()), 4),
        "note": "second inference sees 50k of 315k points (random, seed 0), so agreement measures density sensitivity as well as the bridge",
    },
    "validators": {"x3d_mcp_fork": fork_commit, "xsd_valid": v["valid"], "xsd_errors": v["errors"], "schema": v["schema_version"],
                   "x3dprov": prov},
    "scene": {"bytes": len(xml.encode()), "sha256": hashlib.sha256(xml.encode()).hexdigest(), "points": a.max_points},
}
(out / "stats.json").write_text(json.dumps(stats, indent=1))
(out / "validate-receipt.json").write_text(json.dumps({"validator": "x3d_mcp fork %s validate_xml XSD 4.0" % fork_commit, "ok": bool(v["valid"] and prov["ok"]),
                                                       **stats["validators"], "file": "open3d-segmentation.x3d", "bytes": stats["scene"]["bytes"], "sha256": stats["scene"]["sha256"]}, indent=1))
ld = {"@context": {"o3dml": "https://github.com/isl-org/Open3D-ML#", "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"},
      "@id": "urn:x3d-open3d:s3dis-classes", "@type": "o3dml:SemanticLabelSet", "schema:name": "S3DIS 13-class label set as used by Open3D-ML RandLANet",
      "o3dml:classes": [{"@id": "o3dml:s3dis/%s" % names[k], "@type": "o3dml:SemanticClass", "o3dml:classId": k, "rdfs:label": names[k],
                         "schema:color": B.S3DIS_COLORS[k]} for k in names]}
(out / "semantics.jsonld").write_text(json.dumps(ld, indent=1))
print(json.dumps({k: stats[k] for k in ("inference", "confidence", "loop", "validators")}, indent=1))
print("frame ablation", stats["frame_ablation"])
