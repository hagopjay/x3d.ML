"""Spend ledger and hard caps for the recorded live runs (Tether Firehose 3 and 4).
Every paid call, including probes and failed calls, is appended to ledger.jsonl BEFORE its result is used; a cap is checked before a call is made, with the call's worst case
reserved so parallel workers cannot overshoot it. A Budget counts the rows it is told to (`since` a run's start, one `model`) and can chain to a `parent` cap (the run's total), so
each lane has its own cap and one lane reaching it never stops another. Prices are list prices per 1M tokens as used in the project's earlier ledgers (estimates from reported token
usage, not an invoice); NVIDIA calls run on free trial credits and cost 0 here. Usage: python3 ledger.py [--md] [--cap USD]   (summary, or the markdown table; --cap names the hard stop the run used)."""
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
    def __init__(self, msg, scope="run"):
        super().__init__(msg); self.scope = scope       # "run" for the whole run's cap, else the name of the lane whose own cap was reached


def price(model, provider):
    if model in PRICES:
        return PRICES[model]
    if provider == "nvidia":
        return FREE
    raise BudgetStop(f"no price for {model}; add it to PRICES before calling")


_flock = threading.Lock()     # one writer at a time to the ledger file, whichever Budget writes


class Budget:
    """A spend cap. `since` counts only the ledger rows written from that time (a run's own spend, not the file's history), `model` only one model's rows; `parent` is a wider cap
    that every reserve and charge also passes through (a lane under the run's total). Only the Budget that is charged writes the ledger row."""
    def __init__(self, cap=CAP_USD, path=LEDGER, parent=None, since=None, model=None, name="run"):
        self.cap, self.path, self.parent, self.name, self.lock, self.reserved = cap, path, parent, name, threading.Lock(), 0.0
        self.spent = sum(r.get("usd", 0.0) for r in read(path) if (since is None or r.get("t", 0) >= since) and (model is None or r.get("model") == model))

    def _chain(self):
        b, out = self, []
        while b: out.append(b); b = b.parent
        return out

    def _take(self, worst):
        with self.lock:
            if self.spent + self.reserved + worst > self.cap:
                raise BudgetStop(f"{self.name} cap {self.cap:.2f} USD: spent {self.spent:.4f} + in flight {self.reserved:.4f} + this call's worst case {worst:.4f}", self.name)
            self.reserved += worst

    def _settle(self, worst, usd):
        with self.lock:
            self.reserved = max(0.0, self.reserved - worst); self.spent += usd

    def reserve(self, model, provider, tin_est, max_out):
        pi, po = price(model, provider)
        worst = (tin_est * pi + max_out * po) / 1e6; taken = []
        for b in self._chain():
            try: b._take(worst); taken.append(b)
            except BudgetStop:
                for t in taken: t._settle(worst, 0.0)
                raise
        return worst

    def charge(self, worst, model, provider, tag, tin, tout, **extra):
        pi, po = price(model, provider)
        usd = (tin * pi + tout * po) / 1e6
        row = {"t": round(time.time(), 3), "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tag": tag, "model": model, "provider": provider,
               "in": tin, "out": tout, "usd": round(usd, 6), **extra}
        for b in self._chain(): b._settle(worst, usd)
        with _flock, open(self.path, "a") as f:
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
