import rdflib, re, time, json, sys, os
sys.path.insert(0,'.')
from conv import convert
shapes=open('xb-shapes.ttl').read()
pref="""PREFIX xb: <urn:x3dio:bridge#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX owl: <http://www.w3.org/2002/07/owl#> """
def q(name):
    m=re.search(r'xb:%s_.*?sh:select """(.*?)"""'%name, shapes, re.S)
    return pref+m.group(1).replace('$this','?this')
Q1,Q2=q('R1'),q('R2')
vocab=rdflib.Graph(); vocab.parse('xb-hanim.ttl',format='turtle')
res=[]
tot_j=0
for f in open('hanim_keep.txt').read().split():
    ttl='hanim_ttl/'+f.replace('.x3d','.ttl')
    try:
        convert('hanim_real/'+f, ttl)
    except Exception as e:
        res.append((f,'convert-fail',str(e)[:80])); continue
    g=rdflib.Graph(); g.parse(ttl,format='turtle'); g+=vocab
    nj=len(list(g.query(pref+"SELECT DISTINCT ?j WHERE { ?j a x3do:HAnimJoint ; x3do:name ?n . FILTER NOT EXISTS { ?j owl:sameAs ?d } }")))
    r1=sorted({(str(r.value)) for r in g.query(Q1)})
    r2=sorted({(str(r.n),str(r.m),str(r.expected)) for r in g.query(Q2)})
    tot_j+=nj
    res.append((f.replace('HumanoidAnimation__',''),nj,len(r1),len(r2),r1[:6],r2[:4]))
    print(res[-1],flush=True)
json.dump(res,open('hanim_real_check.json','w'),default=str,indent=0)
print('scenes',len(res),'joints',tot_j,'R1 total',sum(r[2] for r in res if isinstance(r[2],int)),'R2 total',sum(r[3] for r in res if isinstance(r[3],int)))
