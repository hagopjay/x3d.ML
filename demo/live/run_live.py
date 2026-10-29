#!/usr/bin/env python3
"""Recorded live run for Tether Firehose 4 (and 3). Every prompt x every lane goes through the Tether loop with REAL calls: the model writes X3D, the x3d_mcp fork validates it, and
if the fork rejects the scene its exact report goes back and the model is asked again (up to 3 attempts, the same loop and prompts as the 11 Oct GPU-phase 'grounded' runs plus 20 showpieces).
A lane is one model x one arm. Arm A is that loop. Arm B is "autofix first": after the first invalid verdict the fork's own deterministic repair (what its MCP tool repair_x3d calls) is
applied and re-validated, recorded as its own row (model "autofix"); only if the scene is still invalid does the report, with the autofixed body, go to the model as attempt 2 (and 3).
Chains are keyed (model, arm, prompt_id, sample); --samples N repeats every prompt N times per lane so rates get intervals later.
Every call is ledgered (ledger.py) before its result is used. Each lane has its own spend cap, wall budget and stop flag: a lane stops itself after 6 consecutive 429/502-class failures
(backoff 2, 4, 8, 16, 32 s between them), at its own cap or wall, and one lane stopping never stops another; the run's total cap, --wall-min, SIGTERM and SIGINT stop the whole run cleanly
(calls in flight finish and are recorded, nothing new starts). run.json records which chains were cut and which lane stopped why. Resumable: events.jsonl is append-only and a re-run continues unfinished chains.
Each lane has its own worker pool (a slow model never holds up a fast one), --concurrency caps calls in flight across all lanes, and prompts are walked in an interleaved order, bench and showpiece alternating.
Usage: [GCP_PROJECT=<vertex project>] [VALIDATOR_TREE=<fork checkout>] python3 run_live.py <out_dir> [--prompts id,id] [--models id,id | provider:id] [--arms A,B] [--b-models id,id] [--samples N]
       [--cap USD] [--lane-cap USD] [--wall-min N] [--lane-wall-min N] [--concurrency N] [--parallel N]
Writes <out_dir>/events.jsonl (one row per attempt, autofix step or failed call), <out_dir>/x3d/<model>/<prompt>_<arm><sample>_a<k>[f].x3d (f: the autofixed body), <out_dir>/run.json."""
import argparse, concurrent.futures as cf, hashlib, json, os, signal, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ledger
from ledger import Budget, BudgetStop
from llmcall import call, strip_x3d, CallError, RATE
import validate_fork as VF
from prompts_sys import SYSTEM, REPAIR, REPAIR_AUTOFIX

MODELS = [   # id, provider, parallel calls, temperature (None = the API's default), max output tokens (thinking included)
    ("gemini-3.8-flash", "vertex", 8, 0.4, 12000),
    ("gemini-3.1-pro-preview", "vertex", 4, None, 12000),
    ("gpt-6.1-sol", "openai", 4, None, 12000),
    ("z-ai/glm-5.3", "nvidia", 8, 0.4, 8000),
    ("nvidia/nemotron-3-super-120b-a12b", "nvidia", 3, 0.4, 8000),       # 17 Oct lane; 404 "not found for account" on 24 Oct (runs/roster-2026-10-24/ROSTER.md)
    ("nvidia/nemotron-3-ultra-550b-a55b", "nvidia", 2, 0.4, 8000),       # 24 Oct roster
    ("nvidia/nemotron-3.5-super-vl-120b-a12b", "nvidia", 2, 0.4, 8000),
    ("minimaxai/minimax-m3.1-flash", "nvidia", 2, 0.4, 8000),
]
MAX_ATTEMPTS = 3
BACKOFF = (2, 4, 8, 16, 32)     # seconds between a lane's consecutive rate-limit retries
MAX_RATE_FAILS = 6              # the sixth 429/502-class failure in a row stops the lane
slug = lambda m: m.replace("/", "_")


def check_constraints(x3d, c):     # same as the 11 Oct harness
    ok = all(f"<{n}" in x3d for n in c.get("required_nodes", []))
    ok &= x3d.count(" USE=") >= c.get("min_use", 0)
    ok &= x3d.count(" DEF=") >= c.get("min_defs", 0)
    ok &= x3d.count("<ROUTE") >= c.get("min_routes", 0)
    ok &= x3d.count("<Transform") >= c.get("min_transforms", 0)
    return bool(ok)


