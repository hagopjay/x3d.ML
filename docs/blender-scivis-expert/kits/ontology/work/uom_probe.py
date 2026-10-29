import sys
sys.path.insert(0,'repos/x3d_mcp_eb4b4b4/src')
from x3d_utils.x3duom import get_x3duom
u=get_x3duom()
nodes=u.get_concrete_nodes(); abst=u.get_abstract_types()
print(len(nodes),len(abst))
print('Sphere',nodes['Sphere'])
k=list(abst)[0]; print(k, abst[k])
print([f for f in u.get_node_fields('Gain') if f.get('acceptableNodeTypes')])
print([ (f['name'],f['type'],f.get('acceptableNodeTypes')) for f in u.get_node_fields('Transform') if f.get('acceptableNodeTypes')])
