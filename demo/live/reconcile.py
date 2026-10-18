"""Reconcile the spend ledger with what the Tether Firehose 3 page shows.
Every call goes into ledger.jsonl before its result is used; the page shows only the chains that ended (valid, or after the third attempt). The difference is the calls of chains the cap or the time box cut off,
the calls that failed (no tokens reported, so 0 USD), the probes, and one estimated row for the paid calls cut off when a process had to be stopped.
Usage: python3 reconcile.py <live.json> [--md]"""
import collections, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger
d = json.load(open(sys.argv[1])); items = d["items"]
rows = ledger.read(); MD = "--md" in sys.argv
page = collections.defaultdict(lambda: [0, 0, 0, 0.0]); led = collections.defaultdict(lambda: [0, 0, 0, 0.0]); tags = collections.defaultdict(float)
for i in items:
    for a in i["A"]:
        p = page[i["m"]]; p[0] += 1; p[1] += a["ti"]; p[2] += a["to"]; p[3] += a["u"]
for r in rows:
    tags[r["tag"].split(" ")[0]] += r["usd"]
    if r["tag"] == "live":
        l = led[r["model"]]; l[0] += 1; l[1] += r["in"]; l[2] += r["out"]; l[3] += r["usd"]
head = ["model", "ledger calls", "on the page", "not on the page", "ledger USD", "page USD", "not on the page USD", "tokens out not on the page"]
tab = []; tot = [0, 0, 0.0, 0.0, 0]
for m in [x["id"] for x in d["meta"]["models"]]:
    l, p = led[m], page[m]
    tab.append([m, l[0], p[0], l[0] - p[0], f"{l[3]:.4f}", f"{p[3]:.4f}", f"{l[3] - p[3]:.4f}", f"{l[2] - p[2]:,}"])
    tot[0] += l[0]; tot[1] += p[0]; tot[2] += l[3]; tot[3] += p[3]; tot[4] += l[2] - p[2]
tab.append(["all models", tot[0], tot[1], tot[0] - tot[1], f"{tot[2]:.4f}", f"{tot[3]:.4f}", f"{tot[2] - tot[3]:.4f}", f"{tot[4]:,}"])
out = []
if MD:
    out += ["| " + " | ".join(head) + " |", "|" + "|".join("---" if k == 0 else "---:" for k in range(len(head))) + "|"] + ["| " + " | ".join(str(x) for x in r) + " |" for r in tab]
else:
    w = [max(len(str(x)) for x in col) for col in zip(head, *tab)]
    out += ["  ".join(str(h).ljust(w[k]) for k, h in enumerate(head))] + ["  ".join(str(x).ljust(w[k]) for k, x in enumerate(r)) for r in tab]
total = sum(r["usd"] for r in rows)
out += ["", f"ledger total {total:.4f} USD = live calls {tot[2]:.4f} + probes {tags.get('probe', 0):.4f} + killed-in-flight estimate {tags.get('killed-in-flight', 0):.4f}",
        f"page shows {tot[3]:.4f} USD of it; the rest is chains cut off by the cap or the time box ({tot[2] - tot[3]:.4f}), probes and the estimate"]
print("\n".join(out))
