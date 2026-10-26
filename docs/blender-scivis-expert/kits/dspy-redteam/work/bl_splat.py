import sys, os, json, importlib.util, importlib
import bpy, numpy as np
SRC=sys.argv[1]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg; spec.loader.exec_module(pkg)
pe=importlib.import_module("x3dio.parse_x3d40"); pop=importlib.import_module("x3dio.populate"); sio=importlib.import_module("x3dio.splat_io")
res={}
for f in sys.argv[2:]:
    bpy.ops.wm.read_factory_settings(use_empty=True); r={}
    try:
        from bpy_extras.io_utils import axis_conversion
        imp=importlib.import_module("x3dio.import_x3d")
        imp.load(bpy.context, f, global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
        for o in bpy.data.objects:
            if o.type in ("MESH","POINTCLOUD"):
                d=o.data; names=[a.name for a in d.attributes if not a.name.startswith(".")]
                r["obj"]=(o.type,len(d.vertices) if o.type=="MESH" else len(d.points)); r["attrs"]=names
                def get(n,k,c):
                    a=d.attributes.get(n)
                    if a is None: return None
                    v=np.zeros(len(a.data)*c,dtype=np.float32); a.data.foreach_get(k,v); return v.reshape(-1,c)
                for n,k,c in (("splat_scale","vector",3),("splat_opacity","value",1),("splat_rotation","value",4)):
                    v=get(n,k,c)
                    if v is not None: r[n+"_mean"]=v.mean(0).round(4).tolist()
                for a in d.attributes:
                    if a.data_type in ("FLOAT_COLOR","BYTE_COLOR"):
                        v=np.zeros(len(a.data)*4,dtype=np.float32); a.data.foreach_get("color",v); r["color_mean"]=v.reshape(-1,4).mean(0).round(4).tolist()
                pos=np.array([v.co[:] for v in d.vertices]) if o.type=="MESH" else None
                if pos is not None: r["pos_extent"]=(pos.max(0)-pos.min(0)).tolist()
    except Exception as e: r["error"]=repr(e)[:200]
    res[os.path.basename(f)]=r
print(json.dumps(res,indent=1))
