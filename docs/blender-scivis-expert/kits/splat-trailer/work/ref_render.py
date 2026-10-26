#!/usr/bin/env python3
"""Reference 3DGS rasteriser (numpy, float64): the oracle for splat fixtures.
usage: python -I ref_render.py FILE.x3d POSE.json OUT.png [--sh-degree D]
EWA projection (+0.3 px^2 low-pass), front-to-back alpha compositing, per-splat depth sort, SH colour (degree<=1 here), background over."""
import sys, re, json, math, struct, zlib
import numpy as np

C0, C1 = 0.28209479177387814, 0.4886025119029199

def read_x3d(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"<GaussianSplats\b([^>]*)/>", txt)
    attrs = dict(re.findall(r'\s([A-Za-z0-9]+)="([^"]*)"', m.group(1)))
    f = lambda k, w: np.array(attrs[k].split(), np.float32).astype(np.float64).reshape(-1, w)
    d = dict(pos=f("positions", 3), scale=f("scales", 3), quat=f("orientations", 4), op=f("opacities", 1)[:, 0], dc=f("sphericalHarmonicsDegree0Coef0", 3))
    d["sh1"] = np.stack([f(f"sphericalHarmonicsDegree1Coef{c}", 3) for c in range(3)], 1) if "sphericalHarmonicsDegree1Coef0" in attrs else None
    rest = []
    for deg in (1, 2, 3):
        for c in range(2 * deg + 1):
            k = f"sphericalHarmonicsDegree{deg}Coef{c}"
            if k in attrs: rest.append(f(k, 3))
    d["rest"] = np.stack(rest, 1) if rest else None      # [N, 15 or 8 or 3, 3] in INRIA f_rest order
    return d

def axis_angle_to_R(ax):
    x, y, z, a = ax; n = math.sqrt(x*x + y*y + z*z); x, y, z = x/n, y/n, z/n
    c, s = math.cos(a), math.sin(a); C = 1 - c
    return np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s], [y*x*C+z*s, c+y*y*C, y*z*C-x*s], [z*x*C-y*s, z*y*C+x*s, c+z*z*C]])

def quat_to_R(q):  # x y z w, vectorised
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    n = np.sqrt(x*x + y*y + z*z + w*w); x, y, z, w = x/n, y/n, z/n, w/n
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2*(y*y + z*z); R[:, 0, 1] = 2*(x*y - z*w); R[:, 0, 2] = 2*(x*z + y*w)
    R[:, 1, 0] = 2*(x*y + z*w); R[:, 1, 1] = 1 - 2*(x*x + z*z); R[:, 1, 2] = 2*(y*z - x*w)
    R[:, 2, 0] = 2*(x*z - y*w); R[:, 2, 1] = 2*(y*z + x*w); R[:, 2, 2] = 1 - 2*(x*x + y*y)
    return R

