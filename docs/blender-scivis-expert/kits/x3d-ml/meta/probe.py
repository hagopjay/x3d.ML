import sys, subprocess
tree=sys.argv[1]; sys.path[0:0]=[tree+"/src", tree]
from validation.validate import validate_xml
from validation.semantic import validate_semantic
ref=subprocess.run(["git","-C",tree,"rev-parse","--short","HEAD"],capture_output=True,text=True).stdout.strip()
for f in sys.argv[2:]:
    x=open(f,encoding="utf-8").read(); r=validate_xml(x); s=validate_semantic(x)
    errs=[l for l in s.splitlines() if l.startswith("- **[") and "Errors" not in l]
    sec_err = s.split("## Warnings")[0].split("## Info")[0] if "## Errors" in s else ""
    ec=[l[:170] for l in sec_err.splitlines() if l.startswith("- **[")]
    print(ref, f.split("/")[-1], "xsd_valid=",r.get("valid"), "semantic errors:", len(ec)); [print("    ",e) for e in ec[:4]]
