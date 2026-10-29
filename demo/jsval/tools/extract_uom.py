"""Extract the X3DUOM tables the semantic checks need into data/uom-4.1.json (js-port-of-8dd0d3e).

Usage: python3 -I extract_uom.py <fork-tree> <out-dir>

Uses the fork's own x3d_utils.x3duom.X3DUOM parser (so the tables are exactly what
validation/semantic.py and validation/profile.py read) on X3dUnifiedObjectModel-4.1.xml --
get_x3duom() always loads 4.1 regardless of the document version -- and writes the compact
shape documented in PLAN.md section 3:
  {"version":"4.1",
   "nodes":{N:{"c":component,"l":level,"b":baseType,"ab":[additionalBaseTypes],"cf":containerField,
               "f":[[name,type,accessType(,acceptableNodeTypes)], ...]}},   # fields in UOM order
   "abstracts":{A:{"b":baseType,"ab":[...]}},
   "fieldTypes":{T:[isArray 0|1, tupleSize]},
   "profiles":{P:[allowed node names] | null}}   # null = Full ("all nodes"), parsed like profile.py
"""
import json, re, sys
from pathlib import Path

tree, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[0:0] = [str(tree / "src"), str(tree)]
from x3d_utils.x3duom import X3DUOM, X3DUOM_PATH

uom = X3DUOM(X3DUOM_PATH)
nodes = {}
for name, info in uom.get_concrete_nodes().items():
    fields = []
    for f in info["fields"]:
        row = [f["name"], f["type"], f["accessType"]]
        if f.get("acceptableNodeTypes"):
            row.append(f["acceptableNodeTypes"])
        fields.append(row)
    nodes[name] = {"c": info["component"], "l": info["level"], "b": info["baseType"],
                   "ab": info["additionalBaseTypes"], "cf": info["containerField"], "f": fields}
abstracts = {name: {"b": info["baseType"], "ab": info["additionalBaseTypes"]}
             for name, info in uom.get_abstract_types().items()}
field_types = {name: [1 if info["isArray"] else 0, info["tupleSize"]]
               for name, info in uom.get_field_types().items()}
profiles = {}
for name, info in uom.get_profiles().items():   # same regex as validation/profile.py profile_nodes()
    m = re.search(r"Allowed X3D nodes for this profile are:\s*(.*?)\.?\s*$", info.get("appinfo", ""), re.S)
    profiles[name] = sorted(set(m.group(1).split())) if m else None
data = {"version": "4.1", "nodes": nodes, "abstracts": abstracts, "fieldTypes": field_types, "profiles": profiles}
out.mkdir(parents=True, exist_ok=True)
(out / "uom-4.1.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
print("uom-4.1.json", len(nodes), "nodes", len(abstracts), "abstracts", len(field_types), "field types", len(profiles), "profiles")
