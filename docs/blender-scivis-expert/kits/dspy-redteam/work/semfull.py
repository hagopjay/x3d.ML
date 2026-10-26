import sys,os
TREE=sys.argv[1]; sys.path[0:0]=[os.path.join(TREE,"src"),TREE]
from validation.semantic import validate_semantic
for f in sys.argv[2:]:
    print("=====",os.path.basename(f)); print(validate_semantic(open(f).read())[:900])
