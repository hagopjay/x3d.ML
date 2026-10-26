import json, collections
C=collections.Counter
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
def load(f): return {json.loads(l)['scene_id']:json.loads(l) for l in open(f)}
E1=load('val/exp_d5598c4.jsonl'); E2=load('val/exp_74da0ec.jsonl')
V0=load('val/val_d5598c4.jsonl')
print('exports validated', len(E1), C(r['verdict'] for r in E1.values()), C(r['verdict'] for r in E2.values()))
# rt validity by input validity
print(C((V0[i]['verdict'],E1[i]['verdict']) for i in E1))
inv=C(); ex=[]
for i,r in E1.items():
    if r['verdict']!='valid':
        for f in r['findings']:
            if f['severity']=='error': inv[f['code']+': '+f['message'][:90]]+=1
        ex.append(i)
print(len(ex)); 
for k,v in inv.most_common(12): print(v,k)
S={json.loads(l)['id']:json.loads(l) for l in open('bpy/sweep_rt.jsonl')}
print('export bytes total', sum(S[i]['export_bytes'] for i in E1), 'orig bytes', sum(man[i]['bytes'] for i in E1))
# who is invalid by kind
print(C((man[i]['kind'],E1[i]['verdict']) for i in E1))
# timing
ts=sorted(S[i]['import_s'] for i in E1); print('import_s median', ts[len(ts)//2], 'max', ts[-1], 'p95', ts[int(len(ts)*.95)])
