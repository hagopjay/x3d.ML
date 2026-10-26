"""Measure the cube's colour in a still the way design checks FILM v1.8 (design/src/cube_tone.py).

Central crop of the picture (--crop, a share of each side; --box x0,y0,x1,y1 in pixels picks the picture inside a framed
master first); per-pixel luma 0.2126 R + 0.7152 G + 0.0722 B on the sRGB values; the darkest share (--share, 0.15) of the
crop is the letter, the brightest share the lit wall. With --whole the crop is one surface (a waiting wall): its mean only.
For each set: mean sRGB, R/B and luma. FILM v1.8's targets in the stills: lit R/B about 1.25, letters about 0.9, the
waiting wall about 0.65, levels as in v1_7c (letters about 60, waiting wall about 48, lit about 137 in X_ITE).

Usage: python3 cube_colour.py [--crop 0.5] [--share 0.15] [--whole] [--box x0,y0,x1,y1] [--json out.json] img [img ...]
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("imgs", nargs="+")
ap.add_argument("--crop", type=float, default=0.5)
ap.add_argument("--share", type=float, default=0.15)
ap.add_argument("--whole", action="store_true")
ap.add_argument("--box", default="")
ap.add_argument("--json", default="")
A = ap.parse_args()


def stats(px):
    m = px.mean(axis=0)
    return {"srgb": [round(float(v), 1) for v in m], "rb": round(float(m[0] / max(m[2], 1e-6)), 3),
            "luma": round(float(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]), 1), "n": int(len(px))}


out = []
for f in A.imgs:
    im = np.asarray(Image.open(f).convert("RGB")).astype(float)
    if A.box:
        x0, y0, x1, y1 = (int(v) for v in A.box.split(","))
        im = im[y0:y1, x0:x1]
    h, w = im.shape[:2]; ch, cw = int(h * A.crop), int(w * A.crop)
    c = im[(h - ch) // 2:(h - ch) // 2 + ch, (w - cw) // 2:(w - cw) // 2 + cw].reshape(-1, 3)
    y = c @ np.array([0.2126, 0.7152, 0.0722])
    r = {"img": os.path.basename(f), "crop": A.crop}
    if A.whole:
        r["whole"] = stats(c)
    else:
        lo, hi = np.quantile(y, A.share), np.quantile(y, 1 - A.share)
        r["letter"] = stats(c[y <= lo]); r["lit"] = stats(c[y >= hi])
    out.append(r)
    print(r["img"], " ".join(f"{k} luma {v['luma']} R/B {v['rb']} sRGB {v['srgb']}" for k, v in r.items() if isinstance(v, dict)))
if A.json:
    json.dump(out, open(A.json, "w"), indent=1)
