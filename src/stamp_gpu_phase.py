"""Stamp the cached GPU-phase scenes (11 Oct 2026, 3 open models x oneshot/grounded) with real x3dprov records.
Facts come only from results/*-runs.jsonl, *-results.jsonl and prompts.jsonl; nothing is invented.
Only the FINAL accepted attempt's body is cached locally; earlier attempts are summarised (bodies sit in the bucket).
Usage: python3 stamp_gpu_phase.py <outdir>"""
import sys, os, json, hashlib, collections, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import x3dprov as P
import demo as D                       # validate() = fork eb4b4b4
G = "/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11"
prompts = {json.loads(l)["prompt_id"]: json.loads(l) for l in open(G + "/prompts.jsonl")}
out = sys.argv[1]; rows = []
for model in ("qwen3-8b", "qwen2.5-coder-14b-awq", "gpt-oss-20b"):
    runs = {r["run_id"]: r for r in map(json.loads, open(f"{G}/results/{model}-runs.jsonl"))}
    res = collections.defaultdict(list)
    for r in map(json.loads, open(f"{G}/results/{model}-results.jsonl")): res[(r["run_id"], r["prompt_id"])].append(r)
    for (rid, pid), atts in sorted(res.items()):
        run = runs[rid]; mode = "grounded" if run["grounded"] else "oneshot"
        path = f"{G}/results/x3d/{model}/{mode}/{pid}.x3d"
        if not os.path.exists(path): rows.append({"model": model, "mode": mode, "prompt": pid, "status": "no-local-body"}); continue
        atts.sort(key=lambda a: a["attempt"]); fin = atts[-1]; xml = open(path, encoding="utf-8").read()
        gen = {"op": "generate", "model": model, "provider": "vllm_l4", "run_id": rid, "hardware": run["hardware"],
               "condition": "report_repair" if run["grounded"] else "oneshot", "attempts_total": len(atts), "final_attempt": fin["attempt"],
               "prompt_id": pid, "prompt_sha256": hashlib.sha256(prompts[pid]["prompt"].encode()).hexdigest(),
               "temperature": 0.4, "max_tokens": 8000, "tokens_in": sum(a["tokens_in"] for a in atts), "tokens_out": sum(a["tokens_out"] for a in atts),
               "latency_ms": sum(a["latency_ms"] for a in atts), "run_cost_usd": run["cost_usd"],
               "earlier_attempts": [{"attempt": a["attempt"], "xsd_valid": a["xsd_valid"], "semantic_valid": a["semantic_valid"]} for a in atts[:-1]],
               "bodies_of_earlier_attempts": "bucket only, not hashed", "input_sha256": "none"}
        hist = {"op": "validate", "validator": "x3d-mcp-svc (Cloud Run, as called 11 Oct)", "validator_ref": "unrecorded", "xsd_valid": fin["xsd_valid"],
                "semantic_valid": fin["semantic_valid"], "constraints_ok": fin["constraints_ok"], "verdict": "valid" if fin["xsd_valid"] and fin["semantic_valid"] else "invalid", "historical": True}
        x = P.add_step(xml, gen); x = P.add_step(x, hist); cur = D.validate(x); x = P.add_step(x, cur)
        os.makedirs(f"{out}/{model}/{mode}", exist_ok=True); open(f"{out}/{model}/{mode}/{pid}.x3d", "w").write(x)
        rows.append({"model": model, "mode": mode, "prompt": pid, "status": P.verify(x)["status"], "hist": hist["verdict"], "now": cur["verdict"], "now_codes": cur["semantic_error_codes"], "attempts": len(atts)})
json.dump(rows, open(out + "/stamp_summary.json", "w"), indent=1)
ok = [r for r in rows if r["status"] != "no-local-body"]
print(len(rows), "rows;", len(ok), "stamped;", collections.Counter(r["status"] for r in ok))
print("historical vs fork eb4b4b4:", collections.Counter((r["hist"], r["now"]) for r in ok))
for m in ("qwen3-8b", "qwen2.5-coder-14b-awq", "gpt-oss-20b"):
    for md in ("oneshot", "grounded"):
        s = [r for r in ok if r["model"] == m and r["mode"] == md]
        print(f"{m:24s}{md:9s}n={len(s):3d} hist_valid={sum(r['hist']=='valid' for r in s):3d} now_valid={sum(r['now']=='valid' for r in s):3d}")