class Lane:
    """One model x one arm: its own budget (under the run's), wall budget, stop flag and consecutive-failure counter."""
    def __init__(self, mcfg, arm, cap, wall_min, parent, since):
        self.mid, self.prov, self.par, self.temp, self.max_out = mcfg; self.arm = arm; self.key = f"{self.mid}|{arm}"
        self.budget = Budget(cap, parent=parent, since=since, model=self.mid, name="lane " + self.key)
        self.wall = wall_min * 60 if wall_min else None; self.stop = threading.Event(); self.why = None; self.fails = 0; self.lock = threading.Lock()
        self.n = dict(calls=0, failed=0, done=0, cut=0, not_started=0)

    def halt(self, why):
        with self.lock:
            if self.why: return
            self.why = why
        self.stop.set(); print(f"LANE STOPPED {self.key}: {why}", flush=True)

    def rate_fail(self):
        with self.lock: self.fails += 1; return self.fails

    def succeeded(self):
        with self.lock: self.fails = 0

    def record(self):
        return dict(model=self.mid, arm=self.arm, provider=self.prov, parallel=self.par, temperature=self.temp, max_out=self.max_out, cap_usd=self.budget.cap, wall_min=self.wall / 60 if self.wall else None,
                    stopped=self.why, spent_usd=round(self.budget.spent, 6), **self.n)


