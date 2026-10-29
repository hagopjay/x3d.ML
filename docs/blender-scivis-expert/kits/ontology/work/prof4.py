import rdflib, time
pref="""PREFIX xb: <urn:x3dio:bridge#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX owl: <http://www.w3.org/2002/07/owl#> """
g=rdflib.Graph(); g.parse('hanim_ttl/HumanoidAnimation__Characters__HAnimModelHandRight.ttl',format='turtle')
v=rdflib.Graph(); v.parse('xb-hanim.ttl',format='turtle'); g+=v
Q=pref+"""SELECT ?this ?n ?m ?expected WHERE {
  { SELECT ?this ?n ?m WHERE { ?this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p . ?p a x3do:HAnimJoint ; x3do:name ?m .
      FILTER NOT EXISTS { ?this owl:sameAs ?d } } }
  ?jn xb:name ?n . ?jn a xb:Joint . ?jm xb:name ?m . ?jm a xb:Joint .
  FILTER NOT EXISTS { ?jn xb:ancestor ?jm }
  ?jn xb:parent ?e . ?e xb:name ?expected }"""
t=time.time(); r=list(g.query(Q)); print(len(r), time.time()-t)
for x in r[:5]: print(x)
