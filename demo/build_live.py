"""Build data/live.json for the Tether Firehose page from a recorded live run (no network, no spend).
Inputs: a run directory written by live/run_live.py (events.jsonl, x3d/, run.json), the render file made by render/render_final3.py over that run's x3d/ folder
(RENDER_DIR=<run>/x3d RENDER_GLOB='*/*.x3d'; keys are the file path under x3d/), and live/prompts_live.jsonl.
Output: {"items": [...], "meta": {...}}. One item = one chain: one prompt sent to one lane (model x arm) once (sample s). A = its steps in order (call start/end on the run clock in
seconds, tokens, price estimate, validator verdict and report, time to first token and the stream trace, the offline X_ITE render), B = the step bodies, T = the second the chain
finished on the run clock. A step is st "model" (a call), "autofix" (the fork's deterministic repair, never a call: agent, fix) or, with --keep-failures, "fail" (a failed call: err).
The run clock is the real clock minus the gaps in which no call was in flight (a stopped process), each gap kept as GAP seconds.
<run_dir>/notes.json (optional) maps a model (or model|arm) to why its lane stopped short of the prompt list (meta.lanes, what the page prints beside the lane's coverage); without it the
lane stop reasons recorded in run.json are used. meta.lane_list is the list of lanes (model x arm) on the page.
Usage: python3 build_live.py <run_dir> <renders.json> <out.json> [--allow-unrendered] [--keep-failures]
An attempt with no render would read as "valid but blank" on the page, so the build refuses to write unless every attempt has one (--allow-unrendered is for interim builds only).
By default only finished chains are written (last step valid, or the third model attempt). --keep-failures also writes the failed calls (st "fail", ok 0, err), the chains a stop cut
(the item and its last step carry cut: why) and chains that are only failed calls, so the honest firehose can show them."""
import collections, datetime, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 3.0        # seconds kept for each collapsed idle gap
MIN_GAP = 30.0   # a stretch with no call in flight longer than this is an idle gap
MAX_ATT = 3
STREAM_PTS = 150     # the page needs a sketch of the stream, not every sample
ALLOW = "--allow-unrendered" in sys.argv; KEEP = "--keep-failures" in sys.argv
run, rpath, out = [a for a in sys.argv[1:] if not a.startswith("--")][:3]
renders = json.load(open(rpath))
prompts = {json.loads(l)["prompt_id"]: json.loads(l) for l in open(HERE + "/live/prompts_live.jsonl") if l.strip()}
meta = json.load(open(run + "/run.json"))
slug = lambda m: m.replace("/", "_")
KIND = {"gemini-3.8-flash": "closed", "gemini-3.1-pro-preview": "closed", "gpt-6.1-sol": "closed"}      # anything else is an open-weights model on a hosted endpoint

ev = [json.loads(l) for l in open(run + "/events.jsonl") if l.strip()]
errors = [e for e in ev if e.get("error")]
good = [e for e in ev if not e.get("error")]
ckey = lambda e: (e.get("lane", e["model"]), e.get("arm", "A"), e["prompt_id"], e.get("sample", 0))      # 17 Oct rows: one lane per model, arm A, sample 0
by = collections.defaultdict(list); byerr = collections.defaultdict(list)
for e in good: by[ckey(e)].append(e)
for e in errors: byerr[ckey(e)].append(e)
rkey = lambda e, m, pid, k: e["file"][4:] if e.get("file") else f"{slug(m)}/{pid}_a{k}.x3d"      # render key = path under x3d/
cutmap = {(c["lane"], c["arm"], c["prompt_id"], c["sample"]): c["by"] for seg in meta.get("segments", []) for c in seg.get("cut", [])}
cutmap.update({(c["lane"], c["arm"], c["prompt_id"], c["sample"]): c["by"] for c in meta.get("cut", [])})

