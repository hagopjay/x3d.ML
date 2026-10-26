import sys, os, importlib.util, importlib, traceback
import bpy
from bpy_extras.io_utils import axis_conversion
SRC=sys.argv[1]
spec = importlib.util.spec_from_file_location("x3dio", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
pkg = importlib.util.module_from_spec(spec); sys.modules["x3dio"] = pkg; spec.loader.exec_module(pkg)
imp = importlib.import_module("x3dio.import_x3d")
try: imp.load(bpy.context, sys.argv[2], global_matrix=axis_conversion(from_forward='-Z', from_up='Y').to_4x4())
except Exception: traceback.print_exc()
