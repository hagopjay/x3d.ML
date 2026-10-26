import rdflib, time, re
shapes=open('xb-shapes.ttl').read()
pref="""PREFIX xb: <urn:x3dio:bridge#> PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> PREFIX owl: <http://www.w3.org/2002/07/owl#> """
def q(name):
    m=re.search(r'xb:%s_.*?sh:select """(.*?)"""'%name, shapes, re.S)
    return pref+m.group(1).replace('$this','?this')
g=rdflib.Graph(); t=time.time(); g.parse('hanim_ttl/HumanoidAnimation__Characters__HAnimModelHandRight.ttl',format='turtle'); print('parse',len(g),time.time()-t)
v=rdflib.Graph(); v.parse('xb-hanim.ttl',format='turtle'); g+=v
for n in ('R1','R2'):
    t=time.time(); r=list(g.query(q(n))); print(n,len(r),time.time()-t, flush=True)
