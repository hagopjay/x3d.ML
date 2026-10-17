import sys
src,dst=sys.argv[1:3]
t=open(src,encoding='utf-8').read()
assert '<script src="xite/x_ite.min.js">' in t, 'page must load X_ITE from its own published files'
if not t.lstrip().lower().startswith('<!doctype'): t='<!doctype html>\n'+t   # the publish step adds this
open(dst,'w',encoding='utf-8').write(t); print(dst,len(t))
