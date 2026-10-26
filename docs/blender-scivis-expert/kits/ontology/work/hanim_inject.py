import re, json, sys, random, os
sys.path.insert(0,'.')
import rdflib
from hanim_py import Vocab, check
from conv import convert
sys.path.insert(0,'../repos/x3d_mcp_eb4b4b4/src')
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics
V=Vocab()
rows=[]
for f in open('hanim_keep.txt').read().split():
    p='hanim_real/'+f
    t=open(p,encoding='utf-8').read()
    m=re.search(r"<HAnimHumanoid[^>]* version='([0-9.]+)'",t)
    if not m or m.group(1)!='2.0': continue
    names=re.findall(r"<HAnimJoint [^>]*? name='([^']+)'",t)
    names=[n for n in names if n in V.names]
    # pick a swap pair: l_knee<->l_elbow if present, else two named joints with the farthest apart parents
    pair=None
    for a,b in (('l_knee','l_elbow'),('r_knee','r_elbow'),('l_hip','l_shoulder'),('l_talocrural','l_radiocarpal')):
        if a in names and b in names: pair=(a,b); break
    if not pair: rows.append((f,'no-pair',None,None,None)); continue
    a,b=pair
    t2=t.replace(f"name='{a}'",f"name='@@A'").replace(f"name='{b}'",f"name='{a}'").replace("name='@@A'",f"name='{b}'")
    # DEF names stay, only the name attribute swaps (a pure labelling fault)
    open('hanim_mut/'+f,'w',encoding='utf-8').write(t2)
    ttl0=f'hanim_ttl/{f[:-4]}.ttl'; ttl1=f'hanim_mut/{f[:-4]}.ttl'
    if not os.path.exists(ttl0): convert(p,ttl0)
    convert('hanim_mut/'+f,ttl1)
    g0=rdflib.Graph(); g0.parse(ttl0,format='turtle'); g1=rdflib.Graph(); g1.parse(ttl1,format='turtle')
    n0,r10,r20=check(g0,V); n1,r11,r21=check(g1,V)
    new=len(set(r21)-set(r20))
    s=t2.replace("<?xml","<?xml",1)
    try:
        s2=re.sub(r'<!DOCTYPE[^>]*>\s*','',t2)
        v=validate_xml(s2); xsd_valid=v.get('valid'); d=semantic_diagnostics(s2); fork_err=sum(1 for x in d if x.level=='error')
        d0=semantic_diagnostics(re.sub(r'<!DOCTYPE[^>]*>\s*','',t)); fork_err0=sum(1 for x in d0 if x.level=='error')
    except Exception as e:
        xsd_valid=str(e)[:50]; fork_err=None; fork_err0=None
    rows.append((f.replace('HumanoidAnimation__',''),f'{a}<->{b}',new,xsd_valid,fork_err-fork_err0 if fork_err is not None else None))
    print(rows[-1],flush=True)
print('scenes with a swap', sum(1 for r in rows if r[1]!='no-pair'), 'detected by R2', sum(1 for r in rows if isinstance(r[2],int) and r[2]>0))
json.dump(rows,open('hanim_inject.json','w'),indent=0)