# ---- consistent chains: steps in chain order, each body on disk equal to the logged hash, finished = last step valid or the third model attempt
dups = 0; mismatch = []; dropped = []; chains = {}
for key in list(by) + ([k for k in byerr if k not in by] if KEEP else []):      # with --keep-failures a chain that is only failed calls is kept too
    lst = by.get(key, []); m, arm, pid, s = key
    steps = collections.defaultdict(list)
    for e in lst: steps[(e["attempt"], e["model"] == "autofix")].append(e)
    atts = []; finished = False; nxt = (1, False)
    while nxt in steps:
        c = steps[nxt]; k, isfix = nxt
        path = run + "/x3d/" + rkey(c[-1], m, pid, k)
        body = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        pick = [e for e in c if body is not None and hashlib.sha256(body.encode()).hexdigest() == e["sha"]]
        if len(c) > 1: dups += len(c) - 1
        if not pick: mismatch.append((m, arm, pid, s, k, "autofix" if isfix else "model")); break
        atts.append((pick[-1], body))
        if pick[-1]["valid"] or (not isfix and k >= MAX_ATT): finished = True; break
        nxt = (1, True) if (arm == "B" and not isfix and k == 1) else (k + 1, False)
    if not atts and not (KEEP and byerr.get(key)): dropped.append((m, arm, pid, s, "no usable attempt")); continue
    if not finished and not KEEP: dropped.append((m, arm, pid, s, f"unfinished after {len(atts)} step(s)")); continue
    chains[key] = (atts, None if finished else cutmap.get(key, "unfinished"))

# ---- run clock: real time minus the gaps in which nothing was in flight (a stopped process), each gap kept as GAP seconds
iv = sorted([(e["t0"], e["v1"]) for atts, _ in chains.values() for e, _ in atts] + ([(e["t0"], e["t1"]) for key in chains for e in byerr.get(key, [])] if KEEP else []))
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
def sketch(pts):
    if not pts or len(pts) <= STREAM_PTS: return pts
    step = (len(pts) - 1) / (STREAM_PTS - 1)
    return [pts[round(i * step)] for i in range(STREAM_PTS)]

items = []
for (m, arm, pid, s), (atts, cut) in chains.items():
    pr = prompts[pid]; A = []; B = []
    fails = sorted(byerr.get((m, arm, pid, s), []), key=lambda e: (e["attempt"], e.get("try", 0), e["t1"])) if KEEP else []
    def fail_entry(e):
        return {"st": "fail", "t0": clk(e["t0"]), "t1": clk(e["t1"]), "ms": e.get("ms", int((e["t1"] - e["t0"]) * 1000)), "ti": 0, "to": 0, "u": 0.0, "fin": None, "ok": 0, "x": 0, "xe": [], "se": [], "fx": [], "sha": "", "ch": 0, "cn": 0,
                "vms": 0, "rl": 0, "rsha": "", "err": e["error"], "status": e.get("status"), "try": e.get("try"), "backoff": e.get("backoff_s"), "att": e["attempt"], "r": {"rendered": False, "nb": None, "err": None, "msgs": []}}
    for e, body in atts:
        while fails and fails[0]["attempt"] <= e["attempt"] and (e["model"] == "autofix" or fails[0]["attempt"] < e["attempt"] or fails[0]["t1"] <= e["t0"]):
            A.append(fail_entry(fails.pop(0))); B.append("")
        key = rkey(e, m, pid, e["attempt"]); rd = renders.get(key) or {}
        err = rd.get("err")
        if err and "parse X3D" in err: err = "X_ITE could not parse this file"
        cb, shot = rd.get("nonblank"), rd.get("shot"); seen = [v for v in (cb, shot) if v is not None]
        nb = None if err else (max(seen) if seen else 0)
        r = {"nodes": rd.get("nodes"), "nb": nb, "cb": cb, "shot": shot, "nf": 1 if (not err and not rd.get("frames")) else 0, "err": err,
             "msgs": [x.split(": ", 1)[-1][:150] for x in rd.get("msgs", [])][:3], "unknown": rd.get("unknown", 0), "nmsg": rd.get("nmsg", 0),
             "frames": rd.get("frames"), "last": rd.get("last"), "ms": rd.get("ms"), "jpg": rd.get("jpg") if (nb or 0) >= 0.005 else None, "rendered": bool(rd)}
        rm = e.get("repair_msg") or ""
        a = {"st": "autofix" if e["model"] == "autofix" else "model", "att": e["attempt"], "t0": clk(e["t0"]), "t1": clk(e["t1"]), "ms": e["ms"], "ti": e["tin"], "to": e["tout"], "u": e["usd"], "fin": e.get("finish"), "ok": int(bool(e["valid"])),
             "x": int(bool(e["xsd_valid"])), "xe": e["xsd_errors"], "se": e["sem_errors"], "fx": e["fixes"], "sha": e["sha"], "ch": e["chars"], "cn": int(bool(e["constraints_ok"])),
             "vms": e["v_ms"], "rl": len(rm), "rsha": hashlib.sha256(rm.encode()).hexdigest() if rm else "", "r": r}
        if "tft_ms" in e: a["tft"] = e["tft_ms"]; a["stream"] = sketch(e.get("stream") or [])
        if a["st"] == "autofix": a["agent"] = e.get("agent"); a["fix"] = {"n": len(e.get("fix_changes", [])), "changes": e.get("fix_changes", [])[:12], "kinds": e.get("fix_kinds", {}), "unfixable": e.get("fix_unfixable", [])[:6], "bin": e.get("bytes_in"), "bout": e.get("bytes_out"), "err": e.get("fix_error")}
        A.append(a); B.append(body)
    for e in fails: A.append(fail_entry(e)); B.append("")
    if cut and A: A[-1]["cut"] = cut
    T = clk(max(e["v1"] for e, _ in atts)) if atts else clk(max(e["t1"] for e in byerr[(m, arm, pid, s)]))
    it = {"m": m, "arm": arm, "s": s, "p": pid, "c": pr["category"], "k": "showpiece" if pid.startswith("sp-") else "bench", "pt": pr["prompt"],
          "psha": hashlib.sha256(pr["prompt"].encode()).hexdigest(), "at": sum(1 for a in A if a["st"] == "model"), "steps": len(A), "T": T, "A": A, "B": B}
    if cut: it["cut"] = cut
    items.append(it)
