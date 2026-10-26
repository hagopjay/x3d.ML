import json, collections, sys
sys.path.insert(0,'.')
from cov import cls, GEOM, SPLAT, HANIM
C=collections.Counter
rows={json.loads(l)['id']:json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')}
P=[json.loads(l) for l in open('/mnt/project-files/spine/e1/prompts-v1.jsonl')]
print(len(P), C(p['set'] for p in P))
# exemplar licence
ex=C(); exl=set()
for p in P:
    for e in p['exemplars']:
        exl.add(e)
print('distinct exemplars', len(exl))
print('exemplar clean?', C(rows[e]['clean'] if e in rows else 'missing' for e in exl), C(rows[e]['kind'] for e in exl if e in rows))
print('exemplar licence', C(rows[e]['licence'] for e in exl if e in rows))
# prompt source licence
src=[p for p in P if p['source_scene']]
print('library prompts', len(src), C((rows[p['source_scene']]['kind'], rows[p['source_scene']]['clean']) for p in src))
# Blender feasibility
def sc_cov(sc):
    r=rows[sc]; return all(cls(n)!='U' for n in r['nodes'])
print('library prompts whose source has no unhandled node', sum(1 for p in src if sc_cov(p['source_scene'])), 'of', len(src))
print('exemplars with no unhandled node', sum(1 for e in exl if sc_cov(e)), 'of', len(exl))
# bench/unseen required_nodes
for st in ['bench30','unseen31']:
    ps=[p for p in P if p['set']==st]
    ok=0; allreq=C()
    for p in ps:
        rq=(p['constraints'] or {}).get('required_nodes',[])
        allreq.update(rq)
        if all(cls(n)!='U' for n in rq): ok+=1
    print(st, len(ps), 'prompts with all required nodes handled by importer:', ok, 'unhandled req:', {n:c for n,c in allreq.items() if cls(n)=='U'})
