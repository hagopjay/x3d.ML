import numpy as np, os
def make_ply(path, n, deg, rng):
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


