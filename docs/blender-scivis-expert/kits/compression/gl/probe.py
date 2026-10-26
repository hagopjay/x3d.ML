import bpy, addon_utils, os, sys
print("bpy",bpy.app.version_string)
addon_utils.enable("io_scene_gltf2",default_set=False,persistent=False)
op=bpy.ops.export_scene.gltf
props=[p.identifier for p in op.get_rna_type().properties]
print([p for p in props if any(k in p for k in ("draco","meshopt","compress","quant"))])
import io_scene_gltf2, pathlib
d=pathlib.Path(io_scene_gltf2.__file__).parent
print(d)
import glob
print([os.path.basename(x) for x in glob.glob(str(d)+"/**/*draco*",recursive=True)][:10])
print([os.path.basename(x) for x in glob.glob(str(d)+"/**/*meshopt*",recursive=True)][:10])
print([os.path.basename(x) for x in glob.glob(str(d)+"/**/*.so*",recursive=True)][:10])
# import support
imp=[p.identifier for p in bpy.ops.import_scene.gltf.get_rna_type().properties]
print("import props",imp)
