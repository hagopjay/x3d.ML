"""Build data/live.json for the Tether Firehose 3 page from the recorded live run (no network, no spend).
Inputs: a run directory written by live/run_live.py (events.jsonl, x3d/<model>/<prompt>_a<k>.x3d, run.json), the render file made by render/render_final3.py over that
run's x3d/ folder (RENDER_DIR=<run>/x3d RENDER_GLOB='*/*.x3d'; keys are '<model dir>/<prompt>_a<k>.x3d'), and live/prompts_live.jsonl.
Output: {"items": [...], "meta": {...}}. One item = one prompt sent to one model: A = its attempts in order (call start/end on the run clock in seconds, tokens, price estimate,
validator verdict and report, the offline X_ITE render of that attempt), B = the attempt bodies, T = the second the scene was finished on the run clock.
The run clock is the real clock minus the gaps in which no call was in flight (a stopped process), each gap kept as GAP seconds.
<run_dir>/notes.json (optional) maps a model id to why its lane stopped short of the prompt list; the page prints it beside the lane's coverage.
Usage: python3 build_live.py <run_dir> <renders.json> <out.json> [--allow-unrendered]
An attempt with no render would read as "valid but blank" on the page, so the build refuses to write unless every attempt has one (--allow-unrendered is for interim builds only)."""
import collections, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 3.0        # seconds kept for each collapsed idle gap
MIN_GAP = 30.0   # a stretch with no call in flight longer than this is an idle gap
MAX_ATT = 3
ALLOW = "--allow-unrendered" in sys.argv
run, rpath, out = [a for a in sys.argv[1:] if not a.startswith("--")][:3]
renders = json.load(open(rpath))
prompts = {json.loads(l)["prompt_id"]: json.loads(l) for l in open(HERE + "/live/prompts_live.jsonl") if l.strip()}
meta = json.load(open(run + "/run.json"))
slug = lambda m: m.replace("/", "_")
KIND = {"gemini-3.8-flash": "closed", "gemini-3.1-pro-preview": "closed", "gpt-6.1-sol": "closed", "z-ai/glm-5.3": "open", "nvidia/nemotron-3-super-120b-a12b": "open"}

ev = [json.loads(l) for l in open(run + "/events.jsonl") if l.strip()]
errors = [e for e in ev if e.get("error")]
good = [e for e in ev if not e.get("error")]
by = collections.defaultdict(list)
for e in good: by[(e["model"], e["prompt_id"])].append(e)

# ---- consistent chains only: attempts 1..n, each body on disk equal to the logged hash, last attempt valid or the third
dups = 0; mismatch = []; dropped = []; chains = {}
for key, lst in by.items():
    m, pid = key
    byatt = collections.defaultdict(list)
    for e in lst: byatt[e["attempt"]].append(e)
    atts = []
    for k in range(1, MAX_ATT + 1):
        c = byatt.get(k)
        if not c: break
        path = f"{run}/x3d/{slug(m)}/{pid}_a{k}.x3d"
        body = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        pick = [e for e in c if body is not None and hashlib.sha256(body.encode()).hexdigest() == e["sha"]]
        if len(c) > 1: dups += len(c) - 1
        if not pick: mismatch.append((m, pid, k)); break
        atts.append((pick[-1], body))
        if pick[-1]["valid"]: break
    if not atts: dropped.append((m, pid, "no usable attempt")); continue
    last = atts[-1][0]
    if not last["valid"] and len(atts) < MAX_ATT: dropped.append((m, pid, f"unfinished after attempt {len(atts)}")); continue
    chains[key] = atts

# ---- run clock: real time minus the gaps in which nothing was in flight (a stopped process), each gap kept as GAP seconds
iv = sorted((e["t0"], e["v1"]) for atts in chains.values() for e, _ in atts)
t_min = iv[0][0]; shifts = []; removed = 0.0; prev_end = None
for a, b in iv:
    if prev_end is not None and a - prev_end > MIN_GAP:
        removed += (a - prev_end) - GAP; shifts.append((a, removed))      # (start of the next busy stretch in real time, total seconds removed so far)
    prev_end = b if prev_end is None else max(prev_end, b)
def clk(t):
    r = 0.0
    for start, cum in shifts:
        if t >= start - 1e-6: r = cum
    return round(t - t_min - r, 2)

