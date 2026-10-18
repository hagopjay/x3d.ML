"""Spend ledger and hard cap for the recorded live run (Tether Firehose 3).
Every paid call, including probes and failed calls, is appended to ledger.jsonl BEFORE its result is used; the cap is checked before a call is made, with the call's worst case
reserved so parallel workers cannot overshoot it. Prices are list prices per 1M tokens as used in the project's earlier ledgers (estimates from reported token usage, not an invoice);
NVIDIA calls run on free trial credits and cost 0 here. Usage: python3 ledger.py [--md] [--cap USD]   (summary, or the markdown table for the project folder; --cap names the hard stop the run used)."""
import json, os, sys, threading, time, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("LIVE_LEDGER", os.path.join(HERE, "ledger.jsonl"))
CAP_USD = float(os.environ.get("LIVE_CAP_USD", "8.00"))      # hard stop; the thread's grant is $10, the rest is slack for estimate error and the media step
PRICES = {   # model: (USD per 1M input tokens, USD per 1M output tokens incl. thinking tokens)
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gpt-6.1-sol": (2.00, 10.00),
}
FREE = (0.0, 0.0)      # NVIDIA trial credits and anything unlisted that runs on credits; unlisted paid models are refused (see price())


class BudgetStop(Exception):
    pass


def price(model, provider):
    if model in PRICES:
        return PRICES[model]
    if provider == "nvidia":
        return FREE
    raise BudgetStop(f"no price for {model}; add it to PRICES before calling")


class Budget:
    def __init__(self, cap=CAP_USD, path=LEDGER):
        self.cap, self.path, self.lock, self.reserved = cap, path, threading.Lock(), 0.0
        self.spent = sum(r.get("usd", 0.0) for r in read(path))

    def reserve(self, model, provider, tin_est, max_out):
        pi, po = price(model, provider)
        worst = (tin_est * pi + max_out * po) / 1e6
        with self.lock:
            if self.spent + self.reserved + worst > self.cap:
                raise BudgetStop(f"cap {self.cap:.2f} USD: spent {self.spent:.4f} + in flight {self.reserved:.4f} + this call's worst case {worst:.4f}")
            self.reserved += worst
        return worst

    def charge(self, worst, model, provider, tag, tin, tout, **extra):
        pi, po = price(model, provider)
        usd = (tin * pi + tout * po) / 1e6
        row = {"t": round(time.time(), 3), "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tag": tag, "model": model, "provider": provider,
               "in": tin, "out": tout, "usd": round(usd, 6), **extra}
        with self.lock:
            self.reserved = max(0.0, self.reserved - worst)
            self.spent += usd
            with open(self.path, "a") as f:
                f.write(json.dumps(row) + "\n")
        return usd


def read(path=LEDGER):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def summary(rows):
    by = collections.OrderedDict()
    for r in rows:
        k = (r["tag"], r["model"], r["provider"]); b = by.setdefault(k, {"calls": 0, "in": 0, "out": 0, "usd": 0.0, "first": r["utc"], "last": r["utc"]})
        b["calls"] += 1; b["in"] += r["in"]; b["out"] += r["out"]; b["usd"] += r["usd"]; b["last"] = r["utc"]
    return by


def markdown(rows, cap=CAP_USD):
    s = summary(rows); tot = sum(b["usd"] for b in s.values())
    out = ["# Cost ledger: Traceability thread, AI-service grant of 10 USD (19:45Z 17 Oct 2026)", "",
           "Estimates from reported token usage at list prices per 1M tokens (in/out): " + "; ".join(f"{m} {a}/{b}" for m, (a, b) in PRICES.items()) + "; NVIDIA calls on free trial credits count 0. Not an invoice.",
           f"Hard stop in code: {cap:.2f} USD (set per run with `--cap`). Machine-readable source: `demo/live/ledger.jsonl` (one line per call, appended before the result is used).", "",
           "| batch | service | model | calls | tokens in | tokens out | est. USD | first | last |", "|---|---|---|---:|---:|---:|---:|---|---|"]
    for (tag, model, prov), b in s.items():
        out.append(f"| {tag} | {prov} | {model} | {b['calls']} | {b['in']:,} | {b['out']:,} | {b['usd']:.4f} | {b['first']} | {b['last']} |")
    out += ["", f"**Total estimated spend: {tot:.4f} USD of the 10 USD grant (hard stop {cap:.2f}).**", ""]
    return "\n".join(out)


if __name__ == "__main__":
    rows = read()
    cap = float(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else CAP_USD
    print(markdown(rows, cap) if "--md" in sys.argv else json.dumps({"calls": len(rows), "usd": round(sum(r["usd"] for r in rows), 4)}))
