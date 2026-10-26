import sys, os, tempfile, importlib, re
HERE=os.path.dirname(os.path.abspath(__file__)); SRC=HERE+"/x3d-blender-io/source"
tmp=tempfile.mkdtemp(prefix="x3dml_m_",dir=HERE+"/work"); os.symlink(SRC, tmp+"/io_scene_x3d", target_is_directory=True); sys.path.insert(0,tmp)
import bpy; m=importlib.import_module("io_scene_x3d"); m.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
print("import", bpy.ops.import_scene.x3d(filepath=sys.argv[1]))
for o in bpy.data.objects: print("obj", o.name, o.type, "custom props:", {k:(v if isinstance(v,(str,int,float)) else "...") for k,v in o.items()})
print("scene props", list(bpy.context.scene.keys()))
for v in ("X3D40",):
    print("export", bpy.ops.export_scene.x3d(filepath=sys.argv[2], x3d_version=v, use_selection=False))
