import json, collections
C=collections.Counter
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
def load(f): return {json.loads(l)['scene_id']:json.loads(l) for l in open(f)}
V={k:load(f'val/val_{k}.jsonl') for k in ['688174f','d5598c4','74da0ec']}
for k,v in V.items(): print(k, len(v), C(r['verdict'] for r in v.values()))
# agreement with snapshot
ag=C()
for sid,o in man.items():
    ag['fork688_vs_snap', V['688174f'][sid]['verdict']==o['fork']]+=1
    ag['up_vs_snap', V['74da0ec'][sid]['verdict']==o['up']]+=1
print(ag)
dis=[(sid,man[sid]['fork'],V['688174f'][sid]['verdict']) for sid in man if V['688174f'][sid]['verdict']!=man[sid]['fork']]
print('fork688 disagreements', len(dis), dis[:5])
dis=[(sid,man[sid]['up'],V['74da0ec'][sid]['verdict']) for sid in man if V['74da0ec'][sid]['verdict']!=man[sid]['up']]
print('up disagreements', len(dis), dis[:5])
# flips 688174f -> d5598c4
fl=C()
for sid in man: fl[(V['688174f'][sid]['verdict'],V['d5598c4'][sid]['verdict'])]+=1
print('688->d55', fl)
# three-way
tw=C()
for sid in man: tw[(V['688174f'][sid]['verdict'],V['d5598c4'][sid]['verdict'],V['74da0ec'][sid]['verdict'])]+=1
print(tw)
# by kind: d5598c4 valid
bk=C()
for sid,o in man.items(): bk[(o['kind'],V['d5598c4'][sid]['verdict'], V['74da0ec'][sid]['verdict'])]+=1
for k,v in sorted(bk.items()): print(k,v)
# flips detail
for sid in man:
    if V['688174f'][sid]['verdict']=='valid' and V['d5598c4'][sid]['verdict']=='invalid':
        print('FLIP', sid[:8], man[sid]['kind'], man[sid]['path'][-60:], [ (f['code'],f['message'][:100]) for f in V['d5598c4'][sid]['findings'] if f['severity']=='error'][:2])
