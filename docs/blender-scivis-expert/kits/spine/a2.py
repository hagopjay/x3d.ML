import json, collections
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
df=collections.Counter(); tot=collections.Counter()
for r in rows:
    for n,c in r['nodes'].items():
        df[n]+=1; tot[n]+=c
print(len(df))
for n,c in df.most_common(400):
    print(n, c, tot[n])
