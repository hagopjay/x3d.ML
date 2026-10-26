import json, collections, numpy as np
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
z=np.load('/mnt/project-files/polyxandria/library/data/nodebag_v1.npz', allow_pickle=True)
print({k:(z[k].shape, z[k].dtype) for k in z.files})
for k in z.files:
    a=z[k]
    if a.dtype.kind in 'US O': print(k, list(a[:20]))
C=collections.Counter()
for r in rows:
    for n in r['nodes']: C[n]+=1
print(len(C))
for n,c in C.most_common(80): print(n,c)
