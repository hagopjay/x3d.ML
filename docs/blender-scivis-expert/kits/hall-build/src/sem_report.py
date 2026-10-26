import sys
tree, f = sys.argv[1:3]
sys.path[0:0] = [tree + "/src", tree]
from validation.semantic import validate_semantic
print(validate_semantic(open(f).read()))
