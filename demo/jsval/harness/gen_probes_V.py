"""Adversarial probe scenes for the whole-port verification (round 0).

  python3 -I harness/gen_probes_V.py            (rewrites harness/probes/V adversarial-verify-round0/*.x3d)

Each scene targets a place where a JS port is likely to drift from CPython + lxml:
Unicode digits accepted by int()/float(), '1_0' numerals, surrogate pairs in value[0],
namespace-sensitive scene.iter('Tag'), first-DEF-wins vs last-DEF-wins maps, set_/_changed
aliases, Script/Proto interfaces, RigidBodyPhysics and GaussianSplats arithmetic, deep nesting,
CDATA/comment/PI children, BOM, XML 1.1, parse-error strings and many-sorted DEF lists.
"""
import os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probes", "V adversarial-verify-round0")
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith(".x3d"):
        os.remove(os.path.join(OUT, f))

DECL = "<?xml version='1.0' encoding='UTF-8'?>\n"
DOCTYPE = "<!DOCTYPE X3D PUBLIC \"ISO//Web3D//DTD X3D 4.0//EN\" \"https://www.web3d.org/specifications/x3d-4.0.dtd\">\n"

def doc(scene, profile="Immersive", version="4.0", head="", attrs="", decl=DECL, doctype=""):
    p = f" profile='{profile}'" if profile is not None else ""
    v = f" version='{version}'" if version is not None else ""
    return f"{decl}{doctype}<X3D{p}{v}{attrs}>\n<head>{head}</head>\n<Scene>\n{scene}\n</Scene>\n</X3D>\n"

P = {}
VP = "<Viewpoint DEF='V' position='0 0 10'/>\n"
SHAPE = "<Shape><Appearance><Material/></Appearance><Box/></Shape>\n"

# 1 deep nesting (within the 256 default depth: XSD parse must still succeed) with DEF/USE at the bottom
P["v01_deep_nesting_240"] = doc(VP + "".join(f"<Transform DEF='T{i}'>" for i in range(240)) + "<Shape DEF='S'><Box/></Shape>" + "</Transform>" * 240 + "<Shape USE='S'/>")
# 2 USE before DEF in several flavours, incl. DEF and USE on one element and USE naming a later duplicate
P["v02_use_before_def"] = doc(VP + "<Transform USE='A'/><Group USE='B'/><Transform DEF='A'><Shape DEF='B' USE='B'><Box/></Shape></Transform><Transform USE='A'/><Shape USE='C'/><Shape DEF='C'><Sphere/></Shape>")
# 3 ROUTE alias edges: _changed on an outputOnly, set_ on an inputOnly, double alias, empty field, alias on inputOutput (valid)
P["v03_route_alias_edges"] = doc(VP + "<TimeSensor DEF='Clock' loop='true'/><Transform DEF='T'><Shape><Box/></Shape></Transform><PositionInterpolator DEF='PI' key='0 1' keyValue='0 0 0 1 1 1'/>"
    "<ROUTE fromNode='Clock' fromField='fraction_changed_changed' toNode='PI' toField='set_fraction'/>"
    "<ROUTE fromNode='Clock' fromField='fraction_changed' toNode='PI' toField='set_set_fraction'/>"
    "<ROUTE fromNode='PI' fromField='value_changed' toNode='T' toField='set_translation'/>"
    "<ROUTE fromNode='PI' fromField='value_changed' toNode='T' toField='translation_changed'/>"
    "<ROUTE fromNode='T' fromField='set_translation' toNode='T' toField='translation'/>"
    "<ROUTE fromNode='Clock' fromField='' toNode='T' toField=''/>"
    "<ROUTE fromNode='Clock' fromField='loop' toNode='T' toField='translation'/>"
    "<ROUTE fromNode='Clock' fromField='enabled' toNode='T' toField='bboxSize'/>"
    "<ROUTE fromNode='Clock' fromField='isActive' toNode='T' toField='bboxSize'/>")
# 4 Script fields: set_/_changed on declared fields, unnamed field, nested field in a child (ignored), duplicate names
P["v04_script_fields"] = doc(VP + "<Transform DEF='T'><Shape><Box/></Shape></Transform>"
    "<Script DEF='S'><field name='go' type='SFBool' accessType='inputOnly'/><field name='pos' type='SFVec3f' accessType='inputOutput'/><field type='SFInt32' accessType='outputOnly'/><field name='out' type='SFTime' accessType='outputOnly'/><field name='pos' type='SFColor' accessType='outputOnly'/>"
    "<IS><connect nodeField='go' protoField='go'/></IS><![CDATA[ecmascript: function go(v){}]]></Script>"
    "<ROUTE fromNode='S' fromField='pos_changed' toNode='T' toField='set_translation'/>"
    "<ROUTE fromNode='S' fromField='set_go' toNode='T' toField='translation'/>"
    "<ROUTE fromNode='S' fromField='out' toNode='S' toField='set_go'/>"
    "<ROUTE fromNode='T' fromField='translation' toNode='S' toField='pos'/>"
    "<ROUTE fromNode='S' fromField='url' toNode='S' toField='go'/>")
