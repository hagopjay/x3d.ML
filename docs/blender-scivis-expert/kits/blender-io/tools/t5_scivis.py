import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np, logging, traceback

class Cap(logging.Handler):
    def __init__(self): super().__init__(); self.recs = []
    def emit(self, r): self.recs.append(f"{r.levelname}: {r.getMessage()}")
cap = Cap(); logging.getLogger().addHandler(cap); logging.getLogger().setLevel(logging.WARNING)

def snapshot():
    out = []
    for o in bpy.data.objects:
        d = o.data
        info = f"{o.name}:{o.type}"
        if o.type == "MESH":
            info += f" v={len(d.vertices)} e={len(d.edges)} f={len(d.polygons)} attrs={[(a.name,a.domain,a.data_type) for a in d.attributes if not a.name.startswith('.') and a.name not in ('position','sharp_face','material_index')]}"
            info += f" active_color={d.color_attributes.active_color.name if d.color_attributes.active_color else None}"
        elif o.type == "CURVE":
            info += f" splines={len(d.splines)} pts={sum(len(s.points) for s in d.splines)}"
        elif o.type == "POINTCLOUD":
            info += f" pts={len(d.points)}"
        custom = {k: (v if not hasattr(v, 'to_dict') else v.to_dict()) for k, v in o.items() if str(k).startswith("x3d")}
        if custom: info += f" custom={custom}"
        out.append(info)
    return out

def case(tag, body, version="4.0", export_ver="X3D40", head="", **kw):
    reset(); cap.recs.clear()
    p = write(tag + ".x3d", wrap(body, version, head))
    print(f"\n=== {tag}")
    try:
        r = imp(p, **kw)
    except Exception as ex:
        print("  IMPORT EXCEPTION:", type(ex).__name__, str(ex)[:300]); return
    print("  import:", r, "| objects:", snapshot())
    print("  scene props:", {k: v for k, v in bpy.context.scene.items() if str(k).startswith("x3d")} or None)
    if cap.recs: print("  log:", cap.recs[:6])
    q = TMP / (tag + "_out.x3d")
    cap.recs.clear()
    try:
        r = exp(str(q), export_ver)
    except Exception as ex:
        print("  EXPORT EXCEPTION:", type(ex).__name__, str(ex)[:300]); return
    root = ET.parse(q).getroot()
    scene = root.find("Scene")
    tags = Counter(e.tag for e in scene.iter())
    print("  export", export_ver, "Scene tags:", dict(tags))
    for e in root.iter():
        if e.tag in ("Color", "ColorRGBA", "PointSet", "IndexedLineSet", "WorldInfo", "MetadataSet", "MetadataFloat", "MetadataString", "MetadataInteger", "MetadataDouble", "unit"):
            print("   OUT", e.tag, {k: (v[:90]) for k, v in e.attrib.items()})
    metas = [m.attrib.get("content") for m in root.findall("head/meta") if m.attrib.get("name") == "info"]
    if metas: print("  info meta:", metas)
    return root

