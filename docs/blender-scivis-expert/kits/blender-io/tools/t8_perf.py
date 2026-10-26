import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import importlib, time
extract = importlib.import_module("io_scene_x3d.extract")
def grid(n):
    reset()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=n-1, y_subdivisions=n-1, size=1.0)
    mesh = bpy.context.active_object.data
    corners = len(mesh.loops)
    mesh.uv_layers.active.uv.foreach_set("vector", [((i*7919)%1000)/1000.0 for i in range(corners*2)])
    c = mesh.color_attributes.new("c", "FLOAT_COLOR", "CORNER"); c.data.foreach_set("color", [((i*104729)%1000)/1000.0 for i in range(corners*4)])
    mesh.update(); return mesh
for n in (33, 65, 129):
    m = grid(n)
    t = time.perf_counter(); g = extract.extract_mesh_geometries(m, name="g", use_normals=True); dt = time.perf_counter() - t
    print(f"grid {n}x{n}: verts={len(m.vertices)} corners={len(m.loops)} extract_mesh_geometries={dt:.2f}s", flush=True)
