"""Dump the concrete node names of each bundled X3DUOM version (for validate.py's _version_hints).

Usage: python3 -I extract_nodes.py <fork-tree> <out-dir>
Writes <out-dir>/nodes-4.0.json and <out-dir>/nodes-4.1.json: sorted JSON arrays of names,
exactly set(X3DUOM(...).get_concrete_nodes()) as used by validation.validate._nodes_by_version.
"""
import json, sys
from pathlib import Path
tree, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[0:0] = [str(tree / "src"), str(tree)]
from x3d_utils.x3duom import X3DUOM
for v in ("4.0", "4.1"):
    names = sorted(X3DUOM(tree / "src/validation/schemas" / f"X3dUnifiedObjectModel-{v}.xml").get_concrete_nodes())
    (out / f"nodes-{v}.json").write_text(json.dumps(names, separators=(",", ":")) + "\n")
    print(v, len(names), "concrete nodes")
