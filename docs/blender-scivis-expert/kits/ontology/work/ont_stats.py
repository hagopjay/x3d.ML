import rdflib, collections, sys
from rdflib import RDF, RDFS, OWL
P='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl'
g=rdflib.Graph(); g.parse(P,format='turtle')
print('triples',len(g))
cls=set(g.subjects(RDF.type,OWL.Class)); print('owl:Class',len(cls))
op=set(g.subjects(RDF.type,OWL.ObjectProperty)); dp=set(g.subjects(RDF.type,OWL.DatatypeProperty)); print('objprops',len(op),'dataprops',len(dp))
ni=set(g.subjects(RDF.type,OWL.NamedIndividual)); print('named individuals',len(ni))
def short(u): return str(u).split('#')[-1]
names=sorted(short(c) for c in cls)
for kw in ['Gauss','Splat','Metadata','HAnim','Volume','Geo','Unit','Physical','Particle','Point','Armature','Skin','Collection']:
    print(kw,[n for n in names if kw in n][:40])
# any enumeration individuals: humanoid_root
import re
txt=open(P).read()
for kw in ['humanoid_root','l_knee','unit','UNIT','conversionFactor','loa']:
    print(kw, len(re.findall(kw,txt)))
# data properties list
print(sorted(short(p) for p in dp)[:200])
