"""Pass 5 (reads assembled.json from `DUMP=1 compose.py`, writes extra.json):
  a) map each mined loop's steps to the entities that realise them (2 runs, intersection);
  b) community loops (virtuous circles of the global x3d community) - provenance simulated;
  c) hypothesis edges (the missing links) - provenance simulated, 3 runs, kept if 2 of 3 propose the same pair;
  d) visibility: which nodes could sit on a public page (2 runs, both must say public; plus a deny-list)."""
import collections, json, os, re, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem, schema, merge
G3 = merge.G3; FLASH = 'gemini-3.8-flash'; PRO = 'gemini-3.1-pro-preview'
A = json.load(open(G3 + '/assembled.json'))
ents, edges, loops = A['ents'], A['edges'], A['loops']
deg = collections.Counter()
for e in edges: deg[e['s']] += 1; deg[e['o']] += 1
top = sorted([k for k in ents if deg[k] > 0 and not ents[k].get('step')], key=lambda k: (-deg[k], -ents[k]['mentions']))
TOPN = top[:320]
LIST = '\n'.join('%s | %s' % (ents[k]['name'], ents[k]['type']) for k in TOPN)
name2key = {ents[k]['name'].lower(): k for k in TOPN}
def jc(model, prompt, tag, **kw):
    for att in range(3):
        try: return gem.jcall(model, prompt, tag=tag, cap=15.0, **kw)
        except Exception as e: err = str(e)[:80]
    print('ERR', tag, err); return None

def map_loops():
    out = {}
    def one(a):
        li, run = a
        L = loops[li]
        pr = f"""A feedback loop from the PolyXandria / X3D project: "{L['name']}". Steps in order: {json.dumps(L['steps'])}. Source quote: "{L['ev'][:400]}"
Entities in the knowledge graph (name | type):
{LIST}
For each step (by 0-based index), list up to 3 entities from the list that REALISE or PERFORM that step in this project (a tool, validator, rule, dataset or workstream that does it). Use names exactly as listed; skip a step if nothing fits.
Return JSON {{"links":{{"0":["name",...],"1":[...]}}}}"""
        return jc(FLASH, pr, 'maploop:%d:%d' % (li, run), temperature=0.1 + 0.3 * run, max_out=3000)
    jobs = [(li, r) for li in range(len(loops)) if not loops[li].get('links') for r in (0, 1)]
    with cf.ThreadPoolExecutor(4) as ex: res = list(ex.map(one, jobs))
    got = collections.defaultdict(lambda: collections.defaultdict(list))
    for (li, run), r in zip(jobs, res):
        if r: got[li][run] = r.get('links', {})
    for li, runs in got.items():
        links = {}
        if len(runs) == 2:
            for si in set(runs[0]) & set(runs[1]):
                both = [n for n in runs[0][si] if n in runs[1][si] and n.lower() in name2key]
                if both: links[si] = [name2key[n.lower()] for n in both[:3]]
        loops[li]['links'] = links
    return sum(len(l.get('links', {})) for l in loops)

def community_loops():
    pr = f"""Think about the global X3D / Web3D community and its AI-era turn. Describe 6 virtuous circles (flywheels): closed loops where each step makes the next one easier and the last feeds the first.
Examples of the kind of loop: standard -> implementations -> shared example scenes -> bug reports -> spec clarifications -> standard; validator -> AI writers -> new failure classes -> new checks -> validator.
Use these known graph entities as steps where they truly belong (names exactly as listed), otherwise a short new label:
{LIST}
Each loop: 4 to 7 steps, a name, and one sentence on why it is self-reinforcing. Return JSON {{"loops":[{{"name":"","steps":[""],"why":""}}]}}"""
    runs = [jc(PRO, pr, 'commloops:%d' % r, temperature=0.6, max_out=6000) for r in range(2)]
    # keep loops that two runs share (>=50% step overlap by normalised words)
    def toks(L): return set(w for s in L['steps'] for w in merge.norm(s).split() if len(w) > 3)
    keep = []
    if all(runs):
        for L in runs[0].get('loops', []):
            for M in runs[1].get('loops', []):
                t1, t2 = toks(L), toks(M)
                if t1 and len(t1 & t2) / len(t1 | t2) >= 0.3: keep.append(L); break
    return keep

