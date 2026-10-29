"""Generates the group-C probe scenes (python3 -I gen_probes_C.py <outdir>)."""
import sys, os
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

def scene(body, root_attrs="profile='Full' version='4.1'", head=""):
    return f"<X3D {root_attrs}>{head}<Scene>\n{body}\n</Scene></X3D>\n"

P = {}
# ---------------- interpolator-key-length (ik_) ----------------
P["ik_01_not_divisible"] = scene("""<PositionInterpolator DEF='P' key='0 0.5 1' keyValue='0 0 0 1 1 1 2 2'/>""")
P["ik_02_wrong_arity"] = scene("""<OrientationInterpolator DEF='R' key='0 1' keyValue='0 1 0 0 0 1 0 1.57 0 1 0 3.14'/>
<ColorInterpolator key='0,1' keyValue='1 0 0 1 0 1 0 1'/>
<ScalarInterpolator DEF='S' key='0 1' keyValue='0 1'/>""")
P["ik_03_ok"] = scene("""<PositionInterpolator key='0 1' keyValue='0 0 0 1 1 1'/>
<OrientationInterpolator key='0 0.5 1' keyValue='0 1 0 0 0 1 0 1.57 0 1 0 3.14'/>
<CoordinateInterpolator key='0 1' keyValue='0 0 0 1 1 1  2 2 2 3 3 3'/>
<CoordinateInterpolator2D key='0' keyValue='0 0 1 1'/>
<NormalInterpolator key='0 1' keyValue='0 0 1 0 0 1'/>
<ScalarInterpolator key='0 1' keyValue='0 1'/>
<PositionInterpolator2D key='0 1' keyValue='0 0 1 1'/>""")
P["ik_04_variable_base"] = scene("""<CoordinateInterpolator DEF='C' key='0 1' keyValue='0 0 0 1 1 1 2  0 0 0 1 1 1 2'/>
<CoordinateInterpolator2D key='0' keyValue='0 0 1'/>
<NormalInterpolator DEF='N' key='0 1' keyValue='0 0 1 0  0 0 1 0'/>""")
P["ik_05_missing_and_empty"] = scene("""<PositionInterpolator DEF='NoKV' key='0 1'/>
<PositionInterpolator DEF='NoKey' keyValue='0 0 0'/>
<PositionInterpolator DEF='EmptyKey' key='' keyValue='0 0 0 1'/>
<PositionInterpolator DEF='WsKey' key='  ,, ' keyValue='0 0 0 1'/>
<PositionInterpolator DEF='Unicode' key='0 1 2' keyValue='0 0 0 1 1 1 2 2'/>""")
P["ik_06_dict_order_and_ns"] = scene("""<OrientationInterpolator DEF='Rot' key='0 1' keyValue='0 1 0 0 1'/>
<ScalarInterpolator DEF="it's" key='0 1' keyValue='0 1 2'/>
<x:PositionInterpolator xmlns:x='urn:x' DEF='NS' key='0 1' keyValue='0 0 0 1'/>
<PositionInterpolator DEF='Pos' key='0 1' keyValue='0 0 0 1'/>
<GeoPositionInterpolator DEF='Geo' key='0 1 2' keyValue='0 0 0 1 1 1'/>""")
P["ik_07_separators"] = scene("""<PositionInterpolator DEF='Sep' key='0,0.5,,1' keyValue='0 0 0,
\t1 1 1,,
2 2 2 3'/>
<ScalarInterpolator DEF='Tail' key='0 1 ' keyValue=' 0 1 2 '/>""")

