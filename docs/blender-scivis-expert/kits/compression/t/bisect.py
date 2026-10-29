import sys
from lxml import etree
FORK=sys.argv[1]
sch=etree.XMLSchema(etree.parse(FORK+'/src/validation/schemas/x3d-4.1.xsd'))
p=etree.XMLParser(huge_tree=True)
def ok(nchars):
    vals=' '.join(['0.123456']*(nchars//9))
    # positions is the biggest attr; keep multiple of 3
    n=len(vals.split()); n-=n%3; vals=' '.join(['0.123456']*n)
    xml=f'<X3D version="4.1" profile="Immersive"><head><component name="GaussianSplats" level="1" /></head><Scene><GaussianSplats positions="{vals}" /></Scene></X3D>'
    doc=etree.fromstring(xml.encode(),p)
    try: sch.validate(doc); return True
    except Exception as e: return False
lo,hi=8_000_000,24_000_000
while hi-lo>200_000:
    m=(lo+hi)//2
    if ok(m): lo=m
    else: hi=m
print("attr chars: passes up to ~",lo,"fails from ~",hi, "2^24=16777216 2^23.7?")
