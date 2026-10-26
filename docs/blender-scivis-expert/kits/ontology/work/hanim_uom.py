import sys, json
from lxml import etree
P='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/ontology/repos/x3d_mcp/src/validation/schemas/X3dUnifiedObjectModel-4.1.xml'
t=etree.parse(P)
def enum(name):
    st=t.xpath(f"//SimpleType[@name='{name}']")[0]
    rows=[]
    for e in st.findall('enumeration'):
        rows.append({k:e.get(k) for k in ('value','index','loa','parent','alias','default','latin','documentation') if e.get(k) is not None})
    return rows, dict(st.attrib)
out={}
for n in ('hanimJointNameValues','hanimSegmentNameValues','hanimFeaturePointNameValues','hanimHumanoidInfoKeyValues','hanimVersionChoices','unitCategoryChoices','unitLengthNames','unitAngleNames','unitMassNames','unitForceNames'):
    try:
        rows,attrs=enum(n); out[n]=rows
        print(n,len(rows),{k:v[:100] for k,v in attrs.items() if k in('appinfo',)})
    except IndexError:
        print(n,'MISSING')
json.dump(out,open('/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/ontology/work/hanim_uom.json','w'),indent=1)
j=out['hanimJointNameValues']
import collections
print('loa',collections.Counter(r.get('loa') for r in j))
print('with parent',sum(1 for r in j if r.get('parent')),'with default',sum(1 for r in j if r.get('default')),'with alias',sum(1 for r in j if r.get('alias')))
print([r for r in j if r['value'] in('l_elbow','l_knee','l_shoulder')])
print(out['hanimHumanoidInfoKeyValues'])
for u in ('unitCategoryChoices',):
    print(out.get(u))