# ---------------- tuple-count (tc_) ----------------
P["tc_01_coord_point"] = scene("""<Shape><IndexedFaceSet coordIndex='0 1 2 -1'><Coordinate point='0 0 0 1 0 0 1 1'/></IndexedFaceSet></Shape>""")
P["tc_02_ok"] = scene("""<Shape><IndexedFaceSet coordIndex='0 1 2 -1'><Coordinate point='0 0 0 1 0 0 1 1 0'/>
<Color color='1 0 0 0 1 0 0 0 1'/><TextureCoordinate point='0 0 1 0 1 1'/></IndexedFaceSet></Shape>
<Transform translation='1 2' scale='1 2 3 4'><Shape><Box size='1 2'/></Shape></Transform>
<ColorRGBA color='1 0 0 1 0 1 0 1'/>""")
P["tc_03_attr_order"] = scene("""<Shape><IndexedFaceSet><Coordinate DEF='C1' point='0 0 0 1'/></IndexedFaceSet></Shape>
<Color DEF='Col' color='1 0 0 1'/>
<ColorRGBA DEF='Rgba' color='1 0 0 1 0'/>
<TextureCoordinate DEF='Tc' point='0 0 1'/>
<OrientationInterpolator DEF='Oi' key='0' keyValue='0 1 0 0 1'/>
<Extrusion DEF='Ex' scale='1 2 3' crossSection='0 0 1 1 2' spine='0 0 0 1 1'/>
<Coordinate DEF="q'uote" point='1 2'/>""")
P["tc_04_skips"] = scene("""<Shape><IndexedFaceSet><Coordinate point='0 0 0 1' xmlns:p='urn:p' p:point='1 2'/></IndexedFaceSet></Shape>
<Unknown point='1 2'/>
<GaussianSplats positions='1 2 3 4'/>
<Coordinate/>
<!-- comment --><?pi data?>
<Transform translation='1 2'><Group bboxSize='1 2 3 4'/></Transform>
<Coordinate point=''/>""")
P["tc_05_namespaced_element"] = scene("""<x:Coordinate xmlns:x='urn:x' DEF='NsCoord' point='1 2 3 4'/>
<Coordinate DEF='Plain' point='1,2,3,4,5'/>
<MFFloatHolder/>
<ElevationGrid DEF='Eg' height='1 2 3 4'/>
<Normal DEF='Nm' vector='0 0 1 0'/>""")
P["tc_06_matrix_types"] = scene("""<CoordinateDouble DEF='Cd' point='0 0 0 1 0'/>
<HAnimHumanoid DEF='Hu' jointBindingPositions='1 2 3 4' jointBindingRotations='0 1 0 0 1' jointBindingScales='1 1 1 1'/>
<TextureCoordinate3D DEF='T3' point='1 2 3 4'/>
<TextureCoordinate4D DEF='T4' point='1 2 3 4 5'/>""")

# ---------------- GaussianSplats (gs_) ----------------
def quats(n, q):
    return " ".join(q for _ in range(n))
def vec3(n, v="0 0 0"):
    return " ".join(v for _ in range(n))
def ones(n):
    return " ".join("1" for _ in range(n))

