"""M-A: how much of a generated scene's value-bearing attributes can be tied to a phrase of its own prompt
(lexical upper bound, model-free). Corpus: x3d.ml demo/data/live.json (201 items: pt prompt text, B bodies)."""
import sys, json, time, collections
sys.path.insert(0, sys.argv[1])
import x3dtrace as T
live = json.load(open(sys.argv[2]))
rows, t0 = [], time.time()
agg = collections.Counter(); by_model = collections.defaultdict(collections.Counter); by_cat = collections.defaultdict(collections.Counter)
deriv = collections.Counter(); n_items = n_ok = 0
for it in live['items']:
    n_items += 1
    bodies = it['B']
    if not bodies: continue
    body = bodies[-1]
    sc = T.SceneIndex(body)
    if not sc.ok: agg['unparsed'] += 1; continue
    n_ok += 1
    claims, rest = T.suggest_claims(body, it['pt'])
    inv = len(claims) + len(rest)
    rep = T.check_claims(claims, [T.Source('prompt', it['pt'], 'text'), T.Source('scene', body, 'x3d')])
    for c in rep.items:
        agg['verdict_' + c.verdict] += 1
        for d in c.derivation: deriv[d.split(':')[0]] += 1
    agg['values'] += inv; agg['supported'] += len(claims); agg['unsupported'] += len(rest)
    by_model[it['m']]['values'] += inv; by_model[it['m']]['supported'] += len(claims)
    by_cat[it['c']]['values'] += inv; by_cat[it['c']]['supported'] += len(claims)
    nonprompt = [r for r in rest]
    agg['items_all_supported'] += (len(rest) == 0)
out = {'items': n_items, 'parsed_final_bodies': n_ok, 'values': agg['values'], 'supported': agg['supported'],
       'supported_share': round(agg['supported'] / max(1, agg['values']), 4), 'agg': dict(agg), 'derivations': dict(deriv),
       'by_model': {m: {**c, 'share': round(c['supported'] / max(1, c['values']), 4)} for m, c in by_model.items()},
       'by_category': {m: {**c, 'share': round(c['supported'] / max(1, c['values']), 4)} for m, c in by_cat.items()},
       'seconds': round(time.time() - t0, 1)}
print(json.dumps(out, indent=1))