def render(d, pose, W, H, sh_degree=1, bg=(0, 0, 0), blur=0.3, xite_cull=False, near=0.1):
    pos_c = np.array(pose["position"], float); Rc = axis_angle_to_R(pose["orientation"])   # camera-to-world (OpenGL: looks -Z, up +Y)
    fov = pose["fieldOfView"]; f = (min(W, H) / 2) / math.tan(fov / 2)                      # X3D fieldOfView is the smaller angle
    # world -> OpenCV camera (x right, y down, z forward): flip y,z of the OpenGL camera frame
    flip = np.diag([1.0, -1.0, -1.0]); Rwc = flip @ Rc.T
    t = (d["pos"] - pos_c) @ Rwc.T                   # camera-space centres
    z = t[:, 2]; keep = z > (near if xite_cull else 0.2)
    Rq = quat_to_R(d["quat"]); S = d["scale"]
    cov = np.einsum("nij,nj,nkj->nik", Rq, S**2, Rq)  # R S^2 R^T
    covc = np.einsum("ij,njk,lk->nil", Rwc, cov, Rwc)
    # colour (view dependent SH degree 1), direction in world
    col = C0 * d["dc"]
    if sh_degree >= 1 and d["rest"] is not None:
        dirs = d["pos"] - pos_c; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        x, y, zz = dirs[:, 0:1], dirs[:, 1:2], dirs[:, 2:3]; sh = d["rest"]
        col = col - C1 * y * sh[:, 0] + C1 * zz * sh[:, 1] - C1 * x * sh[:, 2]
        if sh_degree >= 2 and sh.shape[1] >= 8:
            xx, yy, z2, xy, yz, xz = x*x, y*y, zz*zz, x*y, y*zz, x*zz
            col = col + 1.0925484305920792*xy*sh[:, 3] - 1.0925484305920792*yz*sh[:, 4] + 0.31539156525252005*(2*z2-xx-yy)*sh[:, 5] \
                - 1.0925484305920792*xz*sh[:, 6] + 0.5462742152960396*(xx-yy)*sh[:, 7]
            if sh_degree >= 3 and sh.shape[1] >= 15:
                col = col - 0.5900435899266435*y*(3*xx-yy)*sh[:, 8] + 2.890611442640554*xy*zz*sh[:, 9] - 0.4570457994644658*y*(4*z2-xx-yy)*sh[:, 10] \
                    + 0.3731763325901154*zz*(2*z2-3*xx-3*yy)*sh[:, 11] - 0.4570457994644658*x*(4*z2-xx-yy)*sh[:, 12] + 1.445305721320277*zz*(xx-yy)*sh[:, 13] \
                    - 0.5900435899266435*x*(xx-3*yy)*sh[:, 14]
    col = np.maximum(col + 0.5, 0.0)
    order = np.argsort(z); img = np.zeros((H, W, 3)); T = np.ones((H, W)); cx, cy = W / 2, H / 2
    for i in order:
        if not keep[i]: continue
        x, y, zi = t[i]
        J = np.array([[f/zi, 0, -f*x/zi**2], [0, f/zi, -f*y/zi**2]])
        c2 = J @ covc[i] @ J.T + blur * np.eye(2)
        det = c2[0, 0]*c2[1, 1] - c2[0, 1]**2
        if det <= 0: continue
        inv = np.array([[c2[1, 1], -c2[0, 1]], [-c2[0, 1], c2[0, 0]]]) / det
        u, v = f*x/zi + cx, f*y/zi + cy
        rad = 3*math.sqrt(max(c2[0, 0], c2[1, 1]))
        if xite_cull and (rad > min(W, H) or abs((u - cx) / cx) > 1.3 or abs((v - cy) / cy) > 1.3): continue   # X_ITE 16.5.1 vertex shader culls
        x0, x1, y0, y1 = int(max(0, math.floor(u-rad))), int(min(W, math.ceil(u+rad)+1)), int(max(0, math.floor(v-rad))), int(min(H, math.ceil(v+rad)+1))
        if x0 >= x1 or y0 >= y1: continue
        px, py = np.meshgrid(np.arange(x0, x1) + 0.5 - u, np.arange(y0, y1) + 0.5 - v)
        e = -0.5 * (inv[0, 0]*px*px + 2*inv[0, 1]*px*py + inv[1, 1]*py*py)
        a = np.minimum(0.99, d["op"][i] * np.exp(e)); a[a < 1/255] = 0
        img[y0:y1, x0:x1] += (T[y0:y1, x0:x1] * a)[..., None] * col[i]
        T[y0:y1, x0:x1] *= (1 - a)
    img += T[..., None] * np.array(bg)
    return np.clip(img, 0, 1), T

def write_png(path, rgb):
    a = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8); H, W, _ = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(H))
    def ch(t, data): return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw, 6)) + ch(b"IEND", b""))

if __name__ == "__main__":
    x3d, posef, out = sys.argv[1:4]; deg = int(sys.argv[sys.argv.index("--sh-degree") + 1]) if "--sh-degree" in sys.argv else 1
    pose = json.load(open(posef)); img, T = render(read_x3d(x3d), pose, pose["w"], pose["h"], deg, pose.get("bg", (0, 0, 0)), xite_cull=("--xite-cull" in sys.argv))
    write_png(out, img); print("wrote", out, img.shape, "mean", img.mean(axis=(0, 1)).round(4).tolist())
