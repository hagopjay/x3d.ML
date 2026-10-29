import json, collections, os
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
C=collections.Counter
# origins format
print(C(r['origin'].split(':')[0] for r in rows))
ex=[r['origin'] for r in rows][:5]; print(ex)
# check on-disk existence of origins of project: type
pf='/mnt/project-files/'
n_exist=0; n_tot=0; kinds=C(); kinds_tot=C()
for r in rows:
    o=r['origin']
    kinds_tot[r['kind']]+=1
    if o.startswith('project:'):
        n_tot+=1
        p=pf+o[len('project:'):]
        if os.path.exists(p): n_exist+=1; kinds[r['kind']]+=1
print('project origin', n_tot, 'exist', n_exist, kinds, kinds_tot)
print(C(r['origin'].split(':')[0]+':'+r['origin'].split(':')[1].split('/')[0] for r in rows if ':' in r['origin']).most_common(30))
