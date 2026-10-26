"""Extra hypothesis pass: 3 pro runs in parallel, runs cached in hypo_runs.json; pairs seen by 2+ runs keep w=2, singles (w=1) are kept too, capped at 45, all provenance simulated / Suspected."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enrich, schema, merge
G3 = merge.G3
runs = json.load(open(G3 + '/hypo_runs.json')) if os.path.exists(G3 + '/hypo_runs.json') else None
if runs is None:
    pr = f"""Knowledge graph of the global X3D community and the PolyXandria project (entities: name | type):
{enrich.LIST}
Existing loops: {json.dumps([l['name'] for l in enrich.loops])}
Propose 25 MISSING links between listed entities that are plausible and, if true, would be valuable: a combination that has not been tried, a tool that could consume another's output, a rule that should be learned from a finding. Use names exactly as listed and a predicate from: {', '.join(sorted(schema.PREDICATES))}.
For each give one sentence of rationale. Return JSON {{"edges":[{{"s":"","p":"","o":"","why":""}}]}}"""
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(3) as ex: runs = list(ex.map(lambda r: enrich.jc(enrich.PRO, pr, 'hypo2:%d' % r, temperature=0.8, max_out=24000), range(3)))
    json.dump(runs, open(G3 + '/hypo_runs.json', 'w'))
seen = collections.defaultdict(list)
for r, res in enumerate(runs):
    for e in (res or {}).get('edges', []):
        s_, o_ = e.get('s', '').lower(), e.get('o', '').lower()
        if s_ in enrich.name2key and o_ in enrich.name2key and e.get('p') in schema.PREDICATES and s_ != o_:
            a, b = enrich.name2key[s_], enrich.name2key[o_]
            seen[(min(a, b), max(a, b))].append((r, a, e['p'], b, e.get('why', '')))
two, one = [], []
for pair, lst in seen.items():
    n = len({r for r, *_ in lst}); _, a, p, b, why = lst[0]
    (two if n >= 2 else one).append({'s': a, 'p': p, 'o': b, 'grade': 'Suspected', 'prov': 'simulated', 'w': n, 'loop': -1, 'ev': [why], 'docs': ['hypothesis: %d of 3 runs proposed this pair' % n]})
out = two + one[:45]
ex = json.load(open(G3 + '/extra_new.json')); ex['edges'] = out
json.dump(ex, open(G3 + '/extra_new.json', 'w')); print('proposed', sum(len((r or {}).get('edges', [])) for r in runs), 'agreed', len(two), 'singles kept', min(45, len(one)), 'of', len(one))
