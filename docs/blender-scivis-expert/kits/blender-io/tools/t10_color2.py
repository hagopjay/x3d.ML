import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import numpy as np
def dump(tag, body):
    reset(); p = write(tag + ".x3d", wrap(body)); imp(p)
    o = [o for o in bpy.data.objects if o.type == "MESH"][0]; m = o.data
    for a in m.color_attributes:
        n = len(a.data); b = np.zeros(n*4, dtype=np.float32); a.data.foreach_get("color", b)
        print(f"{tag}: {a.name} {a.domain} first corner RGBA = {b.reshape(n,4)[0].round(5).tolist()}  (input 0.5,0.5,0.5,a=0.5)  active={m.color_attributes.active_color}")
dump("per_vertex_rgba", '<Shape><IndexedFaceSet coordIndex="0 1 2 -1"><Coordinate point="0 0 0 1 0 0 0 1 0"/><ColorRGBA color="0.5 0.5 0.5 0.5  0.5 0.5 0.5 0.5  0.5 0.5 0.5 0.5"/></IndexedFaceSet></Shape>')
dump("per_face_rgba", '<Shape><IndexedFaceSet coordIndex="0 1 2 -1" colorPerVertex="false"><Coordinate point="0 0 0 1 0 0 0 1 0"/><ColorRGBA color="0.5 0.5 0.5 0.5"/></IndexedFaceSet></Shape>')
dump("elevgrid_rgba", '<Shape><ElevationGrid xDimension="2" zDimension="2" xSpacing="1" zSpacing="1" height="0 0 0 0"><ColorRGBA color="0.5 0.5 0.5 0.5  0.5 0.5 0.5 0.5  0.5 0.5 0.5 0.5  0.5 0.5 0.5 0.5"/></ElevationGrid></Shape>')
print("srgb_to_linear(0.5)=%.5f ; twice=%.5f" % (((0.5+0.055)/1.055)**2.4, ((((0.5+0.055)/1.055)**2.4+0.055)/1.055)**2.4))
