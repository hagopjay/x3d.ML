import json, collections
C=collections.Counter
M={}
for l in open('mut/mutants_v1.jsonl'):
    m=json.loads(l); M.setdefault(m['mutant_id'],m)
def load(f): return {json.loads(l)['scene_id']:json.loads(l) for l in open(f)}
Vf=load('val/mut_d5598c4.jsonl'); Vu=load('val/mut_74da0ec.jsonl')
S={json.loads(l)['id']:json.loads(l) for l in open('bpy/sweep_mut.jsonl')}
B={json.loads(l)['id']:json.loads(l) for l in open('bpy/sweep_rt.jsonl')}
print('mutants', len(M), 'imported rows', len(S))
def sig(st): return (st['objects'],st['verts'],st['faces'],st['materials'],st['anim_objects'],st['lights'],st['cameras'],st['armatures'], tuple(sorted(st['types'].items())))
rows=[]
for mid,m in M.items():
    r=S.get(mid)
    if r is None: continue
    b=B[m['base_id']]['stats1']
    if r.get('worker_died'): out='died'
    elif 'import_exc' in r:
        msg=r['tb'].strip().splitlines(); msg=[x for x in msg if x and not x.startswith('Location')][-1][:70]
        out='exception'
    else:
        out='same' if sig(r['stats1'])==sig(b) else 'changed'
        msg=''
    fk=Vf[mid]['verdict']; up=Vu[mid]['verdict']
    rows.append(dict(op=m['operator'],fam=m['family'],ctl=m['is_control'],out=out,fork=fk,up=up,msg=msg if out=='exception' else '', base=m['base_id']))
print(C((r['ctl'],r['out']) for r in rows))
print('importer outcome vs fork verdict (defect mutants only):')
d=[r for r in rows if not r['ctl']]
print(C((r['out'],r['fork']) for r in d))
print('upstream:', C((r['out'],r['up']) for r in d))
print('controls:', C((r['out'],r['fork'],r['up']) for r in rows if r['ctl']))
# per operator table
ops=collections.defaultdict(lambda: C())
for r in rows:
    o=ops[(r['fam'],r['op'])]; o['n']+=1; o[r['out']]+=1
    if r['fork']=='invalid': o['fork_flag']+=1
    if r['up']=='invalid': o['up_flag']+=1
    if r['out'] in('exception','died') and r['fork']=='valid': o['crash_unflagged']+=1
    if r['out']=='changed' and r['fork']=='valid': o['silent_unflagged']+=1
print(f"{'family':15s} {'op':30s} n  same chg exc died fork up crash_unfl silent_unfl")
for (fam,op),o in sorted(ops.items()):
    print(f"{fam:15s} {op:30s} {o['n']:3d} {o['same']:3d} {o['changed']:3d} {o['exception']:3d} {o['died']:3d} {o['fork_flag']:3d} {o['up_flag']:3d} {o['crash_unflagged']:3d} {o['silent_unflagged']:3d}")
print(C(r['msg'] for r in rows if r['out']=='exception').most_common(12))
json.dump(rows,open('mut_rows.json','w'))
