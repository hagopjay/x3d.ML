"""Fold the two community-loop runs into one list: loops on the same theme in both runs keep run 0's wording (votes 2); a loop seen in one run only keeps votes 1.
Theme pairing was judged by reading both runs (run-0 index -> run-1 index); all provenance simulated, grade Suspected."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enrich, merge
G3 = merge.G3
runs = json.load(open(G3 + '/loops2_runs.json'))
a, b = runs[0]['loops'], runs[1]['loops']
pairs = {0: 0, 1: 1, 3: 2, 4: 3, 5: 5, 2: 4}          # AI validation, Blender export, ontology, splats, benchmarking, interoperability
solo_b = [6, 7]                                         # Community loop, DSPy loop (run 1 only)
n2k = {enrich.ents[k]['name'].lower(): k for k in enrich.ents}
def mk(L, votes, name=None):
    return {'name': (name or L['name'])[:48], 'steps': [s['text'][:44] for s in L['steps']], 'gain': L.get('why'), 'docs': ['community recall'], 'ev': L.get('why', ''), 'votes': votes,
            'prov': 'simulated', 'grade': 'Suspected', 'links': {str(i): [n2k[s['by'].lower()]] for i, s in enumerate(L['steps']) if s.get('by', '').lower() in n2k}}
out = [mk(a[i], 2 if i in pairs else 1) for i in range(len(a)) if i in pairs or i in (6, 7)] + [mk(b[j], 1) for j in solo_b]
ex = json.load(open(G3 + '/extra_new.json')); ex['loops'] = out
json.dump(ex, open(G3 + '/extra_new.json', 'w')); print(len(out), [(L['name'], L['votes'], len(L['links'])) for L in out])
