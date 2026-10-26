import rdflib
from rdflib import RDFS, RDF, OWL
g=rdflib.Graph(); g.parse('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl',format='turtle')
NS='https://www.web3d.org/specifications/X3dOntology4.1#'
for p in ['hasChildren','hasAddChildren','hasGeometry','hasChild']:
    u=rdflib.URIRef(NS+p)
    def flat(o):
        # union class expressions
        out=[]
        for u2 in g.objects(o,OWL.unionOf):
            out+= [str(x).split('#')[-1] for x in rdflib.collection.Collection(g,u2)]
        return out or [str(o).split('#')[-1]]
    doms=[x for d in g.objects(u,RDFS.domain) for x in flat(d)]
    rngs=[x for r in g.objects(u,RDFS.range) for x in flat(r)]
    print(p,'subPropertyOf',[str(x).split('#')[-1] for x in g.objects(u,RDFS.subPropertyOf)],'domains',len(doms),'ranges',len(rngs), rngs[:8])
# how many distinct per-field properties are subproperties of hasChild
sub=set(g.subjects(RDFS.subPropertyOf,rdflib.URIRef(NS+'hasChild')))
print('direct subproperties of hasChild',len(sub), sorted(str(s).split('#')[-1] for s in sub)[:20])
