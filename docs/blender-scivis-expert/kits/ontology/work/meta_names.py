import rdflib
from rdflib import RDF, RDFS, OWL
from rdflib.collection import Collection
P='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl'
g=rdflib.Graph(); g.parse(P,format='turtle')
NS='https://www.web3d.org/specifications/X3dOntology4.1#'
dt=rdflib.URIRef(NS+'metaNameValues')
for r in g.objects(dt,RDFS.range):
    for lst in g.objects(r,OWL.oneOf):
        vals=[str(x) for x in Collection(g,lst)]
print(len(vals)); print(vals)
for k in ['generator','filename','title','creator','description','keywords','reference','license','identifier','rights','subject','created','modified']:
    print(k, k in vals)
