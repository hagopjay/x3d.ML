"""Fast equivalent of shapes R1/R2 (same semantics, no rdflib join planning): used for batch runs."""
import rdflib, json
from rdflib import Namespace, RDF
X3DO=Namespace('https://www.web3d.org/specifications/X3dOntology4.1#'); XB=Namespace('urn:x3dio:bridge#'); OWL=rdflib.OWL
class Vocab:
    def __init__(self, path='xb-hanim.ttl'):
        g=rdflib.Graph(); g.parse(path,format='turtle')
        self.names={}; self.parent={}; self.alias={}
        for j in g.subjects(RDF.type, XB.Joint):
            n=str(g.value(j,XB.name)); self.names[n]=j
            p=g.value(j,XB.parent); self.parent[n]=str(g.value(p,XB.name)) if p is not None else None
            for a in g.objects(j,XB.alias): self.alias[str(a).lower()]=n
        self.lower={n.lower():n for n in self.names}
        self.anc={}
        for n in self.names:
            s=[]; c=self.parent[n]
            while c: s.append(c); c=self.parent[c]
            self.anc[n]=set(s)
def check(g, V):
    joints={}
    for j in g.subjects(RDF.type, X3DO.HAnimJoint):
        if (j,OWL.sameAs,None) in g: continue
        n=g.value(j,X3DO['name']); 
        if n is None: continue
        joints[j]=str(n)
    r1=[]; r2=[]
    for j,n in joints.items():
        if n not in V.names:
            key=n.lower().replace('.','_').replace(' ','_')
            hint=V.lower.get(key) or V.alias.get(n.lower())
            r1.append((n,hint))
        p=g.value(j,X3DO.hasParent)
        if p in joints and n in V.names and joints[p] in V.names and joints[p] not in V.anc[n]:
            r2.append((n,joints[p],V.parent[n]))
    return len(joints), r1, r2
if __name__=='__main__':
    import sys
    V=Vocab(); g=rdflib.Graph(); g.parse(sys.argv[1],format='turtle'); print(check(g,V))
