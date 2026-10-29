import sys
sys.path.insert(0,'repos/x3d_mcp_eb4b4b4/src')
from x3d_utils.x3duom import get_x3duom
u=get_x3duom(); n=u.get_concrete_nodes()['GaussianSplats']
print({k:v for k,v in n.items() if k!='fields'})
for f in n['fields']:
    if f['name'] in('DEF','USE','class','id','style','IS'): continue
    print(f['name'],f['type'],f['accessType'],f.get('default'),f.get('acceptableNodeTypes',''),'|',f['description'][:140])
