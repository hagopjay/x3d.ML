import rdflib, time, re
data=rdflib.Graph(); data.parse('bridge_fixture.ttl',format='turtle'); data.parse('xb-hanim.ttl',format='turtle')
shapes=open('xb-shapes.ttl').read()
pref="""PREFIX xb: <urn:x3dio:bridge#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX owl: <http://www.w3.org/2002/07/owl#> """
for name in ['R1','R2','R3','R4','R5']:
    m=re.search(r'xb:%s_.*?sh:select """(.*?)"""'%name, shapes, re.S)
    q=m.group(1).replace('$this','?this')
    t=time.time(); rows=list(data.query(pref+q)); print(name, len(rows), f'{time.time()-t:.2f}s')
