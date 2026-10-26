import sys, time, re, resource
sys.path.insert(0,'.')
from saxonche import PySaxonProcessor
XSLT='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/semantics-svn/X3dToTurtle.xslt'
src='/mnt/project-files/polyxandria/library/versions/hall_v1_7/library_v1_7.x3d'
t=open(src,encoding='utf-8').read()
t=re.sub(r'<!DOCTYPE[^>]*>\s*','',t)
open('hall/hall_v1_7.stripped.x3d','w',encoding='utf-8').write(t)
t0=time.time()
with PySaxonProcessor(license=False) as p:
    p.new_xslt30_processor().compile_stylesheet(stylesheet_file=XSLT).transform_to_file(source_file='hall/hall_v1_7.stripped.x3d', output_file='hall/hall_v1_7.ttl')
print('xslt seconds', round(time.time()-t0,1), 'maxrss MB', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024)
