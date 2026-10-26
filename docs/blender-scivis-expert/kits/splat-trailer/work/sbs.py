import sys, numpy as np
sys.path.insert(0, '.')
from cmp_png import read_png
from ref_render import write_png
r = read_png(sys.argv[1]); x = read_png(sys.argv[2]); d = np.abs(r - x).clip(0, 255) * 2
write_png(sys.argv[3], np.concatenate([r, x, d], 1) / 255.0)
