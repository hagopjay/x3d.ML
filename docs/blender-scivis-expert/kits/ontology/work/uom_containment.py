"""X3DUOM-derived closed-world containment: legal (parent type, child type) pairs; check any converted Turtle graph."""
import sys, re, json, glob, collections
SRC='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/ontology/repos/x3d_mcp_eb4b4b4/src'
sys.path.insert(0,SRC)
import rdflib
from rdflib import RDF
from x3d_utils.x3duom import X3DUOM
from pathlib import Path
u=X3DUOM(Path(SRC+'/validation/schemas/X3dUnifiedObjectModel-4.1.xml'))
nodes=u.get_concrete_nodes(); abst=u.get_abstract_types()
def bases(n):
    seen={n}; st=[n]
    while st:
        c=st.pop(); d=nodes.get(c) or abst.get(c) or {}
        for b in [d.get('baseType')]+list(d.get('additionalBaseTypes') or []):
            if b and b not in seen: seen.add(b); st.append(b)
    return seen
B={n:bases(n) for n in nodes}
legal=set(); fieldmap=collections.defaultdict(set)
for p in nodes:
    for f in u.get_node_fields(p):
        a=f.get('acceptableNodeTypes')
        if not a or f['type'] not in ('SFNode','MFNode'): continue
        acc=set(re.split(r'[|,\s]+',a))
        for c in nodes:
            if c in acc or (acc & B[c]): legal.add((p,c)); fieldmap[(p,c)].add(f['name'])
print('concrete nodes',len(nodes),'legal (parent,child) pairs',len(legal),'of',len(nodes)**2)
X3DO='https://www.web3d.org/specifications/X3dOntology4.1#'
def check_graph(path):
    g=rdflib.Graph(); g.parse(path,format='turtle')
    typ={}
    for s,o in g.subject_objects(RDF.type):
        so=str(o)
        if so.startswith(X3DO) and so[len(X3DO):] in nodes: typ[s]=so[len(X3DO):]
    n=0; bad=[]
    for s,p in g.subject_objects(rdflib.URIRef(X3DO+'hasParent')):
        if s in typ and p in typ:
            n+=1
            if (typ[p],typ[s]) not in legal: bad.append((typ[p],typ[s]))
    return n,bad
if __name__=='__main__':
    tot=0; totbad=collections.Counter(); per=[]
    for f in sys.argv[1:]:
        n,bad=check_graph(f); tot+=n; per.append((f.split('/')[-1][:50],n,len(bad))); totbad.update(bad)
    for p in per: print(p)
    print('edges checked',tot,'illegal',sum(totbad.values())); print(totbad.most_common(20))
