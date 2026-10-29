"""Pass 1: Gemini extracts entities and typed triples from every corpus chunk, 3 runs each (cached, resumable)."""
import collections, glob, hashlib, json, os, re, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem, schema
HERE = os.path.dirname(os.path.abspath(__file__)); G3 = os.path.dirname(HERE)
OUT = os.path.join(G3, 'runs'); os.makedirs(OUT, exist_ok=True)
RUNS = int(os.environ.get('RUNS', '3')); WORKERS = int(os.environ.get('WORKERS', '4')); MODEL = 'gemini-3.8-flash'

def chunks():
    files = sorted(glob.glob(G3 + '/corpus/*.md')) + sorted(glob.glob(G3 + '/corpus/docs/*'))
    res = []
    for f in files:
        txt = open(f, encoding='utf8', errors='ignore').read()
        txt = re.sub(r'^---\n.*?\n---\n', '', txt, count=1, flags=re.S) if f.endswith('.md') and txt.startswith('---') else txt
        name = os.path.basename(f)
        parts = re.split(r'(?m)^(?=#{1,3} )', txt) if f.endswith('.md') else [txt]
        cur = ''
        for p in parts:
            if len(cur) + len(p) > 7000 and cur:
                res.append((name, cur)); cur = ''
            cur += p
            while len(cur) > 9000:
                res.append((name, cur[:8000])); cur = cur[7500:]
        if cur.strip(): res.append((name, cur))
    # ids of the first build are frozen per document (frozen_chunk_ids.json) so later corpus growth never re-runs finished chunks;
    # documents whose text changed since then, and new documents, get fresh 'v2' ids.
    fz = json.load(open(G3 + '/frozen_chunk_ids.json')) if os.path.exists(G3 + '/frozen_chunk_ids.json') else {}
    CHANGED = {'MEMORY.md', 'data-spine-plan.md'}
    out = []; k = collections.Counter()
    for n, t in res:
        j = k[n]; k[n] += 1
        if n in fz and n not in CHANGED and j < len(fz[n]): cid = fz[n][j]
        else: cid = hashlib.sha1(('v2|%s#%d' % (n, j)).encode()).hexdigest()[:10]
        out.append({'id': cid, 'doc': n, 'text': t})
    return out

SYS = ("You build a knowledge graph of the global X3D (Extensible 3D) community and the PolyXandria project. "
       "You extract ONLY what the passage states. Never add outside knowledge. Every triple needs an exact verbatim evidence quote (max 220 chars) copied from the passage.")
def prompt(ch):
    cls = '\n'.join('- %s: %s' % kv for kv in schema.CLASSES.items())
    pr = '\n'.join('- %s: %s' % kv for kv in schema.PREDICATES.items() if kv[0] not in ('co_used_with',))
    return f"""Passage from document "{ch['doc']}":
<<<
{ch['text']}
>>>

Classes (use exactly these):
{cls}

Predicates (use exactly these, subject -> object):
{pr}

Return JSON:
{{"entities":[{{"name":"canonical short name","type":"<Class>","aliases":["..."]}}],
 "triples":[{{"s":"entity name","p":"<predicate>","o":"entity name","evidence":"verbatim quote","grade":"Confirmed|Likely|Suspected"}}],
 "metrics":[{{"name":"what is measured","value":"number with unit exactly as written","about":"entity name","source_check":"validator/browser/hardware named in the text or null","evidence":"verbatim quote"}}],
 "loops":[{{"name":"loop name","steps":["entity name in order"],"closes_back_to":"first step name","gain":"measured gain as written or null","evidence":"verbatim quote"}}]}}
Rules: grade is what the passage itself claims (Confirmed only if the text says confirmed/verified/measured with a named validator; Suspected if the text hedges). Prefer 12-40 precise triples over many vague ones. A Loop needs a real cycle in the text (finding -> change -> measurement -> new finding). Names must be reused identically across triples."""

def run(ch, k):
    fn = os.path.join(OUT, '%s_%d.json' % (ch['id'], k))
    if os.path.exists(fn): return fn
    r = None; err = ''
    for att in range(3):
        try:
            r = gem.jcall(MODEL, prompt(ch), system=SYS, temperature=0.55, max_out=12000, tag='extract:%s:%d' % (ch['doc'][:30], k), cap=float(os.environ.get('CAP', '15')))
            break
        except Exception as e:
            err = str(e)[:80]
    if r is None:
        return 'ERR %s %s' % (ch['id'], err)
    json.dump({'chunk': ch['id'], 'doc': ch['doc'], 'run': k, 'result': r}, open(fn, 'w'))
    return fn

if __name__ == '__main__':
    cs = chunks()
    json.dump([{'id': c['id'], 'doc': c['doc'], 'n': len(c['text'])} for c in cs], open(os.path.join(G3, 'chunks.json'), 'w'))
    lim = int(os.environ.get('LIMIT', '0')) or len(cs)
    jobs = [(c, k) for c in cs[:lim] for k in range(RUNS)]
    print('chunks', len(cs), 'jobs', len(jobs), flush=True)
    done = 0
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(lambda a: run(*a), jobs):
            done += 1
            if r.startswith('ERR') or done % 20 == 0: print(done, r[-60:], 'spent $%.3f' % gem.spent(), flush=True)
    print('done', gem.spent())
