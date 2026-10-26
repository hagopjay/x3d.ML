import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np
reset()
sc = bpy.context.scene
m = bpy.data.meshes.new("P"); m.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)], [], [(0,1,2,3)]); m.update()
ca = m.color_attributes.new("Color", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", [0.5,0.5,0.5,1]*4)
o = bpy.data.objects.new("P", m); sc.collection.objects.link(o)
mat = bpy.data.materials.new("M"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = "Color"
e = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(a.outputs["Color"], e.inputs["Color"]); nt.links.new(e.outputs["Emission"], out.inputs["Surface"])
m.materials.append(mat)
cam = bpy.data.cameras.new("C"); cam.type = "ORTHO"; cam.ortho_scale = 1.0
co = bpy.data.objects.new("C", cam); co.location = (0,0,5); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 16
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"
for vt in ("Standard", "AgX"):
    sc.view_settings.view_transform = vt
    sc.render.filepath = str(TMP / f"render_{vt}.png")
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(sc.render.filepath)
    px = np.array(img.pixels[:]).reshape(-1, 4)
    centre = px[len(px)//2 + 8]
    print(f"view_transform={vt}: centre pixel (display-referred) = {centre[:3].round(4).tolist()}  -> 8-bit {int(round(centre[0]*255))}")
    bpy.data.images.remove(img)
import math
print("sRGB OETF(0.5) =", round(1.055*0.5**(1/2.4)-0.055,4), "= 8-bit", round((1.055*0.5**(1/2.4)-0.055)*255))
