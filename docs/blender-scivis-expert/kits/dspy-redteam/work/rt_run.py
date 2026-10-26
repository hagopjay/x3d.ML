import sys, os, json, re
import bpy
SRC=sys.argv[1]; OUTD=sys.argv[2]; tmp=os.path.join(OUTD,"pkg"); os.makedirs(tmp,exist_ok=True)
pk=os.path.join(tmp,"io_scene_x3d")
if not os.path.exists(pk): os.symlink(SRC,pk,target_is_directory=True)
sys.path.insert(0,tmp); import importlib; m=importlib.import_module("io_scene_x3d")
try: m.register()
except Exception as e: print("reg",repr(e)[:100])
res={}
for f in sys.argv[3:]:
    n=os.path.basename(f); r={}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        r["import"]=sorted(bpy.ops.import_scene.x3d(filepath=f))
    except Exception as e:
        r["import_error"]=repr(e)[:160]; res[n]=r; continue
    ver="X3D41" if "version=\"4.1\"" in open(f).read() else "X3D40"
    out=os.path.join(OUTD,"rt_"+n)
    try:
        r["export"]=sorted(bpy.ops.export_scene.x3d(filepath=out,x3d_version=ver,use_selection=False,use_hierarchy=True))
    except Exception as e:
        r["export_error"]=repr(e)[:200]
    res[n]=r
json.dump(res,open(os.path.join(OUTD,"rt_summary.json"),"w"),indent=1)
