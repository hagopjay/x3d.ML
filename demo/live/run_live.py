#!/usr/bin/env python3
"""Recorded live run for Tether Firehose 3. Every prompt x every model goes through the Tether loop with REAL calls: generate, validate on the x3d_mcp fork, and if the validator
rejects the scene send it its own report and ask again (up to 3 attempts, the same loop and prompts as the 11 Oct GPU-phase 'grounded' runs, plus 8 showpiece prompts).
Every call is ledgered (ledger.py) and the run stops itself at the cap. Resumable: events.jsonl is append-only and a re-run continues unfinished tasks.
Each model has its own worker pool (a slow model never holds up a fast one) and walks the prompts in an interleaved order, bench and showpiece prompts alternating, so a run that is stopped early still covers both.
SIGTERM or --minutes N stops gracefully: no new call is started, calls in flight finish and are ledgered.
Usage: GCP_PROJECT=<vertex project> python3 run_live.py <out_dir> [--prompts id,id] [--models id,id] [--cap USD] [--minutes N]
Writes <out_dir>/events.jsonl (one row per attempt), <out_dir>/x3d/<model>/<prompt>_a<k>.x3d, <out_dir>/run.json."""
import argparse, concurrent.futures as cf, hashlib, json, os, signal, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ledger
from ledger import Budget, BudgetStop
from llmcall import call, strip_x3d, CallError
import validate_fork as VF
from prompts_sys import SYSTEM, REPAIR

MODELS = [   # id, provider, parallel calls, temperature (None = the API's default), max output tokens (thinking included)
    ("gemini-3.8-flash", "vertex", 8, 0.4, 12000),
    ("gemini-3.1-pro-preview", "vertex", 4, None, 12000),
    ("gpt-6.1-sol", "openai", 4, None, 12000),
    ("z-ai/glm-5.3", "nvidia", 8, 0.4, 8000),
    ("nvidia/nemotron-3-super-120b-a12b", "nvidia", 3, 0.4, 8000),
]
MAX_ATTEMPTS = 3
slug = lambda m: m.replace("/", "_")


