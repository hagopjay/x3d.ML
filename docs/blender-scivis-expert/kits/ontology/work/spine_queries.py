import rdflib, time, json
g=rdflib.Graph(); t=time.time()
g.parse('spine_snapshot_v1.ttl',format='turtle')
g.parse('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl',format='turtle')
print('load s',round(time.time()-t,1),'triples',len(g))
P="""PREFIX hall: <urn:x3dio:hall#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> """
Q={
'Q1 light-family scenes via rdfs:subClassOf* (ontology hierarchy)': "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?c rdfs:subClassOf* x3do:X3DLightNode . ?s hall:uses ?c }",
'Q1b exact DirectionalLight only': "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s hall:uses x3do:DirectionalLight }",
'Q2 volume-rendering family (X3DVolumeDataNode / X3DVolumeRenderStyleNode subclasses)': "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { { ?c rdfs:subClassOf* x3do:X3DVolumeDataNode } UNION { ?c rdfs:subClassOf* x3do:X3DVolumeRenderStyleNode } ?s hall:uses ?c }",
'Q3 geometry family X3DGeometryNode': "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?c rdfs:subClassOf* x3do:X3DGeometryNode . ?s hall:uses ?c }",
'Q4 licence-clean, unveiled, lit scenes using GaussianSplats': "SELECT ?s WHERE { ?s hall:uses x3do:GaussianSplats ; hall:state 'lit' ; hall:veiled false ; hall:licenceClean true }",
'Q5 split scenes (validators disagree) that use HAnimJoint': "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s hall:uses x3do:HAnimJoint ; hall:state 'split' }",
'Q6 Immersive scenes with Physical/UnlitMaterial and no Shape component of level >= 2': """SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s hall:profile 'Immersive' . { ?s hall:uses x3do:PhysicalMaterial } UNION { ?s hall:uses x3do:UnlitMaterial }
   FILTER NOT EXISTS { ?s hall:component ?c . ?c hall:name 'Shape' ; hall:level ?l . FILTER(?l >= 2) } }""",
'Q7 pairs of node classes that never co-occur but share a superclass (skip)': None,
}
for k,q in Q.items():
    if not q: continue
    t=time.time(); r=list(g.query(P+q)); dt=time.time()-t
    print(k, '->', [tuple(str(x).split('#')[-1].split(':')[-1] for x in row) for row in r][:6], f'{dt:.2f}s', flush=True)