P["gs_01_ok"] = scene("""<GaussianSplats DEF='G' positions='0 0 0 1 1 1' scales='1 1 1 2 2 2' orientations='0 0 0 1 0 0 0 1' opacities='0.5 1' sphericalHarmonicsDegree0Coef0='1 0 0 0 1 0'/>""")
P["gs_02_tuple_and_length"] = scene("""<GaussianSplats DEF='Bad' positions='0 0 0 1 1 1 2' scales='1 1 1' orientations='0 0 0 1 0 0 0 1 0 0 0 1' opacities='0.5 1 1' sphericalHarmonicsDegree0Coef0='1 0 0 0 1 0'/>""")
P["gs_03_no_positions"] = scene("""<GaussianSplats scales='1 1 1 1 1 1 1 1 1' opacities='1 1' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='Empty'/>
<GaussianSplats DEF='NoColor' positions='0 0 0'/>""")
P["gs_04_sh_partial"] = scene("""<GaussianSplats DEF='Sh1' positions='0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0' sphericalHarmonicsDegree1Coef0='0 0 0' sphericalHarmonicsDegree1Coef2='0 0 0'/>
<GaussianSplats DEF='Sh2' positions='0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0' sphericalHarmonicsDegree2Coef0='0 0 0' sphericalHarmonicsDegree2Coef1='0 0 0' sphericalHarmonicsDegree2Coef2='0 0 0' sphericalHarmonicsDegree2Coef3='0 0 0' sphericalHarmonicsDegree2Coef4='0 0 0'/>
<GaussianSplats DEF='Sh3' positions='0 0 0' sphericalHarmonicsDegree3Coef0='0 0 0' sphericalHarmonicsDegree3Coef1='0 0 0' sphericalHarmonicsDegree3Coef2='0 0 0' sphericalHarmonicsDegree3Coef3='0 0 0' sphericalHarmonicsDegree3Coef4='0 0 0' sphericalHarmonicsDegree3Coef5='0 0 0' sphericalHarmonicsDegree3Coef6='0 0 0' sphericalHarmonicsDegree1Coef1='0 0 0'/>""")
P["gs_05_scale_opacity_space"] = scene("""<GaussianSplats DEF='Ln' positions='0 0 0 1 1 1' scales='-1.2 0.5 -0.1 1 1 1' opacities='-0.5 1.5' sphericalHarmonicsDegree0Coef0='1 0 0 0 1 0'/>
<GaussianSplats DEF='Tok' positions='0 0 0' scales='-1 abc 1' opacities='2 x' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='Edge' positions='0 0 0' scales='0 -0 0' opacities='0 1' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='Inf' positions='0 0 0' scales='-inf 1 1' opacities='1e400' sphericalHarmonicsDegree0Coef0='1 0 0'/>""")
P["gs_06_quat_norm"] = scene("""<GaussianSplats DEF='Q' positions='0 0 0 1 1 1 2 2 2 3 3 3' orientations='0 0 0 0  0 0 0 2  0.7071 0 0 0.7071  0 0 0 1.0005' sphericalHarmonicsDegree0Coef0='1 0 0 0 1 0 0 0 1 1 1 1'/>
<GaussianSplats DEF='Trail' positions='0 0 0' orientations='0 0 0 1 5' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='Short' positions='0 0 0' orientations='1 0 0' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='ZeroOnly' positions='0 0 0' orientations='0 0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0'/>""")
n = 120
P["gs_07_quat_order_wxyz"] = scene(f"""<GaussianSplats DEF='W' positions='{vec3(n)}' orientations='{quats(n, "1 0 0 0")}' sphericalHarmonicsDegree0Coef0='{vec3(n, "1 0 0")}'/>""")
P["gs_08_quat_order_xyzw"] = scene(f"""<GaussianSplats DEF='X' positions='{vec3(n)}' orientations='{quats(n, "0 0 0 1")}' sphericalHarmonicsDegree0Coef0='{vec3(n, "1 0 0")}'/>
<GaussianSplats DEF='Few' positions='{vec3(99)}' orientations='{quats(99, "1 0 0 0")}' sphericalHarmonicsDegree0Coef0='{vec3(99, "1 0 0")}'/>""")
# 70 first-largest, 30 last-largest -> lead[0]=70 > 60, lead[3]=30 >= 20 -> no warning; second: 61/19 of 100 -> warning
P["gs_09_quat_order_thresholds"] = scene(f"""<GaussianSplats DEF='T1' positions='{vec3(100)}' orientations='{quats(70, "1 0 0 0")} {quats(30, "0 0 0 1")}' sphericalHarmonicsDegree0Coef0='{vec3(100, "1 0 0")}'/>
<GaussianSplats DEF='T2' positions='{vec3(100)}' orientations='{quats(61, "-1 0 0 0")} {quats(20, "0 1 0 0")} {quats(19, "0 0 0 1")}' sphericalHarmonicsDegree0Coef0='{vec3(100, "1 0 0")}'/>
<GaussianSplats DEF='Tie' positions='{vec3(100)}' orientations='{quats(100, "0.5 0.5 0.5 0.5")}' sphericalHarmonicsDegree0Coef0='{vec3(100, "1 0 0")}'/>""")
P["gs_10_namespaced_and_nan"] = scene("""<x:GaussianSplats xmlns:x='urn:x' DEF='Ns' positions='0 0 0 1' scales='nan -1 1' opacities='0.5 nan 2' orientations='nan 0 0 1'/>
<GaussianSplats DEF='NanLater' positions='0 0 0' scales='-1 nan 1' opacities='0.5 nan -1' sphericalHarmonicsDegree0Coef0='1 0 0'/>""")
P["gs_11_empty_attrs"] = scene("""<GaussianSplats DEF='E' positions='' scales='1 2 3' opacities='' sphericalHarmonicsDegree0Coef0=''/>
<GaussianSplats DEF='E2' positions=' , ' sphericalHarmonicsDegree0Coef0='1 0 0'/>""")

