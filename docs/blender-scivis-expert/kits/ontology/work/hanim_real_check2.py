import rdflib, json, sys, time
sys.path.insert(0,'.')
from hanim_py import Vocab, check
V=Vocab(); res=[]; tot=0; allr1={}
import os
for f in open('hanim_keep.txt').read().split():
    ttl='hanim_ttl/'+f.replace('.x3d','.ttl')
    if not os.path.exists(ttl):
        from conv import convert
        convert('hanim_real/'+f, ttl)
    g=rdflib.Graph(); g.parse(ttl,format='turtle')
    n,r1,r2=check(g,V); tot+=n
    res.append((f.replace('HumanoidAnimation__',''),n,len(r1),len(r2),sorted(set(x[0] for x in r1))[:8],r2[:3]))
    print(res[-1],flush=True)
print('scenes',len(res),'joints',tot,'R1',sum(r[2] for r in res),'R2',sum(r[3] for r in res))
json.dump(res,open('hanim_real_check.json','w'),indent=0)
