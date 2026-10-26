import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np, logging
class Cap(logging.Handler):
    def __init__(self): super().__init__(); self.recs = []
    def emit(self, r): self.recs.append(f"{r.levelname}: {r.getMessage()}")
cap = Cap(); logging.getLogger().addHandler(cap); logging.getLogger().setLevel(logging.WARNING)

def objs(): return [(o.name, o.type, tuple(round(x, 4) for x in o.matrix_world.translation)) for o in bpy.data.objects]

# (h) points + Color workaround through the splat-mesh fallback
reset()
m = bpy.data.meshes.new("Pts"); m.from_pydata([(0,0,0),(1,0,0),(0,1,0),(0,0,1)], [], []); m.update()
m["x3d_gaussian_splats"] = True
ca = m.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
cols = [1,0,0,1, 0,0.5,0,1, 0,0,1,1, 2.0,0.25,0.1,1]   # includes an HDR value 2.0
ca.data.foreach_set("color", cols)
bpy.context.scene.collection.objects.link(bpy.data.objects.new("Pts", m))
for ver in ("X3D40", "X3D41"):
    q = TMP / f"pts_workaround_{ver}.x3d"; exp(str(q), ver)
    r = ET.parse(q).getroot()
    print(f"(h) points+Color as splat mesh -> {ver}:", [(e.tag, {k: v[:120] for k, v in e.attrib.items()}) for e in r.iter() if e.tag in ("PointSet", "ColorRGBA", "GaussianSplats")])

# (a) ColorInterpolator / ScalarInterpolator / NormalInterpolator routes
reset(); cap.recs.clear()
p = write("interp.x3d", wrap('''    <TimeSensor DEF="T" cycleInterval="2" loop="true"/>
    <ColorInterpolator DEF="CI" key="0 1" keyValue="1 0 0  0 0 1"/>
    <ScalarInterpolator DEF="SI" key="0 1" keyValue="0 1"/>
    <Shape><Appearance><PhysicalMaterial DEF="MAT" baseColor="1 0 0"/></Appearance><Box DEF="BX"/></Shape>
    <ROUTE fromNode="T" fromField="fraction_changed" toNode="CI" toField="set_fraction"/>
    <ROUTE fromNode="CI" fromField="value_changed" toNode="MAT" toField="baseColor"/>
    <ROUTE fromNode="T" fromField="fraction_changed" toNode="SI" toField="set_fraction"/>
    <ROUTE fromNode="SI" fromField="value_changed" toNode="MAT" toField="transparency"/>'''))
imp(p)
anim = [(o.name, o.animation_data.action.name if o.animation_data and o.animation_data.action else None) for o in bpy.data.objects]
mats = [(mm.name, mm.animation_data is not None, mm.node_tree.animation_data is not None if mm.node_tree else None) for mm in bpy.data.materials]
print("(a) Color/ScalarInterpolator -> material:", "objects anim:", anim, "materials anim:", mats, "log:", cap.recs[:3])

# (b) containers
reset(); cap.recs.clear()
p = write("containers.x3d", wrap('''    <LOD range="10"><Shape DEF="HI"><Box size="1 1 1"/></Shape><Shape DEF="LO"><Sphere radius="0.5"/></Shape></LOD>
    <Billboard axisOfRotation="0 1 0"><Shape><Cylinder/></Shape></Billboard>
    <Anchor url='"http://x"'><Shape><Cone/></Shape></Anchor>
    <Collision enabled="false"><Shape><Box size="2 2 2"/></Shape></Collision>
    <StaticGroup><Shape><Box size="3 3 3"/></Shape></StaticGroup>
    <ProtoDeclare name="P"><ProtoBody><Shape><Box size="4 4 4"/></Shape></ProtoBody></ProtoDeclare>
    <ProtoInstance name="P"/>
    <Fog color="0.5 0.5 0.5" visibilityLimit="100"/>
    <WorldInfo title="T"/>
    <NavigationInfo type='"EXAMINE"'/>
    <OrthoViewpoint position="0 0 10" fieldOfView="-1 -1 1 1" description="o"/>
    <Shape><Box/><Appearance><Material diffuseColor="1 0 0"/></Appearance></Shape>'''))
imp(p)
print("(b) containers: objects:", [(n, t) for n, t, _ in objs()], "log:", cap.recs[:6])

# (c) Geo placement
reset(); cap.recs.clear()
p = write("geo2.x3d", wrap('''    <GeoLocation geoCoords="38.9 -77.0 0" geoSystem='"GD" "WE"'><Shape DEF="S1"><Box size="1 1 1"/></Shape></GeoLocation>
    <Transform translation="5 0 0"><Shape DEF="S2"><Box size="1 1 1"/></Shape></Transform>'''))
imp(p)
print("(c) GeoLocation vs Transform:", objs(), cap.recs[:3])

# (d) float32 precision on large coordinates
reset()
p = write("big.x3d", wrap('''    <Transform translation="6378137.123456 0 0"><Shape><IndexedFaceSet coordIndex="0 1 2 -1"><Coordinate point="6378137.123456 0 0  6378138.123456 0 0  6378137.123456 1 0"/></IndexedFaceSet></Shape></Transform>'''))
imp(p)
o = [o for o in bpy.data.objects if o.type == "MESH"][0]
print("(d) float32: object x =", repr(o.location.x), "| vert[0].x =", repr(o.data.vertices[0].co.x), "| vert[1]-vert[0] =", o.data.vertices[1].co.x - o.data.vertices[0].co.x)
q = TMP / "big_out.x3d"; exp(str(q), "X3D40", use_hierarchy=True)
r = ET.parse(q).getroot()
print("    export Transform:", [e.attrib.get("translation") for e in r.iter("Transform")], "Coordinate:", [e.attrib.get("point") for e in r.iter("Coordinate")])