def hypotheses():
    pr = f"""Knowledge graph of the global X3D community and the PolyXandria project (entities: name | type):
{LIST}
Existing loops: {json.dumps([l['name'] for l in loops])}
Propose 25 MISSING links between listed entities that are plausible and, if true, would be valuable: a combination that has not been tried, a tool that could consume another's output, a rule that should be learned from a finding. Use names exactly as listed and a predicate from: {', '.join(p for p in schema.PREDICATES if p not in ('step_of','feeds','co_used_with'))}.
For each give one sentence of rationale. Return JSON {{"edges":[{{"s":"","p":"","o":"","why":""}}]}}"""
    with cf.ThreadPoolExecutor(3) as ex: runs = list(ex.map(lambda r: jc(PRO, pr, 'hypo:%d' % r, temperature=0.7, max_out=24000), range(3)))
    seen = collections.defaultdict(list)
    for r, res in enumerate(runs):
        for e in (res or {}).get('edges', []):
            if e.get('s', '').lower() in name2key and e.get('o', '').lower() in name2key and e.get('p') in schema.PREDICATES:
                a, b = name2key[e['s'].lower()], name2key[e['o'].lower()]
                if a != b: seen[(min(a, b), max(a, b))].append((r, a, e['p'], b, e.get('why', '')))
    out = []
    for pair, lst in seen.items():
        if len({r for r, *_ in lst}) >= 2:
            _, a, p, b, why = lst[0]
            out.append({'s': a, 'p': p, 'o': b, 'grade': 'Suspected', 'prov': 'simulated', 'w': 1, 'loop': -1, 'ev': [why], 'docs': ['hypothesis: %d of 3 runs proposed this pair' % len({r for r, *_ in lst})]})
    return out, [sum(len((r or {}).get('edges', [])) for r in runs)]

DENY = re.compile(r'(gemini|claude|anthropic|openai|gpt[-\s]?\d|sonnet|opus|haiku|nvidia|vertex|key-tokenizer|c2pa|api[_\s-]?key|secret|credential|\$\s?\d|budget|quota|billing|invoice|iam |service account|gs://|enrie|street view|cloud run|bigquery|hagop|hagsmac|dr\.? polys|polys\b)', re.I)
def visibility():
    keys = [k for k in ents if deg[k] > 0]
    res = {}
    def one(a):
        b, run = a
        chunk = keys[b:b + 90]
        lines = '\n'.join('%d | %s | %s | docs: %s' % (i, ents[k]['name'], ents[k]['type'], ', '.join(d[:28] for d in ents[k]['docs'][:3])) for i, k in enumerate(chunk))
        pr = f"""Decide which graph nodes may appear on a PUBLIC showcase page about the global X3D / Web3D community.
PUBLIC: open standards, public tools/repos/orgs, public conferences and releases, node types and components, generic public concepts.
PRIVATE: anything about one person's unpublished internal project work: private repos, decisions or tasks pending, spend, credentials or cloud resources, private links, unpublished research data, named internal threads or handoffs, individual people's private affairs, AI model/vendor names.
Return JSON {{"public":[indices of public nodes]}}
{lines}"""
        r = jc(FLASH, pr, 'vis:%d:%d' % (b, run), temperature=0.0 + 0.2 * run, max_out=3000)
        return b, run, set((r or {}).get('public', []))
    jobs = [(b, run) for b in range(0, len(keys), 90) for run in (0, 1)]
    with cf.ThreadPoolExecutor(5) as ex: outs = list(ex.map(one, jobs))
    pub = collections.defaultdict(list)
    for b, run, st in outs: pub[b].append(st)
    for b, sets in pub.items():
        both = set.intersection(*sets) if len(sets) == 2 else set()
        for i, k in enumerate(keys[b:b + 90]):
            nm = ents[k]['name'] + ' ' + ' '.join(ents[k].get('docs', []))
            res[k] = 'public' if (i in both and not DENY.search(ents[k]['name']) and ents[k]['type'] not in ('Decision',) and not re.search(r'private|handoff|ledger|spend', nm, re.I)) else 'private'
    for k in ents:
        if ents[k]['prov'] == 'data' and k not in res: res[k] = 'public'
    return res

if __name__ == '__main__':
    extra = {}
    n = map_loops(); print('loop links', n, flush=True)
    cl = community_loops(); print('community loops', len(cl), flush=True)
    for L in cl:
        extra.setdefault('loops', []).append({'name': merge.norm(L['name']).title()[:48], 'steps': [s[:40] for s in L['steps']], 'gain': L.get('why'), 'docs': ['community recall'], 'ev': L.get('why', ''), 'votes': 2, 'prov': 'simulated', 'grade': 'Suspected',
              'links': {str(i): [name2key[s.lower()]] for i, s in enumerate(L['steps']) if s.lower() in name2key}})
    h, hc = hypotheses(); print('hypothesis edges', len(h), 'of', hc, flush=True)
    extra['edges'] = h
    extra['vis'] = visibility(); print('public', sum(v == 'public' for v in extra['vis'].values()), 'of', len(extra['vis']))
    extra['mapped_loops'] = {l['name']: l.get('links', {}) for l in loops}
    json.dump(extra, open(G3 + '/extra_new.json', 'w'))
