"""EVENTS for Tether Firehose 4 (SPEC section 8 step 1; drawn by S6 "the run as film" and quoted by S16 "Ask the files").
Reads the 17 Oct run (runs/live-2026-10-17/events.jsonl, run.json, notes.json), the spend ledger (demo/live/ledger.jsonl) and the page's live.json (demo/data/live.json,
read only to prove the run clock here is the one the page already uses). Writes demo/v4/data/events.json:
  failed[62]   {m, p, k, t0, t1, kind}   the calls that errored, on the run clock; kind in {429, 502, credit, other} computed from the error text at build; the raw text NEVER ships
                                        (it can carry a provider function id and an account string)
  cut[17]      {m, p, k, calls, t1, reason}  chains the run stopped before they finished (reason "cap" or "time box", from notes.json / run.json lane stop reasons)
  probes[46]   {m, dt, utc, ok, code, ms}  the ledger's probe rows (model roster checks), dt = seconds from the 17 Oct run start (negative = before it), error text reduced to an HTTP code
  collapse[]   [[from_s, to_s, removed_s]] the idle gaps the run clock skips, computed exactly as demo/build_live.py does (MIN_GAP 30 s, GAP 3 s kept), exposed as LM.collapse
  creditStop   {t, utc, refused}           the first insufficient-credits row on the run clock and how many calls it refused
  reconcile    the ledger against the page (demo/live/reconcile.py's 464 / 358 / 106), broken down by why a call is not on the page
Usage: python3 demo/v4/build/build_events.py [out.json]      (no network, no spend; prints the reconciliation table)"""
import collections, datetime, json, os, re, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUN = os.path.join(ROOT, "runs/live-2026-10-17")
OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(ROOT, "demo/v4/data/events.json")
GAP, MIN_GAP = 3.0, 30.0          # the same constants as demo/build_live.py: a stretch > MIN_GAP s with no call in flight is an idle gap, kept as GAP s on the run clock
WINDOW = 600.0                    # ledger rows this many seconds around the run count as the run's (the probes right before it are listed separately)
CREDIT = re.compile(r"insufficient_quota|no credits|insuffic", re.I)


def kind_of(err):
    """Reduce an error string to a kind. Only the kind leaves this script. The 62 failed calls use 429 / 502 / credit; the finer kinds appear in the reconciliation only."""
    s = (err or "").strip()
    if CREDIT.search(s): return "credit"
    if s.startswith("429"): return "429"
    if s.startswith("502"): return "502"
    if "exceeded" in s and "s" in s: return "timeout"
    if re.match(r"(ChunkedEncodingError|ConnectionError|ReadTimeout)", s): return "connection"
    return "other"


def code_of(err):
    """A probe outcome: the leading HTTP status, 'timeout', or 'other'."""
    s = (err or "").strip()
    m = re.match(r"(\d{3})\b", s)
    return m.group(1) if m else ("timeout" if "exceeded" in s else "other")


meta = json.load(open(RUN + "/run.json"))
notes = json.load(open(RUN + "/notes.json")) if os.path.exists(RUN + "/notes.json") else {}
ev = [json.loads(l) for l in open(RUN + "/events.jsonl") if l.strip()]
errors = [e for e in ev if e.get("error")]; good = [e for e in ev if not e.get("error")]
live = json.load(open(os.path.join(ROOT, "demo/data/live.json")))
page = {(i["m"], i["p"]): i for i in live["items"]}
ledger = [json.loads(l) for l in open(os.path.join(ROOT, "demo/live/ledger.jsonl")) if l.strip()]
T0, T1 = meta["t_start"], meta["segments"][-1]["end"]

# ---- run clock: the page's chains' (t0, v1) intervals, as build_live.py built live.json (no --keep-failures), so the failed rows land where the page's bars are
by = collections.defaultdict(list)
for e in good: by[(e["model"], e["prompt_id"])].append(e)
for k in by: by[k].sort(key=lambda e: e["attempt"])
iv = sorted((e["t0"], e["v1"]) for k in page for e in by[k])
t_min = iv[0][0]; shifts = []; removed = 0.0; prev_end = None; collapse = []
for a, b in iv:
    if prev_end is not None and a - prev_end > MIN_GAP:
        removed += (a - prev_end) - GAP; shifts.append((a, removed))
        collapse.append([round(prev_end - t_min, 2), round(a - t_min, 2), round((a - prev_end) - GAP, 2)])     # [gap start, gap end] in real seconds from the run start, seconds removed
    prev_end = b if prev_end is None else max(prev_end, b)


