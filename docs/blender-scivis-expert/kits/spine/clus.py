import json, collections, sys
sys.path.insert(0,'.')
from cov import cls, GEOM, SPLAT, HANIM
rows={json.loads(l)['id']:json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')}
lay=json.load(open('/mnt/project-files/polyxandria/library/data/layout_v1.json'))
cl={s['id']:s['c'] for s in lay['scenes']}
for c in lay['clusters']:
    k=c['k']
    mem=[rows[i] for i,cc in cl.items() if cc==k]
    clean=[r for r in mem if r['clean']]
    parsed=[r for r in clean if r['nodes'].get('Scene')]
    strict=[r for r in parsed if all(cls(n)!='U' for n in r['nodes'])]
    lit=[r for r in clean if r['fork']=='valid' and r['up']=='valid']
    print(k, 'n',c['n'],'clean',len(clean),'lit&clean',len(lit),'clean parsed',len(parsed),'noU',len(strict), c['top_terms'][:6], c['kinds'][:3])