nrm = lambda s: re.sub(r"\s+", " ", s)
items = []
for (m, pid), atts in chains.items():
    pr = prompts[pid]; A = []; B = []
    for k, (e, body) in enumerate(atts):
        key = f"{slug(m)}/{pid}_a{k + 1}.x3d"; rd = renders.get(key) or {}
        err = rd.get("err")
        if err and "parse X3D" in err: err = "X_ITE could not parse this file"
        cb, shot = rd.get("nonblank"), rd.get("shot"); seen = [v for v in (cb, shot) if v is not None]
        nb = None if err else (max(seen) if seen else 0)
        r = {"nodes": rd.get("nodes"), "nb": nb, "cb": cb, "shot": shot, "nf": 1 if (not err and not rd.get("frames")) else 0, "err": err,
             "msgs": [x.split(": ", 1)[-1][:150] for x in rd.get("msgs", [])][:3], "unknown": rd.get("unknown", 0), "nmsg": rd.get("nmsg", 0),
             "frames": rd.get("frames"), "last": rd.get("last"), "ms": rd.get("ms"), "jpg": rd.get("jpg") if (nb or 0) >= 0.005 else None, "rendered": bool(rd)}
        rm = e.get("repair_msg") or ""
        A.append({"t0": clk(e["t0"]), "t1": clk(e["t1"]), "ms": e["ms"], "ti": e["tin"], "to": e["tout"], "u": e["usd"], "fin": e.get("finish"), "ok": int(bool(e["valid"])),
                  "x": int(bool(e["xsd_valid"])), "xe": e["xsd_errors"], "se": e["sem_errors"], "fx": e["fixes"], "sha": e["sha"], "ch": e["chars"], "cn": int(bool(e["constraints_ok"])),
                  "vms": e["v_ms"], "rl": len(rm), "rsha": hashlib.sha256(rm.encode()).hexdigest() if rm else "", "r": r})
        B.append(body)
    last = atts[-1][0]
    items.append({"m": m, "p": pid, "c": pr["category"], "k": "showpiece" if pid.startswith("sp-") else "bench", "pt": pr["prompt"],
                  "psha": hashlib.sha256(pr["prompt"].encode()).hexdigest(), "at": len(atts), "T": clk(last["v1"]), "A": A, "B": B})
items.sort(key=lambda i: (i["T"], i["m"], i["p"]))

missing = sum(1 for i in items for a in i["A"] if not a["r"]["rendered"])
if missing and not ALLOW:
    sys.exit(f"refusing to write {out}: {missing} attempts have no render in {rpath}; render them first (render/render_final3.py) or pass --allow-unrendered for an interim build")
models = []
for m in [x["id"] for x in meta["models"]]:
    mm = next(x for x in meta["models"] if x["id"] == m)
    if any(i["m"] == m for i in items):
        models.append({"id": m, "prov": mm["provider"], "temp": mm["temperature"], "max_out": mm["max_out"], "kind": KIND.get(m, "open")})
t_total = max(i["T"] for i in items)
notes = json.load(open(run + "/notes.json")) if os.path.exists(run + "/notes.json") else {}    # optional {model id: why its lane stopped short}, plain words without provider names
lm = {"models": models, "lanes": notes, "validator": ("fork@" + meta["validator"]) if not meta["validator"].startswith("fork@") else meta["validator"], "t_total": round(t_total, 1), "idle_collapsed_s": round(removed, 1), "n_prompts": len(prompts), "max_attempts": MAX_ATT,
      "failed_calls": len(errors), "date": "2026-10-17", "gaps": len(shifts)}
json.dump({"items": items, "meta": lm}, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
per = collections.Counter(i["m"] for i in items)
print(f"{len(items)} scenes, {sum(len(i['A']) for i in items)} calls, models {dict(per)}")
print(f"run clock {t_total:.0f} s, {len(shifts)} idle gap(s) collapsed ({removed:.0f} s removed); failed-call rows {len(errors)}; duplicate events {dups}; hash mismatches {len(mismatch)}; dropped {len(dropped)}; attempts without render {missing}")
for d in dropped[:12]: print("  dropped", d)
for d in mismatch[:12]: print("  mismatch", d)
print(out, os.path.getsize(out) // 1024, "KB")