# 5 ProtoDeclare/ProtoInstance interface routing, instance of an unknown proto (skip), shorthand element form
P["v05_proto_instance"] = doc(VP + "<ProtoDeclare name='Spinner'><ProtoInterface><field name='speed' type='SFFloat' accessType='inputOutput' value='1'/><field name='tick' type='SFTime' accessType='outputOnly'/><field name='translation' type='SFVec3f' accessType='initializeOnly' value='0 0 0'/></ProtoInterface>"
    "<ProtoBody><Transform DEF='Inner'><Shape DEF='InnerShape'><Box/></Shape></Transform><TimeSensor DEF='InnerClock'/><ROUTE fromNode='InnerClock' fromField='fraction_changed' toNode='Inner' toField='set_scale'/></ProtoBody></ProtoDeclare>"
    "<ProtoInstance name='Spinner' DEF='P1'><fieldValue name='speed' value='2'/></ProtoInstance>"
    "<ProtoInstance name='Nope' DEF='P2'/><Spinner DEF='P3'/>"
    "<TimeSensor DEF='Clock'/>"
    "<ROUTE fromNode='P1' fromField='tick' toNode='Clock' toField='set_startTime'/>"
    "<ROUTE fromNode='P1' fromField='speed_changed' toNode='Clock' toField='cycleInterval'/>"
    "<ROUTE fromNode='Clock' fromField='time' toNode='P1' toField='translation'/>"
    "<ROUTE fromNode='Clock' fromField='bogus' toNode='P2' toField='bogus'/>"
    "<ROUTE fromNode='P2' fromField='x' toNode='Clock' toField='y'/>"
    "<ROUTE fromNode='P3' fromField='speed' toNode='Clock' toField='enabled'/>"
    "<ROUTE fromNode='P1' fromField='speed' toNode='P3' toField='speed'/>")
# 6 ExternProtoDeclare + ProtoInstance
P["v06_externproto"] = doc(VP + "<ExternProtoDeclare name='Ext' url='\"ext.x3d#Ext\"'><field name='on' type='SFBool' accessType='inputOnly'/><field name='level' type='SFFloat' accessType='outputOnly'/><field type='SFInt32' accessType='inputOnly'/></ExternProtoDeclare>"
    "<ProtoInstance name='Ext' DEF='E'/><Transform DEF='T'/><TimeSensor DEF='Clock'/>"
    "<ROUTE fromNode='E' fromField='level' toNode='T' toField='set_scale'/><ROUTE fromNode='Clock' fromField='isActive' toNode='E' toField='on'/><ROUTE fromNode='Clock' fromField='isActive' toNode='E' toField='set_on'/><ROUTE fromNode='E' fromField='on' toNode='Clock' toField='enabled'/>")
# 7 MF tuple edge counts
P["v07_mf_tuple_edges"] = doc(VP + "<Shape><IndexedFaceSet coordIndex='0 1 2 -1'><Coordinate DEF='C1' point='1 2 34 5 6'/></IndexedFaceSet></Shape>"
    "<Shape><PointSet><Coordinate point='1,2,3,4,5,6,'/><Color color='1 0 0 0 1'/></PointSet></Shape>"
    "<Shape><PointSet><Coordinate point=' , , 1 2 3  '/><ColorRGBA color='1 0 0 1 0 1 0'/></PointSet></Shape>"
    "<Shape><IndexedLineSet coordIndex='0 1 -1'><Coordinate point='1e3 2E-2 .5 -.5 +1 1.'/><CoordinateDouble point='1 2 3 4'/></IndexedLineSet></Shape>"
    "<Shape><IndexedFaceSet coordIndex='0 1 2 -1'><Coordinate point=''/><Normal vector='0 0'/><TextureCoordinate point='0 0 1'/></IndexedFaceSet></Shape>"
    "<Shape><ElevationGrid height='1 2 3 4 5' xDimension='2' zDimension='2'/></Shape>"
    "<OrientationInterpolator DEF='OI' key='0 0.5 1' keyValue='0 0 1 0 0 0 1 3.14 0 0 1 6.28 1'/>"
    "<Transform rotation='0 0 1 0' translation='1 2' scale='1 2 3 4'><Shape><Box size='1 2'/></Shape></Transform>")
# 8 interpolator key edges
P["v08_interp_edges"] = doc(VP + "<ScalarInterpolator DEF='S0' key='' keyValue='1 2 3'/><ScalarInterpolator DEF='S1' key='0 1' keyValue=''/><ScalarInterpolator DEF='S2' key='0 1' keyValue='1'/>"
    "<CoordinateInterpolator DEF='CI' key='0 1' keyValue='0 0 0 1 1 1 2 2'/><CoordinateInterpolator DEF='CI2' key='0 1' keyValue='0 0 0 1 1 1 0 0 0 1 1 1'/><NormalInterpolator key='0,1' keyValue='0,0,1,0,0,1,0'/>"
    "<CoordinateInterpolator2D key='0 1' keyValue='0 0 1 1 2'/><PositionInterpolator2D key='0 1 2' keyValue='0 0 1 1'/><SplinePositionInterpolator key='0' keyValue='0 0 0 0'/><SquadOrientationInterpolator key='0 1' keyValue='0 0 1 0 0 0 1 0'/>"
    "<GeoPositionInterpolator key='0 1' keyValue='0 0 0 1 1'/><ColorInterpolator key='0' keyValue=''/><OrientationInterpolator key='0 1' keyValue='0 0 1 0 0 0 1'/><ScalarInterpolator key='0 1 2' keyValue='1 2 3 4 5 6 7'/>")
