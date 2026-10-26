import sys, json, collections
sys.path.insert(0,'/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/deps')
from lxml import etree
C=collections.Counter
man={o['id']:o for o in json.load(open('manifest_clean_ondisk.json'))}
S={json.loads(l)['id']:json.loads(l) for l in open('bpy/sweep_rt.jsonl')}
P=etree.XMLParser(huge_tree=True,resolve_entities=False,no_network=True,recover=True)
def bag(path):
    t=etree.parse(path,P).getroot()
    sc=t.find('Scene')
    c=C()
    if sc is None: return c
    for e in sc.iter():
        if isinstance(e.tag,str): c[e.tag]+=1
    return c
inp={}; out={}
for i,r in S.items():
    if 'export_path' not in r or not r.get('export_bytes'): continue
    try:
        inp[i]=bag(man[i]['path']); out[i]=bag('/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/bpy/'+r['export_path'])
    except Exception as e:
        print('err',i[:8],e)
json.dump({'inp':inp,'out':out},open('survive_bags.json','w'))
print(len(inp))
