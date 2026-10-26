import json, collections, rdflib
from rdflib import RDF, OWL
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
ont=rdflib.Graph(); ont.parse('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl',format='turtle')
cls={str(c).split('#')[-1] for c in ont.subjects(RDF.type,OWL.Class)}
names=collections.Counter()
for r in rows:
    for n in (r['nodes'] or {}): names[n]+=1
print('distinct node-names in spine',len(names),'resolving to ontology classes',sum(1 for n in names if n in cls))
unres=[n for n in names if n not in cls]
print('unresolved distinct',len(unres))
aff=[r for r in rows if any(n not in cls for n in (r['nodes'] or {}))]
print('scenes with >=1 unresolved name',len(aff))
print('  fork verdicts',collections.Counter(r['fork'] for r in aff))
print('  up verdicts',collections.Counter(r['up'] for r in aff))
ok=[r for r in rows if r['nodes'] and all(n in cls for n in r['nodes'])]
print('scenes with all names resolving',len(ok),'fork',collections.Counter(r['fork'] for r in ok))
# scenes with zero nodes recorded (json/vrml)
print('no nodes recorded',sum(1 for r in rows if not r['nodes']))
# top unresolved by scene count
print(sorted(((names[n],n) for n in unres),reverse=True)[:25])
# HAnim, splats, geo etc: states
def state_ct(pred):
    c=collections.Counter(); cc=collections.Counter()
    for r in rows:
        if pred(r):
            c[r['state']]+=1; cc[(r['state'],r['clean'] and not r['veiled'])]+=1
    return dict(c)
print('HAnim', state_ct(lambda r:any(n.startswith('HAnim') for n in (r['nodes'] or {}))))
print('Splats', state_ct(lambda r:r['splats']))
print('Geo', state_ct(lambda r:r['geo']))
print('Script', state_ct(lambda r:r['script']))
print('Volume', state_ct(lambda r:any('Volume' in n or n=='IsoSurfaceVolumeData' for n in (r['nodes'] or {}))))
print('GaussianSplats node', state_ct(lambda r:'GaussianSplats' in (r['nodes'] or {})))
print('PointSet', state_ct(lambda r:'PointSet' in (r['nodes'] or {})))
print('Metadata*', state_ct(lambda r:any(n.startswith('Metadata') for n in (r['nodes'] or {}))))
print('blender_export kind', [(r['origin'].split('/')[-1], r['state']) for r in rows if r['kind']=='blender_export'])
# profile-component: PhysicalMaterial/UnlitMaterial under Immersive without Shape>=2
def sh2(r):
    for c in r['components'] or []:
        n,l=c.split(':')
        if n=='Shape' and l.isdigit() and int(l)>=2: return True
    return False
pm=[r for r in rows if r['profile']=='Immersive' and any(n in ('PhysicalMaterial','UnlitMaterial') for n in (r['nodes'] or {}))]
nos=[r for r in pm if not sh2(r)]
print('Immersive scenes w/ Physical/Unlit',len(pm),'without Shape>=2 component',len(nos),'fork invalid among them',sum(1 for r in nos if r['fork']=='invalid'),'fork profile-component flagged',sum(1 for r in nos if any(d['code']=='profile-component' for d in (r['fork_top'] or []))))
print('  upstream verdict among them',collections.Counter(r['up'] for r in nos))
