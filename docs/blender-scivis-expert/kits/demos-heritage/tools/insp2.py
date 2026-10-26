import bpy,sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
me=bpy.data.meshes['SwatchTwoTone'] if 'SwatchTwoTone' in bpy.data.meshes else None
for m in bpy.data.meshes:
    for a in m.color_attributes:
        print(m.name,a.name,a.data_type,a.domain,[tuple(round(c,4) for c in a.data[i].color) for i in range(0,min(len(a.data),37),9)])
