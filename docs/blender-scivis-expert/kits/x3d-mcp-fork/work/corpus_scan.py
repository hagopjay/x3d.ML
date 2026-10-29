"""Run the prototype sci checks over every .x3d on the project drive (read-only). One JSON line per file."""
import sys, os, json, time, hashlib, multiprocessing as mp
SRC = sys.argv[1]; LISTING = sys.argv[2]; OUT = sys.argv[3]
sys.path.insert(0, SRC); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sci_checks
sci_checks._bind(SRC)
ROOT = "/mnt/project-files/"

def work(item):
    size, rel = item
    path = ROOT + rel[2:]
    t0 = time.time()
    rec = {"path": rel[2:], "bytes": size}
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        rec["sha256_16"] = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]
        rec["has_splats"] = "<GaussianSplats" in text
        rec["version"] = (text.split('version="', 1) + [""])[1][:4] if 'version="' in text[:2000] else ""
        before = dict(sci_checks.STATS)
        d = sci_checks.run(text, SRC)
        rec["elig"] = {k: v - before.get(k, 0) for k, v in sci_checks.STATS.items() if v - before.get(k, 0)}
        rec["findings"] = [[x.level, x.check, x.message[:300]] for x in d if x.check != "splat-size-budget"]
        rec["budget"] = [x.message for x in d if x.check == "splat-size-budget"][:3]
    except Exception as e:
        rec["error"] = repr(e)[:200]
    rec["secs"] = round(time.time() - t0, 2)
    return rec

if __name__ == "__main__":
    items = []
    for l in open(LISTING):
        s, p = l.rstrip("\n").split(" ", 1)
        items.append((int(s), p))
    items.sort()
    with mp.Pool(3) as pool, open(OUT, "w") as out:
        for rec in pool.imap_unordered(work, items, chunksize=1):
            out.write(json.dumps(rec) + "\n"); out.flush()
