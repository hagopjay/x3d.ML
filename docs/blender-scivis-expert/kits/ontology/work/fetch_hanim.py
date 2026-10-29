import json, subprocess, os, random
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
a=json.load(open('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sparql-use-checks/scale200/all_paths.json'))
cands=[p for p in a if p.startswith('HumanoidAnimation/') and not p.startswith('HumanoidAnimation/Bones/') and not p.startswith('HumanoidAnimation/Specifications/') and not p.startswith('HumanoidAnimation/Legacy/')]
random.Random(17).shuffle(cands)
base='https://sourceforge.net/p/x3d/code/HEAD/tree/www.web3d.org/x3d/content/examples/'
def get(p):
    dst='hanim_real/'+p.replace('/','__')
    if os.path.exists(dst): return p,'ok',os.path.getsize(dst)
    r=subprocess.run(['curl','-s','-L','-m','60','--fail','-o',dst,base+quote(p)+'?format=raw'],capture_output=True)
    if r.returncode!=0:
        if os.path.exists(dst): os.remove(dst)
        return p,'fail',0
    return p,'ok',os.path.getsize(dst)
sel=cands[:60]
with ThreadPoolExecutor(6) as ex: res=list(ex.map(get,sel))
import collections
print(collections.Counter(s for _,s,_ in res))
json.dump(res,open('hanim_real_fetch.json','w'))