# ---------------- RigidBodyPhysics (ph_) ----------------
P["ph_01_ok"] = scene("""<RigidBodyCollection DEF='World'>
  <RigidBody DEF='A' mass='1'><CollidableShape containerField='geometry'><Shape><Box/></Shape></CollidableShape></RigidBody>
  <RigidBody DEF='B' mass='2' fixed='true'/>
  <SingleAxisHingeJoint DEF='J' axis='0 1 0' containerField='joints'>
    <RigidBody USE='A' containerField='body1'/>
    <RigidBody USE='B' containerField='body2'/>
  </SingleAxisHingeJoint>
</RigidBodyCollection>""")
P["ph_02_non_finite"] = scene("""<RigidBodyCollection DEF='World'>
  <RigidBody DEF='A' mass='nan' linearVelocity='1 inf 0' forces='1e400 0 0' position='1 abc 0' orientation='0 1 0 Infinity' fixed='nan' inertia='1 0 0 0 1 0 0 0 -inf'/>
  <RigidBody USE='A' mass='nan'/>
  <BallJoint DEF='J' anchorPoint='nan 0 0'><RigidBody USE='A' containerField='body1'/><RigidBody USE='A' containerField='body2'/></BallJoint>
  <MotorJoint DEF='M' axis1Angle='inf' motor1Axis='0 0 0' stop1Bounce='-inf'/>
</RigidBodyCollection>""")
P["ph_03_mass"] = scene("""<RigidBodyCollection>
  <RigidBody DEF='Zero' mass='0'/>
  <RigidBody DEF='ZeroFixed' mass='0' fixed='true'/>
  <RigidBody DEF='ZeroFixedUpper' mass='0' fixed='TRUE'/>
  <RigidBody DEF='Neg' mass='-2'/>
  <RigidBody DEF='Two' mass='0 5'/>
  <RigidBody DEF='Empty' mass=''/>
  <RigidBody DEF='Alpha' mass='abc'/>
  <RigidBody DEF='NegZero' mass='-0'/>
  <RigidBody DEF='Pos' mass='0.001'/>
  <RigidBody DEF='Nan' mass='nan'/>
  <RigidBody USE='Zero'/>
  <RigidBody mass='-1'/>
</RigidBodyCollection>""")
P["ph_04_zero_axis"] = scene("""<RigidBodyCollection>
  <RigidBody DEF='O1' orientation='0 0 0 1'/>
  <RigidBody DEF='O2' orientation='0 0 0'/>
  <RigidBody DEF='O3' orientation='0 -0 0.0 3.14'/>
  <RigidBody DEF='O4' orientation='nan 0 0 1'/>
  <RigidBody DEF='O5' orientation='0 0 1 0'/>
  <RigidBody DEF='O6' orientation=''/>
  <SingleAxisHingeJoint DEF='J1' axis='0 0 0'><RigidBody USE='O1' containerField='body1'/><RigidBody USE='O2' containerField='body2'/></SingleAxisHingeJoint>
  <DoubleAxisHingeJoint DEF='J2' axis1='0 -0 0.0' axis2='nan 0 0'><RigidBody USE='O1' containerField='body1'/><RigidBody USE='O2' containerField='body2'/></DoubleAxisHingeJoint>
  <UniversalJoint DEF='J3' axis1='' axis2='0 0'><RigidBody USE='O1' containerField='body1'/><RigidBody USE='O2' containerField='body2'/></UniversalJoint>
  <SliderJoint DEF='J4' axis='0 0 0 0'><RigidBody USE='O1' containerField='body1'/><RigidBody USE='O2' containerField='body2'/></SliderJoint>
  <SliderJoint USE='J1'/>
</RigidBodyCollection>
<SliderJoint USE='J1' axis='0 0 0'/>""")
P["ph_05_not_in_collection"] = scene("""<Group>
  <RigidBody DEF='Loose'/>
  <SingleAxisHingeJoint DEF='LooseJoint' axis='0 1 0'>
    <RigidBody DEF='B1' containerField='body1'/>
    <RigidBody DEF='B2' containerField='body2'/>
    <RigidBody DEF='B3' containerField='geometry'/>
  </SingleAxisHingeJoint>
  <SingleAxisHingeJoint USE='LooseJoint'/>
  <RigidBody USE='Loose'/>
  <CollidableShape DEF='CS'/>
</Group>
<RigidBodyCollection DEF='World'><RigidBody DEF='In'/><RigidBodyCollection DEF='Nested'><RigidBody DEF='Deep'/></RigidBodyCollection></RigidBodyCollection>""")
P["ph_06_joint_body"] = scene("""<RigidBodyCollection>
  <RigidBody DEF='A'/><RigidBody DEF='B'/>
  <Transform DEF='T'/>
  <BallJoint DEF='None'/>
  <BallJoint DEF='OnlyOne'><RigidBody USE='A' containerField='body1'/></BallJoint>
  <BallJoint DEF='NotBody'><Transform USE='T' containerField='body1'/><Group containerField='body2'/></BallJoint>
  <BallJoint DEF='Same'><RigidBody USE='A' containerField='body1'/><RigidBody USE='A' containerField='body2'/></BallJoint>
  <BallJoint DEF='SameInline'><RigidBody DEF='X' containerField='body1'/><RigidBody USE='X' containerField='body2'/></BallJoint>
  <BallJoint DEF='Undefined'><RigidBody USE='Nope' containerField='body1'/><RigidBody USE='Nope' containerField='body2'/></BallJoint>
  <BallJoint DEF='Fine'><RigidBody USE='A' containerField='body1'/><RigidBody USE='B' containerField='body2'/></BallJoint>
</RigidBodyCollection>""")
P["ph_07_cross_collection"] = scene("""<RigidBodyCollection DEF='C1'>
  <RigidBody DEF='A'/>
  <RigidBody DEF='Other' containerField='joints'/>
  <RigidBody USE='A' containerField='bodies'/>
</RigidBodyCollection>
<RigidBodyCollection DEF='C2'>
  <RigidBody DEF='B'/>
  <SingleAxisHingeJoint DEF='J1' axis='0 1 0'><RigidBody USE='A' containerField='body1'/><RigidBody USE='B' containerField='body2'/></SingleAxisHingeJoint>
  <SingleAxisHingeJoint DEF='J2' axis='0 1 0'><RigidBody USE='Other' containerField='body1'/><RigidBody DEF='Inline' containerField='body2'/></SingleAxisHingeJoint>
  <SingleAxisHingeJoint DEF='J3' axis='0 1 0'><Transform containerField='body1'/><RigidBody USE='B' containerField='body2'/></SingleAxisHingeJoint>
</RigidBodyCollection>
<Group><SliderJoint DEF='Outside'><RigidBody USE='A' containerField='body1'/><RigidBody USE='B' containerField='body2'/></SliderJoint></Group>""")
P["ph_08_first_def_wins"] = scene("""<Transform DEF='Dup'/>
<RigidBodyCollection>
  <RigidBody DEF='Dup'/>
  <RigidBody DEF='Ok'/>
  <BallJoint DEF='J'><RigidBody USE='Dup' containerField='body1'/><RigidBody USE='Ok' containerField='body2'/></BallJoint>
</RigidBodyCollection>""")
P["ph_09_ends_order_and_duplicates"] = scene("""<RigidBodyCollection>
  <RigidBody DEF='A'/><Transform DEF='T'/><Group DEF='G'/>
  <BallJoint DEF='Rev'><Transform USE='T' containerField='body2'/><Group USE='G' containerField='body1'/></BallJoint>
  <BallJoint DEF='Dups'><RigidBody USE='A' containerField='body1'/><Transform USE='T' containerField='body2'/><Group USE='G' containerField='body1'/></BallJoint>
  <BallJoint DEF='Cmt'><!-- c --><RigidBody USE='A' containerField='body1'/><?pi x?><RigidBody USE='A' containerField='body2'/></BallJoint>
</RigidBodyCollection>""")
P["ph_10_namespaced"] = scene("""<x:RigidBodyCollection xmlns:x='urn:x'>
  <x:RigidBody DEF='A' mass='-1'/>
  <x:BallJoint DEF='J'><x:RigidBody USE='A' containerField='body1'/></x:BallJoint>
</x:RigidBodyCollection>
<Group><x:RigidBody xmlns:x='urn:x' mass='0' orientation='0 0 0 0'/></Group>""")
P["ph_11_labels_and_attr_order"] = scene("""<RigidBodyCollection>
  <RigidBody linearVelocity='nan 0 0' mass='-1' angularVelocity='0 inf 0' orientation='0 0 0 1'/>
  <RigidBody DEF='D' USE='U' mass='nan'/>
  <SingleAxisHingeJoint USE='Z' axis='0 0 0'/>
  <MotorJoint axis1Angle='nan'/>
</RigidBodyCollection>""")
P["ph_12_collision_nodes"] = scene("""<Group>
  <CollisionCollection DEF='CC' bounce='nan' frictionCoefficients='inf 1' softnessConstantForceMix='abc'/>
  <CollidableShape DEF='CS' translation='0 nan 0' rotation='0 1 0 0'/>
  <Contact DEF='Ct' depth='-inf' position='1 2 3'/>
  <CollisionSpace DEF='Sp' bboxSize='inf inf inf'/>
  <CollisionSensor DEF='Sn'/>
  <CollidableOffset DEF='Off' translation='1 2 nan'/>
</Group>""")

