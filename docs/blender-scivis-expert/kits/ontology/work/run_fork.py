import sys, json
repo=sys.argv[1]; path=sys.argv[2]
sys.path.insert(0, repo+'/src')
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics
xml=open(path,encoding='utf-8').read()
v=validate_xml(xml)
d=semantic_diagnostics(xml)
print('commit', repo.split('/')[-1])
print('xsd valid:', v.get('valid'), 'errors:', len(v.get('errors',[])), 'warnings:', len(v.get('warnings',[])))
from collections import Counter
c=Counter((x.level, x.check) for x in d)
print('semantic:', dict(c))
for x in [y for y in d if y.level!="info"]:
    print('  ', x.level, x.check, x.message[:140])
