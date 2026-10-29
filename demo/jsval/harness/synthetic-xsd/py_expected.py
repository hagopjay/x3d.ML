import sys, json
sys.path[0:0]=['/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad/fork-main/src','/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad/fork-main']
from validation.validate import validate_xml
cases = json.load(open(sys.argv[1]))
out = {k: validate_xml(v) for k, v in cases.items()}
json.dump(out, open(sys.argv[2], 'w'), indent=1)
