"""Roster probe for the NVIDIA lanes of a recorded live run (free tier through the project's credential-injecting proxy; no key in this file, no other provider is touched).
Step 1: GET /v1/models -> <out>/models.json (the ids the account can see). Step 2: one tiny streaming chat call per candidate (max_tokens 24, 60 s wall), each ledgered with tag
"probe" before its result is used, -> <out>/probes.jsonl and <out>/ROSTER.md (status, latency, time to first token, output tokens, error text). Probes run one at a time so the
free tier's rate limit is not tripped by the probe itself.
Usage: python3 probe_nvidia.py <out_dir> [--list-only] [--models id,id] [--cap USD] [--tries N] [--force]"""
import argparse, json, os, sys, time, requests
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ledger
from llmcall import call, CallError, CA

URL = "https://integrate.api.nvidia.com/v1"
PROMPT = "Reply with the single word: ready."


def list_models(out):
    r = requests.get(URL + "/models", timeout=60, verify=CA)
    r.raise_for_status()
    ids = sorted(m["id"] for m in r.json().get("data", []))
    json.dump({"fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": r.status_code, "ids": ids, "raw": r.json()}, open(out + "/models.json", "w"), indent=1)
    return ids


def probe(budget, mid, tries):
    t = time.time(); row = {"id": mid, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        r = call(budget, "nvidia", mid, [{"role": "user", "content": PROMPT}], "probe", max_out=24, temp=None, tries=tries, max_wall=60)
        row.update(status="ok", ms=r["ms"], tft_ms=r["tft_ms"], tin=r["tin"], tout=r["tout"], finish=r["finish"], text=r["text"][:80], est=not (r["tin"] or r["tout"]))
    except (CallError, ledger.BudgetStop) as e:
        row.update(status="error", ms=int((time.time() - t) * 1000), http=getattr(e, "status", None), error=str(e)[:300])
    return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--list-only", action="store_true"); ap.add_argument("--models"); ap.add_argument("--cap", type=float, default=0.05); ap.add_argument("--tries", type=int, default=2); ap.add_argument("--force", action="store_true", help="probe ids that are not in /v1/models too (a listing can be incomplete, a listed id can still 404)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    ids = list_models(a.out); print(f"{len(ids)} model ids -> {a.out}/models.json", flush=True)
    if a.list_only:
        print("\n".join(ids)); return
    want = a.models.split(",") if a.models else ids
    budget = ledger.Budget(cap=a.cap, since=time.time(), name="probe")
    rows = []
    with open(a.out + "/probes.jsonl", "a") as f:
        for mid in want:
            if mid not in ids and not a.force: row = {"id": mid, "status": "not listed", "ms": 0, "error": "not in /v1/models"}
            else: row = probe(budget, mid, a.tries); row["listed"] = mid in ids
            rows.append(row); f.write(json.dumps(row) + "\n"); f.flush()
            print(f"{row['status']:10s} {row.get('ms', 0) / 1000:6.1f}s tft {str(row.get('tft_ms')):>6s} out {str(row.get('tout', '')):>4s} {mid}  {row.get('error') or row.get('text', '')[:40]!r}", flush=True)
    lines = ["# NVIDIA roster probe " + time.strftime("%Y-%m-%d %H:%MZ", time.gmtime()), "", f"`GET {URL}/models` listed {len(ids)} ids (models.json). One chat call per candidate: `{PROMPT}`, max_tokens 24, 60 s wall, ledger tag `probe` (free tier, 0 USD).", "",
             "| model | listed | status | latency | first token | tokens out | finish | error / text |", "|---|---|---|---:|---:|---:|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {'yes' if r.get('listed', r['status'] != 'not listed') else 'no'} | {r['status']} | {r.get('ms', 0) / 1000:.1f} s | {r.get('tft_ms', '')} | {r.get('tout', '')} | {r.get('finish', '') or ''} | {(r.get('error') or r.get('text', '')).replace('|', '/')[:90]} |")
    open(a.out + "/ROSTER.md", "w").write("\n".join(lines) + "\n"); print(a.out + "/ROSTER.md")


if __name__ == "__main__":
    main()
