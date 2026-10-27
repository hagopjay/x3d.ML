"""3D layout for the graph that replaces the gobbler's network. Deterministic (seeded).
Scene units are the gobbler's (1 unit = 100 design px; the head spans x -2.8..4.8, y 2.7..-5.2). The graph grows out of the neck
base to the right as a flattened cone; every flywheel loop is a ring (a wheel) of its steps, rings stacked along the cone axis."""
import math
import numpy as np

ROOT = np.array([4.1, -3.7, 0.0])
AXIS = np.array([0.975, 0.22, 0.0]); AXIS /= np.linalg.norm(AXIS)
UPV = np.array([-0.22, 0.975, 0.0])
ZV = np.array([0.0, 0.0, 1.0])

SPREAD = 1.0      # deep builds widen the cone so a few thousand stars fit around the core

def cone_radius(s):          # allowed radius at distance s along the axis: (y-ish, z) semi-axes of an elliptical cone
    return (1.1 + 0.36 * s) * SPREAD, (1.3 + 0.78 * s) * SPREAD

def ell(rel_up, rel_z, s):
    ry, rz = cone_radius(s)
    return np.sqrt((rel_up / ry) ** 2 + (rel_z / rz) ** 2)

def layout(n, edges, weights, loops, cls_idx, seed=11, iters=420, length=11.0):
    """edges: list of (a, b, w); weights 0..1 (hubness); loops: list of lists of node ids (cycle order); cls_idx: class index per node."""
    rng = np.random.default_rng(seed)
    w = np.asarray(weights, float)
    # start positions: hubs near the root, leaves further out
    s0 = (1.0 - w) ** 0.8 * length * rng.uniform(0.55, 1.0, n)
    ang = rng.uniform(0, 2 * math.pi, n)
    ry0, rz0 = cone_radius(s0); rr = np.sqrt(rng.uniform(0.05, 1, n)) * 0.8
    pos = ROOT + np.outer(s0, AXIS) + np.outer(ry0 * rr * np.cos(ang), UPV) + np.outer(rz0 * rr * np.sin(ang), ZV)
    # rings
    ring = {}   # node -> (target)
    centers = []
    for li, L in enumerate(loops):
        m = len(L)
        s = 2.6 + (length - 4.2) * (li + 0.5) / max(1, len(loops))
        c = ROOT + AXIS * s + UPV * rng.uniform(-0.6, 0.6) + ZV * rng.uniform(-2.2, 2.2) * (0.4 + 0.1 * s)
        R = 0.8 + 0.2 * m
        tilt = rng.uniform(-0.6, 0.6); tilt2 = rng.uniform(-0.5, 0.5)
        nrm = np.array([math.sin(tilt2), math.sin(tilt), math.cos(tilt) * math.cos(tilt2)]); nrm /= np.linalg.norm(nrm)
        u = np.cross(nrm, [0, 1, 0]); 
        if np.linalg.norm(u) < 1e-3: u = np.cross(nrm, [1, 0, 0])
        u /= np.linalg.norm(u); v = np.cross(nrm, u)
        ph = rng.uniform(0, 2 * math.pi)
        centers.append((c, R, nrm, u, v))
        for k, nid in enumerate(L):
            a = ph + 2 * math.pi * k / m
            ring[nid] = c + R * (math.cos(a) * u + math.sin(a) * v)
    for nid, t in ring.items():
        pos[nid] = t
    E = np.array([(a, b) for a, b, _ in edges], int) if edges else np.zeros((0, 2), int)
    EW = np.array([ww for _, _, ww in edges], float) if edges else np.zeros(0)
    cls = np.asarray(cls_idx, int)
    ncls = cls.max() + 1 if n else 1
    ccen = np.array([ROOT + AXIS * (2.5 + length * 0.8 * (k + 0.5) / ncls) + UPV * 1.6 * math.sin(k * 2.4) + np.array([0, 0, 2.2 * math.cos(k * 1.7)]) for k in range(ncls)])
    fixed = np.zeros(n, bool)
    for nid in ring: fixed[nid] = True
    # Fruchterman-Reingold: repulsion k^2/d, attraction d^2/k along edges (heavier edges pull harder), a soft pull to the cone's axis,
    # a weak pull to the class centroid, and a soft cone: nodes that leave it are pulled back (never clamped onto its surface).
    vol = math.pi * 3.0 * 6.0 * length / 3.0
    k = 0.62 * (vol / max(n, 1)) ** (1.0 / 3.0)
    T0 = 0.9
    for it in range(iters):
        T = T0 * (1.0 - it / iters) ** 1.5 + 0.015
        f = np.zeros_like(pos)
        for a0 in range(0, n, 600):                                                   # repulsion in row blocks: a few thousand nodes stay inside memory
            d = pos[a0:a0 + 600, None, :] - pos[None, :, :]
            dist = np.sqrt((d ** 2).sum(-1)) + 0.05
            f[a0:a0 + 600] = (d / dist[..., None] * (k * k / dist)[..., None]).sum(1)
        if len(E):
            dv = pos[E[:, 1]] - pos[E[:, 0]]; dl = np.linalg.norm(dv, axis=1) + 1e-6
            fa = dv / dl[:, None] * (dl ** 2 / k * (0.5 + EW))[:, None]
            np.add.at(f, E[:, 0], fa); np.add.at(f, E[:, 1], -fa)
        rel = pos - ROOT; s_raw = rel @ AXIS
        radial = rel - np.outer(s_raw, AXIS)
        f -= radial * 0.18 * (1.0 + 0.5 * (1.0 - w))[:, None]                       # soft pull to the axis
        f += np.outer(np.clip(3.0 + 5.0 * w - s_raw, -2, 2) * 0.25, AXIS)             # heavy nodes sit nearer the neck
        f += (ccen[cls] - pos) * 0.012
        s_c = np.clip(s_raw, 0.8, length)
        e = ell(radial @ UPV, radial @ ZV, s_c)
        f -= radial * (np.maximum(e - 1.0, 0) * 5.0)[:, None]
        f -= np.outer(np.maximum(s_raw - length, 0) * 4.0, AXIS)
        f += np.outer(np.maximum(1.6 - s_raw, 0) * 6.0, AXIS)                          # clear of the neck
        fl = np.linalg.norm(f, axis=1) + 1e-9
        step_ = np.minimum(fl, T) / fl
        pos += f * step_[:, None]
        rel = pos - ROOT; s_new = rel @ AXIS; pos += np.outer(np.clip(s_new, 1.0, length + 0.6) - s_new, AXIS)
        for nid, t in ring.items(): pos[nid] = t
    for nid, t in ring.items(): pos[nid] = t
    # drift hubs slightly toward the root for the tether
    return pos, [dict(center=c.tolist(), radius=R, normal=n_.tolist(), u=u.tolist(), v=v.tolist()) for (c, R, n_, u, v) in centers]


def place_free(pos, cls_idx, ncls, length=11.0, seed=5, cand=14):
    """Untethered stars: best-candidate sampling inside the cone, biased toward their class centre, each new star placed where it is furthest from what is already there."""
    rng = np.random.default_rng(seed)
    placed = [p for p in pos]; allp = np.array(placed)
    ccen = np.array([ROOT + AXIS * (2.5 + length * 0.8 * (k + 0.5) / max(ncls, 1)) + UPV * 1.6 * math.sin(k * 2.4) + np.array([0, 0, 2.2 * math.cos(k * 1.7)]) for k in range(max(ncls, 1))])
    out = []
    for c in cls_idx:
        best = None; bd = -1
        for _ in range(cand):
            s = float(np.clip(rng.normal(((ccen[c] - ROOT) @ AXIS), 2.4), 1.8, length))
            ry, rz = cone_radius(s); a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0.02, 1.0)) * 0.95
            q = ROOT + AXIS * s + UPV * ry * r * math.cos(a) + ZV * rz * r * math.sin(a)
            d = np.min(np.linalg.norm(allp - q, axis=1))
            if d > bd: bd = d; best = q
        out.append(best); allp = np.vstack([allp, best])
    return out
