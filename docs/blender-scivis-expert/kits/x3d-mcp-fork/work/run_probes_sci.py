import sys, json, os
SRC = sys.argv[1]
os.environ["X3D_MCP_SRC"] = SRC
sys.path.insert(0, SRC); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probes_lib, sci_checks
for k, t in probes_lib.P.items():
    d = sci_checks.run(t, SRC)
    print(f"{k:45s}", sorted({f'{x.level}:{x.check}' for x in d if x.check not in ('provenance-meta-missing','splat-size-budget')}))
