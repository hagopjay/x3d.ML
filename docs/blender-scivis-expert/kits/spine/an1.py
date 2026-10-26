import json, collections, sys
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
print(len(rows))
print(sorted(rows[0].keys()))
C=collections.Counter
for k in ['kind','encoding','version','profile','licence','clean','state','veiled','fork','up','script','splats','geo']:
    print(k, C(str(r.get(k)) for r in rows).most_common(15))
print('clean&veiled', C((r['clean'],r['veiled']) for r in rows))
print('bytes', sum(r['bytes'] for r in rows), max(r['bytes'] for r in rows))
