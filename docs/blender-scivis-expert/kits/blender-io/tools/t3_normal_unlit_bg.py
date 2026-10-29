import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np

def show_out(q, tags):
    root = ET.parse(q).getroot()
    for e in root.iter():
        if e.tag in tags:
            print("   OUT", e.tag, {k: v for k, v in e.attrib.items()})

# --- Normal
reset()
p = write("normal_in.x3d", wrap('''    <Shape>
      <Appearance><PhysicalMaterial baseColor="0.8 0.8 0.8"/></Appearance>
      <IndexedFaceSet coordIndex="0 1 2 -1" solid="false">
        <Coordinate point="0 0 0 1 0 0 0 1 0"/>
        <Normal vector="0.6 0 0.8  0 0.6 0.8  0.6 0.6 0.5291502622"/>
      </IndexedFaceSet>
    </Shape>'''))
imp(p)
m = [o for o in bpy.data.objects if o.type == "MESH"][0].data
cn = np.array([list(v.vector) for v in m.corner_normals]).round(5)
print("NORMAL import: has_custom_normals:", m.has_custom_normals, "corner_normals:", cn.tolist())
for use_normals in (False, True):
    q = TMP / f"normal_out_{use_normals}.x3d"; exp(str(q), "X3D40", use_normals=use_normals)
    print(" export use_normals=%s" % use_normals); show_out(q, {"Normal", "IndexedFaceSet"})

# --- UnlitMaterial
reset()
p = write("unlit_in.x3d", wrap('''    <Shape>
      <Appearance><UnlitMaterial emissiveColor="0.96 0.845 0.69" transparency="0.25"/></Appearance>
      <Box size="1 1 1"/>
    </Shape>'''))
imp(p)
mat = bpy.data.materials[0]
print("UNLIT import: material", mat.name, "nodes:", [n.bl_idname.replace("ShaderNode", "") for n in mat.node_tree.nodes])
bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
print("  base", tuple(round(x,4) for x in bsdf.inputs["Base Color"].default_value), "emission", tuple(round(x,4) for x in bsdf.inputs["Emission Color"].default_value), "strength", bsdf.inputs["Emission Strength"].default_value, "alpha", bsdf.inputs["Alpha"].default_value, "metallic", bsdf.inputs["Metallic"].default_value, "rough", bsdf.inputs["Roughness"].default_value)
for g in range(2):
    q = TMP / f"unlit_out{g}.x3d"; exp(str(q), "X3D40")
    show_out(q, {"UnlitMaterial", "PhysicalMaterial"})
    reset(); imp(str(q))

# --- Background
reset()
p = write("bg_in.x3d", wrap('''    <Background skyColor="0 0 0.5  0.2 0.4 1  0.9 0.9 1" skyAngle="0.9 1.5708" groundColor="0.3 0.2 0.1  0.1 0.1 0.1" groundAngle="1.5" transparency="0"/>
    <Shape><Appearance><PhysicalMaterial/></Appearance><Box/></Shape>'''))
imp(p)
print("BACKGROUND import: scene prop x3d_background:", dict(bpy.context.scene.get("x3d_background")) if bpy.context.scene.get("x3d_background") else None, "| world:", bpy.context.scene.world)
q = TMP / "bg_out.x3d"; exp(str(q), "X3D40"); show_out(q, {"Background"})
# Background with Blender-made world colour only
reset()
w = bpy.data.worlds.new("W"); w.use_nodes = False; w.color = (0.1, 0.2, 0.3)
bpy.context.scene.world = w
bpy.ops.mesh.primitive_cube_add()
q = TMP / "bg_out2.x3d"; exp(str(q), "X3D40"); print(" Blender world colour (0.1,0.2,0.3) ->"); show_out(q, {"Background"})