items.sort(key=lambda i: (i["T"], i["m"], i["arm"], i["s"], i["p"]))

missing = sum(1 for i in items for a in i["A"] if a["st"] != "fail" and not a["r"]["rendered"])
if missing and not ALLOW:
    sys.exit(f"refusing to write {out}: {missing} attempts have no render in {rpath}; render them first (render/render_final3.py) or pass --allow-unrendered for an interim build")
models = []
for mm in meta["models"]:
    m = mm["id"]
    if any(i["m"] == m for i in items):
        models.append({"id": m, "prov": mm["provider"], "temp": mm["temperature"], "max_out": mm["max_out"], "kind": KIND.get(m, "open")})
for m in sorted({i["m"] for i in items} - {x["id"] for x in models}):      # a lane run as provider:id, outside the table
    e = next(e for e in good if e.get("lane", e["model"]) == m and e["model"] != "autofix")
    models.append({"id": m, "prov": e["provider"], "temp": None, "max_out": None, "kind": KIND.get(m, "open")})
lanes = sorted({(i["m"], i["arm"]) for i in items}, key=lambda x: ([x["id"] for x in models].index(x[0]), x[1]))
t_total = max(i["T"] for i in items)
narms = collections.Counter(v["model"] for v in meta.get("lanes", {}).values())
notes = json.load(open(run + "/notes.json")) if os.path.exists(run + "/notes.json") else {(v["model"] if narms[v["model"]] == 1 else k): v["stopped"] for k, v in meta.get("lanes", {}).items() if v.get("stopped")}    # {model or model|arm: why it stopped short}; the page reads meta.lanes[model]
date = datetime.datetime.fromtimestamp(meta["t_start"], datetime.timezone.utc).strftime("%Y-%m-%d") if meta.get("t_start") else "2026-10-17"
lm = {"models": models, "lanes": notes, "lane_list": [{"m": m, "arm": arm} for m, arm in lanes], "arms": sorted({a for _, a in lanes}), "samples": max(i["s"] for i in items) + 1,
      "validator": ("fork@" + meta["validator"]) if not meta["validator"].startswith("fork@") else meta["validator"], "t_total": round(t_total, 1), "idle_collapsed_s": round(removed, 1), "n_prompts": len(prompts), "max_attempts": MAX_ATT,
      "failed_calls": len(errors), "cut_chains": sum(1 for i in items if i.get("cut")), "autofix_steps": sum(1 for i in items for a in i["A"] if a["st"] == "autofix"), "keep_failures": KEEP, "date": date, "gaps": len(shifts)}
json.dump({"items": items, "meta": lm}, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
per = collections.Counter(f"{i['m']}|{i['arm']}" for i in items)
print(f"{len(items)} chains, {sum(i['at'] for i in items)} model calls, {lm['autofix_steps']} autofix steps, lanes {dict(per)}")
print(f"run clock {t_total:.0f} s, {len(shifts)} idle gap(s) collapsed ({removed:.0f} s removed); failed-call rows {len(errors)}{' (kept)' if KEEP else ''}; cut chains kept {lm['cut_chains']}; duplicate events {dups}; hash mismatches {len(mismatch)}; dropped {len(dropped)}; attempts without render {missing}")
for d in dropped[:12]: print("  dropped", d)
for d in mismatch[:12]: print("  mismatch", d)
print(out, os.path.getsize(out) // 1024, "KB")
