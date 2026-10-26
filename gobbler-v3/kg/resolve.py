"""Pass 2b: entity resolution. Two independent Gemini runs cluster names that are the same thing; a merge is kept only where BOTH runs agree.
Writes canon.json: normalised name -> canonical normalised name (+ display names)."""
import json, os, re, sys, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem, schema, merge
G3 = merge.G3; MODEL = 'gemini-3.8-flash'; BATCH = 200

def candidates(m):
    inpair = set()
    for t in m['triples']: inpair.add(t['s']); inpair.add(t['o'])
    for l in m['loops']:
        for st in l['steps']: inpair.add(merge.norm(st))
    return {k: v for k, v in m['entities'].items() if v['mentions'] >= 2 or k in inpair}

def prompt(items):
    lines = '\n'.join('%d | %s | %s' % (i, v['name'], ', '.join(v['aliases'][:3])) for i, (k, v) in enumerate(items))
    return f"""Below are entity names (index | name | known aliases) from a knowledge graph about X3D, Blender, validators, AI evaluation and the PolyXandria project.
Group the indices that are DEFINITELY the same real-world thing (spelling, plural, version-less vs named, abbreviation, 'the X' vs 'X').
Do NOT merge different versions (X3D 4.0 vs 4.1), different builds/commits, different people, or a thing with its parent or part.
Return JSON {{"clusters":[{{"canonical":"best display name","members":[indices]}}]}} listing only clusters with 2 or more members.
{lines}"""

def one(args):
    typ, items, run = args
    fn = '%s/resolve/%s_%d_%d.json' % (G3, re.sub(r'\W', '', typ), hash(tuple(k for k, _ in items)) % 10**8, run)
    if os.path.exists(fn): return json.load(open(fn))
    sh = items if run == 0 else items[::-1]
    for att in range(3):
        try:
            r = gem.jcall(MODEL, prompt(sh), temperature=0.1 + 0.2 * run, max_out=8000, tag='resolve:%s:%d' % (typ, run), cap=15.0)
            out = [{'canonical': c.get('canonical'), 'members': [sh[i][0] for i in c.get('members', []) if isinstance(i, int) and 0 <= i < len(sh)]} for c in r.get('clusters', [])]
            json.dump(out, open(fn, 'w')); return out
        except Exception as e:
            err = str(e)[:80]
    print('resolve ERR', typ, err); return []

def main():
    m = json.load(open(G3 + '/merged.json')); os.makedirs(G3 + '/resolve', exist_ok=True)
    cand = candidates(m)
    by = collections.defaultdict(list)
    for k, v in sorted(cand.items(), key=lambda kv: kv[1]['name'].lower()): by[v['type']].append((k, v))
    jobs = []
    for typ, items in by.items():
        for b in range(0, len(items), BATCH):
            for run in (0, 1): jobs.append((typ, items[b:b + BATCH], run))
    print('candidates', len(cand), 'jobs', len(jobs), flush=True)
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(one, jobs))
    # agreement: a pair merges only if both runs put it in one cluster
    pairs = collections.defaultdict(set)
    canon_name = {}
    for (typ, items, run), clusters in zip(jobs, res):
        for c in clusters:
            mem = c['members']
            for a in mem:
                for b in mem:
                    if a < b: pairs[(a, b)].add(run)
            canon_name[tuple(sorted(mem))] = c['canonical']
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    agreed = 0
    for (a, b), runs in pairs.items():
        if len(runs) == 2: parent[find(a)] = find(b); agreed += 1
    groups = collections.defaultdict(list)
    for k in list(parent): groups[find(k)].append(k)
    canon = {}
    for root, mem in groups.items():
        best = max(mem, key=lambda k: (cand[k]['mentions'], -len(cand[k]['name'])))
        for k in mem: canon[k] = best
    # aliases that equal another candidate's name
    for k, v in cand.items():
        for a in v['aliases']:
            na = merge.norm(a)
            if na in cand and na != k and na not in canon and k not in canon: canon[na] = k
    json.dump(canon, open(G3 + '/canon.json', 'w'))
    print('pairs', len(pairs), 'agreed', agreed, 'merged groups', len(groups), 'names mapped', len(canon))
if __name__ == '__main__': main()
