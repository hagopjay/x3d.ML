#!/usr/bin/env python3
"""never_black.py <video> <fps> <out.json>: per-frame light statistics of a film (decoded by ffmpeg at <fps>, 240 x 180 grey of the max channel)
and the longest stretches with no light in frame. A frame has light if its 99.9th percentile (max of R, G, B) reaches 40 of 255."""
import sys, json, subprocess
import numpy as np
vid, fps, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
W, H = 240, 180
p = subprocess.run(["ffmpeg", "-v", "error", "-i", vid, "-vf", f"fps={fps},scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
a = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3).max(-1).reshape(-1, H * W).astype(float)
p999 = np.percentile(a, 99.9, axis=1); mean = a.mean(1)
lit = p999 >= 40
runs = []; s = None
for i, v in enumerate(list(lit) + [True]):
    if not v and s is None: s = i
    if v and s is not None: runs.append((s / fps, i / fps)); s = None
runs.sort(key=lambda r: r[0] - r[1])
rep = {"video": vid.split("/")[-1], "fps_sampled": fps, "frames": int(len(a)), "rule": "a frame has light if its 99.9th percentile (max channel, 240 x 180) is at least 40 of 255",
       "longest_dark_s": [[round(x, 2), round(y, 2), round(y - x, 2)] for x, y in runs[:6]],
       "dark_share": round(float((~lit).mean()), 4), "mean_luma_255": round(float(mean.mean()), 2)}
json.dump({**rep, "p999": [round(float(v), 1) for v in p999], "mean": [round(float(v), 2) for v in mean]}, open(out, "w"))
print(json.dumps(rep))