def clk(t):
    r = 0.0
    for start, cum in shifts:
        if t >= start - 1e-6: r = cum
    return round(t - t_min - r, 2)


# prove the clock: every one of the page's 358 attempts must land on its own A[].t0
drift = [(k, e["attempt"], clk(e["t0"]), a["t0"]) for k, it in page.items() for e, a in zip(by[k], it["A"]) if abs(clk(e["t0"]) - a["t0"]) > 0.011]
assert not drift, f"run clock differs from live.json on {len(drift)} attempts: {drift[:3]}"
assert abs(removed - live["meta"]["idle_collapsed_s"]) < 0.1 and len(shifts) == live["meta"]["gaps"], (removed, len(shifts), live["meta"])

# ---- the 62 failed calls, reduced
failed = [{"m": e["model"], "p": e["prompt_id"], "k": e["attempt"], "t0": clk(e["t0"]), "t1": clk(e["t1"]), "kind": kind_of(e["error"])} for e in sorted(errors, key=lambda e: e["t0"])]
assert all(f["kind"] in ("429", "502", "credit") for f in failed), collections.Counter(f["kind"] for f in failed)

# ---- the 17 cut chains: good calls in events.jsonl whose chain never finished (not valid, fewer than 3 attempts) and so is not on the page
REASON = lambda why: "cap" if "cap" in (why or "") else "time box" if "time-box" in (why or "") or "time box" in (why or "") else "credit" if "credit" in (why or "") else "stopped"
cut = []
for k, calls in by.items():
    if k in page: continue
    assert not calls[-1]["valid"] and max(e["attempt"] for e in calls) < meta["max_attempts"], k   # anything finished would be on the page
    cut.append({"m": k[0], "p": k[1], "k": max(e["attempt"] for e in calls), "calls": len(calls), "t1": clk(max(e["v1"] for e in calls)), "reason": REASON(notes.get(k[0]))})
cut.sort(key=lambda c: c["t1"])
# the cut chains' bodies (recorded under runs/live-2026-10-17/x3d/<model_dir>/<prompt>_a<k>.x3d) ride with the rows so the page holds every body the
# canary names (358 live + 174 replay + 25 cut + 1 ledger = 558); key = the renders / canary key shape `<model_dir>/<prompt>_a<k>.x3d`
n_bodies = 0
for c in cut:
    mdir = c["m"].replace("/", "_"); c["bodies"] = []
    for k in range(1, c["k"] + 1):
        f = os.path.join(RUN, "x3d", mdir, f"{c['p']}_a{k}.x3d")
        if os.path.isfile(f): c["bodies"].append({"k": f"{mdir}/{c['p']}_a{k}.x3d", "xml": open(f, encoding="utf-8").read()}); n_bodies += 1
    assert len(c["bodies"]) == c["calls"], (c["m"], c["p"], c["calls"], len(c["bodies"]))

# ---- probes (every ledger probe row; the 24 Oct roster probes sit far right of the run), error text reduced to a code
probes = [{"m": r["model"], "dt": round(r["t"] - T0, 1), "utc": r["utc"], "ok": not r.get("err"), "code": None if not r.get("err") else code_of(r["err"]), "ms": r.get("ms")}
          for r in ledger if r["tag"] == "probe"]

