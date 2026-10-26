import sys,time,random
FORK=sys.argv[1]; sys.path[0:0]=[FORK+'/src',FORK]
from validation.validate import validate_xml
random.seed(2)
def node(k,dec=6):
    f=lambda lo,hi: f"{random.uniform(lo,hi):.{dec}f}"
    a=dict(positions=' '.join(f(-20,40) for _ in range(3*k)),scales=' '.join(f(-6,-3) for _ in range(3*k)),orientations=' '.join(f(-1,1) for _ in range(4*k)),opacities=' '.join(f(0,1) for _ in range(k)),sphericalHarmonicsDegree0Coef0=' '.join(f(-1,1) for _ in range(3*k)))
    return '<GaussianSplats '+' '.join(f'{k_}="{v}"' for k_,v in a.items())+' />\n'
for nodes,k in ((1,100000),(6,60000),(10,70000)):
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<X3D version="4.1" profile="Immersive"><head><component name="GaussianSplats" level="1" /></head><Scene>\n'+''.join(node(k) for _ in range(nodes))+'</Scene></X3D>\n'
    t=time.time(); r=validate_xml(xml)
    print(f"{nodes} node(s) x {k:,} splats = {nodes*k:,} splats, file {len(xml)/1e6:.1f} MB: valid={r['valid']} {[e[:110] for e in r['errors']][:1]} {time.time()-t:.1f}s",flush=True)
