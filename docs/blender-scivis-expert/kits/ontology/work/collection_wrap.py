import sys, re
sys.path.insert(0,'.'); sys.path.insert(0,'../repos/x3d_mcp_eb4b4b4/src')
from lxml import etree
import rdflib
from conv import convert
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics
src=open('bridge_fixture.x3d',encoding='utf-8').read()
body=re.sub(r'<!DOCTYPE[^>]*>\s*','',src)
root=etree.fromstring(body.encode())
scene=root.find('Scene')
def wrap(names, col):
    g=etree.Element('Group', DEF='COL_'+col)
    md=etree.SubElement(g,'MetadataString', containerField='metadata', name='blender:collection', value='"%s"'%col)
    first=None
    for t in list(scene.findall('Transform')):
        if t.get('DEF') in names:
            if first is None: first=scene.index(t)
            g.append(t)
    scene.insert(first,g)
wrap({'OB_Cell_A','OB_Cell_B','OB_Tumour_Mask'},'Specimen_Tissue')
wrap({'OB_Scale_Bar_Anchor'},'Annotations')
# a global identifier so the graph gets its own namespace
head=root.find('head'); m=etree.SubElement(head,'meta',name='identifier',content='urn:x3dio:fixture:bridge-collections.x3d')
out=etree.tostring(root,pretty_print=True,xml_declaration=True,encoding='UTF-8').decode()
open('bridge_collections.x3d','w',encoding='utf-8').write(out)
v=validate_xml(out); d=semantic_diagnostics(out)
print('fork eb4b4b4: xsd valid',v['valid'],'errors',len(v['errors']),'semantic errors',sum(1 for x in d if x.level=='error'))
convert('bridge_collections.x3d','bridge_collections.ttl')
g=rdflib.Graph(); g.parse('bridge_collections.ttl',format='turtle')
Q="""PREFIX x3do: <https://www.web3d.org/specifications/X3dOntology4.1#>
SELECT ?col ?obj ?q ?val ?unit WHERE {
  ?grp a x3do:Group ; x3do:hasMetadata ?cm . ?cm x3do:name 'blender:collection' ; x3do:value ?col .
  ?shape x3do:hasParent+ ?grp . ?shape a x3do:Shape ; x3do:hasMetadata ?set .
  ?set x3do:hasMetadataString ?qs . ?qs x3do:name 'quantity' ; x3do:value ?q .
  ?set x3do:hasMetadataString ?us . ?us x3do:name 'unit' ; x3do:value ?unit .
  ?set x3do:hasMetadataFloat ?vs . ?vs x3do:name 'value' ; x3do:value ?val .
  BIND(?shape AS ?obj) }"""
for r in g.query(Q): print([str(x).split('#')[-1] for x in r])
