import json, collections
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
C=collections.Counter
t=C()
for r in rows: t[(r['kind'],r['licence'],r['clean'])]+=1
for k,v in sorted(t.items()): print(k,v)
print()
# kind x fork verdict, clean only
t=C()
for r in rows:
    if r['clean']: t[(r['kind'],r['fork'],r['up'])]+=1
for k,v in sorted(t.items()): print(k,v)
# version/profile among clean
print(C((r['version']) for r in rows if r['clean']))
print('scene present', sum(1 for r in rows if r['nodes'].get('Scene')), 'clean', sum(1 for r in rows if r['nodes'].get('Scene') and r['clean']))
print('n_nodes==0', sum(1 for r in rows if r['n_nodes']==0))
print('bytes by kind', {k:sum(r['bytes'] for r in rows if r['kind']==k) for k in set(r['kind'] for r in rows)})
print('clean bytes quantiles', sorted(r['bytes'] for r in rows if r['clean'])[::220])