# 9 version variants (4.1 header with 4.0 schema location; 3.3 legacy dead-route rule; 3.3.1 float fail; missing; non-numeric)
DEAD = "<BooleanFilter DEF='BF'/><IntegerTrigger DEF='IT'/><TimeTrigger DEF='TT'/><BooleanToggle DEF='BT'/><ROUTE fromNode='BF' fromField='inputFalse' toNode='IT' toField='set_boolean'/><ROUTE fromNode='BF' fromField='inputFalse' toNode='TT' toField='set_boolean'/><ROUTE fromNode='BF' fromField='inputFalse' toNode='BT' toField='set_boolean'/><ROUTE fromNode='BF' fromField='inputNegate' toNode='BT' toField='set_boolean'/>"
P["v09a_version_41_xsi40"] = doc(VP + SHAPE + DEAD + "<PhysicalMaterial/>", version="4.1", attrs=" xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'")
P["v09b_version_33_legacy"] = doc(VP + SHAPE + DEAD, version="3.3")
P["v09c_version_331"] = doc(VP + SHAPE + DEAD, version="3.3.1")
P["v09d_version_missing"] = doc(VP + SHAPE + DEAD, version=None)
P["v09e_version_text"] = doc(VP + SHAPE + DEAD, version="four")
P["v09f_version_4"] = doc(VP + SHAPE + DEAD, version="4")
P["v09g_version_ws"] = doc(VP + SHAPE + DEAD, version=" 4.0 ")
# 10 BOM + no declaration + DOCTYPE
P["v10_bom_doctype"] = "﻿" + doc(VP + SHAPE, decl="", doctype=DOCTYPE)
# 11 CDATA / comments / PIs as children; comment-only Group is not empty, PI-only Transform is not empty, text-only Switch is empty
P["v11_cdata_comment_pi"] = doc(VP + "<Group DEF='commentOnly'><!-- just a comment --></Group><Transform DEF='piOnly'><?x3d-hint a='1'?></Transform><Switch DEF='textOnly'>  text  </Switch><Group DEF='cdataOnly'><![CDATA[<Shape/>]]></Group>"
    "<Shape DEF='withComment'><!-- no geometry --><Appearance><Material/></Appearance></Shape><Script DEF='S'><![CDATA[ecmascript:\nfunction initialize(){}\n]]></Script>"
    "<Group DEF='mixed'><!--a--><?pi b?><Shape><Box/></Shape></Group>")
# 12 default namespace: lxml scene.iter('Shape')/iter('ROUTE') do not match namespaced tags, _local_tag-based checks do
NS = " xmlns='http://www.web3d.org/specifications/x3d-4.0.xsd'"
P["v12a_default_namespace"] = doc(VP + "<Shape DEF='NoGeo'><Appearance><Material/></Appearance></Shape><Group DEF='Empty'/><Transform DEF='T'/><TimeSensor DEF='Clock'/><ROUTE fromNode='Clock' fromField='nope' toNode='T' toField='nope'/><ROUTE fromNode='Missing' fromField='x' toNode='T' toField='y'/>" + DEAD + "<Shape><Material/></Shape>", attrs=NS)
P["v12b_prefixed_namespace"] = "<?xml version='1.0'?>\n<x:X3D xmlns:x='urn:x3d' profile='Interchange' version='4.0'><x:head/><x:Scene><x:Viewpoint/><x:Shape DEF='S'><x:Appearance/></x:Shape><x:Group/><x:ROUTE fromNode='S' fromField='a' toNode='S' toField='b'/><x:Transform DEF='1x'/><x:PhysicalMaterial/></x:Scene></x:X3D>\n"
P["v12c_mixed_namespace"] = doc(VP + "<Shape DEF='plain'><Appearance/></Shape><y:Shape xmlns:y='urn:y' DEF='ns'><y:Appearance/></y:Shape><y:Group xmlns:y='urn:y' DEF='nsEmpty'/><Group DEF='plainEmpty'/>")
# 13 whitespace in attribute values and names
P["v13_whitespace"] = doc(VP + "<Transform DEF=' lead' translation='\n1\t2\n3 '><Shape DEF='trail '><Box/></Shape></Transform><Transform DEF='in ner'/><Transform DEF='nb&#160;sp'/><Transform DEF='nel&#x85;x'/><Transform DEF='zw&#x200b;x'/><Transform DEF='tab\tx'/><Group USE='in ner'/>"
    "<PositionInterpolator key='\n0\n1\n' keyValue='0 0 0\n\n\t1 1 1'/><Coordinate point='\n\n'/>")
# 14 large attribute (~300 KB coordIndex) and a 5-number tail
P["v14_large_attribute"] = doc(VP + "<Shape><IndexedFaceSet coordIndex='" + "0 1 2 -1 " * 30000 + "'><Coordinate point='" + "0 0 0 1 0 0 0 1 0 " * 5000 + "1 1'/></IndexedFaceSet></Shape>")
# 15 HAnim: skeleton root without containerField, empty joints/segments/sites (exempt), displacer, nested joints, HAnimSite inside Transform
P["v15_hanim"] = doc(VP + "<HAnimHumanoid DEF='H' name='h' version='2.0'><HAnimJoint DEF='hanim_humanoid_root' name='humanoid_root'><HAnimJoint DEF='hanim_sacroiliac' name='sacroiliac' containerField='children'><HAnimSegment DEF='hanim_pelvis' name='pelvis'><HAnimSite DEF='hanim_site' name='site'/><HAnimDisplacer DEF='disp' name='d'/></HAnimSegment></HAnimJoint></HAnimJoint>"
    "<HAnimJoint USE='hanim_humanoid_root' containerField='joints'/><HAnimSegment USE='hanim_pelvis' containerField='segments'/><HAnimSite USE='hanim_site' containerField='sites'/><HAnimJoint DEF='empty_joint' name='x' containerField='skeleton'/><Transform DEF='Tx'><HAnimSite DEF='siteInTransform' name='s'/></Transform></HAnimHumanoid>", profile="Interchange")
# 16 Geospatial (Immersive profile lacks Geospatial), GeoViewpoint only (no Viewpoint), empty GeoLOD with and without children
P["v16_geospatial"] = doc("<GeoViewpoint DEF='GV' position='0 0 10'/><GeoOrigin DEF='GO' geoCoords='0 0 0'/><GeoLocation DEF='GL' geoCoords='1 2 3'><Shape><Box/></Shape></GeoLocation><GeoLOD DEF='empty' center='0 0 0'/><GeoLOD DEF='nonempty' center='0 0 0' child1Url='\"a.x3d\"'><GeoOrigin USE='GO'/></GeoLOD>"
    "<GeoPositionInterpolator DEF='GPI' key='0 1' keyValue='0 0 0 1 1'/><GeoCoordinate point='1 2 3 4' containerField='coord'/><GeoElevationGrid height='1 2 3' xDimension='2' zDimension='2'/>")
