import sys, os, importlib.util, importlib, traceback
import bpy
from bpy_extras.io_utils import axis_conversion
SRC=sys.argv[1]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg; spec.loader.exec_module(pkg)
imp = importlib.import_module("x3dio.import_x3d")
orig=imp.set_new_float_color_attribute
def spy(b,c,name="ColorPerCorner",convert_to_linear=True):
    print("SET",name,convert_to_linear,list(c)[:4]); return orig(b,c,name,convert_to_linear)
imp.set_new_float_color_attribute=spy
imp.load(bpy.context, sys.argv[2], global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
for o in bpy.data.objects:
    if o.type=="MESH":
        for a in o.data.color_attributes:
            import numpy as np; v=np.zeros(len(a.data)*4,dtype=np.float32); a.data.foreach_get("color",v); print(a.name,v[:4])