# ---- credit stop
cred = [f for f in failed if f["kind"] == "credit"]
first = min(errors, key=lambda e: e["t0"] if CREDIT.search(e["error"]) else float("inf"))
creditStop = {"t": clk(first["t0"]), "elapsed": round(first["t0"] - t_min, 1), "utc": datetime.datetime.fromtimestamp(first["t0"], datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "refused": len(cred), "m": first["model"]}      # t on the run clock (idle gaps collapsed), elapsed in real seconds since the first call

# ---- reconciliation against the ledger (reconcile.py: ledger live calls vs calls on the page), broken down
led = [r for r in ledger if r["tag"] == "live" and T0 - WINDOW <= r["t"] <= T1 + WINDOW]
lok = [r for r in led if not r.get("err")]; lerr = [r for r in led if r.get("err")]
key3 = lambda x, p="prompt_id", a="attempt": (x["model"], x.get(p), x.get(a))
assert collections.Counter(map(key3, lok)) == collections.Counter(map(key3, good)), "ledger charge rows and good events differ"
extra = collections.Counter(map(key3, lerr)) - collections.Counter(map(key3, errors))         # ledger error rows with no events row: retries inside the call layer
assert not (collections.Counter(map(key3, errors)) - collections.Counter(map(key3, lerr))), "an events.jsonl failure is missing from the ledger"
retry_kinds = collections.Counter()
for r in lerr:
    if extra[key3(r)] > 0: extra[key3(r)] -= 1; retry_kinds[kind_of(r["err"])] += 1
on_page = sum(len(i["A"]) for i in live["items"]); in_cut = sum(c["calls"] for c in cut)
usd_led = sum(r["usd"] for r in led); usd_page = sum(a["u"] for i in live["items"] for a in i["A"])
per = []
for m in [x["id"] for x in meta["models"]]:
    l = [r for r in led if r["model"] == m]; p = [a for i in live["items"] if i["m"] == m for a in i["A"]]
    per.append({"m": m, "ledger": len(l), "page": len(p), "not": len(l) - len(p), "failed": sum(1 for f in failed if f["m"] == m), "cut_calls": sum(c["calls"] for c in cut if c["m"] == m),
                "retries": sum(1 for r in lerr if r["model"] == m) - sum(1 for f in failed if f["m"] == m), "usd_ledger": round(sum(r["usd"] for r in l), 4), "usd_page": round(sum(a["u"] for a in p), 4)})
reconcile = {"ledger_calls": len(led), "on_page": on_page, "not_on_page": len(led) - on_page, "failed": len(failed), "cut_chains": len(cut), "cut_calls": in_cut,
             "retries_in_call_layer": sum(retry_kinds.values()), "retry_kinds": dict(retry_kinds), "probes_in_window": sum(1 for r in ledger if r["tag"] == "probe" and T0 - WINDOW <= r["t"] <= T1 + WINDOW),
             "probes_total": len(probes), "killed_in_flight_rows": sum(1 for r in ledger if r["tag"].startswith("killed")), "usd_ledger": round(usd_led, 4), "usd_page": round(usd_page, 4), "per": per,
             "rule": "ledger calls = tag 'live' rows within 600 s of the 17 Oct run; on the page = attempts in live.json; not on the page = failed calls (events.jsonl) + calls of cut chains + retries the call layer made before logging one event"}
assert len(led) - on_page == len(failed) + in_cut + sum(retry_kinds.values()), reconcile

out = {"run": "live-2026-10-17", "validator": "fork@eb4b4b4", "failed": failed, "cut": cut, "probes": probes, "collapse": collapse, "creditStop": creditStop,
       "kinds": dict(collections.Counter(f["kind"] for f in failed)), "cut_reasons": dict(collections.Counter(c["reason"] for c in cut)),
       "collapse_rule": f"intervals (t0, v1) of the {on_page} attempts on the page, sorted; a stretch with nothing in flight longer than {MIN_GAP:.0f} s is cut to {GAP:.0f} s; identical to demo/build_live.py",
       "idle_collapsed_s": round(removed, 1), "t_total": live["meta"]["t_total"], "reconcile": reconcile}
out["cut_bodies"] = n_bodies; out["cut_bodies_empty"] = sum(1 for c in cut for b in c["bodies"] if not b["xml"].strip())   # recorded empty answers (0 chars): in the canary set, nothing to chain
json.dump(out, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)
s = open(OUT).read()
assert not re.search(r"Function '|account '|insufficient_quota|platform\.openai|Too Many Requests|upstream request", s), "an error string leaked into events.json"

print(f"failed {len(failed)} {out['kinds']} · cut chains {len(cut)} ({in_cut} calls) {out['cut_reasons']} · probes {len(probes)} · idle gaps {len(collapse)} ({removed:.1f} s removed) · credit stop {creditStop}")
head = ["model", "ledger", "page", "not", "failed", "cut calls", "retries", "ledger USD", "page USD"]
rows = [[p["m"], p["ledger"], p["page"], p["not"], p["failed"], p["cut_calls"], p["retries"], f"{p['usd_ledger']:.4f}", f"{p['usd_page']:.4f}"] for p in per]
rows.append(["all", len(led), on_page, len(led) - on_page, len(failed), in_cut, sum(retry_kinds.values()), f"{usd_led:.4f}", f"{usd_page:.4f}"])
w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
for r in rows: print("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))
print(f"retries inside the call layer by kind {dict(retry_kinds)}; probes in the run window {reconcile['probes_in_window']}, killed-in-flight estimate rows {reconcile['killed_in_flight_rows']}")
print(OUT, os.path.getsize(OUT), "B")
