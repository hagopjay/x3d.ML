import rdflib
from rdflib import RDF, RDFS, OWL
from rdflib.collection import Collection
P='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl'
g=rdflib.Graph(); g.parse(P,format='turtle')
rows=[]
for dt in g.subjects(RDF.type,RDFS.Datatype):
    for r in g.objects(dt,RDFS.range):
        for lst in g.objects(r,OWL.oneOf):
            vals=list(Collection(g,lst))
            rows.append((str(dt).split('#')[-1],len(vals)))
rows.sort(key=lambda x:-x[1])
print('datatypes with oneOf:',len(rows)); print(rows[:12])
print([r for r in rows if r[0].startswith('hanim') or r[0].startswith('unit')])
# does ontology encode joint parent / LOA anywhere?
import re
txt=open(P).read()
print('"loa" literal mentions as property:', len(re.findall(r':loa\b',txt)), 'hasJointParent', len(re.findall('jointParent',txt)))
