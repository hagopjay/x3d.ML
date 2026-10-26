import sys, os, json, importlib.util, importlib
import bpy, numpy as np
from bpy_extras.io_utils import axis_conversion
SRC=sys.argv[1]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg; spec.loader.exec_module(pkg)
imp = importlib.import_module("x3dio.import_x3d")
for f in sys.argv[2:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    imp.load(bpy.context, f, global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
    for o in bpy.data.objects:
        if o.type=="MESH":
            vs=np.array([v.co[:] for v in o.data.vertices]); print(os.path.basename(f),"local dims",(vs.max(0)-vs.min(0)).tolist(),"loc",list(o.location),"parent",o.parent and o.parent.name)
        elif o.type=="CAMERA": print(os.path.basename(f),"camera loc",list(o.location))
