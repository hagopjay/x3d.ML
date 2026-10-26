import json, collections, re
C=collections.Counter
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
def load(f): return {json.loads(l)['scene_id']:json.loads(l) for l in open(f)}
V={k:load(f'val/val_{k}.jsonl') for k in ['d5598c4']}
S={json.loads(l)['id']:json.loads(l) for l in open('bpy/sweep_rt.jsonl')}
last=C()
for i,r in S.items():
    if 'import_exc' in r:
        tb=r['tb'].strip().splitlines()
        # last meaningful line before Location
        msg=[l for l in tb if l and not l.startswith('Location')][-1]
        last[msg[:140]]+=1
        f=[x for x in V['d5598c4'][i]['findings'] if x['severity']=='error'][:1]
        print(i[:8], man[i]['kind'], man[i]['bytes'], msg[:110], '|', f[0]['message'][:80] if f else V['d5598c4'][i].get('semantic_status'))
print(last)
print([ (i[:8],man[i]['path'][-50:],V['d5598c4'][i]['verdict'], S[i]['stats1']) for i in S if 'stats1' in S[i] and S[i]['stats1']['objects']==0])
# round trip face/bbox mismatches
for i,r in S.items():
    if 'stats2' not in r: continue
    a,b=r['stats1'],r['stats2']
    bb=True
    if a['bbox'] and b['bbox']:
        for k in range(2):
            for j in range(3):
                if abs(a['bbox'][k][j]-b['bbox'][k][j])>1e-3*max(1,abs(a['bbox'][k][j])): bb=False
    if a['faces']!=b['faces'] or not bb:
        print('RT-DIFF', i[:8], man[i]['kind'], man[i]['path'][-55:], 'faces',a['faces'],b['faces'],'verts',a['verts'],b['verts'],'obj',a['objects'],b['objects'], 'bbox_same',bb, 'fork', V['d5598c4'][i]['verdict'])
