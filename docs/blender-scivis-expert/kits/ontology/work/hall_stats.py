import rdflib, time, collections
from rdflib import RDF
t=time.time(); g=rdflib.Graph(); g.parse('hall/hall_v1_7.ttl',format='turtle'); print('parse s',round(time.time()-t,1),'triples',len(g))
X='https://www.web3d.org/specifications/X3dOntology4.1#'
c=collections.Counter(str(o).split('#')[-1] for o in g.objects(None,RDF.type) if str(o).startswith(X))
print('node-class individuals',sum(c.values()),'distinct classes',len(c)); print(c.most_common(25))
lit=[(len(str(o)),str(p).split('#')[-1]) for s,p,o in g if isinstance(o,rdflib.Literal)]
lit.sort(reverse=True); print('largest literals',lit[:6])
print('total literal chars',sum(l for l,_ in lit))