# 17 Inline / IMPORT / EXPORT and ROUTEs to imported names
P["v17_inline_import_export"] = doc(VP + "<Inline DEF='Inl' url='\"other.x3d\"'/><IMPORT inlineDEF='Inl' importedDEF='X' AS='LocalX'/><IMPORT inlineDEF='Missing' importedDEF='Y'/><Transform DEF='T'><Shape><Box/></Shape></Transform><EXPORT localDEF='T' AS='Out'/><EXPORT localDEF='Nope'/><TimeSensor DEF='Clock'/>"
    "<ROUTE fromNode='Clock' fromField='fraction_changed' toNode='LocalX' toField='set_fraction'/><ROUTE fromNode='X' fromField='value_changed' toNode='T' toField='translation'/><Inline DEF='Unused' load='false'/>")
# 18 PhysicalMaterial textures with/without containerField; Material inside Shape; Box inside Transform; Material with containerField='geometry'
P["v18_physical_material"] = doc(VP + "<Shape><Appearance><PhysicalMaterial DEF='PM'><ImageTexture url='\"a.png\"'/><ImageTexture url='\"n.png\"' containerField='normalTexture'/><TextureTransform/><ImageTexture url='\"e.png\"' containerField='emissive'/></PhysicalMaterial></Appearance><Box/></Shape>"
    "<Shape><Material/><Box containerField='geometry'/></Shape><Shape><Material containerField='geometry'/><Sphere/></Shape><Transform><Box/><Material/></Transform><Shape><Appearance><Material containerField=''/></Appearance><Cone containerField=''/></Shape><Transform><MetadataString name='m' value='\"x\"'/><MetadataSet containerField='metadata'><MetadataString name='a' containerField='value'/><MetadataString name='b'/></MetadataSet></Transform>", version="4.0")
# 19/20 RigidBodyPhysics defects (X-09/X-10 classes): mass, zero axis, NaN/inf, joint bodies, cross-collection, outside collection
P["v19_rigidbody_defects"] = doc(VP + "<RigidBodyCollection DEF='World' gravity='0 -9.8 0'>"
    "<RigidBody DEF='B1' mass='-1' orientation='0 0 0 1'><Shape containerField='geometry'><Box/></Shape></RigidBody>"
    "<RigidBody DEF='B2' mass='0' fixed='true' linearVelocity='nan 0 0' angularVelocity='0 inf 0' position='1e400 0 0'/>"
    "<RigidBody DEF='B3' mass='0' fixed='false' position='1_0 0 0' centerOfMass='infinity 0 0'/>"
    "<RigidBody DEF='B4' mass='٠' orientation='0 0 1 0' enabled='true' torques='NaN 0 0 1 2 3'/>"
    "<SingleAxisHingeJoint DEF='J1' axis='0 0 0' anchorPoint='nan nan nan' containerField='joints'><RigidBody USE='B1' containerField='body1'/><RigidBody USE='B1' containerField='body2'/></SingleAxisHingeJoint>"
    "<DoubleAxisHingeJoint DEF='J2' axis1='0 0 0' axis2='1 0 0' containerField='joints'><RigidBody USE='B2' containerField='body1'/></DoubleAxisHingeJoint>"
    "<BallJoint DEF='J3' containerField='joints'><Transform DEF='NotABody' containerField='body1'/><RigidBody DEF='Inline' mass='1' containerField='body2'/></BallJoint>"
    "<SliderJoint DEF='J4' axis='-0 0.0 +0' containerField='joints'><RigidBody USE='B3' containerField='body1'/><RigidBody USE='Other' containerField='body2'/></SliderJoint>"
    "<UniversalJoint DEF='J5' containerField='joints'><RigidBody USE='B4' containerField='body1'/><RigidBody USE='Ghost' containerField='body2'/></UniversalJoint>"
    "<MotorJoint DEF='J6' containerField='joints' axis1Angle='inf'/>"
    "</RigidBodyCollection>"
    "<RigidBodyCollection DEF='World2'><RigidBody DEF='Other' mass='2'/><RigidBody DEF='Stray' mass='1' containerField='children'/></RigidBodyCollection>"
    "<RigidBody DEF='Loose' mass='1' orientation='0 0 0 0'/><BallJoint DEF='LooseJoint'><RigidBody USE='Loose' containerField='body1'/><RigidBody USE='Loose' containerField='body2'/></BallJoint><BallJoint USE='LooseJoint'/><RigidBody USE='Loose'/>"
    "<CollisionCollection DEF='CC' bounce='nan' frictionCoefficients='1 inf'/><CollisionSensor DEF='CS'><CollisionCollection USE='CC' containerField='collider'/></CollisionSensor><Contact DEF='Ct' position='nan 0 0' bounce='1'/>", profile="Full")
P["v20_rigidbody_order_and_use"] = doc(VP + "<RigidBodyCollection DEF='W'><SingleAxisHingeJoint DEF='J' axis='0 1 0' containerField='joints'><RigidBody USE='Later' containerField='body1'/><RigidBody USE='Later' containerField='body2'/></SingleAxisHingeJoint><RigidBody DEF='Later' mass='1'/><RigidBody DEF='Later' mass='-3'/><RigidBody USE='Later' containerField='bodies'/></RigidBodyCollection>"
    "<Group DEF='G'><RigidBodyCollection DEF='W2'><RigidBody DEF='Bx' mass='1'><Shape containerField='geometry'><Sphere/></Shape></RigidBody></RigidBodyCollection><BallJoint DEF='Jo'><RigidBody USE='Bx' containerField='body1'/><RigidBody USE='Bx' containerField='body2'/></BallJoint></Group>", profile="Full")
