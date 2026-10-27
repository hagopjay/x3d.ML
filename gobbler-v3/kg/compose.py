"""Pass 4: compose graph.json from the merged doc/community extraction, the data layers, the mined loops, then lay it out in 3D."""
import collections, json, math, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge, layers, layout, schema
G3 = merge.G3
NMAX = int(os.environ.get('NMAX', '520')); EMAX = int(os.environ.get('EMAX', '1500'))
ALL = os.environ.get('ALL') == '1'          # deep mode: every connected entity is drawn; the first NMAX are the core (full ribbons), the rest a star tier with 1-2 faint tethers
CORE_PEOPLE = {   # GitHub handles read from the public pages on 27 Oct 2026
    'ahujasid': {'role': 'GitHub account of Siddharth, author of blender-mcp', 'license': 'MIT', 'contributions': 'README: "Contributions are welcome!"', 'src': 'github.com/ahujasid/blender-mcp, read 27 Oct 2026'},
    'coderextreme': {'role': 'GitHub account of John Carlson, author of X3DJSONLD', 'license': 'BSD 3-clause (Copyright 2015-6 John Carlson)', 'src': 'github.com/coderextreme/X3DJSONLD LICENSE, read 27 Oct 2026'},
}
GR = {'Confirmed': 3, 'Likely': 2, 'Suspected': 1}
FAM = {c: i for i, (_, cs) in enumerate([('spec', ('Standard', 'Component', 'NodeType')), ('tool', ('Tool', 'Validator', 'Repo')), ('people', ('Org', 'Person', 'Event')),
       ('work', ('Workstream', 'Document', 'Dataset', 'Scene')), ('learn', ('Experiment', 'Finding', 'Metric')), ('rule', ('Rule', 'Decision')), ('loop', ('Loop',))]) for c in cs}

def short(s, n=40):
    s = re.sub(r'\s+', ' ', str(s)).strip(' .;:')
    return (s[:1].upper() + s[1:])[:n].rstrip()

def cluster_loops(m):
    items = [l for l in m['loops'] if len(l['steps']) >= 3]
    clusters = []
    for l in items:
        toks = set(w for st in l['steps_raw'] for w in merge.norm(st).split() if len(w) > 3)
        for c in clusters:
            j = len(toks & c['toks']) / max(1, len(toks | c['toks']))
            if j >= 0.5 or merge.norm(l['name']) == c['namek']:
                c['members'].append(l); c['toks'] |= toks; break
        else:
            clusters.append({'toks': set(toks), 'members': [l], 'namek': merge.norm(l['name'])})
    out = []
    for c in clusters:
        mem = c['members']
        occ = {(l['chunk'], l['run']) for l in mem}
        if len(occ) < 2: continue
        steps = collections.Counter(tuple(l['steps_raw']) for l in mem).most_common(1)[0][0]
        name = collections.Counter(l['name'] for l in mem if l['name']).most_common(1)[0][0]
        gains = [l['gain'] for l in mem if l.get('gain') and re.search(r'\d', str(l['gain']))]
        out.append({'name': short(name, 48), 'steps': [short(s) for s in steps], 'gain': gains[0] if gains else None, 'docs': sorted({l['doc'] for l in mem}),
                    'ev': mem[0]['ev'], 'votes': len(occ), 'prov': 'doc', 'grade': 'Likely'})
    return out

