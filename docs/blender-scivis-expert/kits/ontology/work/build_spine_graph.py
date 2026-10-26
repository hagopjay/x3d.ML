"""Hall snapshot v1 (3,058 spine rows) -> Turtle, joined to the X3D Ontology 4.1 class IRIs. Metadata only: the scene XML is not on this disk."""
import json, time, hashlib, collections
import rdflib
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, XSD, BNode, URIRef
SNAP='/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl'
ONT='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl'
X3DO=Namespace('https://www.web3d.org/specifications/X3dOntology4.1#'); HALL=Namespace('urn:x3dio:hall#')
ont=Graph(); ont.parse(ONT,format='turtle')
classes={str(c).split('#')[-1]:c for c in ont.subjects(RDF.type,OWL.Class)}
g=Graph(); g.bind('hall',HALL); g.bind('x3do',X3DO)
rows=[json.loads(l) for l in open(SNAP)]
unresolved=collections.Counter()
t=time.time()
for r in rows:
    s=URIRef('urn:x3dio:spine:scene:'+r['id'][:16])
    g.add((s,RDF.type,HALL.Scene)); g.add((s,HALL.sha256,Literal(r['id'])))
    for k in ('kind','origin','state','licence','encoding'):
        if r.get(k) is not None: g.add((s,HALL[k],Literal(r[k])))
    g.add((s,HALL.veiled,Literal(bool(r['veiled'])))); g.add((s,HALL.licenceClean,Literal(bool(r['clean']))))
    for k,p in (('version','x3dVersion'),('profile','profile')):
        if r.get(k): g.add((s,HALL[p],Literal(r[k])))
    for k,p in (('bytes','bytes'),('n_nodes','nodeCount'),('n_routes','routeCount'),('n_def','defCount')):
        if r.get(k) is not None: g.add((s,HALL[p],Literal(int(r[k]))))
    for k,p in (('script','hasScript'),('splats','hasSplats'),('geo','hasGeo')):
        g.add((s,HALL[p],Literal(bool(r[k]))))
    for c in r.get('components') or []:
        n,l=c.split(':'); b=BNode(); g.add((s,HALL.component,b)); g.add((b,HALL.name,Literal(n)))
        if l.isdigit(): g.add((b,HALL.level,Literal(int(l))))
    for node,cnt in (r.get('nodes') or {}).items():
        cls=classes.get(node)
        if cls is None: unresolved[node]+=1; continue
        g.add((s,HALL.uses,cls))
        b=BNode(); g.add((s,HALL.usage,b)); g.add((b,HALL.node,cls)); g.add((b,HALL['count'],Literal(int(cnt))))
    for who,v,e,w,top in (('fork',r['fork'],r['fork_err'],r['fork_warn'],r['fork_top']),('upstream',r['up'],r['up_err'],None,r['up_top'])):
        g.add((s,HALL[who+'Verdict'],Literal(v)))
        if e is not None: g.add((s,HALL[who+'Errors'],Literal(int(e))))
        for d in top or []:
            b=BNode(); g.add((s,HALL.diagnostic,b)); g.add((b,HALL.validator,Literal(who))); g.add((b,HALL.code,Literal(d['code'])))
    if r.get('prompt'): g.add((s,HALL.hasPrompt,Literal(True)))
print('triples',len(g),'build s',round(time.time()-t,2))
print('unresolved node names (not an owl:Class in ontology 4.1):',len(unresolved),dict(unresolved.most_common(20)))
g.serialize('spine_snapshot_v1.ttl',format='turtle')
import os; print('ttl bytes',os.path.getsize('spine_snapshot_v1.ttl'))
