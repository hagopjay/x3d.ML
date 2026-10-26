import rdflib, time
data=rdflib.Graph(); data.parse('bridge_fixture.ttl',format='turtle'); data.parse('xb-hanim.ttl',format='turtle')
pref="""PREFIX xb: <urn:x3dio:bridge#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX owl: <http://www.w3.org/2002/07/owl#> """
qs={
'A basic': "SELECT ?this ?n ?m WHERE { ?this x3do:name ?n ; x3do:hasParent ?p . ?p a x3do:HAnimJoint ; x3do:name ?m . }",
'B +type first': "SELECT ?this ?n ?m WHERE { ?this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p . ?p a x3do:HAnimJoint ; x3do:name ?m . }",
'C +vocab': "SELECT ?this ?n ?m WHERE { ?this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p . ?p a x3do:HAnimJoint ; x3do:name ?m . ?jn xb:name ?n . ?jm xb:name ?m . }",
'D +notexists anc': "SELECT ?this ?n ?m WHERE { ?this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p . ?p a x3do:HAnimJoint ; x3do:name ?m . ?jn xb:name ?n . ?jm xb:name ?m . FILTER NOT EXISTS { ?jn xb:ancestor ?jm } }",
'E +notexists sameAs': "SELECT ?this ?n ?m WHERE { ?this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p . FILTER NOT EXISTS { ?this owl:sameAs ?d } ?p a x3do:HAnimJoint ; x3do:name ?m . ?jn xb:name ?n . ?jm xb:name ?m . FILTER NOT EXISTS { ?jn xb:ancestor ?jm } }",
}
for k,q in qs.items():
    t=time.time(); r=list(data.query(pref+q)); print(k,len(r),f'{time.time()-t:.2f}s')
