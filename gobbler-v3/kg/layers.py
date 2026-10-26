"""Data layers (provenance 'data', grade Confirmed): BigQuery x3d_spine aggregates and the ecosystem watch state. No model involved."""
import collections, itertools, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge
G3 = merge.G3
D = G3 + '/data/'
def jl(n): return json.load(open(D + n))

def spine_layer():
    nodes, edges = {}, []
    def N(label, cls, **props):
        k = merge.norm(label)
        nodes[k] = {'name': label, 'type': cls, 'prov': 'data', 'grade': 'Confirmed', 'props': props, 'src': 'BigQuery x3d_spine (query 26 Oct 2026)'}
        return k
    def E(a, p, b, w=None, **kw):
        edges.append({'s': a, 'p': p, 'o': b, 'grade': 'Confirmed', 'prov': 'data', 'w': w, 'src': 'BigQuery x3d_spine', **kw})
    kinds = jl('spine_kinds.json'); total = sum(int(k['n']) for k in kinds)
    sp = N('x3d_spine', 'Dataset', scenes=total, note='non-mutant scenes: showcase, archive mirror, generated, tuned eval, evolve, hand, bench')
    labels = {'tuned_eval': 'spine tuned-eval scenes', 'archive_mirror': 'spine archive mirror', 'generated': 'spine generated scenes', 'showcase_demo': 'spine showcase demos',
              'evolve': 'spine evolve scenes', 'hand': 'spine hand-made scenes', 'bench': 'spine bench scenes', 'archive_repro': 'spine archive repros'}
    for k in kinds:
        lab = labels.get(k['source_kind'], 'spine ' + k['source_kind'])
        kk = N(lab, 'Dataset', scenes=int(k['n']), with_splats=int(k['splats']), with_geo=int(k['geo']), with_script=int(k['scripts']))
        E(kk, 'part_of', sp, int(k['n']))
    comps = collections.defaultdict(int)
    for c in jl('spine_components.json'):
        name = c['comp'].split(':')[0]; comps[name] = max(comps[name], int(c['n']))
    for name, n in sorted(comps.items(), key=lambda kv: -kv[1])[:28]:
        kk = N(name + ' component', 'Component', scenes=n)
        E(sp, 'contains', kk, n, note='scenes declaring the component')
    ver = collections.defaultdict(int)
    for v in jl('spine_versions.json'):
        if v['v']: ver[v['v']] += int(v['n'])
    for v, n in ver.items():
        if n >= 5:
            kk = N('X3D ' + v, 'Standard', scenes=n); E(sp, 'contains', kk, n)
    # node types and their co-use
    top = [r for r in jl('spine_nodes.json')][:70]
    cnt = {r['n']: int(r['k']) for r in top}
    for r in top[:48]:
        N(r['n'], 'NodeType', scenes=int(r['k']))
    sets = [set(x for x in s['node_set'] if x in cnt) for s in jl('spine_scenes_nodesets.json') if isinstance(s['node_set'], list)]
    n_sc = len(sets); pair = collections.Counter()
    for st in sets:
        for a, b in itertools.combinations(sorted(st), 2): pair[(a, b)] += 1
    sc = []
    for (a, b), c in pair.items():
        if a in [r['n'] for r in top[:48]] and b in [r['n'] for r in top[:48]] and c >= 20:
            lift = c * n_sc / (cnt[a] * cnt[b]) if cnt[a] and cnt[b] else 0
            sc.append((lift * math.log(c), a, b, c, lift))
    for _, a, b, c, lift in sorted(sc, reverse=True)[:70]:
        E(merge.norm(a), 'co_used_with', merge.norm(b), c, lift=round(lift, 2), note='scenes containing both (of %d non-mutant scenes with node sets)' % n_sc)
    for v in jl('spine_validators.json'):
        lab = {'fork_integration': 'fork validator (integration)', 'upstream_main': 'upstream validator (main)'}.get(v['validator'], v['validator'])
        kk = N(lab, 'Validator', runs=int(v['n']), xsd_valid=int(v['xsd_ok']), note='validation runs over spine scenes including mutants')
        E(kk, 'validates', sp, int(v['n']))
    for r in jl('spine_creators.json'):
        n = int(r['n']); c = r['creator']
        if n < 8 or 'Doug Sanden' in c or ' and ' in c and False: continue
        c = {'John W Carlson': 'John Carlson'}.get(c, c)
        kk = N(c, 'Person', archive_scenes=n, note='creator credited in scene metadata')
        E(merge.norm('spine archive mirror'), 'authored_by', kk, n)
    return nodes, edges

def eco_layer():
    nodes, edges = {}, []
    st = json.load(open(G3 + '/corpus/docs/ecosystem_state.json'))
    def N(label, cls, **props):
        k = merge.norm(label); nodes[k] = {'name': label, 'type': cls, 'prov': 'data', 'grade': 'Confirmed', 'props': props, 'src': 'ecosystem watch state.json (last run %s)' % st['last_run'][:10]}; return k
    w = N('Ecosystem watch', 'Workstream', note='daily watch of public repos and package registries')
    for key, val in st['values'].items():
        kind, _, rest = key.partition(':')
        if kind == 'git' and key.endswith(':head'):
            repo = rest[:-5]; owner = repo.split('/')[0]
            r = N(repo, 'Repo', head=(val or 'not fetched')[:12] if isinstance(val, str) or val is None else str(val)); o = N(owner, 'Org')
            edges.append({'s': r, 'p': 'maintained_by', 'o': o, 'grade': 'Confirmed', 'prov': 'data', 'w': 1, 'src': 'ecosystem watch'})
            edges.append({'s': w, 'p': 'watches', 'o': r, 'grade': 'Confirmed', 'prov': 'data', 'w': 1, 'src': 'ecosystem watch'})
        elif kind in ('npm', 'pypi') and isinstance(val, dict):
            r = N(rest, 'Tool', version=val.get('version'), released=val.get('date'), registry=kind)
            edges.append({'s': w, 'p': 'watches', 'o': r, 'grade': 'Confirmed', 'prov': 'data', 'w': 1, 'src': 'ecosystem watch'})
    return nodes, edges
if __name__ == '__main__':
    a, b = spine_layer(); c, d = eco_layer()
    print(len(a), len(b), len(c), len(d))