# 21/22 GaussianSplats arithmetic (4.1)
def splats(n, first=False):
    import math
    qs = []
    for i in range(n):
        q = [0.0, 0.0, 0.0, 1.0] if not first else [1.0, 0.0, 0.0, 0.0]
        qs.append(" ".join(repr(v) for v in q))
    return " ".join(qs)
P["v21_gaussian_splats"] = doc(VP + "<GaussianSplats DEF='G1' positions='0 0 0 1 1 1' scales='1 1 1 -1 -1 -1' orientations='0 0 0 1 0 0 0 0' opacities='0.5 1.5' sphericalHarmonicsDegree0Coef0='0.1 0.2 0.3 0.4 0.5 0.6' sphericalHarmonicsDegree1Coef0='0 0 0 0 0 0' sphericalHarmonicsDegree1Coef1='0 0 0 0 0 0'/>"
    "<GaussianSplats DEF='G2' scales='1 1 1 1' opacities='1 1 1' sphericalHarmonicsDegree2Coef0='0 0 0 0 0 0 0 0 0' sphericalHarmonicsDegree2Coef1='0 0 0' sphericalHarmonicsDegree2Coef2='0 0 0' sphericalHarmonicsDegree2Coef3='0 0 0' sphericalHarmonicsDegree2Coef4='0 0 0'/>"
    "<GaussianSplats DEF='G3' positions='" + " ".join("0 0 0" for _ in range(120)) + "' orientations='" + splats(120, True) + "' opacities='" + " ".join("1" for _ in range(120)) + "' sphericalHarmonicsDegree0Coef0='" + " ".join("0.5 0.5 0.5" for _ in range(120)) + "'/>"
    "<GaussianSplats DEF='G4' positions='0 0 0' orientations='0.7 0.7 0.1 0.1' scales='١ 2 3' opacities='-٠.5' sphericalHarmonicsDegree0Coef0='1 1 1'/>"
    "<GaussianSplats DEF='G5'/><GaussianSplats DEF='G6' positions='0 0 0' orientations='1e154 0 0 0'/>", version="4.1")
P["v22_gaussian_splats_in_40"] = doc(VP + "<GaussianSplats DEF='G' positions='0 0 0 1 1' orientations='0 0 0 1'/><PhysicalMaterial/>", version="4.0")
# 23 duplicates: case variants, duplicates inside ProtoBody, duplicate on same tag, last-DEF-wins for ROUTE types
P["v23_duplicate_defs"] = doc(VP + "<Transform DEF='a'/><Transform DEF='A'/><Transform DEF='a'><Shape DEF='a'><Box/></Shape></Transform><ProtoDeclare name='P'><ProtoBody><Group DEF='a'/><TimeSensor DEF='Dup'/></ProtoBody></ProtoDeclare><Transform DEF='Dup'/><TimeSensor DEF='Dup' loop='true'/><Transform DEF='Tgt'/>"
    "<ROUTE fromNode='Dup' fromField='fraction_changed' toNode='Tgt' toField='set_scale'/><ROUTE fromNode='Dup' fromField='translation' toNode='Tgt' toField='set_translation'/><Group USE='a'/>")
# 24 empty scene, 25 no scene, 26 Scene as root (profile None), 27 nested Scene
P["v24_empty_scene"] = doc("")
P["v25_no_scene"] = DECL + "<X3D profile='Immersive' version='4.0'><head><meta name='x' content='y'/></head></X3D>\n"
P["v26_scene_root"] = DECL + "<Scene><Shape><Box/></Shape><Group/></Scene>\n"
P["v27_nested_scene"] = doc(VP + "<Group><Scene><Shape><Box/></Shape></Scene></Group><Shape DEF='outer'><Sphere/></Shape>")
# 28 profile edge cases
P["v28a_profile_unknown"] = doc(VP + "<Shape><Box/></Shape><PhysicalMaterial/>", profile="Bogus")
P["v28b_profile_core"] = doc(VP + "<Shape><Appearance><Material/></Appearance><Box/></Shape><Transform><Group/></Transform><ROUTE fromNode='V' fromField='bindTime' toNode='V' toField='set_bind'/><ProtoDeclare name='P'><ProtoBody><Group/></ProtoBody></ProtoDeclare>", profile="Core")
P["v28c_profile_missing"] = doc(VP + SHAPE, profile=None)
P["v28d_profile_ws"] = doc(VP + SHAPE + "<PhysicalMaterial/>", profile=" Immersive")
P["v28e_profile_empty"] = doc(VP + SHAPE, profile="")
# 29 component level parsing: int() accepts whitespace, '+2', fullwidth/Arabic digits, '1_0'; rejects '', 'x', '0x10', '2.0'
P["v29_component_levels"] = doc(VP + SHAPE + "<PhysicalMaterial/><GeoOrigin/><HAnimHumanoid/><NurbsCurve/><Rectangle2D/><TextureBackground/><ParticleSystem/><DISEntityManager/><CADLayer/>",
    profile="Interchange", head="<component name='Shaders' level='x'/><component name='Shaders' level=''/><component name='Geospatial' level=' 1 '/><component name='HAnim' level='+1'/><component name='NURBS' level='１'/><component name='Geometry2D' level='1_0'/><component name='EnvironmentalEffects' level='2.0'/><component name='ParticleSystems' level='0x10'/><component name='DIS' level='-5'/><component level='3'/><component name='CADGeometry' level='٢'/>")