for name, xml in P.items():
    with open(os.path.join(OUT, name + ".x3d"), "w", encoding="utf-8") as f:
        f.write(xml)
print(len(P))

# ---- added after run 1: more edge cases
P2 = {}
P2["gs_12_sh_all_degrees"] = scene("<GaussianSplats DEF='Full' positions='0 0 0' " + " ".join(f"sphericalHarmonicsDegree{d}Coef{c}='0 0 0'" for d in range(4) for c in range(2*d+1)) + "/>\n"
    "<GaussianSplats DEF='Deg2Only' positions='0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0' " + " ".join(f"sphericalHarmonicsDegree2Coef{c}='0 0 0'" for c in range(5)) + "/>")
P2["gs_13_quat_norm_boundaries"] = scene("""<GaussianSplats DEF='B' positions='0 0 0 1 1 1 2 2 2 3 3 3 4 4 4' orientations='0 0 0 1.001  0 0 0 0.999  0 0 0 1.0009  0 0 0 -1  0.5 0.5 0.5 0.5' sphericalHarmonicsDegree0Coef0='1 0 0 1 0 0 1 0 0 1 0 0 1 0 0'/>
<GaussianSplats DEF='Inf' positions='0 0 0' orientations='inf 0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0'/>
<GaussianSplats DEF='Nan' positions='0 0 0 1 1 1' orientations='nan 0 0 0 0 0 0 0' sphericalHarmonicsDegree0Coef0='1 0 0 1 0 0'/>""")
P2["ph_13_use_members"] = scene("""<RigidBodyCollection DEF='C1'><RigidBody DEF='A'/><RigidBody DEF='B'/></RigidBodyCollection>
<RigidBodyCollection DEF='C2'>
  <RigidBody USE='A'/>
  <BallJoint DEF='J1'><RigidBody USE='A' containerField='body1'/><RigidBody USE='B' containerField='body2'/></BallJoint>
  <SingleAxisHingeJoint DEF='J2' containerField='bodies'><RigidBody USE='A' containerField='body1'/><RigidBody USE='A' containerField='body2'/></SingleAxisHingeJoint>
  <RigidBody USE='Missing'/>
</RigidBodyCollection>
<RigidBodyCollection DEF='C3'><Group containerField='bodies'><RigidBody DEF='Hidden'/></Group><BallJoint DEF='J3'><RigidBody USE='Hidden' containerField='body1'/><RigidBody DEF='Direct' containerField='body2'/></BallJoint></RigidBodyCollection>""")
P2["ik_08_namespaced_scene_and_head"] = scene("""<PositionInterpolator DEF='P' key='0 1' keyValue='0 0 0 1 1'/>
<Transform><Group><ScalarInterpolator DEF='Deep' key='0 1 2' keyValue='0 1'/></Group></Transform>
<ProtoDeclare name='Pr'><ProtoBody><PositionInterpolator DEF='InProto' key='0' keyValue='1 2'/></ProtoBody></ProtoDeclare>""", head="<head><PositionInterpolator key='0' keyValue='1 2'/></head>")
P2["tc_07_head_and_proto"] = scene("""<ProtoDeclare name='Pr'><ProtoBody><Coordinate DEF='InProto' point='1 2'/></ProtoBody></ProtoDeclare>
<ProtoInstance name='Pr'><fieldValue name='point' value='1 2'/></ProtoInstance>
<Shape><IndexedFaceSet><Coordinate point=' 1 2 ' USE='X'/></IndexedFaceSet></Shape>""", head="<head><Coordinate point='1 2'/></head>")
for name, xml in P2.items():
    with open(os.path.join(OUT, name + ".x3d"), "w", encoding="utf-8") as f:
        f.write(xml)
print(len(P2))
