import sys, os, json, zlib, struct
import numpy as np
def read_png(p):
    b = open(p, "rb").read(); i = 8; idat = b""; W = H = ct = bd = None
    while i < len(b):
        n = struct.unpack(">I", b[i:i+4])[0]; t = b[i+4:i+8]; d = b[i+8:i+8+n]; i += 12 + n
        if t == b"IHDR": W, H, bd, ct = struct.unpack(">IIBB", d[:10])
        elif t == b"IDAT": idat += d
    raw = zlib.decompress(idat); ch = {2: 3, 6: 4}[ct]; stride = W * ch; out = np.zeros((H, stride), np.uint8); prev = np.zeros(stride, np.int32); pos = 0
    for y in range(H):
        f = raw[pos]; line = np.frombuffer(raw[pos+1:pos+1+stride], np.uint8).astype(np.int32); pos += 1 + stride
        if f == 0: cur = line
        elif f == 1:
            cur = line.copy()
            for x in range(ch, stride): cur[x] = (cur[x] + cur[x-ch]) & 255
        elif f == 2: cur = (line + prev) & 255
        elif f == 3:
            cur = line.copy()
            for x in range(stride): cur[x] = (cur[x] + (((cur[x-ch] if x >= ch else 0) + prev[x]) >> 1)) & 255
        elif f == 4:
            cur = line.copy()
            for x in range(stride):
                a = cur[x-ch] if x >= ch else 0; bb = prev[x]; c = prev[x-ch] if x >= ch else 0; p = a + bb - c
                pa, pb, pc = abs(p-a), abs(p-bb), abs(p-c); pr = a if pa <= pb and pa <= pc else (bb if pb <= pc else c)
                cur[x] = (cur[x] + pr) & 255
        out[y] = cur; prev = cur
    return out.reshape(H, W, ch)[..., :3].astype(np.float64)
def psnr(a, b): 
    m = ((a-b)**2).mean(); return 99.0 if m == 0 else 10*np.log10(255**2/m)
REF = sys.argv[2] if len(sys.argv) > 2 else "ref"; DIR = sys.argv[3] if len(sys.argv) > 3 else "fx"
if __name__ == "__main__":
    for t in os.environ.get("TAGS", "sh0,sh1").split(","):
        for p in ("A_front", "B_oblique", "C_close"):
            r = read_png(f"{DIR}/{REF}_{t}_{p}.png"); x = read_png(sys.argv[1].replace("TAG", t) + f"/{p}.png")
            d = np.abs(r - x)
            print(t, p, "PSNR %.2f dB" % psnr(r, x), "mean|d| %.2f" % d.mean(), "p99|d| %.1f" % np.percentile(d, 99), "max %d" % d.max(), "means ref", r.mean((0,1)).round(1).tolist(), "xite", x.mean((0,1)).round(1).tolist())