P["v29b_component_in_scene_and_dupes"] = doc(VP + SHAPE + "<component name='Texturing3D' level='2'/><ComposedTexture3D/><Rectangle2D/>", profile="Interchange", head="<component name='Geometry2D' level='1'/><component name='Geometry2D' level='0'/><component name='Geometry2D' level='2'/>")
# 30 naming conventions: isdigit/isspace Unicode, surrogate-pair first char, repeated values dedup across attrs, 'name' on nodes
P["v30_naming_unicode"] = doc(VP + "<Transform DEF='😀x'/><Transform DEF='٣x'/><Transform DEF='²'/><Transform DEF='x '/><Transform DEF=' x'/><Transform DEF='a.b-c'/><Transform USE='a.b-c'/><Group DEF='a.b-c'/><Transform DEF='x' name='a.b'/><Transform name='a.b'/><Transform name='a-b'/><Transform DEF='\U0001D7CE1'/><Transform DEF='x​'/><Transform DEF='x﻿'/><Transform DEF='٠'/>")
# 31 Shape edges: USE'd Shape with children, geometry via ProtoInstance, two geometries, namespaced geometry child, Text/FontStyle
P["v31_shape_edges"] = doc(VP + "<Shape DEF='S'><Box/></Shape><Shape USE='S'><Sphere/></Shape><Shape><ProtoInstance name='Geo'/></Shape><Shape><Box/><Sphere/><Appearance/></Shape><Shape xmlns:q='urn:q'><q:Box/><Appearance/></Shape><Shape><Text string='\"a\" \"b\"'><FontStyle family='\"SANS\"'/></Text><Appearance><Material/></Appearance></Shape><Shape><Appearance USE='missingApp'/><IndexedQuadSet/></Shape><Shape><Polyline2D lineSegments='0 0 1 1 2'/></Shape><Shape><ParticleSystem/></Shape>")
# 32 ROUTE duplicates/missing attributes/USE names
P["v32_route_missing_attrs"] = doc(VP + "<Transform DEF='T'/><Transform USE='T'/><ROUTE/><ROUTE fromNode='T' toNode='T'/><ROUTE fromNode='T' fromField='translation' toNode='T' toField='translation'/><ROUTE fromNode='T' fromField='translation' toNode='T' toField='translation'/><ROUTE fromNode='' fromField='' toNode='' toField=''/>")
# 33 entities (internal subset) in content and attributes; resolve_entities=False keeps a reference node as a child
P["v33_entities"] = DECL + "<!DOCTYPE X3D [<!ENTITY nm 'Named'><!ENTITY frag '<Shape><Box/></Shape>'>]>\n<X3D profile='Immersive' version='4.0'><head/><Scene><Viewpoint/><Group DEF='&nm;'>&frag;</Group><Transform DEF='Lt'>&lt;</Transform><Transform DEF='Amp&amp;'/><Group DEF='withEntity'>&nm;</Group><Group DEF='empty'/></Scene></X3D>\n"
# 34 XML 1.1 declaration, standalone, encoding variants
P["v34_xml11"] = "<?xml version='1.1' encoding='utf-8' standalone='yes'?>\n<X3D profile='Immersive' version='4.0'><head/><Scene><Viewpoint/><Group DEF='G'>&#x1;</Group></Scene></X3D>\n"
# 35 tuple-count attribute order and namespaced attributes
P["v35_tuple_attr_order"] = doc(VP + "<Transform xmlns:z='urn:z' scale='1 2' z:translation='1 2' translation='1 2' center='1' xml:lang='en' rotation='1 2 3'><Shape><Box/></Shape></Transform><Coordinate point='1 2 3 4' DEF='C'/><Shape><LineSet vertexCount='2'><Coordinate point='1 2 3 4 5'/><Color color='1 2 3 4'/></LineSet></Shape>")
# 36 viewpoints: OrthoViewpoint only / Viewpoint only in ProtoDeclare / namespaced Viewpoint
P["v36a_ortho_only"] = doc("<OrthoViewpoint DEF='O'/>" + SHAPE)
P["v36b_viewpoint_in_proto"] = doc("<ProtoDeclare name='P'><ProtoBody><Viewpoint DEF='V'/></ProtoBody></ProtoDeclare>" + SHAPE)
P["v36c_viewpoint_ns"] = doc("<q:Viewpoint xmlns:q='urn:q'/>" + SHAPE)
# 37 DEF sorting (code-point order) in Available DEF lists
P["v37_def_sorting"] = doc(VP + "".join(f"<Transform DEF='{d}'/>" for d in ["Z", "a", "_x", "é", "x1", "x10", "x2", "Ω", "zebra", "Zebra", "ß", "ẞ", "ab", "aB", "a_b", "a-b", "a.b", "😀", "\U0001D4D0", "Ａ"]) + "<Group USE='nope'/><Group USE='Nope'/><ROUTE fromNode='none' fromField='x' toNode='Z' toField='y'/><ROUTE fromNode='Z' fromField='translation' toNode='none2' toField='y'/>")
# 38 Python float() accepts Unicode digits, underscores, 'nan'/'inf'/'Infinity', whitespace
P["v38_pyfloat_edges"] = doc(VP + "<RigidBodyCollection><RigidBody DEF='B1' mass='١' position='1_000 0 0' linearVelocity='Infinity 0 0'/><RigidBody DEF='B2' mass='+0' fixed='false' angularVelocity='-nan 0 0'/><RigidBody DEF='B3' mass='1e400'/><RigidBody DEF='B4' mass='0x10'/><RigidBody DEF='B5' mass='in_f' position='1.5e 0 0'/><RigidBody DEF='B6' mass='٠.٠' orientation='٠ 0 0 1'/><RigidBody DEF='B7' mass='' orientation='0 0 0'/><RigidBody DEF='B8' mass='1,5' position='1, 2, 3'/></RigidBodyCollection>"
    "<GaussianSplats DEF='G' positions='0 0 0' scales='-١ 1 1' opacities='١.٥' orientations='١ 0 0 0'/>", profile="Full", version="4.1")
