import json, collections
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
C=collections.Counter(); I=collections.Counter()
for r in rows:
    for n,c in r['nodes'].items(): C[n]+=1; I[n]+=c
print(' '.join(f"{n}:{c}" for n,c in C.most_common()[80:]))
print()
print([r['origin'] for r in rows if r['kind']=='tuned_eval'][:3])
print([r['origin'] for r in rows if r['kind']=='archive_mirror'][:3])
print([r['origin'] for r in rows if r['kind']=='evolve'][:3])
print(C.most_common(0), sum(I.values()))
