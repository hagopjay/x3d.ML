"""Demo 81 v2: Open3D-ML RandLA-Net (S3DIS) on Rohbau3D shell-construction scans (CC BY 4.0), scored against its ground truth.

Usage: python build_rohbau.py OUT_DIR --scenes DIR/site_02 --ckpt ... --cfg ... --fork x3d_mcp [--show scene_02009]
Rohbau3D: Rauch et al., Univ. der Bundeswehr Munchen, https://doi.org/10.60776/ZWJFI4 (CC BY 4.0).
The 18 Rohbau classes are mapped to the 13 S3DIS classes only where the meaning is the same; everything else is left out of the score.
"""
import argparse, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "src"))
import x3do3d as B  # noqa: E402
import x3dprov  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--scenes", required=True); ap.add_argument("--ckpt", required=True)
ap.add_argument("--cfg", required=True); ap.add_argument("--fork", required=True)
ap.add_argument("--list", default="scene_02009,scene_02010,scene_02000"); ap.add_argument("--show", default="scene_02009")
ap.add_argument("--points", type=int, default=400000); ap.add_argument("--reps", type=int, default=3); ap.add_argument("--shown", type=int, default=50000)
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
import open3d as o3d, torch  # noqa: E402

ROHBAU = {0: "None", 1: "Ceiling", 2: "Slanted Ceiling", 3: "Ceiling Cutout", 4: "Floor", 5: "Wall", 6: "Drywall", 7: "Wall Cutout", 8: "Parapet",
          9: "Beam", 10: "Column", 11: "Staircase", 12: "Window Cutout", 13: "Window", 14: "Door Rough Opening", 15: "Facade Element", 16: "Elevator Doors", 17: "TGA"}
# same meaning only; cutouts, openings, parapet, staircase, facade, lift doors, TGA, None are NOT scored
MAP = {1: 0, 2: 0, 3: 0, 4: 1, 5: 2, 6: 2, 9: 3, 10: 4, 13: 5}
NAMES = B.S3DIS_NAMES
ck_sha = B.sha256_file(a.ckpt)

def score(lab, gt):
    g = np.array([MAP.get(int(x), -1) for x in gt]); ok = g >= 0
    res = {"scored_points": int(ok.sum()), "accuracy": float((lab[ok] == g[ok]).mean()), "classes": {}}
    ious = []
    for c in sorted(set(MAP.values())):
        t = g == c
        if t.sum() < 100:
            continue
        p = (lab == c) & ok
        iou = float((t & p).sum() / max(1, (t | p).sum())); ious.append(iou)
        res["classes"][NAMES[c]] = {"gt_points": int(t.sum()), "recall": float((lab[t] == c).mean()), "iou": iou}
    res["miou"] = float(np.mean(ious)) if ious else None
    conf = np.zeros((6, 13), dtype=np.int64)
    for gi in range(6):
        conf[gi] = np.bincount(lab[g == gi], minlength=13)
    res["confusion_rows_gt_ceiling_floor_wall_beam_column_window"] = conf.tolist()
    return res, g

scenes, shown = {}, None
for sc in a.list.split(","):
    d = Path(a.scenes) / sc
    c0 = np.load(d / "coord.npy"); k = np.load(d / "class.npy").ravel().astype(int); col = np.load(d / "color.npy", mmap_mode="r")
    sel = np.sort(np.random.default_rng(0).choice(len(c0), min(a.points, len(c0)), replace=False))
    P = c0[sel].astype(np.float64); rgb = np.asarray(col[sel], np.float32) / 255.0; gt = k[sel]
    Pm, off = B.ml_frame_from_source(P, "z")
    runs, secs = [], []
    for r in range(a.reps):
        t = time.time(); lab, conf = B.run_randlanet_s3dis(Pm, rgb, a.ckpt, a.cfg); secs.append(time.time() - t)
        res, g = score(lab, gt); runs.append(res)
        if r == 0:
            first = (lab, conf, g)
    acc = [x["accuracy"] for x in runs]; mi = [x["miou"] for x in runs]
    scenes[sc] = {"file_points": int(len(c0)), "points_used": int(len(sel)), "seconds_per_run": [round(s, 1) for s in secs],
                  "gt_counts": {ROHBAU[i]: int(n) for i, n in enumerate(np.bincount(gt, minlength=18)) if n},
                  "pred_counts": {NAMES[i]: int(n) for i, n in enumerate(np.bincount(first[0], minlength=13)) if n},
                  "accuracy_mean": round(float(np.mean(acc)), 4), "accuracy_sd": round(float(np.std(acc, ddof=1)), 4),
                  "miou_mean": round(float(np.mean(mi)), 4), "miou_sd": round(float(np.std(mi, ddof=1)), 4),
                  "first_run": runs[0], "bbox_min": [round(float(x), 2) for x in c0.min(0)], "bbox_max": [round(float(x), 2) for x in c0.max(0)]}
    print(sc, scenes[sc]["accuracy_mean"], scenes[sc]["miou_mean"], flush=True)
    if sc == a.show:
        shown = (Pm, rgb, gt, first)

