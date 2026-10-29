import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np

def tri_ifs(color_xml, extra=""):
    return wrap(f'''    <Shape>
      <Appearance><PhysicalMaterial baseColor="0.8 0.8 0.8"/></Appearance>
      <IndexedFaceSet coordIndex="0 1 2 -1" {extra}>
        <Coordinate point="0 0 0 1 0 0 0 1 0"/>
        {color_xml}
      </IndexedFaceSet>
    </Shape>''')

def report(tag, x3d_text, version="X3D40"):
    reset()
    p = write(tag + "_in.x3d", x3d_text)
    imp(p)
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    print(f"--- {tag}: meshes={len(obs)}")
    for o in obs:
        m = o.data
        ca = m.color_attributes
        print("   color_attributes:", [(a.name, a.domain, a.data_type) for a in ca], "active:", ca.active_color.name if ca.active_color else None,
              "render:", ca.render_color_index)
        for a in ca:
            n = len(a.data)
            buf = np.zeros(n * 4, dtype=np.float32); a.data.foreach_get("color", buf)
            print("   ", a.name, buf.reshape(n, 4).round(5).tolist())
    q = TMP / (tag + "_out.x3d")
    exp(str(q), version)
    root = ET.parse(q).getroot()
    for e in root.iter():
        if e.tag in ("Color", "ColorRGBA", "Normal"):
            print("   OUT", e.tag, e.attrib)
    return root

# per-vertex RGB: c = 0.5 mid-grey etc.
report("ifs_color_rgb", tri_ifs('<Color color="1 0 0  0 0.5 0  0 0 1"/>'))
report("ifs_color_rgba_a05", tri_ifs('<ColorRGBA color="1 0 0 0.5  0 0.5 0 0.25  0 0 1 1"/>'))
