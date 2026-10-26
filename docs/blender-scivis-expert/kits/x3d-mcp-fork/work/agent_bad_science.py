"""An agent-style script that makes five plausible science-vis mistakes."""
import bpy, math, sys, random
sys.path.insert(0, __import__("os").environ["GUARD_WORK"])
sys.dont_write_bytecode = True
# 1. geospatial mesh with raw UTM coordinates, 1 cm detail
verts, faces = [], []
N = 20
for j in range(N):
    for i in range(N):
        verts.append((500000.0 + 0.01 * i, 4100000.0 + 0.01 * j, 100.0))
for j in range(N - 1):
    for i in range(N - 1):
        a = j * N + i; faces.append((a, a + 1, a + N + 1, a + N))
m = bpy.data.meshes.new("terrain"); m.from_pydata(verts, [], faces); m.update()
# 2. scalar field -> vertex colour: pLDDT-like 0..100 values pushed through a 0..1 ramp that was never rescaled
col = m.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
vals = [30 + 70 * (k / (N * N - 1)) for k in range(N * N)]
col.data.foreach_set("color", [c for v in vals for c in (v / 100.0, 0.2, 1 - v / 100.0, 1.0)])
o = bpy.data.objects.new("terrain", m); bpy.context.scene.collection.objects.link(o)
# 3. emission far above 1 (X3D colour fields stop at 1)
mat = bpy.data.materials.new("glow"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Emission Color"].default_value = (1, 0.4, 0.1, 1); b.inputs["Emission Strength"].default_value = 25.0
m.materials.append(mat)
# 4. splats whose SH0 was filled with plain RGB
from tools_splat import make_wrong_splats
make_wrong_splats(bpy)
# 5. never touches colour management: the factory default is AgX
