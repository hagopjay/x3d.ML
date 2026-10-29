import json, math, numpy as np
def lookat(pos, target, up=(0, 1, 0)):
    pos = np.array(pos, float); fwd = np.array(target, float) - pos; fwd /= np.linalg.norm(fwd)
    r = np.cross(fwd, up); r /= np.linalg.norm(r); u = np.cross(r, fwd); R = np.stack([r, u, -fwd], 1)
    ang = math.acos(max(-1, min(1, (np.trace(R) - 1) / 2)))
    if abs(ang) < 1e-9: ax = [0, 1, 0]
    elif abs(ang - math.pi) < 1e-6:
        i = int(np.argmax(np.diag(R))); v = np.sqrt(np.maximum((np.diag(R) + 1) / 2, 0)); ax = v.tolist()
    else: ax = (np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(ang))).tolist()
    return list(map(float, pos)), [float(x) for x in ax] + [float(ang)]
W, H = 640, 360
poses = {}
for name, pos, tgt, fov in (("A_front", (0, 1.8, 7.5), (0, 1.2, 0), 0.9), ("B_oblique", (5.5, 2.6, 4.5), (0, 1.0, 0), 0.9), ("C_close", (-1.2, 1.1, 3.2), (0.4, 1.2, 0), 1.0)):
    p, o = lookat(pos, tgt); poses[name] = dict(position=p, orientation=o, fieldOfView=fov, w=W, h=H)
json.dump(poses, open("fx/poses.json", "w"), indent=1)
json.dump([dict(name=k, position=v["position"], orientation=v["orientation"], fieldOfView=v["fieldOfView"]) for k, v in poses.items()], open("fx/shots.json", "w"), indent=1)
for k, v in poses.items(): json.dump(v, open(f"fx/pose_{k}.json", "w"))
print(json.dumps(poses)[:400])
