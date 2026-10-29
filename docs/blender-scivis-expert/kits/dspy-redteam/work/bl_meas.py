import sys, os, json, importlib.util, importlib
import bpy, numpy as np
from bpy_extras.io_utils import axis_conversion
SRC=sys.argv[1]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg; spec.loader.exec_module(pkg)
imp = importlib.import_module("x3dio.import_x3d")
out={}
for f in sys.argv[2:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    imp.load(bpy.context, f, global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
    r={}
    for o in bpy.data.objects:
        if o.type=="MESH":
            vs=np.array([(o.matrix_world@v.co)[:] for v in o.data.vertices],dtype=np.float64)
            r["bbox_dims"]=(vs.max(0)-vs.min(0)).tolist(); r["min"]=vs.min(0).tolist()
            r["attrs"]=[(a.name,a.domain,a.data_type) for a in o.data.attributes if not a.name.startswith(".") and a.name not in ("position","sharp_face")]
            for a in o.data.attributes:
                if a.data_type in("FLOAT_COLOR","BYTE_COLOR"):
                    vals=np.zeros(len(a.data)*4,dtype=np.float32); a.data.foreach_get("color",vals); r["color0"]=vals[:4].tolist(); r["color_type"]=a.data_type
    r["scene_unit"]=(bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length)
    out[os.path.basename(f)]=r
print(json.dumps(out,indent=1))
