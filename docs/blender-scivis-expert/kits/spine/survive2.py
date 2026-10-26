import json, collections
C=collections.Counter
d=json.load(open('survive_bags.json')); inp=d['inp']; out=d['out']
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
tab={}
for i in inp:
    for n,c in inp[i].items():
        t=tab.setdefault(n,{'scenes':0,'kept_any':0,'inst_in':0,'inst_out':0})
        t['scenes']+=1; t['inst_in']+=c
        o=out[i].get(n,0)
        if o>0: t['kept_any']+=1
        t['inst_out']+=min(o,c) if False else o
rows=sorted(tab.items(), key=lambda kv:-kv[1]['scenes'])
for n,t in rows[:70]:
    print(f"{n:28s} scenes={t['scenes']:4d} kept_any={t['kept_any']:4d} ({100*t['kept_any']/t['scenes']:5.1f}%) inst {t['inst_in']}->{t['inst_out']}")
