"""The Tether's validator: the x3d_mcp fork (XSD plus semantic checks), run in-process. valid = XSD valid and no semantic errors. The repair message lists the XSD errors, the
semantic Errors section and the exact-fix lines the report gives (E1 showed errors only; the fork's MCP tool returns the whole report, so a model on the loop sees the fixes too)."""
import os, subprocess, sys, threading, time
TREE = os.environ.get("VALIDATOR_TREE", "/home/user/x3d_mcp")
sys.path[0:0] = [TREE + "/src", TREE]
from validation.validate import validate_xml        # noqa: E402
from validation.semantic import validate_semantic   # noqa: E402
_lock = threading.Lock()


def ref():
    try:
        return subprocess.run(["git", "-C", TREE, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def validate(xml):
    """-> dict(valid, xsd_valid, xsd_errors[:20], sem_errors[:20], fixes[:10], ms). Never raises."""
    t0 = time.time()
    try:
        with _lock:
            x = validate_xml(xml); sem = validate_semantic(xml)
        head = sem.split("## Warnings")[0].split("## Info")[0]
        errs = [l for l in head.splitlines() if l.startswith("- **[")] if "## Errors" in sem else []
        fixes = [l for l in sem.splitlines() if l.startswith("- **[") and "-fix]**" in l]
        return {"valid": bool(x.get("valid")) and not errs, "xsd_valid": bool(x.get("valid")), "xsd_errors": list(x.get("errors", []))[:20], "sem_errors": errs[:20], "fixes": fixes[:10],
                "ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"valid": False, "xsd_valid": False, "xsd_errors": [f"validator could not run: {type(e).__name__}: {str(e)[:120]}"], "sem_errors": [], "fixes": [], "ms": int((time.time() - t0) * 1000)}


def repair_text(REPAIR, v):
    sem = "\n".join(v["sem_errors"] + v["fixes"]) or "none"
    return REPAIR.format(xsd="\n".join(v["xsd_errors"]) or "none", sem=sem)
