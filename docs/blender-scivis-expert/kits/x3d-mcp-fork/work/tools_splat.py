import random, math
def make_wrong_splats(bpy, n=200, wrong=True, seed=2):
    r = random.Random(seed)
    C0 = 0.28209479177387814
    pos = [(r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0, 2)) for _ in range(n)]
    rgb = [(r.random(), r.random(), r.random()) for _ in range(n)]
    sh0 = rgb if wrong else [tuple((c - 0.5) / C0 for c in t) for t in rgb]
    mesh = bpy.data.meshes.new("Splats" + ("Wrong" if wrong else "Ok"))
    mesh.from_pydata(pos, [], []); mesh.update()
    mesh["x3d_gaussian_splats"] = True
    mesh["x3d_splat_color_space"] = "SRGB_REC709_DISPLAY"
    sc = mesh.attributes.new("splat_scale", "FLOAT_VECTOR", "POINT"); sc.data.foreach_set("vector", [0.05] * (3 * n))
    ro = mesh.attributes.new("splat_rotation", "QUATERNION", "POINT"); ro.data.foreach_set("value", [1, 0, 0, 0] * n)
    op = mesh.attributes.new("splat_opacity", "FLOAT", "POINT"); op.data.foreach_set("value", [r.uniform(0.3, 0.95) for _ in range(n)])
    s0 = mesh.attributes.new("splat_sh0_0", "FLOAT_VECTOR", "POINT"); s0.data.foreach_set("vector", [c for t in sh0 for c in t])
    col = mesh.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
    col.data.foreach_set("color", [c for t in rgb for c in (*t, 1.0)])
    obj = bpy.data.objects.new("Splats", mesh); bpy.context.scene.collection.objects.link(obj)
    return obj
