import json, collections, sys
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
print(len(rows))
print(sorted(rows[0].keys()))
C=collections.Counter
for k in ['kind','encoding','version','profile','licence','clean','veiled','state','fork','up','script','splats','geo']:
    print(k, C(str(r.get(k)) for r in rows).most_common(15))
print('clean&!veiled', sum(1 for r in rows if r['clean'] and not r['veiled']))
print('clean', sum(1 for r in rows if r['clean']), 'veiled', sum(1 for r in rows if r['veiled']))
print('clean x veiled', C((r['clean'], r['veiled']) for r in rows))
print('kind x clean', C((r['kind'], r['clean']) for r in rows))
print('licence x clean', C((r['licence'], r['clean']) for r in rows))
print('state x veiled', C((r['state'], r['veiled']) for r in rows))
