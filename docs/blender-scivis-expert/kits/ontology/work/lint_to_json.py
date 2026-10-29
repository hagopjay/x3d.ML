import sys, json, rdflib
sys.path.insert(0,'.')
from run_shacl import run
import rdflib
rows=run('bridge_fixture.ttl','fixture')
g=rdflib.Graph(); g.parse('bridge_fixture.ttl',format='turtle')
X3DO=rdflib.Namespace('https://www.web3d.org/specifications/X3dOntology4.1#')
out={}
for shape,sev,focus,msg in rows:
    base=dict(g.namespaces())['']
    node=rdflib.URIRef(str(base)+focus)
    nm=g.value(node,X3DO['name'])
    kind='bone' if (node,rdflib.RDF.type,X3DO.HAnimJoint) in g else 'scene'
    key=str(nm) if kind=='bone' else 'SCENE'
    out.setdefault(f'{kind}:{key}',[]).append({'rule':shape.split('_')[0],'severity':sev,'message':msg})
json.dump(out,open('lint.json','w'),indent=1); print(json.dumps(out,indent=1)[:900])