def main():
    m = json.load(open(G3 + '/merged.json'))
    sn, se = layers.spine_layer(); en, ee = layers.eco_layer()
    ents = {}
    for k, v in m['entities'].items():
        ents[k] = {'name': v['name'], 'type': v['type'], 'prov': v['prov'], 'mentions': v['mentions'], 'docs': v.get('docs', []), 'props': {}, 'notes': v.get('notes', [])}
    for lay in (sn, en):
        for k, v in lay.items():
            if k in ents:
                ents[k]['prov'] = 'data'; ents[k]['props'].update(v['props']); ents[k]['src'] = v['src']
            else:
                ents[k] = {'name': v['name'], 'type': v['type'], 'prov': 'data', 'mentions': 3, 'docs': [], 'props': v['props'], 'notes': [], 'src': v['src']}
    # GitHub owner handles were typed Org when they were only a repo prefix; a lowercase single-token handle is a person's account unless it names a group
    for k, v in ents.items():
        if v['type'] == 'Org' and re.fullmatch(r'[a-z0-9_-]{4,}', v['name']) and not re.search(r'group|consortium|innovation|foundation|labs?$|inc$', v['name']):
            v['type'] = 'Person'
        if v['name'].lower() in CORE_PEOPLE:
            v['type'] = 'Person'; v['prov'] = 'data'; v['props'].update({kk: vv for kk, vv in CORE_PEOPLE[v['name'].lower()].items() if kk != 'src'}); v['src'] = CORE_PEOPLE[v['name'].lower()]['src']
    edges = []
    for t in m['triples']:
        if t['s'] not in ents or t['o'] not in ents: continue
        if t['prov'] == 'doc':
            if t['votes'] >= 2: g = 'Confirmed' if t['hint'] == 'Confirmed' else 'Likely'
            else: continue
        else:
            if t['votes'] >= 3: g = 'Likely'
            elif t['votes'] == 2: g = 'Suspected'
            else: continue
        edges.append({'s': t['s'], 'o': t['o'], 'p': t['p'], 'grade': g, 'prov': t['prov'], 'w': t['votes'], 'ev': t['ev'][:1], 'docs': t['docs'][:3]})
    for lay_e in (se, ee): edges += lay_e
    # metrics
    for k, ms in m['metrics'].items():
        if k in ents:
            seen = set(); keep = []
            for x in sorted(ms, key=lambda x: -len(str(x['check'] or ''))):
                kk = (x['name'], x['value'])
                if kk in seen: continue
                seen.add(kk); keep.append({'name': x['name'], 'value': x['value'], 'check': x['check'], 'doc': x['doc']})
                if len(keep) >= 4: break
            ents[k]['metrics'] = keep
    loops = cluster_loops(m)
    extra = json.load(open(G3 + '/extra.json')) if os.path.exists(G3 + '/extra.json') else {}
    for e in extra.get('edges', []):
        if e['s'] in ents and e['o'] in ents: edges.append(e)
    for L in loops: L['links'] = {i: [k for k in ks if k in ents] for i, ks in (extra.get('mapped_loops', {}).get(L['name'], {}) or {}).items()}
    for L in extra.get('loops', []): loops.append(L)
    if os.environ.get('DUMP'):
        json.dump({'ents': ents, 'edges': edges, 'loops': loops}, open(G3 + '/assembled.json', 'w'))
        print('assembled dumped:', len(ents), 'entities', len(edges), 'edges', len(loops), 'loops'); return
    # loops: step nodes + a centre node each
    loop_nodes = []
    for li, L in enumerate(loops):
        ids = []
        for si, st in enumerate(L['steps']):
            key = 'loop%d_step%d' % (li, si)
            ents[key] = {'name': st, 'type': 'Loop', 'prov': L['prov'], 'mentions': 3, 'docs': L['docs'], 'props': {'loop': L['name'], 'step': si + 1}, 'notes': [], 'step': True}
            ids.append(key)
        ck = 'loop%d_centre' % li
        ents[ck] = {'name': L['name'], 'type': 'Loop', 'prov': L['prov'], 'mentions': 5, 'docs': L['docs'], 'props': {'gain': L['gain'], 'steps': len(ids)}, 'notes': [], 'centre': True}
        L['ids'] = ids; L['centre'] = ck
        for si, keys_ in (L.get('links') or {}).items():
            for kk in keys_:
                if kk in ents and int(si) < len(ids):
                    edges.append({'s': ids[int(si)], 'o': kk, 'p': 'implements' if ents[kk]['type'] in ('Tool', 'Validator', 'Rule', 'Repo') else 'uses', 'grade': 'Likely', 'prov': L['prov'], 'w': 2, 'loop': -1, 'ev': [L['ev']], 'docs': L['docs'][:2]})
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges.append({'s': a, 'o': b, 'p': 'feeds', 'grade': L['grade'], 'prov': L['prov'], 'w': 3, 'loop': li, 'ev': [L['ev']], 'docs': L['docs'][:2]})
        for a in ids:
            edges.append({'s': a, 'o': ck, 'p': 'step_of', 'grade': L['grade'], 'prov': L['prov'], 'w': 1, 'loop': -2})
    # degree and selection
    deg = collections.Counter()
    for e in edges: deg[e['s']] += 1; deg[e['o']] += 1
    protected = {k for k, v in ents.items() if v['prov'] == 'data' or v.get('step') or v.get('centre')}
    score = {k: deg[k] + 0.5 * min(v['mentions'], 6) + (3 if v['prov'] == 'data' else 0) for k, v in ents.items() if deg[k] > 0}
    orphans = set()
    if ALL:      # entities no relation survived voting for: drawn as untethered stars when two or more runs saw them, listed in the data when only one did
        orphans = {k for k, v in ents.items() if deg[k] == 0 and v['mentions'] >= 2 and not v.get('step') and not v.get('centre')}
        for k in orphans: score[k] = 0.25 * min(ents[k]['mentions'], 6)
    undrawn = [k for k, v in ents.items() if deg[k] == 0 and k not in orphans and not v.get('step') and not v.get('centre')]
    keep = set(protected & set(score))
    # the flywheel is findings -> rules -> metrics: reserve room for them instead of letting hub tools crowd them out
    QUOTA = {'Finding': 70, 'Rule': 55, 'Experiment': 40, 'Metric': 12, 'Decision': 14, 'Workstream': 40, 'Validator': 30}
    for cls, qn in QUOTA.items():
        have = sum(1 for k in keep if ents[k]['type'] == cls)
        for k in sorted((k for k in score if ents[k]['type'] == cls and k not in keep), key=lambda k: -score[k]):
            if have >= qn: break
            keep.add(k); have += 1
    for k in sorted(score, key=lambda k: -score[k]):
        if len(keep) >= NMAX: break
        keep.add(k)
    core = set(keep)
    ed = [e for e in edges if e['s'] in core and e['o'] in core]
    loop_e = [e for e in ed if e.get('loop', -1) != -1]
    other = sorted([e for e in ed if e.get('loop', -1) == -1], key=lambda e: (-GR[e['grade']], -e['w']))
    ed = loop_e + other[:max(0, EMAX - len(loop_e))]
    if ALL:
        # star tier: every other connected entity is drawn, tethered by its best 2 relations (faint ribbons); the relations stay in the data
        keep |= set(score)      # includes orphans
        best = collections.defaultdict(list)
        for e in edges:
            if e.get('loop', -1) != -1: continue
            for a, b in ((e['s'], e['o']), (e['o'], e['s'])):
                if a in keep and a not in core and b in keep and b != a:
                    best[a].append((-(GR[e['grade']] * 2 + (b in core) * 3 + min(e['w'], 3)), id(e), e))
        have = {(min(e['s'], e['o']), max(e['s'], e['o'])) for e in ed}
        for a, lst in best.items():
            n_ = 0
            for _, _, e in sorted(lst, key=lambda x: x[:2]):
                kk = (min(e['s'], e['o']), max(e['s'], e['o']))
                if kk in have: n_ += 1; continue
                if n_ >= 2: break
                e = dict(e); e['faint'] = 1; ed.append(e); have.add(kk); n_ += 1
    deg = collections.Counter()
    for e in ed: deg[e['s']] += 1; deg[e['o']] += 1
    keys = [k for k in keep if deg[k] > 0 or k in orphans]
    order = [k for k in keys if not ents[k].get('step') and not ents[k].get('centre')] + [k for k in keys if ents[k].get('step')] + [k for k in keys if ents[k].get('centre')]
    # keep step nodes contiguous per loop in cycle order for the layout
    idx = {k: i for i, k in enumerate(order)}
    mx = max(score.get(k, 1) for k in order)
    nodes = []
    for k in order:
        v = ents[k]
        best = max([GR[e['grade']] for e in ed if e['s'] == k or e['o'] == k] + [0])
        w = (min(1.0, score.get(k, deg[k]) / (0.55 * mx))) ** 0.6
        nodes.append({'id': k, 'label': v['name'], 'cls': v['type'], 'grade': {3: 'Confirmed', 2: 'Likely', 1: 'Suspected', 0: 'Suspected'}[best] if v['prov'] != 'data' else 'Confirmed',
                      'tier': 1 if k in core else 2, 'orphan': 1 if k in orphans else 0, 'prov': v['prov'], 'vis': extra.get('vis', {}).get(k, 'private' if v['prov'] == 'doc' else 'public'), 'w': round(w, 3), 'deg': deg[k], 'docs': v['docs'][:4], 'props': v['props'], 'metrics': v.get('metrics', []), 'notes': v.get('notes', [])[:1], 'loops': []})
    E_out = []
    for e in ed:
        E_out.append({'s': idx[e['s']], 't': idx[e['o']], 'p': e['p'], 'grade': e['grade'], 'prov': e['prov'], 'loop': e.get('loop', -1), 'w': e['w'], 'faint': e.get('faint', 0), 'ev': e.get('ev', []), 'docs': e.get('docs', [])})
    Lo = []
    for li, L in enumerate(loops):
        if not all(i in idx for i in L['ids']) or L['centre'] not in idx: continue
        steps = [idx[i] for i in L['ids']]
        for s_ in steps: nodes[s_]['loops'].append(len(Lo))
        nodes[idx[L['centre']]]['loops'].append(len(Lo))
        Lo.append({'name': L['name'], 'steps': steps, 'centre': idx[L['centre']], 'gain': L['gain'], 'docs': L['docs'], 'ev': L['ev'], 'prov': L['prov'], 'grade': L['grade'], 'votes': L['votes']})
        for e in E_out:
            if e['loop'] == li: e['loop'] = len(Lo) - 1
    for e in E_out:
        if e['loop'] == -2: e['loop'] = -3          # spokes: kept in the data, not drawn as wheel rim
    # drawn wheel edges only for loop >= 0 ; spokes (-3) are data only
    if ALL: layout.SPREAD = float(os.environ.get('SPREAD', '1.35'))
    conn = [i for i, n in enumerate(nodes) if not n.get('orphan')]
    cmap = {o: k for k, o in enumerate(conn)}
    sub_edges = [(cmap[e['s']], cmap[e['t']], min(1.0, 0.3 + 0.2 * e['w'])) for e in E_out if e['s'] in cmap and e['t'] in cmap]
    pos_c, rings = layout.layout(len(conn), sub_edges, [nodes[i]['w'] for i in conn], [[cmap[x] for x in L['steps']] for L in Lo], [FAM.get(nodes[i]['cls'], 0) for i in conn])
    orph = [i for i, n in enumerate(nodes) if n.get('orphan')]
    pos_o = layout.place_free(pos_c, [FAM.get(nodes[i]['cls'], 0) for i in orph], len(set(FAM.values()))) if orph else []
    pos = [None] * len(nodes)
    for o, k in cmap.items(): pos[o] = pos_c[k]
    for o, p_ in zip(orph, pos_o): pos[o] = p_
    for n, p_ in zip(nodes, pos): n['xyz'] = [round(float(x), 3) for x in p_]
    for L, r in zip(Lo, rings):
        L['ring'] = r
        # the centre sits at the ring's centre
        nodes[L['centre']]['xyz'] = [round(x, 3) for x in r['center']]
    meta = {'nodes': len(nodes), 'edges': len(E_out), 'loops': len(Lo), 'extraction_chunks': m['chunks_done'], 'stats': m['stats'],
            'prov_counts': dict(collections.Counter(n['prov'] for n in nodes)), 'grade_counts': dict(collections.Counter(n['grade'] for n in nodes)), 'class_counts': dict(collections.Counter(n['cls'] for n in nodes)),
            'edge_prov_counts': dict(collections.Counter(e['prov'] for e in E_out)), 'edge_grade_counts': dict(collections.Counter(e['grade'] for e in E_out))}
    meta['undrawn'] = len(undrawn); meta['assembled'] = len(ents)
    und = [{'label': ents[k]['name'], 'cls': ents[k]['type'], 'prov': ents[k]['prov'], 'mentions': ents[k]['mentions'], 'docs': ents[k]['docs'][:3], 'vis': extra.get('vis', {}).get(k, 'private')} for k in undrawn]
    json.dump({'nodes': nodes, 'edges': E_out, 'loops': Lo, 'meta': meta, 'undrawn': und}, open(sys.argv[1] if len(sys.argv) > 1 else G3 + '/graph.json', 'w'))
    print(json.dumps(meta, indent=1)[:1800])
if __name__ == '__main__': main()
