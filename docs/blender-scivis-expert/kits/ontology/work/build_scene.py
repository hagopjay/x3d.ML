# Build a sci-vis style Blender scene in bpy 5.2.3 and export it with x3d-blender-io main 482741b.
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg'))
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import importlib
mod = importlib.import_module('io_scene_x3d')
try: mod.register()
except Exception as e: print('register note', e)

out = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'out.x3d'
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 0.001      # 1 Blender unit = 1 mm
sc.unit_settings.length_unit = 'MILLIMETERS'
sc.unit_settings.mass_unit = 'GRAMS'

def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or sc.collection).children.link(c)
    return c

col_spec = collection('Specimen_Tissue')
col_ann  = collection('Annotations')
col_rig  = collection('Humanoid_Rig')

def add_mesh(name, kind, loc, color, coll):
    if kind == 'sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0, location=loc)
    else: bpy.ops.mesh.primitive_cube_add(size=2.0, location=loc)
    ob = bpy.context.active_object; ob.name = name; ob.data.name = name + '_mesh'
    for c in ob.users_collection: c.objects.unlink(ob)
    coll.objects.link(ob)
    m = bpy.data.materials.new('Mat_' + name); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = color
    ob.data.materials.append(m)
    return ob

a = add_mesh('Cell_A', 'sphere', (0, 0, 0), (0.9, 0.2, 0.1, 1), col_spec)
b = add_mesh('Cell_B', 'sphere', (4, 0, 0), (0.1, 0.4, 0.9, 1), col_spec)
t = add_mesh('Tumour_Mask', 'cube', (0, 4, 0), (0.2, 0.8, 0.2, 1), col_spec)

# Scientific quantity + unit + provenance as the exporter's x3d_metadata custom property (MetadataSet)
def mset(name, entries):
    return {'node': 'MetadataSet', 'name': name, 'value': [
        {'node': n, 'name': k, 'value': v} for (n, k, v) in entries]}
a['x3d_metadata'] = mset('sciviz', [
    ('MetadataString', 'quantity', '"temperature"'),
    ('MetadataString', 'unit', '"K"'),
    ('MetadataFloat',  'value', '310.15'),
    ('MetadataString', 'provenance', '"pipeline-run-0007; step=segment; sha256=ab12"')])
b['x3d_metadata'] = mset('sciviz', [
    ('MetadataString', 'quantity', '"temperature"'),
    ('MetadataString', 'unit', '"K"'),
    ('MetadataFloat',  'value', '298.15')])
t['x3d_metadata'] = mset('sciviz', [
    ('MetadataString', 'quantity', '"segmentation label"'),
    ('MetadataInteger','value', '3')])      # no unit on purpose

# Empty annotation
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(2, 2, 2)); e = bpy.context.active_object; e.name = 'Scale_Bar_Anchor'
for c in e.users_collection: c.objects.unlink(e)
col_ann.objects.link(e)

# Armature with bones: valid H-Anim names, one bad name, one wrong case, one wrong parent
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.active_object; arm.name = 'Figure'; arm.data.name = 'FigureData'
for c in arm.users_collection: c.objects.unlink(arm)
col_rig.objects.link(arm)
eb = arm.data.edit_bones
root = eb[0]; root.name = 'humanoid_root'; root.head=(0,0,0.9); root.tail=(0,0,1.0)
def bone(name, head, tail, parent):
    nb = eb.new(name); nb.head=head; nb.tail=tail; nb.parent=parent; return nb
sac  = bone('sacroiliac', (0,0,1.0),(0,0,1.1), root)
lhip = bone('l_hip',(0.1,0,0.95),(0.1,0,0.5), sac)
lkne = bone('l_knee',(0.1,0,0.5),(0.1,0,0.1), lhip)
lank = bone('l_talocrural',(0.1,0,0.1),(0.1,0,0.0), lkne)
rhip = bone('r_hip',(-0.1,0,0.95),(-0.1,0,0.5), sac)
rkne = bone('R_Knee',(-0.1,0,0.5),(-0.1,0,0.1), rhip)        # wrong case -> not a CAESAR/HAnim name
lelb = bone('l_elbow',(0.3,0,1.4),(0.5,0,1.4), lhip)         # valid name, wrong parent (should hang off l_shoulder chain)
x    = bone('Bone.001',(0,0,1.1),(0,0,1.3), sac)             # not an H-Anim name
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.1, depth=1.0, location=(0,0,0.5))
sk = bpy.context.active_object; sk.name='Body'; sk.data.name='BodyMesh'
for c in sk.users_collection: c.objects.unlink(sk)
col_rig.objects.link(sk)
for bn in ('humanoid_root','l_hip','l_knee'):
    g = sk.vertex_groups.new(name=bn)
    g.add([v.index for v in sk.data.vertices], 1.0 if bn=='humanoid_root' else 0.0, 'REPLACE')
md = sk.modifiers.new('Armature','ARMATURE'); md.object = arm; sk.parent = arm

# Camera + light so the export is a normal scene
bpy.ops.object.light_add(type='SUN', location=(5,5,10))
bpy.ops.object.camera_add(location=(10,-10,8), rotation=(math.radians(60),0,math.radians(45)))
sc.camera = bpy.context.active_object

bpy.ops.export_scene.x3d(filepath=out, x3d_version='X3D40', use_animation=False, use_selection=False,
    meta_title='Ontology bridge fixture', meta_creator='HagopJay', meta_description='Collections, units, metadata, bones',
    meta_keywords='sciviz,hanim,units', meta_reference='urn:example:run-0007', meta_license='CC0_1.0')
print('exported', out, os.path.getsize(out))
print('blender', bpy.app.version_string, bpy.app.build_hash)
