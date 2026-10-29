"""Visibility for entities added since the first pass: same rule as enrich.visibility (two runs must both say public, plus the deny list), batches of 60, 8000 output tokens."""
import collections, json, os, re, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enrich, merge
G3 = merge.G3; ents = enrich.ents; deg = enrich.deg
extra = json.load(open(G3 + '/extra_new.json'))
old = extra.get('vis', {})
keys = [k for k in ents if deg[k] > 0 and k not in old]
print('new keys', len(keys), flush=True)
B = 60
def one(a):
    b, run = a
    chunk = keys[b:b + B]
    lines = '\n'.join('%d | %s | %s | docs: %s' % (i, ents[k]['name'], ents[k]['type'], ', '.join(d[:28] for d in ents[k]['docs'][:3])) for i, k in enumerate(chunk))
    pr = f"""Decide which graph nodes may appear on a PUBLIC showcase page about the global X3D / Web3D community.
PUBLIC: open standards, public tools/repos/orgs, public conferences and releases, node types and components, generic public concepts.
PRIVATE: anything about one person's unpublished internal project work: private repos, decisions or tasks pending, spend, credentials or cloud resources, private links, unpublished research data, names of AI models or vendors used internally, file paths.
Return JSON {{"public":[indices of public nodes]}}
{lines}"""
    r = enrich.jc(enrich.FLASH, pr, 'vis2:%d:%d' % (b, run), temperature=0.0 + 0.2 * run, max_out=8000)
    return b, run, set((r or {}).get('public', []))
jobs = [(b, run) for b in range(0, len(keys), B) for run in (0, 1)]
with cf.ThreadPoolExecutor(6) as ex: outs = list(ex.map(one, jobs))
pub = collections.defaultdict(list)
for b, run, st in outs: pub[b].append(st)
res = dict(old)
for b, sets in pub.items():
    both = set.intersection(*sets) if len(sets) == 2 else set()
    for i, k in enumerate(keys[b:b + B]):
        nm = ents[k]['name'] + ' ' + ' '.join(ents[k].get('docs', []))
        res[k] = 'public' if (i in both and not enrich.DENY.search(ents[k]['name']) and ents[k]['type'] not in ('Decision',) and not re.search(r'private|handoff|ledger|spend|^repo_x3d-ml', nm, re.I)) else 'private'
for k in ents:
    if ents[k]['prov'] == 'data' and k not in res: res[k] = 'public'
extra['vis'] = res
json.dump(extra, open(G3 + '/extra_new.json', 'w')); print('public', sum(v == 'public' for v in res.values()), 'of', len(res))
