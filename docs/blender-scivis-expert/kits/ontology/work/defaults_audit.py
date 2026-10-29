import sys, os, json
sys.path.insert(0,'../repos/x3d_mcp_eb4b4b4/src')
from x3d_utils.x3duom import get_x3duom
u=get_x3duom()
def dflt(node,field):
    for f in u.get_node_fields(node):
        if f['name']==field: return f.get('default')
print('UOM 4.1 defaults:', {n:{f:dflt(n,f) for f in fs} for n,fs in {'Sphere':['radius'],'Box':['size'],'Cone':['bottomRadius','height'],'Cylinder':['radius','height'],'Rectangle2D':['size'],'Disk2D':['innerRadius','outerRadius'],'Material':['diffuseColor','transparency'],'PhysicalMaterial':['baseColor','roughness','metallic'],'UnlitMaterial':['emissiveColor']}.items()})
