"""Re-run fork eb4b4b4 evaluation/cross_validate_ontology.py on the real 4.1 ontology, record per-pair verdicts,
and compare the ontology's prediction and an X3DUOM acceptableNodeTypes prediction with the XSD 4.1."""
import sys, json, re, tempfile, os
from pathlib import Path
SRC='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/ontology/repos/x3d_mcp_eb4b4b4/src'
sys.path.insert(0,SRC); sys.path.insert(0,SRC.replace('/src','/evaluation'))
import x3d_utils.ontology as O
ttl=open('/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl',encoding='utf-8').read()
ttl=ttl.replace('X3dOntology4.1#','X3dOntology4.0#')            # only the namespace IRI, as in the 17 Oct run
tmp=tempfile.NamedTemporaryFile('w',suffix='.ttl',delete=False); tmp.write(ttl); tmp.close()
onto=O.X3DOntology(Path(tmp.name))
from x3d_utils.x3duom import get_x3duom
from validation.validate import validate_xml
import cross_validate_ontology as C
uom=get_x3duom(); nodes=uom.get_concrete_nodes(); abst=uom.get_abstract_types()
def bases(n):
    seen=set(); st=[n]
    while st:
        c=st.pop()
        d=nodes.get(c) or abst.get(c) or {}
        for b in [d.get('baseType')]+list(d.get('additionalBaseTypes') or []):
            if b and b not in seen: seen.add(b); st.append(b)
    return seen
def uom_accepts(parent, cf, child):
    for f in uom.get_node_fields(parent):
        if f['name']==cf and f.get('acceptableNodeTypes'):
            acc=set(re.split(r'[|,\s]+',f['acceptableNodeTypes']))
            return child in acc or bool(acc & bases(child))
    return False
children=['Sphere','Box','Material','Appearance','Coordinate','PointLight','TimeSensor','Transform','Shape','ImageTexture']
rows=[]
for child in children:
    default_cf=nodes.get(child,{}).get('containerField')
    pred=[(r['parent'],r['field']) for r in onto.node_parents(child) if r['parent'] in nodes]
    for parent,field in pred:
        cf=field[3:4].lower()+field[4:] if field.startswith('has') else field
        cf_attr=None if cf==default_cf else cf
        parent_cf=nodes.get(parent,{}).get('containerField')
        doc=C.minimal_doc(parent,child,cf_attr,parent_cf)
        v=validate_xml(doc); ok=v['valid']
        if not ok and f"'{child}'" not in v['errors'][0]: verdict='inconclusive'
        else: verdict='accept' if ok else 'reject'
        rows.append(dict(child=child,parent=parent,field=field,cf=cf,verdict=verdict,uom=uom_accepts(parent,cf,child)))
json.dump(rows,open('work/containment_pairs.json','w'),indent=0)
from collections import Counter
print('pairs',len(rows),Counter(r['verdict'] for r in rows))
conc=[r for r in rows if r['verdict']!='inconclusive']
print('conclusive',len(conc))
# ontology: predicts everything legal -> accuracy = share XSD accepts
acc=sum(r['verdict']=='accept' for r in conc); print('ontology precision (XSD accepts of predicted):',acc,'/',len(conc),round(acc/len(conc),3))
tp=sum(1 for r in conc if r['uom'] and r['verdict']=='accept'); fp=sum(1 for r in conc if r['uom'] and r['verdict']=='reject')
fn=sum(1 for r in conc if not r['uom'] and r['verdict']=='accept'); tn=sum(1 for r in conc if not r['uom'] and r['verdict']=='reject')
print('X3DUOM acceptableNodeTypes vs XSD on the same pairs: TP',tp,'FP',fp,'FN',fn,'TN',tn,'agree',round((tp+tn)/len(conc),3))
bad=[r for r in conc if (r['uom'] and r['verdict']=='reject') or (not r['uom'] and r['verdict']=='accept')]
print('disagreements',[(r['child'],r['parent'],r['cf'],r['verdict']) for r in bad][:30])
