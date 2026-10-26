"""Fork-validator run (hagopjay/x3d_mcp @ eb4b4b4): XSD (huge_tree patched), semantic, profile, per file. Read-only."""
import sys, os, json, gzip, time, collections
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/demos-heritage'
sys.path.insert(0,S+'/pylibs'); sys.path.insert(0,S+'/x3d_mcp/src')
from lxml import etree
_HUGE=etree.XMLParser(huge_tree=True, resolve_entities=False, no_network=True)
_orig=etree.fromstring
etree.fromstring=lambda t,parser=None,**k:_orig(t,parser or _HUGE,**k)
from validation.validate import validate_xml
from validation import semantic as sem
from validation import profile as prof
out=[]
for p in sys.argv[1:]:
    t=time.time()
    raw=open(p,'rb').read()
    if p.endswith('.x3dz') or raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
    txt=raw.decode('utf8')
    # lxml refuses str with encoding declaration only when passed as str; validator encodes to bytes
    r={'file':p.replace('/mnt/project-files/polyxandria/',''),'bytes':len(raw)}
    try:
        x=validate_xml(txt)
        r['xsd']=x['valid']; r['xsd_schema']=x.get('schema_version'); r['xsd_errors']=len(x['errors']); r['xsd_err0']=(x['errors'][:1] or [''])[0][:160]
    except Exception as e:
        r['xsd']='ERR'; r['xsd_err0']=repr(e)[:160]
    try:
        d=sem.semantic_diagnostics(txt)
        c=collections.Counter(x.level for x in d)
        r['sem']=dict(c); r['sem_msgs']=sorted({x.message[:90] for x in d if x.level in('error','warning')})[:4]
    except Exception as e:
        r['sem']='ERR '+repr(e)[:120]
    try:
        root=_orig(raw,_HUGE)
        rep=prof.check_profile(root)
        r['profile_ok']=getattr(rep,'ok',None); 
        if r['profile_ok'] is None: r['profile_repr']=repr(rep)[:200]
    except Exception as e:
        r['profile_ok']='ERR '+repr(e)[:100]
    r['s']=round(time.time()-t,1)
    print(json.dumps(r),flush=True)