def parse_models(arg):
    if not arg: return list(MODELS)
    out = []
    for tok in arg.split(","):
        m = next((m for m in MODELS if m[0] == tok), None)
        if m: out.append(m)
        elif ":" in tok: prov, mid = tok.split(":", 1); out.append((mid, prov, 3, 0.4, 8000))      # a model not in the table: provider:id with the defaults
        else: sys.exit(f"unknown model {tok}: add it to MODELS or write provider:id")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--prompts"); ap.add_argument("--models"); ap.add_argument("--arms", default="A"); ap.add_argument("--b-models", help="arm B only for these models (default: all)")
    ap.add_argument("--samples", type=int, default=1); ap.add_argument("--cap", type=float, help="the run's total spend cap in USD"); ap.add_argument("--lane-cap", type=float, help="each lane's own cap (default: the run's)")
    ap.add_argument("--wall-min", type=float, help="stop the whole run after N minutes (calls in flight finish)"); ap.add_argument("--minutes", type=float, help=argparse.SUPPRESS)      # old name of --wall-min
    ap.add_argument("--lane-wall-min", type=float, help="each lane stops itself after N minutes"); ap.add_argument("--concurrency", type=int, help="calls in flight across all lanes"); ap.add_argument("--parallel", type=int, help="override every lane's worker count")
    a = ap.parse_args(); wall_min = a.wall_min or a.minutes
    out = a.out; os.makedirs(out + "/x3d", exist_ok=True)
    prompts = [json.loads(l) for l in open(HERE + "/prompts_live.jsonl") if l.strip()]
    if a.prompts: keep = a.prompts.split(","); prompts = [p for p in prompts if p["prompt_id"] in keep]
    sp = [p for p in prompts if p["prompt_id"].startswith("sp-")]; bench = [p for p in prompts if not p["prompt_id"].startswith("sp-")]
    prompts = [p for _, p in sorted([((i + .5) / len(bench), p) for i, p in enumerate(bench)] + [((i + .5) / len(sp), p) for i, p in enumerate(sp)], key=lambda t: t[0])]
    models = parse_models(a.models); arms = [x.strip().upper() for x in a.arms.split(",")]; bmodels = a.b_models.split(",") if a.b_models else None
    evp = out + "/events.jsonl"; done = {}
    if os.path.exists(evp):
        for l in open(evp):
            e = json.loads(l); done.setdefault((e.get("lane", e["model"]), e.get("arm", "A"), e["prompt_id"], e.get("sample", 0)), []).append(e)
    T0 = time.time(); meta_p = out + "/run.json"
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {"t_start": T0, "validator": VF.ref(), "max_attempts": MAX_ATTEMPTS, "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12],
                                                                    "repair_autofix_sha": hashlib.sha256(REPAIR_AUTOFIX.encode()).hexdigest()[:12]}
    run_budget = Budget(cap=a.cap if a.cap else ledger.CAP_USD, since=meta["t_start"], name="run")
    lanes = []
    for m in models:
        for arm in arms:
            if arm == "B" and bmodels and m[0] not in bmodels: continue
            if a.parallel: m = (m[0], m[1], a.parallel, m[3], m[4])
            lanes.append(Lane(m, arm, a.lane_cap if a.lane_cap else run_budget.cap, a.lane_wall_min, run_budget, meta["t_start"]))
    for ln in lanes:
        if ln.prov == "vertex" and not os.environ.get("GCP_PROJECT"): ln.halt("GCP_PROJECT not set: the Vertex lane is configured but cannot run in this environment")
    stop, wlock, sem = threading.Event(), threading.Lock(), threading.Semaphore(a.concurrency or sum(ln.par for ln in lanes) or 1)
    run_why = {"why": None}; cut = []
    def stop_run(why):
        if not run_why["why"]: run_why["why"] = why
        stop.set(); print(f"STOP ({why}): finishing calls in flight, nothing new starts", flush=True)
    for sg in (signal.SIGTERM, signal.SIGINT): signal.signal(sg, lambda *_: stop_run("signal"))
    timer = threading.Timer(wall_min * 60, lambda: stop_run(f"wall {wall_min:g} min")) if wall_min else None
    if timer: timer.daemon = True; timer.start()
    table = MODELS + [m for m in models if m[0] not in {x[0] for x in MODELS}]
    meta.update(cap_usd=run_budget.cap, prompts=len(prompts), models=[dict(id=m[0], provider=m[1], parallel=m[2], temperature=m[3], max_out=m[4]) for m in table], arms=arms, samples=a.samples)   # the record shows the latest segment's settings
    seg = {"start": T0, "validator": VF.ref(), "cap_usd": run_budget.cap, "lane_cap_usd": a.lane_cap, "wall_min": wall_min, "lane_wall_min": a.lane_wall_min, "concurrency": a.concurrency, "arms": arms, "b_models": bmodels, "samples": a.samples,
           "lanes": [ln.key for ln in lanes], "parallel": {ln.key: ln.par for ln in lanes}}
    meta.setdefault("segments", []).append(seg); json.dump(meta, open(meta_p, "w"), indent=1)

    def log(e):
        with wlock:
            open(evp, "a").write(json.dumps(e, ensure_ascii=False) + "\n")
            state = "ERROR  " if e.get("error") else "VALID" if e.get("valid") else "invalid"
            print(f"{time.time() - T0:7.1f}s {e['model'][:22]:22s} {e['arm']} s{e['sample']} {e['prompt_id']:8s} a{e['attempt']} {state} in {e.get('tin', 0):5d} out {e.get('tout', 0):5d} "
                  f"{e.get('ms', 0) / 1000:5.1f}s tft {str(e.get('tft_ms', '-')):>6s} ${e.get('usd', 0):.4f}  run ${run_budget.spent:.3f}", flush=True)

    def finish_meta():
        seg.update(end=time.time(), stopped_by=run_why["why"], lanes={ln.key: ln.record() for ln in lanes}, cut=cut)
        meta.update(lanes={ln.key: ln.record() for ln in lanes}, cut=cut, spent_usd_est=round(run_budget.spent, 4), stopped_by=run_why["why"])
        with wlock: json.dump(meta, open(meta_p, "w"), indent=1)

    def task(ln, p, s):
        pid = p["prompt_id"]; rows = sorted((e for e in done.get((ln.mid, ln.arm, pid, s), []) if not e.get("error")), key=lambda e: (e["attempt"], e["model"] == "autofix"))
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["prompt"]}]
        k = seq = 0; body = None; nxt = "model"; tried = False
        for e in rows:                                    # resume: replay the recorded chain into the conversation (an errored call is not a step; it is retried)
            seq = e.get("seq", seq + 1); path = f"{out}/{e['file']}" if e.get("file") else f"{out}/x3d/{slug(ln.mid)}/{pid}_a{e['attempt']}.x3d"
            if e["model"] != "autofix": k = e["attempt"]; body = open(path).read(); msgs.append({"role": "assistant", "content": body})
            elif os.path.exists(path): body = open(path).read()
            if e.get("valid") or (e["model"] != "autofix" and k >= MAX_ATTEMPTS): return
            if e.get("repair_msg"): msgs.append({"role": "user", "content": e["repair_msg"]})
        if rows: nxt = "autofix" if (ln.arm == "B" and rows[-1]["model"] != "autofix" and rows[-1]["attempt"] == 1) else "model"
        base = {"run": os.path.basename(os.path.abspath(out)), "lane": ln.mid, "arm": ln.arm, "sample": s, "prompt_id": pid, "category": p["category"]}
        def cut_by(why=None):
            why = why or (("lane: " + ln.why) if ln.why else run_why["why"] or "stop")
            if seq or tried: cut.append({**{x: base[x] for x in ("lane", "arm", "sample", "prompt_id")}, "after_attempt": k, "after_seq": seq, "by": why}); ln.n["cut"] += 1      # a chain with only failed calls is cut, not unstarted
            else: ln.n["not_started"] += 1
        while True:
            if stop.is_set() or ln.stop.is_set(): return cut_by()
            if ln.wall and time.time() - T0 > ln.wall: ln.halt(f"lane wall {ln.wall / 60:g} min reached"); continue
            if nxt == "autofix":                          # arm B: the fork's deterministic repair before any repair call
                seq += 1; t0 = time.time(); f = VF.autofix(body); t1 = time.time(); fixed = f["fixed"] or body
                rel = f"x3d/{slug(ln.mid)}/{pid}_{ln.arm}{s}_a{k}f.x3d"; open(f"{out}/{rel}", "w").write(fixed)
                v0 = time.time(); v = VF.validate(fixed); v1 = time.time()
                ev = {**base, "model": "autofix", "agent": VF.agent(), "provider": "fork", "attempt": k, "seq": seq, "file": rel, "t0": round(t0, 3), "t1": round(t1, 3), "v0": round(v0, 3), "v1": round(v1, 3), "ms": f["ms"],
                      "tin": 0, "tout": 0, "usd": 0.0, "finish": "autofix", "sha": hashlib.sha256(fixed.encode()).hexdigest(), "chars": len(fixed), "bytes_in": len(body.encode()), "bytes_out": len(fixed.encode()),
                      "fix_changes": f["changes"], "fix_kinds": f["kinds"], "fix_unfixable": f["unfixable"], "fix_error": f["error"], "valid": v["valid"], "xsd_valid": v["xsd_valid"], "xsd_errors": v["xsd_errors"],
                      "sem_errors": v["sem_errors"], "fixes": v["fixes"], "v_ms": v["ms"], "constraints_ok": check_constraints(fixed, p["constraints"])}
                if not v["valid"]:
                    ev["repair_msg"] = REPAIR_AUTOFIX.format(n=len(f["changes"]), changes="; ".join(f["changes"]) or "none", body=fixed, xsd="\n".join(v["xsd_errors"]) or "none", sem="\n".join(v["sem_errors"] + v["fixes"]) or "none") if f["fixed"] else VF.repair_text(REPAIR, v)
                log(ev)
                if v["valid"]: ln.n["done"] += 1; return
                msgs.append({"role": "user", "content": ev["repair_msg"]}); body = fixed; nxt = "model"; continue
            k += 1; seq += 1; ntry = 0; r = None
            while r is None:                              # one model attempt, with the lane's own backoff on rate-limit and gateway failures
                if stop.is_set() or ln.stop.is_set(): k -= 1; seq -= 1; return cut_by()
                ntry += 1; tc = time.time(); tried = True
                try:
                    with sem: tc = time.time(); r = call(ln.budget, ln.prov, ln.mid, msgs, "live", max_out=ln.max_out, temp=ln.temp, rate_retry=False, prompt_id=pid, attempt=k)
                except BudgetStop as e:
                    if e.scope == "run": stop_run("cap: " + str(e))
                    else: ln.halt("cap: " + str(e))
                except CallError as e:
                    ln.n["failed"] += 1; ev = {**base, "model": ln.mid, "provider": ln.prov, "attempt": k, "seq": seq, "try": ntry, "t0": round(tc, 3), "t1": round(time.time(), 3), "ms": int((time.time() - tc) * 1000), "error": str(e)[:200], "status": e.status}
                    if e.status in RATE:
                        n = ln.rate_fail()
                        if n >= MAX_RATE_FAILS: log(ev); ln.halt(f"{n} consecutive rate-limit/gateway failures, last: {str(e)[:60]}"); continue
                        ev["backoff_s"] = BACKOFF[min(n - 1, len(BACKOFF) - 1)]; log(ev); time.sleep(ev["backoff_s"]); continue
                    log(ev)
                    if "insufficient_quota" in str(e):
                        for o in lanes:
                            if o.mid == ln.mid: o.halt("provider account refused the call (insufficient_quota)")
                    k -= 1; seq -= 1; return cut_by("error: " + str(e)[:80])        # another error ends the chain for now; a resume retries this attempt
            ln.succeeded(); ln.n["calls"] += 1
            x3d = strip_x3d(r["text"]); os.makedirs(f"{out}/x3d/{slug(ln.mid)}", exist_ok=True)
            rel = f"x3d/{slug(ln.mid)}/{pid}_{ln.arm}{s}_a{k}.x3d"; open(f"{out}/{rel}", "w").write(x3d)
            v0 = time.time(); v = VF.validate(x3d); v1 = time.time()
            ev = {**base, "model": ln.mid, "provider": ln.prov, "attempt": k, "seq": seq, "file": rel, "t0": round(r["t0"], 3), "t1": round(r["t1"], 3), "v0": round(v0, 3), "v1": round(v1, 3), "ms": r["ms"], "tft_ms": r["tft_ms"], "stream": r["stream"],
                  "tin": r["tin"], "tout": r["tout"], "usd": round(r["usd"], 6), "finish": r["finish"], "sha": hashlib.sha256(x3d.encode()).hexdigest(), "chars": len(x3d), "valid": v["valid"], "xsd_valid": v["xsd_valid"],
                  "xsd_errors": v["xsd_errors"], "sem_errors": v["sem_errors"], "fixes": v["fixes"], "v_ms": v["ms"], "constraints_ok": check_constraints(x3d, p["constraints"])}
            if not v["valid"]:
                if ln.arm == "B" and k == 1: nxt = "autofix"          # the report goes to the fixer first; this row carries no repair message
                elif k < MAX_ATTEMPTS: ev["repair_msg"] = VF.repair_text(REPAIR, v)
            log(ev)
            if v["valid"] or k >= MAX_ATTEMPTS: ln.n["done"] += 1; return
            msgs.append({"role": "assistant", "content": x3d}); body = x3d
            if nxt != "autofix": msgs.append({"role": "user", "content": ev["repair_msg"]})

    exs = {ln.key: cf.ThreadPoolExecutor(ln.par, thread_name_prefix=slug(ln.key)) for ln in lanes}      # one pool per lane
    futs = [exs[ln.key].submit(task, ln, p, s) for ln in lanes for s in range(a.samples) for p in prompts]
    print(f"{len(lanes)} lane(s) x {len(prompts)} prompt(s) x {a.samples} sample(s) = {len(futs)} chains; validator {VF.ref()}; run cap ${run_budget.cap:.2f}, lane cap ${lanes[0].budget.cap if lanes else 0:.2f}; in flight <= {a.concurrency or sum(ln.par for ln in lanes)}", flush=True)
    for f in cf.as_completed(futs):
        try: f.result()
        except Exception as e: print("TASK EXCEPTION", repr(e)[:300], flush=True)
    for ex in exs.values(): ex.shutdown()
    if timer: timer.cancel()
    finish_meta()
    print(f"done in {time.time() - T0:.0f}s, run spend ${run_budget.spent:.4f}, stopped by: {run_why['why']}, lanes stopped: {sum(1 for ln in lanes if ln.why)}, chains cut: {len(cut)}", flush=True)


if __name__ == "__main__":
    main()
