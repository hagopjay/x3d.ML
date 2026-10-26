"""Generate (1) xb-hanim.ttl: H-Anim joint/segment/site vocabulary with parent, loa, rest centre, from X3DUOM 4.1
   and (2) xb-shapes.ttl: SHACL-SPARQL shapes over the Consortium's X3dToTurtle output."""
import json, re
from rdflib import Graph, Namespace, Literal, RDF, RDFS, XSD, URIRef
D=json.load(open('hanim_uom.json'))
XB=Namespace('urn:x3dio:bridge#')
g=Graph(); g.bind('xb',XB)
def add(kind, rows, cls):
    for r in rows:
        u=XB[f'{kind}_{r["value"]}']
        g.add((u,RDF.type,XB[cls])); g.add((u,XB.name,Literal(r['value'])))
        if r.get('index'): g.add((u,XB['index'],Literal(int(r['index']))))
        if r.get('loa') is not None: g.add((u,XB.loa,Literal(int(r['loa']))))
        if r.get('parent'): g.add((u,XB.parent,XB[f'{kind}_{r["parent"]}']))
        if r.get('default'):
            x,y,z=[float(v) for v in r['default'].split()]
            g.add((u,XB.restCentre,Literal(f'{x} {y} {z}')))
        if r.get('alias'):
            for a in r['alias'].split(','): g.add((u,XB.alias,Literal(a.strip())))
add('joint', D['hanimJointNameValues'], 'Joint')
add('segment', D['hanimSegmentNameValues'], 'Segment')
add('site', D['hanimFeaturePointNameValues'], 'Site')
# materialise the ancestor closure so SHACL-SPARQL needs no property path (rdflib evaluates parent+ slowly)
for kind in ('joint','segment','site'):
    for u in list(g.subjects(RDF.type, XB[kind.capitalize()])):
        cur=u; seen=set()
        while True:
            p=g.value(cur, XB.parent)
            if p is None or p in seen: break
            g.add((u, XB.ancestor, p)); seen.add(p); cur=p
g.serialize('xb-hanim.ttl',format='turtle')
print('xb-hanim.ttl triples', len(g))

SHAPES = r'''
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xb: <urn:x3dio:bridge#> .
@prefix x3do: <https://www.web3d.org/specifications/X3dOntology4.1#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

xb:Prefixes a owl:Ontology ;
  sh:declare [ sh:prefix "xb" ; sh:namespace "urn:x3dio:bridge#"^^xsd:anyURI ] ,
             [ sh:prefix "x3do" ; sh:namespace "https://www.web3d.org/specifications/X3dOntology4.1#"^^xsd:anyURI ] ,
             [ sh:prefix "owl" ; sh:namespace "http://www.w3.org/2002/07/owl#"^^xsd:anyURI ] .

# R1. HAnimJoint name is not in the H-Anim joint list (open list in X3DUOM: additionalEnumerationValuesAllowed=true -> Warning)
xb:R1_JointName a sh:NodeShape ; sh:targetClass x3do:HAnimJoint ; sh:severity sh:Warning ;
  sh:sparql [ a sh:SPARQLConstraint ; sh:prefixes xb:Prefixes ;
    sh:message "R1 HAnimJoint name {?value} is not an H-Anim 2.0 joint name{?hint}." ;
    sh:select """
      SELECT $this ?value ?hint WHERE {
        $this a x3do:HAnimJoint ; x3do:name ?value .
        FILTER NOT EXISTS { $this owl:sameAs ?d }
        FILTER NOT EXISTS { ?j xb:name ?value . ?j a xb:Joint }
        OPTIONAL { ?kj xb:name ?kn . ?kj a xb:Joint . FILTER(lcase(str(?kn)) = lcase(replace(str(?value), "[. ]", "_"))) }
        OPTIONAL { ?aj xb:alias ?al . ?aj a xb:Joint . ?aj xb:name ?an . FILTER(lcase(str(?al)) = lcase(str(?value))) }
        BIND(COALESCE(CONCAT("; did you mean ", ?kn), CONCAT("; alias of ", ?an), "") AS ?hint)
      }""" ] .

# R2. Declared parent joint is not an ancestor of this joint in the H-Anim hierarchy (X3DUOM 'parent') -> Violation
xb:R2_JointParent a sh:NodeShape ; sh:targetClass x3do:HAnimJoint ; sh:severity sh:Violation ;
  sh:sparql [ a sh:SPARQLConstraint ; sh:prefixes xb:Prefixes ;
    sh:message "R2 HAnimJoint {?n} hangs under {?m}; in the H-Anim hierarchy {?n} descends from {?expected}." ;
    sh:select """
      SELECT $this ?n ?m ?expected WHERE {
        $this a x3do:HAnimJoint ; x3do:name ?n ; x3do:hasParent ?p .
        FILTER NOT EXISTS { $this owl:sameAs ?d }
        ?p a x3do:HAnimJoint ; x3do:name ?m .
        ?jn xb:name ?n . ?jn a xb:Joint . ?jm xb:name ?m . ?jm a xb:Joint .
        FILTER NOT EXISTS { ?jn xb:ancestor ?jm }
        ?jn xb:parent ?e . ?e xb:name ?expected .
      }""" ] .

# R3. A MetadataSet that names a quantity carries no unit
xb:R3_QuantityUnit a sh:NodeShape ; sh:targetClass x3do:MetadataSet ; sh:severity sh:Warning ;
  sh:sparql [ a sh:SPARQLConstraint ; sh:prefixes xb:Prefixes ;
    sh:message "R3 MetadataSet {?set} names quantity {?q} but has no 'unit' entry (a dimensionless label is fine; say so)." ;
    sh:select """
      SELECT $this ?set ?q WHERE {
        $this x3do:name ?set ; x3do:hasMetadataString ?qs . ?qs x3do:name "quantity" ; x3do:value ?q .
        FILTER NOT EXISTS { $this x3do:hasMetadataString ?us . ?us x3do:name "unit" }
      }""" ] .

# R4. Head has no UNIT statement but the scene declares physical quantities in Metadata (or was written by a Blender exporter)
xb:R4_UnitStatement a sh:NodeShape ; sh:targetClass x3do:head ; sh:severity sh:Info ;
  sh:sparql [ a sh:SPARQLConstraint ; sh:prefixes xb:Prefixes ;
    sh:message "R4 no length UNIT statement in head: coordinates default to metres. If the source tool used another length unit the scene is valid but wrong by that factor." ;
    sh:select """
      SELECT $this WHERE {
        FILTER NOT EXISTS { ?u a x3do:unit ; x3do:category "length" }
      }""" ] .

# R5. Head has no meta identifier ending .x3d: the converter falls back to one shared IRI namespace for every scene
xb:R5_Identifier a sh:NodeShape ; sh:targetClass x3do:head ; sh:severity sh:Warning ;
  sh:sparql [ a sh:SPARQLConstraint ; sh:prefixes xb:Prefixes ;
    sh:message "R5 no <meta name='identifier'> containing '.x3d': X3dToTurtle puts this scene in the shared UnnamedX3dModel namespace, so graphs of two scenes collide." ;
    sh:select """
      SELECT $this WHERE {
        FILTER NOT EXISTS { $this x3do:hasMeta ?m . ?m x3do:name "identifier" ; x3do:content ?c . FILTER(CONTAINS(str(?c), ".x3d")) }
      }""" ] .
'''
open('xb-shapes.ttl','w').write(SHAPES)
print('xb-shapes.ttl written', len(SHAPES))
