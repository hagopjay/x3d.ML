import bpy, math
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
mat = bpy.data.materials.new("m"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1)
cube.data.materials.append(mat)
bpy.context.scene.view_settings.view_transform = "Standard"
bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
bpy.ops.object.camera_add(location=(6, -6, 4), rotation=(math.radians(65), 0, math.radians(45)))
