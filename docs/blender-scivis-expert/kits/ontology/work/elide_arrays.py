"""Replace long numeric RDF lists in X3dToTurtle output by one summary node: length, min, max, sha256 of the list text."""
import re, sys, hashlib, math
src, dst, MIN_LEN = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 16
t=open(src,encoding='utf-8').read()
cnt=[0,0]
def sub(m):
    body=m.group(1); toks=body.split()
    if len(toks)<MIN_LEN: return m.group(0)
    try: vals=[float(x) for x in toks]
    except ValueError: return m.group(0)         # strings / mixed lists stay as lists
    cnt[0]+=1; cnt[1]+=len(toks)
    h=hashlib.sha256(' '.join(toks).encode()).hexdigest()
    return f'[ a xb:ArraySummary ; xb:length {len(toks)} ; xb:min {min(vals)!r} ; xb:max {max(vals)!r} ; xb:sha256 "{h}" ]'
out=re.sub(r'\(([^()]*)\)', sub, t)
out=out.replace('@prefix x3do:','@prefix xb: <urn:x3dio:bridge#> .\n@prefix x3do:',1)
open(dst,'w',encoding='utf-8').write(out)
print('lists elided',cnt[0],'elements',cnt[1],'bytes',len(t),'->',len(out))