# 39 ROUTE with one endpoint an undeclared ProtoInstance: skipped entirely even when the other side is bogus
P["v39_route_undeclared_proto"] = doc(VP + "<ProtoInstance DEF='PI' name='Unknown'/><Transform DEF='T'/><ROUTE fromNode='T' fromField='bogus' toNode='PI' toField='bogus'/><ROUTE fromNode='PI' fromField='bogus' toNode='T' toField='bogus'/><ProtoInstance DEF='PI2'/><ROUTE fromNode='PI2' fromField='a' toNode='T' toField='b'/>")
# 40 shaders with declared fields
P["v40_shader_fields"] = doc(VP + "<Shape><Appearance><ComposedShader DEF='CS' language='GLSL'><field name='time' type='SFFloat' accessType='inputOnly'/><field name='color' type='SFColor' accessType='inputOutput' value='1 0 0'/><ShaderPart type='VERTEX' url='\"v.glsl\"'/><ShaderPart type='FRAGMENT'><![CDATA[void main(){}]]></ShaderPart></ComposedShader></Appearance><Box/></Shape>"
    "<Shape><Appearance><PackagedShader DEF='PS' language='HLSL'><field name='k' type='SFInt32' accessType='initializeOnly'/></PackagedShader></Appearance><Sphere/></Shape>"
    "<Shape><Appearance><ProgramShader DEF='PR'><ShaderProgram DEF='SP' type='VERTEX'><field name='u' type='SFVec3f' accessType='inputOnly'/></ShaderProgram></ProgramShader></Appearance><Cone/></Shape>"
    "<TimeSensor DEF='Clock'/><ROUTE fromNode='Clock' fromField='fraction_changed' toNode='CS' toField='time'/><ROUTE fromNode='Clock' fromField='fraction_changed' toNode='CS' toField='set_time'/><ROUTE fromNode='CS' fromField='color_changed' toNode='PS' toField='k'/><ROUTE fromNode='Clock' fromField='isActive' toNode='PS' toField='set_k'/><ROUTE fromNode='Clock' fromField='cycleTime' toNode='SP' toField='u'/><ROUTE fromNode='CS' fromField='activate' toNode='SP' toField='activate'/>")
