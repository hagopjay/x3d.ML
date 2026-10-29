import sys,time,random
from lxml import etree
FORK=sys.argv[1]
sch=etree.XMLSchema(etree.parse(FORK+'/src/validation/schemas/x3d-4.1.xsd'))
random.seed(1)
def build(k,dec):
    f=lambda lo,hi: f"{random.uniform(lo,hi):.{dec}f}"
    a=dict(positions=' '.join(f(-20,40) for _ in range(3*k)),scales=' '.join(f(-6,-3) for _ in range(3*k)),orientations=' '.join(f(-1,1) for _ in range(4*k)),opacities=' '.join(f(0,1) for _ in range(k)),sphericalHarmonicsDegree0Coef0=' '.join(f(-1,1) for _ in range(3*k)))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<X3D version="4.1" profile="Immersive"><head><component name="GaussianSplats" level="1" /></head><Scene>\n<GaussianSplats '+' '.join(f'{k_}="{v}"' for k_,v in a.items())+' />\n</Scene></X3D>\n', max(len(v) for v in a.values())
p=etree.XMLParser(huge_tree=True)
for dec in (3,6):
  for k in [int(x) for x in sys.argv[2:]]:
    xml,big=build(k,dec); t=time.time()
    doc=etree.fromstring(xml.encode(),p)
    for e in doc.iter():
        for a in list(e.attrib):
            if a.startswith('{'): del e.attrib[a]
    try:
        v=sch.validate(doc); r=f"valid={v} {[str(x.message)[:60] for x in sch.error_log][:1]}"
    except Exception as e: r=f"EXC {type(e).__name__}: {e}"
    print(f"dec={dec} k={k:>7,d} bigattr={big/1e6:5.1f}MB huge_tree+XSD4.1 {r} {time.time()-t:.1f}s",flush=True)
