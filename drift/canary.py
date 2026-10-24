"""Validator canary: validate every recorded body with one x3d_mcp tree and compare with a committed baseline.

    python3 -I drift/canary.py --tree <x3d_mcp checkout> --baseline drift/verdicts-8dd0d3e.json          # exit 1 on any flip
    python3 -I drift/canary.py --tree <x3d_mcp checkout> --write drift/verdicts-<sha>.json                # write a new baseline

Bodies: the 174 replay scenes (demo/data/replay.json, field b), every runs/live-*/x3d/**/*.x3d attempt, and the physics ledger.
A verdict is: xsd valid (lxml XMLSchema), the semantic error codes, the warning codes; valid = xsd valid and no semantic errors.
Run it in CI (.github/workflows/tether-check.yml) against the pinned fork commit, and by hand before moving the pinned commit."""
import argparse, glob, json, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--tree", required=True)
ap.add_argument("--baseline")
ap.add_argument("--write")
ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
a = ap.parse_args()
sys.path[0:0] = [a.tree + "/src", a.tree]
from validation.validate import validate_xml          # noqa: E402
from validation.semantic import validate_semantic     # noqa: E402

def ref(tree):
    try:
        return subprocess.run(["git", "-C", tree, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"

def bodies(repo):
    out = {}
    rp = os.path.join(repo, "demo/data/replay.json")
    if os.path.exists(rp):
        for it in json.load(open(rp)):
            out["replay/" + it["k"]] = it["b"]
    for f in sorted(glob.glob(os.path.join(repo, "runs/live-*/x3d/*/*.x3d"))):
        out["/".join(f.split("/")[-4:])] = open(f, encoding="utf-8", errors="replace").read()
    for f in sorted(glob.glob(os.path.join(repo, "runs/suite-physics-*/*.ledger.x3d"))):
        out["/".join(f.split("/")[-2:])] = open(f, encoding="utf-8", errors="replace").read()
    return out

def codes(section):
    return sorted(set(l.split("]**")[0].split("[")[-1] for l in section.splitlines() if l.startswith("- **[")))

def verdict(xml):
    x = validate_xml(xml); sem = validate_semantic(xml)
    errs = codes(sem.split("## Warnings")[0].split("## Info")[0]) if "## Errors" in sem else []
    warns = codes(sem.split("## Warnings")[1].split("## Info")[0]) if "## Warnings" in sem else []
    return {"valid": bool(x.get("valid")) and not errs, "xsd": bool(x.get("valid")), "nxsd": len(x.get("errors", [])), "sem": errs, "warn": warns}

t0 = time.time(); B = bodies(a.repo); V = {}
for k, xml in B.items():
    try:
        V[k] = verdict(xml)
    except Exception as e:
        V[k] = {"valid": False, "xsd": False, "nxsd": -1, "sem": [], "warn": [], "err": f"{type(e).__name__}: {str(e)[:100]}"}
r = ref(a.tree)
print(f"canary: tree {r} bodies {len(V)} valid {sum(v['valid'] for v in V.values())} xsd-valid {sum(v['xsd'] for v in V.values())} wall {time.time()-t0:.1f}s")
if a.write:
    json.dump({"tree": r, "n": len(V), "verdicts": V}, open(a.write, "w"), indent=0, sort_keys=True)
    print("wrote", a.write)
if a.baseline:
    base = json.load(open(a.baseline)); bv = base["verdicts"]
    flips = [k for k in V if k in bv and (V[k]["valid"] != bv[k]["valid"] or V[k]["xsd"] != bv[k]["xsd"])]
    semd = [k for k in V if k in bv and (V[k]["sem"] != bv[k]["sem"] or V[k]["warn"] != bv[k]["warn"])]
    new = [k for k in V if k not in bv]; gone = [k for k in bv if k not in V]
    print(f"against {a.baseline} (tree {base.get('tree')}): verdict flips {len(flips)}, code changes {len(semd)}, new bodies {len(new)}, missing {len(gone)}")
    for k in flips[:20]: print("  FLIP", k, bv[k]["valid"], "->", V[k]["valid"], bv[k]["sem"], "->", V[k]["sem"])
    for k in semd[:20]:
        if k not in flips: print("  CODES", k, bv[k]["sem"], bv[k]["warn"], "->", V[k]["sem"], V[k]["warn"])
    if flips or semd:
        print("CANARY: FAIL (the validator moved; investigate before moving the pinned commit)"); sys.exit(1)
    print("CANARY: OK")
