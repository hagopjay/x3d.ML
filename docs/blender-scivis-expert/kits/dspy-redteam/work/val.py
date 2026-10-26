import sys,os,re,json
TREE=sys.argv[1]
sys.path[0:0]=[os.path.join(TREE,"src"),TREE]
from validation.validate import validate_xml
from validation.semantic import validate_semantic
out={}
for f in sorted(sys.argv[2:]):
    xml=open(f).read(); r={}
    try:
        x=validate_xml(xml); r["xsd"]=bool(x.get("valid")); r["xsd_err"]=[str(e)[:160] for e in x.get("errors",[])[:2]]
    except Exception as e: r["xsd"]="CRASH"; r["xsd_err"]=[repr(e)[:120]]
    try:
        sem=validate_semantic(xml); sec=re.search(r"## Errors\n(.*?)(?=\n## |\Z)",sem,re.S)
        r["sem_errs"]=[l[:160] for l in (sec.group(1).splitlines() if sec else []) if l.startswith("- **[")][:3]
    except Exception as e: r["sem_errs"]=["CRASH "+repr(e)[:100]]
    out[os.path.basename(f)]=r
print(json.dumps(out,indent=1))