def check_constraints(x3d, c):     # same as the 11 Oct harness
    ok = all(f"<{n}" in x3d for n in c.get("required_nodes", []))
    ok &= x3d.count(" USE=") >= c.get("min_use", 0)
    ok &= x3d.count(" DEF=") >= c.get("min_defs", 0)
    ok &= x3d.count("<ROUTE") >= c.get("min_routes", 0)
    ok &= x3d.count("<Transform") >= c.get("min_transforms", 0)
    return bool(ok)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--prompts"); ap.add_argument("--models"); ap.add_argument("--cap", type=float); ap.add_argument("--minutes", type=float)
    a = ap.parse_args()
    out = a.out; os.makedirs(out + "/x3d", exist_ok=True)
    budget = Budget(cap=a.cap if a.cap else ledger.CAP_USD)
    prompts = [json.loads(l) for l in open(HERE + "/prompts_live.jsonl") if l.strip()]
    if a.prompts: keep = a.prompts.split(","); prompts = [p for p in prompts if p["prompt_id"] in keep]
    sp = [p for p in prompts if p["prompt_id"].startswith("sp-")]; bench = [p for p in prompts if not p["prompt_id"].startswith("sp-")]
    prompts = [p for _, p in sorted([((i + .5) / len(bench), p) for i, p in enumerate(bench)] + [((i + .5) / len(sp), p) for i, p in enumerate(sp)], key=lambda t: t[0])]
    models = [m for m in MODELS if not a.models or m[0] in a.models.split(",")]
    evp = out + "/events.jsonl"; done = {}
    if os.path.exists(evp):
        for l in open(evp):
            e = json.loads(l); done.setdefault((e["model"], e["prompt_id"]), []).append(e)
    wlock, stop = threading.Lock(), threading.Event()
    dead = set()      # models whose account refused every call (no credits): their remaining tasks are skipped, not retried
    for sg in (signal.SIGTERM, signal.SIGINT): signal.signal(sg, lambda *_: (stop.set(), print("STOP requested: finishing calls in flight", flush=True)))
    if a.minutes: threading.Timer(a.minutes * 60, lambda: (stop.set(), print(f"STOP: --minutes {a.minutes} reached, finishing calls in flight", flush=True))).start()
    T0 = time.time(); meta_p = out + "/run.json"
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {"t_start": T0, "validator": VF.ref(), "cap_usd": budget.cap, "max_attempts": MAX_ATTEMPTS,
            "models": [dict(id=m[0], provider=m[1], parallel=m[2], temperature=m[3], max_out=m[4]) for m in MODELS], "prompts": len(prompts), "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12]}
    meta.update(cap_usd=budget.cap, prompts=len(prompts), models=[dict(id=m[0], provider=m[1], parallel=m[2], temperature=m[3], max_out=m[4]) for m in MODELS])   # the record shows the latest segment's settings
    meta.setdefault("segments", []).append({"start": T0, "cap_usd": budget.cap, "parallel": {m[0]: m[2] for m in MODELS}, "minutes": a.minutes or None})
    json.dump(meta, open(meta_p, "w"))

    def log(e):
        with wlock:
            open(evp, "a").write(json.dumps(e, ensure_ascii=False) + "\n")
            print(f"{time.time() - T0:7.1f}s {e['model'][:22]:22s} {e['prompt_id']:8s} a{e['attempt']} {'VALID' if e.get('valid') else 'invalid' if not e.get('error') else 'ERROR  '} "
                  f"in {e.get('tin', 0):5d} out {e.get('tout', 0):5d} {e.get('ms', 0) / 1000:5.1f}s ${e.get('usd', 0):.4f}  total ${budget.spent:.3f}", flush=True)

    def task(mcfg, p):
        mid, prov, _, temp, max_out = mcfg
        prev = sorted((e for e in done.get((mid, p["prompt_id"]), []) if not e.get("error")), key=lambda e: e["attempt"])    # an errored attempt is retried on resume (its row stays in the log)
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["prompt"]}]
        for e in prev:                                  # resume: replay earlier attempts into the conversation
            if e.get("valid") or e["attempt"] >= MAX_ATTEMPTS: return
            msgs += [{"role": "assistant", "content": open(f"{out}/x3d/{slug(mid)}/{p['prompt_id']}_a{e['attempt']}.x3d").read()}, {"role": "user", "content": e["repair_msg"]}]
        start = len(prev) + 1
        if True:
            for k in range(start, MAX_ATTEMPTS + 1):
                if stop.is_set() or mid in dead: return
                ev = {"run": os.path.basename(os.path.abspath(out)), "model": mid, "provider": prov, "prompt_id": p["prompt_id"], "category": p["category"], "attempt": k}
                try:
                    r = call(budget, prov, mid, msgs, "live", max_out=max_out, temp=temp, prompt_id=p["prompt_id"], attempt=k)
                except BudgetStop as e:
                    stop.set(); print("BUDGET STOP:", e, flush=True); return
                except CallError as e:
                    if "insufficient_quota" in str(e) and mid not in dead: dead.add(mid); print(f"MODEL STOPPED: {mid} has no credits left; its remaining tasks are skipped", flush=True)
                    log({**ev, "t0": time.time(), "t1": time.time(), "error": str(e)[:200]}); return
                x3d = strip_x3d(r["text"]); os.makedirs(f"{out}/x3d/{slug(mid)}", exist_ok=True)
                open(f"{out}/x3d/{slug(mid)}/{p['prompt_id']}_a{k}.x3d", "w").write(x3d)
                v0 = time.time(); v = VF.validate(x3d); v1 = time.time()
                ev.update({"t0": round(r["t0"], 3), "t1": round(r["t1"], 3), "v0": round(v0, 3), "v1": round(v1, 3), "ms": r["ms"], "tin": r["tin"], "tout": r["tout"], "usd": round(r["usd"], 6),
                           "finish": r["finish"], "sha": hashlib.sha256(x3d.encode()).hexdigest(), "chars": len(x3d), "valid": v["valid"], "xsd_valid": v["xsd_valid"],
                           "xsd_errors": v["xsd_errors"], "sem_errors": v["sem_errors"], "fixes": v["fixes"], "v_ms": v["ms"], "constraints_ok": check_constraints(x3d, p["constraints"])})
                if not v["valid"] and k < MAX_ATTEMPTS: ev["repair_msg"] = VF.repair_text(REPAIR, v)
                log(ev)
                if v["valid"]: return
                msgs += [{"role": "assistant", "content": x3d}, {"role": "user", "content": ev.get("repair_msg") or ""}]

    exs = {m[0]: cf.ThreadPoolExecutor(m[2], thread_name_prefix=slug(m[0])) for m in models}      # one pool per model
    futs = [exs[m[0]].submit(task, m, p) for m in models for p in prompts]
    for f in cf.as_completed(futs):
        try: f.result()
        except Exception as e: print("TASK EXCEPTION", repr(e)[:300], flush=True)
    for ex in exs.values(): ex.shutdown()
    meta["segments"][-1]["end"] = time.time(); meta["spent_usd_est"] = round(budget.spent, 4); json.dump(meta, open(meta_p, "w"))
    print(f"done in {time.time() - T0:.0f}s, ledger total ${budget.spent:.4f}, stopped by cap: {stop.is_set()}", flush=True)


if __name__ == "__main__":
    main()
