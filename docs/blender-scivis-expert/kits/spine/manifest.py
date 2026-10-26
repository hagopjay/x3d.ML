import json, hashlib, re, os, collections
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
out=[]; mism=0; chk=0
for r in rows:
    if not r['clean'] or not r['origin'].startswith('project:'): continue
    p='/mnt/project-files/'+r['origin'][8:]
    if not os.path.exists(p): continue
    data=open(p,'rb').read()
    text=data.decode('utf-8',errors='replace')
    sid=hashlib.sha256(re.sub(r"\s+"," ",text).strip().encode()).hexdigest()
    ok = sid==r['id']
    chk+=1
    if not ok: mism+=1
    out.append(dict(id=r['id'],path=p,kind=r['kind'],bytes=len(data),match=ok,fork=r['fork'],up=r['up'],version=r['version'],profile=r['profile'],licence=r['licence'],nodes=r['nodes'],enc=r['encoding'],splats=r['splats']))
print('clean on-disk', len(out),'id matches', chk-mism,'mismatch', mism)
json.dump(out,open('manifest_clean_ondisk.json','w'))
print(collections.Counter(o['kind'] for o in out))
print('size<=2MB', sum(1 for o in out if o['bytes']<=2_000_000), 'size>2MB', [ (o['kind'],o['bytes']) for o in out if o['bytes']>2_000_000][:20])
print('mismatch examples', [(o['path'][-60:]) for o in out if not o['match']][:5])