# A. PointSet + Color / ColorRGBA
case("pointset_color", '''    <Shape><PointSet><Coordinate point="0 0 0  1 0 0  0 1 0  0 0 1"/><Color color="1 0 0  0 1 0  0 0 1  0.5 0.5 0.5"/></PointSet></Shape>''')
case("pointset_colorrgba", '''    <Shape><PointSet><Coordinate point="0 0 0  1 0 0"/><ColorRGBA color="1 0 0 0.5  0 1 0 1"/></PointSet></Shape>''')
# B. IndexedLineSet + Color, LineSet + Color
case("ils_color", '''    <Shape><IndexedLineSet coordIndex="0 1 2 -1" colorPerVertex="true"><Coordinate point="0 0 0 1 0 0 1 1 0"/><Color color="1 0 0 0 1 0 0 0 1"/></IndexedLineSet></Shape>''')
case("lineset_color", '''    <Shape><LineSet vertexCount="3"><Coordinate point="0 0 0 1 0 0 1 1 0"/><Color color="1 0 0 0 1 0 0 0 1"/></LineSet></Shape>''')
# C. Blender-native point mesh with a Color attribute (vertex-only mesh) and a PointCloud object -> export
reset(); cap.recs.clear()
m = bpy.data.meshes.new("PtsMesh"); m.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], []); m.update()
ca = m.color_attributes.new("Color", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", [1,0,0,1, 0,1,0,1, 0,0,1,1])
sc = m.attributes.new("scalar", "FLOAT", "POINT"); sc.data.foreach_set("value", [0.1, 0.5, 0.9])
bpy.context.scene.collection.objects.link(bpy.data.objects.new("PtsMesh", m))
pc = bpy.data.pointclouds.new("PtsCloud"); pc.resize(3)
a = pc.attributes.new("temperature", "FLOAT", "POINT"); a.data.foreach_set("value", [1.0, 2.0, 3.0])
pc.attributes["position"].data.foreach_set("vector", [0,0,0, 2,0,0, 0,2,0])
bpy.context.scene.collection.objects.link(bpy.data.objects.new("PtsCloud", pc))
print("\n=== blender_native_points (vertex-only mesh w/ Color + scalar; PointCloud w/ temperature)")
for ver in ("X3D40", "X3D41"):
    q = TMP / f"native_points_{ver}.x3d"; exp(str(q), ver)
    root = ET.parse(q).getroot()
    print(" ", ver, "Scene tags:", dict(Counter(e.tag for e in root.find("Scene").iter())), "| info meta:", [m.attrib["content"] for m in root.findall("head/meta") if m.attrib.get("name")=="info"])
# D. Volume
case("volumedata", '''    <Shape><Appearance><PhysicalMaterial/></Appearance><VolumeData dimensions="1 1 1"><ImageTexture3D url='"vol.nrrd"'/><OpacityMapVolumeStyle/></VolumeData></Shape>
    <Shape><Box/></Shape>''')
case("isosurface", '''    <Shape><IsoSurfaceVolumeData dimensions="1 1 1" contourStepSize="0.1" surfaceValues="0.5"><ImageTexture3D containerField="voxels" url='"vol.nrrd"'/><ToneMappedVolumeStyle containerField="renderStyle"/></IsoSurfaceVolumeData></Shape>''')
# E. Metadata placements
md = '<MetadataSet name="provenance" reference="urn:x"><MetadataString name="source" value=\'"AF-P12345-F1"\'/><MetadataFloat name="plddt_min" value="12.5"/><MetadataInteger name="n_res" value="287"/><MetadataString name="unit" value=\'"angstrom"\'/></MetadataSet>'
case("md_shape", f'    <Shape><Appearance><PhysicalMaterial/></Appearance><Box>{md.replace("<MetadataSet","<MetadataSet containerField=\'metadata\'") }</Box></Shape>')
case("md_shape_child", f'    <Shape>{md.replace("<MetadataSet","<MetadataSet containerField=\'metadata\'")}<Appearance><PhysicalMaterial/></Appearance><Box/></Shape>')
case("md_worldinfo", f'    <WorldInfo title="T" info=\'"i"\'>{md.replace("<MetadataSet","<MetadataSet containerField=\'metadata\'")}</WorldInfo><Shape><Box/></Shape>')
case("md_transform", f'    <Transform DEF="T1" translation="1 0 0">{md.replace("<MetadataSet","<MetadataSet containerField=\'metadata\'")}<Shape><Box/></Shape></Transform>')
case("md_coordinate", f'''    <Shape><IndexedFaceSet coordIndex="0 1 2 -1"><Coordinate point="0 0 0 1 0 0 0 1 0">{md.replace("<MetadataSet","<MetadataSet containerField='metadata'")}</Coordinate></IndexedFaceSet></Shape>''')
# F. Geo
case("geolocation", '''    <GeoOrigin geoSystem='"GD" "WE"' geoCoords="38 -77 0"/>
    <GeoLocation geoCoords="38.9 -77.0 0" geoSystem='"GD" "WE"'><Shape><Box/></Shape></GeoLocation>''')
case("geotransform", '''    <GeoTransform geoCenter="38.9 -77.0 0" geoSystem='"GD" "WE"' translation="10 0 0"><Shape><Box/></Shape></GeoTransform>''')
case("geocoordinate_ifs", '''    <Shape><IndexedFaceSet coordIndex="0 1 2 -1"><GeoCoordinate geoSystem='"GD" "WE"' point="38 -77 0  38.1 -77 0  38 -76.9 0"/></IndexedFaceSet></Shape>''')
case("geoelevationgrid", '''    <Shape><GeoElevationGrid geoGridOrigin="38 -77 0" geoSystem='"GD" "WE"' xDimension="2" zDimension="2" xSpacing="0.01" zSpacing="0.01" height="0 1 2 3"/></Shape>''')
case("geoviewpoint", '''    <GeoViewpoint geoSystem='"GD" "WE"' position="38.9 -77.0 1000" description="gv"/><Shape><Box/></Shape>''')
# CoordinateDouble
case("coordinatedouble", '''    <Shape><IndexedFaceSet coordIndex="0 1 2 -1"><CoordinateDouble point="0 0 0 1 0 0 0 1 0"/></IndexedFaceSet></Shape>''')
case("pointset_coorddouble", '''    <Shape><PointSet><CoordinateDouble point="0 0 0 1 0 0"/></PointSet></Shape>''')
# unit statement
case("unit_km", '''    <Shape><Box size="1 1 1"/></Shape>''', head='<unit category="length" name="kilometre" conversionFactor="1000"/><meta name="title" content="t"/>')
