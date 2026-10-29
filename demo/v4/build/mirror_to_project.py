"""Mirror the run data behind Tether Firehose 4 into the shared project files (SPEC section 8 step 7; S15 members' desk reads this tree).
Copies JSON, JSONL and X3D only, with cp, into /mnt/project-files/research/traceability-2026-10-17/firehose4/{data, data/v4, drift, runs/<date>, runs/suite-physics-<date>}:
  demo/data/*.json (top level) -> data/        demo/v4/data/*.json + demo/v4/parts/manifest.json -> data/v4/        drift/*.json -> drift/
  runs/live-2026-10-17/{events.jsonl, run.json, notes.json} and x3d/<model>/*.x3d -> runs/2026-10-17/        runs/suite-physics-2026-10-17/{result.json, *.steps.json, *.ledger.x3d} -> runs/suite-physics-2026-10-17/
NEVER an image: PNG, JPEG, SVG (and anything else) are refused by extension and by magic bytes, because files in the shared folder get C2PA-stamped. The parts (*.txt) are not
mirrored: they are derived from the JSON here. The 24 Oct run is still recording and is not touched; pass --run runs/live-<date> to add a finished run later.
The destination is a network mount: this script only creates directories, copies files and stats what it copied; it never lists or greps the tree recursively.
Usage: python3 demo/v4/build/mirror_to_project.py [--dest <dir>] [--run <runs/live-<date>>]"""
import glob, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEST = sys.argv[sys.argv.index("--dest") + 1] if "--dest" in sys.argv else "/mnt/project-files/research/traceability-2026-10-17/firehose4"
RUNS = [os.path.join(ROOT, "runs/live-2026-10-17")] + ([sys.argv[sys.argv.index("--run") + 1]] if "--run" in sys.argv else [])
ALLOW = {".json", ".jsonl", ".x3d"}
MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"RIFF", b"<svg", b"<?xml-stylesheet")


def ok(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOW: return False
    with open(path, "rb") as f: head = f.read(64)
    if any(head.lstrip().startswith(m) for m in MAGIC) or b"<svg" in head: return False
    return True


jobs = {"data": sorted(glob.glob(ROOT + "/demo/data/*.json")),
        "data/v4": sorted(glob.glob(ROOT + "/demo/v4/data/*.json")) + [ROOT + "/demo/v4/parts/manifest.json"],
        "drift": sorted(glob.glob(ROOT + "/drift/*.json"))}
for run in RUNS:
    date = os.path.basename(run).replace("live-", "")
    jobs[f"runs/{date}"] = [p for p in (f"{run}/events.jsonl", f"{run}/run.json", f"{run}/notes.json") if os.path.exists(p)]
    for md in sorted(glob.glob(run + "/x3d/*/")):
        jobs[f"runs/{date}/x3d/{os.path.basename(md.rstrip('/'))}"] = sorted(glob.glob(md + "*.x3d"))
for sd in sorted(glob.glob(ROOT + "/runs/suite-physics-*/")):
    jobs["runs/" + os.path.basename(sd.rstrip("/"))] = sorted(glob.glob(sd + "*.json") + glob.glob(sd + "*.ledger.x3d"))

total = 0; n = 0; refused = []
for rel, files in jobs.items():
    good = [f for f in files if ok(f)]; refused += [f for f in files if not ok(f)]
    if not good: continue
    d = os.path.join(DEST, rel); os.makedirs(d, exist_ok=True)
    subprocess.run(["cp", "-f", *good, d + "/"], check=True)
    b = sum(os.path.getsize(os.path.join(d, os.path.basename(f))) for f in good); total += b; n += len(good)
    print(f"{rel:48} {len(good):4} files {b:>12,} B")
print(f"mirrored {n} files, {total:,} B, into {DEST}; refused {len(refused)} (not JSON/JSONL/X3D or image bytes)" + (f": {[os.path.basename(r) for r in refused][:6]}" if refused else ""))