Pm, rgb, gt, (lab, conf, g) = shown
X = B.ml_to_x3d(Pm)
correct = np.where((g < 0)[:, None], [0.35, 0.35, 0.38], np.where((lab == g)[:, None], [0.25, 0.85, 0.45], [0.95, 0.25, 0.3]))
gtcol = np.array([B._hex_to_rgb(B.S3DIS_COLORS[int(v)]) if v >= 0 else [0.35, 0.35, 0.38] for v in g])
src = Path(a.scenes) / a.show
metas = [("x3do3d.model", "Open3D-ML RandLANet torch, S3DIS (checkpoint randlanet_s3dis_202201071330utc.pth)"), ("x3do3d.ckpt_sha256", ck_sha),
         ("x3do3d.open3d", o3d.__version__), ("x3do3d.torch", torch.__version__), ("x3do3d.device", "cpu"),
         ("x3do3d.source", "Rohbau3D %s/%s, CC BY 4.0, doi:10.60776/ZWJFI4, Rauch et al." % (Path(a.scenes).name, a.show)),
         ("x3do3d.source_coord_sha256", B.sha256_file(src / "coord.npy")), ("x3do3d.points_inferred", len(Pm)), ("x3do3d.points_shown", a.shown),
         ("x3do3d.score_mapping", "ceiling<-Ceiling,Slanted Ceiling,Ceiling Cutout; floor<-Floor; wall<-Wall,Drywall; beam<-Beam; column<-Column; window<-Window; others unscored")]
xml, st = B.segmentation_to_x3d(X, lab, NAMES, B.S3DIS_COLORS, rgb=rgb, scores=conf, max_points=a.shown, metas=metas,
                                title="Open3D-ML on Rohbau3D shell scan (%s)" % a.show, point_size=2.0,
                                extra_lenses={"correct": correct, "groundtruth": gtcol})
step = {"kind": "ml-inference", "tool": "Open3D-ML RandLANet S3DIS", "open3d": o3d.__version__, "torch": torch.__version__, "ckpt_sha256": ck_sha,
        "device": "cpu", "points_in": int(len(Pm)), "points_out": a.shown, "source_dataset": "Rohbau3D CC BY 4.0 doi:10.60776/ZWJFI4", "rounding": "3 decimals"}
xml = x3dprov.add_step(xml, step)
(out / "open3d-rohbau.x3d").write_text(xml, encoding="utf-8")
sys.path.insert(0, str(Path(a.fork) / "src"))
from validation.validate import validate_xml  # noqa: E402
v = validate_xml(xml, "4.0"); prov = x3dprov.verify(xml)
seg = B.read_segmentation(xml)
fork_commit = subprocess.run(["git", "-C", a.fork, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
stats = {"schema": "open3d-ml-bridge/v2", "dataset": {"name": "Rohbau3D", "site": Path(a.scenes).name, "doi": "10.60776/ZWJFI4", "licence": "CC BY 4.0",
         "authors": "Lukas Rauch et al., Universitat der Bundeswehr Munchen", "licence_checked": "Dataverse API latestVersion.license, 26 Nov 2026"},
         "model": {"ckpt": Path(a.ckpt).name, "ckpt_sha256": ck_sha}, "env": {"open3d": o3d.__version__, "torch": torch.__version__, "python": platform.python_version(), "device": "cpu"},
         "mapping": {ROHBAU[k]: NAMES[v] for k, v in MAP.items()}, "scenes": scenes, "shown_scene": a.show, "classes": st,
         "x3d": {"bytes": len(xml.encode()), "sha256": hashlib.sha256(xml.encode()).hexdigest(), "classes_read_back": {n: s["count"] for n, s in seg.items()},
                 "xsd_valid": v["valid"], "xsd_errors": v["errors"], "validator": "x3d_mcp fork " + fork_commit, "x3dprov": prov, "lenses": "class,rgb,confidence,correct,groundtruth"}}
(out / "stats.json").write_text(json.dumps(stats, indent=1))
(out / "validate-receipt.json").write_text(json.dumps({"validator": "x3d_mcp fork %s validate_xml XSD 4.0" % fork_commit, "ok": bool(v["valid"] and prov["ok"]), "xsd_valid": v["valid"], "xsd_errors": v["errors"], "x3dprov": prov, "bytes": stats["x3d"]["bytes"], "sha256": stats["x3d"]["sha256"]}, indent=1))
print("xsd", v["valid"], prov["status"])
