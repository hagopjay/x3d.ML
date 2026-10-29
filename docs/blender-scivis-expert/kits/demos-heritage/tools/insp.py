import bpy,sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
for o in bpy.data.objects:
    if o.type=='MESH':
        me=o.data
        print(o.name,len(me.polygons),'attrs',[(a.name,a.domain) for a in me.attributes if not a.name.startswith('.') and a.name not in('position','sharp_face')],'mats',[m.name if m else None for m in me.materials], 'color_attributes',[c.name for c in me.color_attributes])
for m in bpy.data.materials:
    types=sorted({n.bl_idname for n in m.node_tree.nodes}) if m.node_tree else None
    print(m.name,types)
