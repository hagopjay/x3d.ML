import sys,time
sys.path.insert(0,sys.argv[1])
from src.validation import validate as V
from lxml import etree
patched = len(sys.argv)>2
if patched:
    P=etree.XMLParser(huge_tree=True,resolve_entities=False,no_network=True)
    orig=etree.fromstring
    class E:
        def __getattr__(s,n): return getattr(etree,n)
        @staticmethod
        def fromstring(x,*a,**k): return orig(x,P)
    V.etree=E()
for n in ["n36000_sh1","n41000_sh1","n14000_sh3","n16000_sh3"]:
    s=open(f"{sys.argv[3] if len(sys.argv)>3 else '/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/hall-build/huge'}/{n}.x3d",encoding="utf-8").read()
    t=time.time()
    try:r=V.validate_xml(s)
    except Exception as e:r={"EXC":repr(e)[:200]}
    print(n,len(s),r.get("valid"),str(r.get("errors") or r)[:160],round(time.time()-t,1))
