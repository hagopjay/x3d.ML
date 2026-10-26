import sys, os, json, tempfile, io, contextlib
ROOT='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/clone/x3d-blender-io'
import bpy
tmp=tempfile.mkdtemp(prefix='x3dreg_'); os.symlink(ROOT+'/source', tmp+'/io_scene_x3d'); sys.path.insert(0,tmp)
import importlib; mod=importlib.import_module('io_scene_x3d'); mod.register()
base='/mnt/project-files/polyxandria/library/data/repairs/'
res={}
for case in ['metalness-sphere','chessboard-roughness','button-route']:
    for side in ['before','after']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        p=f'{base}{case}/{side}.x3d'
        try:
            with contextlib.redirect_stdout(io.StringIO()): bpy.ops.import_scene.x3d(filepath=p)
        except Exception as e:
            res[f'{case}/{side}']={'exc':str(e)[-120:]}; continue
        mats=[]
        for m in bpy.data.materials:
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type=='BSDF_PRINCIPLED':
                        mats.append({'name':m.name,'base':[round(x,3) for x in n.inputs['Base Color'].default_value[:3]],'metallic':round(n.inputs['Metallic'].default_value,3),'rough':round(n.inputs['Roughness'].default_value,3)})
        res[f'{case}/{side}']={'objects':len(bpy.data.objects),'mats':mats[:3],'anim':sum(1 for o in bpy.data.objects if o.animation_data and o.animation_data.action)}
json.dump(res,open("repairs_result.json","w"))
