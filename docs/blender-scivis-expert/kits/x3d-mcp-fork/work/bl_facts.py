import os, sys, json, struct
import numpy as np
import bpy, mathutils
out = {"bpy": bpy.app.version_string, "python": sys.version.split()[0]}
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
out["default_view_transform"] = sc.view_settings.view_transform
out["view_transform_choices"] = [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
out["default_look"] = sc.view_settings.look
out["display_device"] = sc.display_settings.display_device
out["unit_system"] = sc.unit_settings.system
out["scale_length"] = sc.unit_settings.scale_length
out["length_unit"] = sc.unit_settings.length_unit
out["up_forward_note"] = "Blender is Z-up right-handed; X3D is Y-up"
# image colorspace names
out["colorspaces"] = [i.identifier for i in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties["name"].enum_items][:30]
# 32-bit border
v = mathutils.Vector((500000.123456, 4100000.654321, 12.000001))
out["Vector_readback"] = [repr(c) for c in v]
mesh = bpy.data.meshes.new("m")
mesh.from_pydata([(500000.123456, 4100000.654321, 12.000001)], [], [])
out["mesh_co_readback"] = [repr(c) for c in mesh.vertices[0].co]
f32 = lambda x: float(np.float32(x))
out["numpy_float32"] = [repr(f32(c)) for c in (500000.123456, 4100000.654321, 12.000001)]
out["ulp_at_5e5"] = float(np.spacing(np.float32(500000.0)))
out["ulp_at_4.1e6"] = float(np.spacing(np.float32(4100000.0)))
# 1 cm grid at UTM-like y: how many distinct rows survive?
ys = [4100000.0 + 0.01 * j for j in range(20)]
out["distinct_y_after_float32_of_20_rows"] = len({f32(y) for y in ys})
xs = [500000.0 + 0.01 * i for i in range(20)]
out["distinct_x_after_float32_of_20_cols"] = len({f32(x) for x in xs})
# attribute data types
a = mesh.attributes.new("plddt", "FLOAT", "POINT"); a.data[0].value = 93.4
out["float_attr_readback"] = repr(a.data[0].value)
fc = mesh.color_attributes.new("lin", "FLOAT_COLOR", "POINT"); fc.data[0].color = (0.2, 0.2, 0.2, 1.0)
bc = mesh.color_attributes.new("byte", "BYTE_COLOR", "POINT"); bc.data[0].color = (0.2, 0.2, 0.2, 1.0)
out["FLOAT_COLOR_readback"] = [repr(c) for c in fc.data[0].color]
out["BYTE_COLOR_readback_after_set_0.2"] = [repr(c) for c in bc.data[0].color]
out["note_byte_color_is_srgb_encoded_8bit"] = "BYTE_COLOR stores sRGB-encoded bytes; API shows linear"
# custom property types
mesh["pLDDT_note"] = "x"; 
print(json.dumps(out, indent=1))
