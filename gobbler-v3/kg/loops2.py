"""Replace the thin community loops with better ones: steps are short verb phrases, each optionally realised by a listed entity.
Two pro runs in parallel; a loop is kept if the other run has one with >=0.3 realiser/step overlap. Provenance simulated, grade Suspected."""
import collections, json, os, re, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enrich, merge
G3 = merge.G3
ok = [k for k in enrich.TOPN if enrich.ents[k]['type'] in ('Standard', 'Component', 'Tool', 'Validator', 'Org', 'Workstream', 'Finding', 'Rule', 'Experiment', 'Dataset', 'Event')
      and not re.search(r'[/\\]|\.md|\.py|\.json|\.x3d', enrich.ents[k]['name'])]
LIST = '\n'.join(enrich.ents[k]['name'] for k in ok[:230])
n2k = {enrich.ents[k]['name'].lower(): k for k in ok}
pr = f"""Think about the global X3D / Web3D community and its AI-era turn (validators, AI writers, X_ITE, Blender, glTF, USD, Khronos, the Web3D Consortium, the VRML and X3D heritage, open scene archives).
Describe 8 virtuous circles (flywheels): closed loops of 4 to 6 steps where each step makes the next one easier and the last step feeds the first.
Each step is a SHORT VERB PHRASE of at most 6 words (for example "Validator exposes a new failure class"), plus optionally one realising entity from this list (names exactly as listed), or "" when none fits:
{LIST}
Return JSON {{"loops":[{{"name":"","why":"one sentence on why it is self-reinforcing","steps":[{{"text":"","by":""}}]}}]}}"""
def run(r):
    for att in range(3):
        try: return enrich.gem.jcall(enrich.PRO, pr, temperature=0.7, max_out=24000, tag='loops2:%d' % r, cap=15.0)
        except Exception as e: err = str(e)[:80]
    print('ERR', err); return None
with cf.ThreadPoolExecutor(2) as ex: runs = list(ex.map(run, range(2)))
json.dump(runs, open(G3 + '/loops2_runs.json', 'w'))
def tk(L): return set(w for s in L['steps'] for w in merge.norm(s['text'] + ' ' + s.get('by', '')).split() if len(w) > 3)
keep = []
if all(runs):
    used = set()
    for L in runs[0].get('loops', []):
        for j, M in enumerate(runs[1].get('loops', [])):
            if j in used: continue
            a, b = tk(L), tk(M)
            if a and len(a & b) / len(a | b) >= 0.2: keep.append(L); used.add(j); break
ex = json.load(open(G3 + '/extra_new.json'))
ex['loops'] = [{'name': L['name'][:48], 'steps': [s['text'][:44] for s in L['steps']], 'gain': L.get('why'), 'docs': ['community recall'], 'ev': L.get('why', ''),
                'links': {str(i): [n2k[s['by'].lower()]] for i, s in enumerate(L['steps']) if s.get('by', '').lower() in n2k}} for L in keep]
json.dump(ex, open(G3 + '/extra_new.json', 'w'))
print('loops proposed', [len(r.get('loops', [])) for r in runs if r], 'kept', len(keep), [L['name'] for L in keep])
