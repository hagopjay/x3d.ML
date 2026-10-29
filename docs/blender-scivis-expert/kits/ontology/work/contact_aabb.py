import sys, json, re
sys.path.insert(0,'/mnt/project-files/research/ontology-lentz-polys-2026-10-17/steps-2-to-4/step4-parts-contact')
import parts_contact as P
ex=json.load(open('contact_exact.json'))
names={'S1':'S1_tangent','S2':'S2_parallel_rods','S3':'S3_corner'}
for k in ('S1','S2','S3'):
    xml=re.sub(r'<!DOCTYPE[^>]*>\s*','',open(f'contact_{k}.x3d').read())
    an=P.analyse(xml); a,b=an['parts'][0],an['parts'][1]
    print(k,'AABB gap',round(P.gap(a,b),4),'touching(5% tol)',P.touching(a,b),'| exact mesh distance (Blender BVH)',round(ex[names[k]],4))
