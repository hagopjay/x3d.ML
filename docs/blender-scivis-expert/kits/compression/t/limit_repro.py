import sys, time, random
FORK=sys.argv[1]
sys.path[0:0]=[FORK+'/src',FORK]
from validation.validate import validate_xml
import validation.semantic as S
random.seed(1)
def fmt(dec): 
    return lambda lo,hi: f"{random.uniform(lo,hi):.{dec}f}"
def build(k, dec):
    f=fmt(dec)
    a=dict(
     positions=' '.join(f(-20,40) for _ in range(3*k)),
     scales=' '.join(f(-6,-3) for _ in range(3*k)),
     orientations=' '.join(f(-1,1) for _ in range(4*k)),
     opacities=' '.join(f(0,1) for _ in range(k)),
     sphericalHarmonicsDegree0Coef0=' '.join(f(-1,1) for _ in range(3*k)))
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<X3D version="4.1" profile="Immersive"><head><component name="GaussianSplats" level="1" /></head><Scene>\n<GaussianSplats '+' '.join(f'{k_}="{v}"' for k_,v in a.items())+' />\n</Scene></X3D>\n'
    return xml, max(len(v) for v in a.values())
for dec in (3,6):
  for k in [int(x) for x in sys.argv[2:]]:
    xml,big=build(k,dec); t=time.time()
    r=validate_xml(xml)
    t1=time.time()-t
    t=time.time()
    try:
        sd=S.semantic_diagnostics(xml); sem=f"semantic ok, {len(sd)} diags"
    except Exception as e:
        sem=f"semantic EXC {type(e).__name__}: {str(e)[:80]}"
    print(f"dec={dec} k={k:>7,d} file={len(xml)/1e6:5.1f}MB bigattr={big/1e6:4.1f}MB validate_xml valid={r.get('valid')} err={[e[:70] for e in r.get('errors',[])][:1]} {t1:.1f}s | {sem} {time.time()-t:.1f}s",flush=True)
