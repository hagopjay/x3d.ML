"""Pass 2: vote across the 3 runs, drop any triple whose evidence quote is not verbatim in its chunk, canonicalise names (canon.json from resolve.py).
Also folds in the community-recall runs (provenance model_recall)."""
import glob, json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract, schema
G3 = extract.G3

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()
def squash(s):
    return re.sub(r'\s+', ' ', str(s)).strip().lower()

def load():
    cs = {c['id']: c for c in extract.chunks()}
    runs = collections.defaultdict(dict)
    for fn in glob.glob(G3 + '/runs/*.json'):
        d = json.load(open(fn)); runs[d['chunk']][d['run']] = d['result']
    return cs, runs

def main():
    canon = json.load(open(G3 + '/canon.json')) if os.path.exists(G3 + '/canon.json') else {}
    cn = lambda n: canon.get(n, n)
    cs, runs = load()
    stats = collections.Counter()
    ent = collections.defaultdict(lambda: {'types': collections.Counter(), 'aliases': set(), 'names': collections.Counter(), 'docs': set(), 'runs': 0, 'prov': collections.Counter(), 'notes': []})
    trip = collections.defaultdict(lambda: {'runs': set(), 'docs': set(), 'grades': collections.Counter(), 'ev': [], 'chunks': set(), 'prov': 'doc'})
    pairs = collections.defaultdict(lambda: {'runs': set()})
    metrics = collections.defaultdict(list); loops = []
    for cid, rr in runs.items():
        ch = cs.get(cid)
        if not ch: continue
        hay = squash(ch['text'])
        for k, r in rr.items():
            if not isinstance(r, dict): continue
            for e in r.get('entities') or []:
                if not isinstance(e, dict) or not e.get('name') or e.get('type') not in schema.CLASSES: continue
                n = cn(norm(e['name']))
                if not n: continue
                x = ent[n]; x['types'][e['type']] += 1; x['names'][e['name'].strip()] += 1; x['docs'].add(ch['doc']); x['runs'] += 1; x['prov']['doc'] += 1
                for a in e.get('aliases') or []:
                    if isinstance(a, str) and norm(a): x['aliases'].add(a.strip())
            for t in r.get('triples') or []:
                stats['triples_raw'] += 1
                if not isinstance(t, dict) or t.get('p') not in schema.PREDICATES: stats['bad_pred'] += 1; continue
                ev = squash(t.get('evidence', ''))
                if len(ev) < 12 or ev not in hay: stats['evidence_not_verbatim'] += 1; continue
                s, o = cn(norm(t.get('s', ''))), cn(norm(t.get('o', '')))
                if not s or not o or s == o: continue
                key = (s, t['p'], o)
                y = trip[key]; y['runs'].add((cid, k)); y['docs'].add(ch['doc']); y['chunks'].add(cid)
                y['grades'][t.get('grade') if t.get('grade') in schema.GRADES else 'Likely'] += 1
                if len(y['ev']) < 3 and t['evidence'] not in y['ev']: y['ev'].append(t['evidence'])
                pairs[(min(s, o), max(s, o))]['runs'].add((cid, k))
                stats['triples_kept'] += 1
            for m in r.get('metrics') or []:
                if isinstance(m, dict) and m.get('value') and m.get('about') and len(squash(m.get('evidence', ''))) > 8 and squash(m['evidence']) in hay:
                    metrics[cn(norm(m['about']))].append({'name': m.get('name'), 'value': m['value'], 'check': m.get('source_check'), 'doc': ch['doc'], 'ev': m['evidence'], 'run': k})
                    stats['metrics_kept'] += 1
            for l in r.get('loops') or []:
                if isinstance(l, dict) and isinstance(l.get('steps'), list) and len(l['steps']) >= 3 and len(squash(l.get('evidence', ''))) > 8 and squash(l['evidence']) in hay:
                    loops.append({'name': l.get('name'), 'steps': [cn(norm(x)) for x in l['steps']], 'steps_raw': l['steps'], 'gain': l.get('gain'), 'doc': ch['doc'], 'ev': l['evidence'], 'chunk': cid, 'run': k})
                    stats['loops_kept'] += 1
    # chunk-level vote
    out_t = []
    for (s, p, o), y in trip.items():
        votes = 0; denom = 0
        for cid in y['chunks']:
            nrun = len(runs[cid]); hit = len({k for (c, k) in y['runs'] if c == cid})
            votes = max(votes, hit); denom = max(denom, nrun)
        pv = max((len({k for (c, k) in pairs[(min(s, o), max(s, o))]['runs'] if c == cid}) for cid in y['chunks']), default=0)
        out_t.append({'s': s, 'p': p, 'o': o, 'votes': votes, 'pair_votes': pv, 'of': denom, 'docs': sorted(y['docs']), 'hint': y['grades'].most_common(1)[0][0], 'ev': y['ev'], 'prov': 'doc'})
    # community runs (model recall): 3 runs per facet; a triple/entity counts once per run
    ctr = collections.defaultdict(set); cent = collections.defaultdict(lambda: {'types': collections.Counter(), 'names': collections.Counter(), 'runs': set(), 'notes': [], 'conf': []})
    nfac = collections.defaultdict(set)
    for fn in glob.glob(G3 + '/runs_community/*.json'):
        d = json.load(open(fn)); r = d['result']; nfac[d['facet']].add(d['run'])
        for e in r.get('entities') or []:
            if isinstance(e, dict) and e.get('name') and e.get('type') in schema.CLASSES:
                x = cent[cn(norm(e['name']))]; x['types'][e['type']] += 1; x['names'][e['name'].strip()] += 1; x['runs'].add((d['facet'], d['run']))
                if e.get('note') and len(x['notes']) < 2: x['notes'].append(e['note'])
                try: x['conf'].append(float(e.get('confidence', 0.8)))
                except Exception: pass
        for t in r.get('triples') or []:
            if isinstance(t, dict) and t.get('p') in schema.PREDICATES:
                s, o = cn(norm(t.get('s', ''))), cn(norm(t.get('o', '')))
                if s and o and s != o:
                    try: c = float(t.get('confidence', 0.8))
                    except Exception: c = 0.8
                    ctr[(s, t['p'], o)].add((d['facet'], d['run'], c))
    comm_t = []
    for (s, p, o), v in ctr.items():
        fac = collections.Counter(f for f, _, _ in v)
        votes = max(len({r for f2, r, _ in v if f2 == f}) for f in fac)
        comm_t.append({'s': s, 'p': p, 'o': o, 'votes': votes, 'pair_votes': votes, 'of': 3, 'docs': ['community:' + f for f in fac], 'hint': 'Likely' if votes == 3 else 'Suspected',
                       'conf': round(sum(c for _, _, c in v) / len(v), 2), 'ev': [], 'prov': 'model_recall'})
    ents = {}
    for n, x in ent.items():
        ents[n] = {'name': x['names'].most_common(1)[0][0], 'type': x['types'].most_common(1)[0][0], 'aliases': sorted(x['aliases'])[:8], 'docs': sorted(x['docs']), 'mentions': x['runs'], 'prov': 'doc'}
    for n, x in cent.items():
        if n in ents:
            ents[n]['community_runs'] = len(x['runs']); ents[n]['notes'] = x['notes']
        else:
            ents[n] = {'name': x['names'].most_common(1)[0][0], 'type': x['types'].most_common(1)[0][0], 'aliases': [], 'docs': [], 'mentions': 0, 'prov': 'model_recall', 'community_runs': len(x['runs']), 'notes': x['notes'], 'conf': round(sum(x['conf']) / max(1, len(x['conf'])), 2)}
    json.dump({'entities': ents, 'triples': out_t + comm_t, 'metrics': metrics, 'loops': loops, 'stats': dict(stats), 'chunks_done': len(runs), 'chunks_total': len(cs)}, open(G3 + '/merged.json', 'w'))
    print(dict(stats), 'entities', len(ents), 'triples', len(out_t), '+ community', len(comm_t), 'chunks', len(runs), '/', len(cs))
    print('doc votes', dict(collections.Counter(t['votes'] for t in out_t)), 'pair votes', dict(collections.Counter(t['pair_votes'] for t in out_t)))
if __name__ == '__main__': main()
