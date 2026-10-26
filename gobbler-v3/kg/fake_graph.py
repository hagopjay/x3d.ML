import json, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout, numpy as np
rng = random.Random(5)
CLS = ['Standard','Tool','Org','Workstream','Finding','Rule','Loop']
n = 420
nodes = [{'id': 'n%d' % i, 'label': 'Node %d' % i, 'cls': CLS[rng.randrange(6)], 'grade': rng.choice(['Confirmed','Likely','Likely','Suspected']), 'prov': rng.choice(['doc','doc','data','model_recall','simulated']), 'w': min(1, rng.random() ** 3 * 1.4)} for i in range(n)]
edges = []
for i in range(n):
    for _ in range(2):
        j = int(min(n - 1, abs(rng.gauss(0, n / 5)) )) if rng.random() < 0.5 else rng.randrange(n)
        if j != i: edges.append({'s': i, 't': j, 'p': rng.choice(['uses','part_of','implements','evidences','improves','depends_on']), 'grade': 'Likely', 'prov': 'doc', 'loop': -1})
loops = []
for k in range(6):
    steps = rng.sample(range(n), rng.randrange(5, 9)); loops.append({'name': 'Loop %d' % k, 'steps': steps, 'gain': None})
    for a, b in zip(steps, steps[1:] + steps[:1]):
        edges.append({'s': a, 't': b, 'p': 'feeds', 'grade': 'Likely', 'prov': 'doc', 'loop': k})
    for s in steps: nodes[s]['w'] = max(nodes[s]['w'], 0.5)
cls_idx = [CLS.index(x['cls']) for x in nodes]
pos, rings = layout.layout(n, [(e['s'], e['t'], 0.5) for e in edges], [x['w'] for x in nodes], [l['steps'] for l in loops], cls_idx)
for x, p in zip(nodes, pos): x['xyz'] = [round(float(v), 3) for v in p]
for l, r in zip(loops, rings): l['ring'] = r
json.dump({'nodes': nodes, 'edges': edges, 'loops': loops, 'meta': {'fake': True}}, open(sys.argv[1], 'w'))
print('bbox', pos.min(0).round(1), pos.max(0).round(1))