# 41 grouping-node containerField variants
P["v41_grouping_variants"] = doc(VP + "<Switch whichChoice='0'><Shape><Box/></Shape><Shape containerField='children'><Sphere/></Shape></Switch><LOD range='5'><Shape containerField='level'><Box/></Shape><Group/></LOD><Collision><Shape containerField='proxy'><Box/></Shape><Group containerField='proxy'/></Collision><Billboard axisOfRotation='0 0 0'/><Anchor url='\"x\"'><Shape><Box/></Shape></Anchor><StaticGroup><Shape><Box/></Shape></StaticGroup><CADAssembly><CADPart><CADFace><Shape><Box/></Shape></CADFace></CADPart><CADLayer/></CADAssembly><Transform><Transform containerField='metadata'/></Transform>", profile="Full")
# 42 Layout component nodes, empty Viewport/ScreenGroup/LayoutGroup; DIS nodes empty
P["v42_layout_dis"] = doc(VP + "<LayoutLayer><LayoutGroup DEF='LG'/><ScreenGroup/><Viewport/></LayoutLayer><EspduTransform DEF='E'/><ReceiverPdu/><SignalPdu/><TransmitterPdu/><EspduTransform DEF='E2'><Shape><Box/></Shape></EspduTransform>", profile="Immersive")
# 43 Text / MFString quoting edge cases and Appearance-only Shape
P["v43_text_mfstring"] = doc(VP + "<Shape DEF='T'><Text string='\"a \\\"quoted\\\" b\" \"c\"' length='1 2' maxExtent='3'/><Appearance><Material diffuseColor='1 0 0 0.5'/></Appearance></Shape><Shape><Appearance><Material emissiveColor='1 2'/></Appearance></Shape>")
# 44 malformed XML variants (one file each)
BAD = {
    "v44a_unclosed": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape><Box/></Shape>\n",
    "v44b_bad_attr_quote": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF=abc><Box/></Shape></Scene></X3D>\n",
    "v44c_dup_attr": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF='a' DEF='b'><Box/></Shape></Scene></X3D>\n",
    "v44d_undefined_entity": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF='&nope;'><Box/></Shape></Scene></X3D>\n",
    "v44e_undefined_prefix": DECL + "<X3D profile='Immersive' version='4.0'><Scene><q:Shape><Box/></q:Shape></Scene></X3D>\n",
    "v44f_control_char": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF='a\x01b'><Box/></Shape></Scene></X3D>\n",
    "v44g_text_after_root": DECL + "<X3D profile='Immersive' version='4.0'><Scene/></X3D>\ntrailing text\n",
    "v44h_two_roots": DECL + "<X3D profile='Immersive' version='4.0'><Scene/></X3D><X3D/>\n",
    "v44i_whitespace_only": "   \n\t  ",
    "v44j_decl_not_first": " <?xml version='1.0'?>\n<X3D profile='Immersive' version='4.0'><Scene/></X3D>\n",
    "v44k_bad_encoding_decl": "<?xml version='1.0' encoding='nope-8'?>\n<X3D profile='Immersive' version='4.0'><Scene/></X3D>\n",
    "v44l_lt_in_attr": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF='a<b'><Box/></Shape></Scene></X3D>\n",
    "v44m_mismatched_close": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape><Box/></Sphere></Scene></X3D>\n",
    "v44n_comment_dashes": DECL + "<X3D profile='Immersive' version='4.0'><Scene><!-- a -- b --></Scene></X3D>\n",
    "v44o_cdata_unterminated": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Script><![CDATA[ x </Script></Scene></X3D>\n",
    "v44p_html_entity": DECL + "<X3D profile='Immersive' version='4.0'><Scene><Shape DEF='a&nbsp;b'/></Scene></X3D>\n",
}
P.update(BAD)
# 45 PI and comment before the root, DOCTYPE with external id (no network), xml-stylesheet
P["v45_prolog_nodes"] = DECL + "<?xml-stylesheet type='text/xsl' href='x.xsl'?>\n<!-- leading comment -->\n" + DOCTYPE + "<X3D profile='Immersive' version='4.0'><!-- in root --><head><?pi in head?><meta name='a' content='b'/></head><Scene><?pi in scene?><Viewpoint/><Group DEF='G'><?pi?></Group></Scene></X3D>\n<!-- trailing comment -->\n"
# 46 huge/odd numbers in geometry and interpolators (no OverflowError path: only GaussianSplats squares)
P["v46_huge_numbers"] = doc(VP + "<Transform translation='1e308 -1e308 1e-320'><Shape><Box size='1e400 1 1'/></Shape></Transform><PositionInterpolator key='0 1e400' keyValue='0 0 0 1 1 1'/><Coordinate point='1e999 2 3'/><RigidBodyCollection><RigidBody DEF='B' mass='1e308' position='1e308 1e308 1e308'/></RigidBodyCollection>", profile="Full")
# 47 MF comma separators
P["v47_mf_commas"] = doc(VP + "<Shape><IndexedFaceSet coordIndex='0,1,2,-1'><Coordinate point='1,2,3,4,5,6'/><Color color='1 2 3,'/><Normal vector=',1 2 3'/><TextureCoordinate point='1,,2,,3'/></IndexedFaceSet></Shape><Shape><PointSet><Coordinate point='1 2 3 ,, 4 5'/><Color color='1;2;3'/></PointSet></Shape>")
# 48 4.1 nodes in a 4.0 document and vice versa
P["v48_41_nodes_in_40"] = doc(VP + "<Shape><Appearance><PhysicalMaterial/></Appearance><Box/></Shape><Shape><Appearance><UnlitMaterial/></Appearance><GaussianSplats positions='0 0 0'/></Shape>", version="4.0")
# 49 USE'd name in ROUTE / ROUTE to a DEF only inside ProtoBody
P["v49_route_use_name"] = doc(VP + "<Transform DEF='T'/><Transform USE='T' DEF='U'/><TimeSensor DEF='Clock'/><ROUTE fromNode='Clock' fromField='fraction_changed' toNode='U' toField='set_scale'/><ProtoDeclare name='P'><ProtoBody><Transform DEF='InBody'/></ProtoBody></ProtoDeclare><ROUTE fromNode='Clock' fromField='time' toNode='InBody' toField='set_translation'/>")
# 50 namespaced DEF/USE attributes are not DEF/USE
P["v50_namespaced_attrs"] = doc(VP + "<Transform xmlns:x='urn:x' x:DEF='ns' xml:id='xid' DEF='real'><Shape x:USE='ns'><Box/></Shape></Transform><Group x:USE='real' xmlns:x='urn:x'/>")
# 51 empty-string DEF/USE/containerField
P["v51_empty_values"] = doc(VP + "<Transform DEF='' USE=''><Shape DEF='' containerField=''><Box containerField=''/></Shape></Transform><Group DEF=''/><ROUTE fromNode='' fromField='x' toNode='' toField='y'/>")
# 52 metadata and Scene-level nodes with containerField
P["v52_metadata"] = doc(VP + "<MetadataString DEF='M' name='n' value='\"v\"'/><WorldInfo DEF='WI' title='t'><MetadataSet><MetadataFloat name='f' value='1 2'/><MetadataInteger name='i' containerField='value'/><MetadataDouble name='d' containerField='metadata'/></MetadataSet></WorldInfo><Transform><MetadataString USE='M'/><MetadataString USE='M' containerField='children'/></Transform>")
# 53 everything valid: a clean scene (all clear + XSD valid)
P["v53_all_clear"] = doc(VP + "<Transform DEF='T'><Shape><Appearance><Material diffuseColor='1 0 0'/></Appearance><Box/></Shape></Transform><TimeSensor DEF='Clock' cycleInterval='4' loop='true'/><OrientationInterpolator DEF='OI' key='0 1' keyValue='0 1 0 0 0 1 0 6.28'/><ROUTE fromNode='Clock' fromField='fraction_changed' toNode='OI' toField='set_fraction'/><ROUTE fromNode='OI' fromField='value_changed' toNode='T' toField='set_rotation'/>")
# 54 deep nesting past 256 for the XSD parser (no HUGE) but fine for the semantic parser (HUGE)
P["v54_depth_300"] = doc(VP + "<Group>" * 300 + SHAPE + "</Group>" * 300)
# 55 many DEF/USE with unused + duplicates to stress sorting and dedupe of USE sets
P["v55_many_defs"] = doc(VP + "".join(f"<Transform DEF='n{i:03d}'/>" for i in range(60)) + "".join(f"<Group USE='n{(i*7)%70:03d}'/>" for i in range(60)) + "<ROUTE fromNode='n001' fromField='translation_changed' toNode='n002' toField='set_translation'/><EXPORT localDEF='n003'/>")
# 56 attribute value character references that survive as raw characters in messages
P["v56_charref_values"] = doc(VP + "<Transform DEF='a&#10;b'/><Transform DEF='c&#9;d'/><Transform DEF='e&#13;f'/><Transform DEF='&#x2028;g'/><Group USE='a&#10;b'/><ROUTE fromNode='a&#10;b' fromField='x' toNode='nope&#9;' toField='y'/>")

for name, body in P.items():
    with open(os.path.join(OUT, name + ".x3d"), "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
print(len(P), "probes written to", OUT)
