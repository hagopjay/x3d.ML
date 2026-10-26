import sys, re
from pathlib import Path
from saxonche import PySaxonProcessor
XSLT='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/semantics-svn/X3dToTurtle.xslt'
def convert(src, dst):
    t=open(src,encoding='utf-8').read()
    t=re.sub(r'<!DOCTYPE[^>]*>\s*','',t)
    tmp=str(dst)+'.stripped.x3d'; open(tmp,'w',encoding='utf-8').write(t)
    with PySaxonProcessor(license=False) as p:
        p.new_xslt30_processor().compile_stylesheet(stylesheet_file=XSLT).transform_to_file(source_file=tmp, output_file=str(dst))
if __name__=='__main__':
    convert(sys.argv[1], sys.argv[2]); print('ok', sys.argv[2])
