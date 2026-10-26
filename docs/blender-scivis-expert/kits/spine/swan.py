import json, collections
C=collections.Counter
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
def load(f): return {json.loads(l)['scene_id']:json.loads(l) for l in open(f)}
V={k:load(f'val/val_{k}.jsonl') for k in ['688174f','d5598c4','74da0ec']}
S={}
for l in open('bpy/sweep_rt.jsonl'):
    r=json.loads(l); S[r['id']]=r
print(len(S))
def outcome(r):
    if r.get('worker_died'): return 'worker_died'
    if 'import_exc' in r: return 'import_exception'
    s=r['stats1']
    if s['objects']==0: return 'imported_empty'
    return 'imported'
O={i:outcome(r) for i,r in S.items()}
print('import outcome', C(O.values()))
print('by kind', C((man[i]['kind'],O[i]) for i in S))
# by fork verdict
print('by fork d5598c4 verdict', C((V['d5598c4'][i]['verdict'],O[i]) for i in S))
print('by upstream verdict', C((V['74da0ec'][i]['verdict'],O[i]) for i in S))
# import exc types
print(C(r.get('import_exc','')[:90] for r in S.values() if 'import_exc' in r).most_common(10))
# log levels
print('with ERROR logs', sum(1 for r in S.values() if r.get('log_levels',{}).get('ERROR')), 'WARNING', sum(1 for r in S.values() if r.get('log_levels',{}).get('WARNING')))
# export
ex=C()
for i,r in S.items():
    if O[i]!='imported': continue
    ex['export_exc' if 'export_exc' in r else ('export_ok' if r.get('export_bytes') else 'export_none')]+=1
print('export', ex)
print(C(r.get('export_exc','')[:100] for r in S.values() if 'export_exc' in r).most_common(5))
print('reimport', C(('reimport_exc' if 'reimport_exc' in r else ('stats2' if 'stats2' in r else 'none')) for i,r in S.items() if O[i]=='imported'))
# fidelity: compare stats
import math
fid=C(); bad=[]
for i,r in S.items():
    if 'stats2' not in r: continue
    a,b=r['stats1'],r['stats2']
    same_v = a['verts']==b['verts']; same_f=a['faces']==b['faces']
    # bbox
    bb=True
    if a['bbox'] and b['bbox']:
        for k in range(2):
            for j in range(3):
                if abs(a['bbox'][k][j]-b['bbox'][k][j])>1e-3*max(1,abs(a['bbox'][k][j])): bb=False
    fid[(same_v,same_f,bb)]+=1
    if not (same_v and same_f and bb): bad.append((i[:8],man[i]['kind'],a['verts'],b['verts'],a['faces'],b['faces'],a['objects'],b['objects'],a['types'],b['types']))
print('fidelity (verts==,faces==,bbox==)', fid)
for b in bad[:25]: print(b)
