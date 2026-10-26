import sys, json, numpy as np
from PIL import Image
def measure(png, man, w=1400, h=600, ppu=100, x0=-1.0, y_top=1.0):
    im = np.asarray(Image.open(png).convert('RGB')).astype(float)
    sx, sy = im.shape[1] / w, im.shape[0] / h
    out = []
    for p in man:
        cx = (p['x'] - x0) * ppu * sx; cy = (y_top - p['y']) * ppu * sy
        r = 12 * sx
        patch = im[int(cy - r):int(cy + r), int(cx - r):int(cx + r)].reshape(-1, 3)
        out.append(patch.mean(0))
    return np.array(out)
if __name__ == '__main__':
    man = json.load(open(sys.argv[1] + '.json'))
    for png in sys.argv[2:]:
        m = measure(png, man)
        print(png.split('/')[-2] if '/' in png else png, m[:3].round(1).tolist())
