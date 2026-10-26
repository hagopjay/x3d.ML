import bpy, numpy as np
m=bpy.data.meshes.new("m"); m.from_pydata([(0,0,0),(1,0,0),(1,1,0)],[],[(0,1,2)]); m.update()
a=m.color_attributes.new("c","FLOAT_COLOR","CORNER"); a.data.foreach_set("color",[0.5,0.5,0.5,1.0]*3)
v=np.zeros(12,dtype=np.float32); a.data.foreach_get("color",v); print("roundtrip raw",v[:4])
