import sys, json, difflib, collections, rdflib
sys.path.insert(0,'../repos/x3d_mcp_eb4b4b4/src')
from validation.validate import validate_xml
from rdflib import RDF, OWL
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
ont=rdflib.Graph(); ont.parse('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl',format='turtle')
cls=sorted({str(c).split('#')[-1] for c in ont.subjects(RDF.type,OWL.Class)})
# keep only concrete-looking classes (exclude abstract X3D* types) for suggestions
concrete=[c for c in cls if not c.startswith('X3D')]
cnt=collections.Counter()
for r in rows:
    for n in (r['nodes'] or {}):
        if n not in cls: cnt[n]+=1
lower={c.lower():c for c in concrete}
out=[]
for n,k in cnt.most_common():
    s=lower.get(n.lower()) or (difflib.get_close_matches(n,concrete,n=1,cutoff=0.6) or [None])[0]
    out.append((n,k,s))
print(len(out)); print(out[:40])
json.dump(out,open('invented_names.json','w'))
# what does the fork say for a Torus?
x="""<?xml version="1.0" encoding="UTF-8"?><X3D version="4.0" profile="Immersive"><Scene><Shape><Appearance><Material/></Appearance><Torus/></Shape><Route fromNode="a" fromField="b" toNode="c" toField="d"/></Scene></X3D>"""
v=validate_xml(x); print(v['valid']); print(v['errors'][:3]); print(v.get('hints'))
