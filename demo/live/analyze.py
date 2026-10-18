"""Numbers for the write-up of the recorded live run, computed from data/live.json (what the page embeds), so the text and the page cannot disagree.
Usage: python3 analyze.py <live.json> [--md]   Prints plain text, or Markdown tables with --md."""
import collections, json, re, statistics, sys

d = json.load(open(sys.argv[1])); items, meta = d["items"], d["meta"]
MD = "--md" in sys.argv
draws = lambda r: (not r.get("err")) and (r.get("nb") or 0) >= 0.005
fin = lambda i: i["A"][-1]
code = lambda l: (re.search(r"\*\*\[([\w-]+)\]\*\*", l) or [None, None])[1]
codes = lambda a: ([] if a["x"] else ["xsd"]) + [c for c in dict.fromkeys(code(l) for l in a["se"]) if c]
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
short = lambda m: re.sub(r"^(z-ai|nvidia)/", "", m)
out = []
def p(*a): out.append(" ".join(str(x) for x in a) if a else "")
def table(head, rows):
    if MD:
        p("| " + " | ".join(head) + " |"); p("|" + "|".join("---" if i == 0 else "---:" for i in range(len(head))) + "|")
        for r in rows: p("| " + " | ".join(str(x) for x in r) + " |")
    else:
        w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
        p("  ".join(str(h).ljust(w[i]) for i, h in enumerate(head)))
        for r in rows: p("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))
    p()

n = len(items); calls = sum(len(i["A"]) for i in items)
p(f"{n} scenes from {calls} calls, {len(meta['models'])} models, {meta['t_total']:.0f} s run clock ({meta['idle_collapsed_s']:.0f} s idle collapsed), validator {meta['validator']}, failed call rows {meta['failed_calls']}")
p()
rows = []
for m in meta["models"]:
    s = [i for i in items if i["m"] == m["id"]]; c = sum(len(i["A"]) for i in s)
    first = sum(1 for i in s if i["A"][0]["ok"]); end = sum(1 for i in s if fin(i)["ok"]); bad1 = [i for i in s if not i["A"][0]["ok"]]
    rep = sum(1 for i in bad1 if fin(i)["ok"]); blank = sum(1 for i in s if fin(i)["ok"] and not draws(fin(i)["r"])); dr = sum(1 for i in s if draws(fin(i)["r"]))
    usd = sum(a["u"] for i in s for a in i["A"]); tin = sum(a["ti"] for i in s for a in i["A"]); tout = sum(a["to"] for i in s for a in i["A"])
    lat = sorted(a["ms"] for i in s for a in i["A"])
    rows.append([short(m["id"]), len(s), c, f"{first} ({pct(first, len(s))})", f"{rep}/{len(bad1)}", f"{end} ({pct(end, len(s))})", blank, dr, f"{tin:,}", f"{tout:,}", f"${usd:.2f}", f"{statistics.median(lat) / 1000:.1f} s" if lat else "-"])
table(["model", "scenes", "calls", "valid first try", "repaired", "valid at end", "valid+blank", "draw", "tokens in", "tokens out", "est. spend", "median call"], rows)

# valid by attempt, cost per valid scene, calls cut off at the output limit
rows = []
for m in meta["models"]:
    s = [i for i in items if i["m"] == m["id"]]
    if not s: continue
    by = lambda k: sum(1 for i in s if any(a["ok"] for a in i["A"][:k]))
    usd = sum(a["u"] for i in s for a in i["A"]); v = by(3)
    cut = sum(1 for i in s for a in i["A"] if re.search(r"length|max_tokens", a.get("fin") or "", re.I))
    rows.append([short(m["id"]), len(s), f"{by(1)} ({pct(by(1), len(s))})", f"{by(2)} ({pct(by(2), len(s))})", f"{by(3)} ({pct(by(3), len(s))})", f"${usd / v:.3f}" if v and usd else "-", cut])
p("valid within 1, 2, 3 attempts; list-price estimate per valid scene; calls cut off at the output-token limit")
table(["model", "scenes", "valid at attempt 1", "by attempt 2", "by attempt 3", "est. $ per valid scene", "calls cut at limit"], rows)

# the same prompts for every paid model (a fair comparison; the free lanes are partial)
paid = [m["id"] for m in meta["models"] if m["prov"] != "nvidia"]
common = set.intersection(*[{i["p"] for i in items if i["m"] == m} for m in paid]) if paid else set()
rows = []
for m in paid:
    s = [i for i in items if i["m"] == m and i["p"] in common]
    rows.append([short(m), len(s), f"{sum(1 for i in s if i['A'][0]['ok'])} ({pct(sum(1 for i in s if i['A'][0]['ok']), len(s))})", f"{sum(1 for i in s if fin(i)['ok'])} ({pct(sum(1 for i in s if fin(i)['ok']), len(s))})"])
p(f"the {len(common)} prompts every paid model finished")
table(["model", "scenes", "valid first try", "valid at end"], rows)

# by prompt category, all models
cat = collections.defaultdict(lambda: [0, 0, 0])
for i in items:
    c = cat[i["c"]]; c[0] += 1; c[1] += int(i["A"][0]["ok"]); c[2] += int(fin(i)["ok"])
p("by prompt category (all models)")
table(["category", "scenes", "valid first try", "valid at end"], [[k, v[0], f"{v[1]} ({pct(v[1], v[0])})", f"{v[2]} ({pct(v[2], v[0])})"] for k, v in sorted(cat.items(), key=lambda x: x[1][1] / x[1][0])])

cf = collections.Counter(); cfix = collections.Counter(); cmodel = collections.defaultdict(collections.Counter)
for i in items:
    a = i["A"][0]
    if not a["ok"]:
        for c in codes(a): cf[c] += 1; cmodel[c][short(i["m"])] += 1
    for k in range(1, len(i["A"])):
        prev, now = i["A"][k - 1], i["A"][k]
        for c in codes(prev): cfix[(c, now["ok"] or c not in codes(now))] += 1
p("first-try failure codes (scenes carrying the code, all models)")
table(["code", "scenes", "by model"], [[c, k, ", ".join(f"{m} {v}" for m, v in cmodel[c].most_common())] for c, k in cf.most_common(12)])
p("attempt 2 outcome per code that attempt 1 had: gone / still there")
agg = collections.defaultdict(lambda: [0, 0])
for (c, gone), k in cfix.items(): agg[c][0 if gone else 1] += k
table(["code", "gone", "still there"], [[c, v[0], v[1]] for c, v in sorted(agg.items(), key=lambda x: -sum(x[1]))[:10]])

# how much of a scene a repair rewrites: first attempt against the final one, one tag per line (the unit the page's Tether diff uses)
import difflib
tags = lambda b: re.findall(r"<[^>]+>", b)
ch, fr = [], []
for i in items:
    if len(i["A"]) > 1 and fin(i)["ok"]:
        a0, a1 = tags(i["B"][0]), tags(i["B"][-1]); sm = difflib.SequenceMatcher(None, a0, a1, autojunk=False)
        c = sum((i2 - i1) if op in ("replace", "delete") else 0 for op, i1, i2, j1, j2 in sm.get_opcodes()) + sum((j2 - j1) if op in ("replace", "insert") else 0 for op, i1, i2, j1, j2 in sm.get_opcodes())
        ch.append(c); fr.append(c / max(1, len(a0)))
if ch:
    ch.sort(); fr.sort()
    p(f"repairs that ended valid: {len(ch)}; changed tag lines (added + removed) median {statistics.median(ch):.0f}, p90 {ch[int(.9 * len(ch))]}; share of the first attempt's tags: median {100 * statistics.median(fr):.0f}%, p90 {100 * fr[int(.9 * len(fr))]:.0f}%; "
      f"rewrote more than half: {sum(1 for f in fr if f > .5)}"); p()

att = collections.Counter(len(i["A"]) for i in items)
p("attempts per scene:", dict(sorted(att.items())))
never = [i for i in items if not fin(i)["ok"]]
p(f"never valid after 3 attempts: {len(never)}", [f"{short(i['m'])}/{i['p']}" for i in never][:20]); p()
rep_calls = [(a, i) for i in items for k, a in enumerate(i["A"]) if k > 0]; first_calls = [(a, i) for i in items for a in i["A"][:1]]
mean = lambda xs: sum(xs) / len(xs) if xs else 0
p(f"mean call: first {mean([a['to'] for a, _ in first_calls]):.0f} out tokens, {mean([a['ms'] for a, _ in first_calls]) / 1000:.1f} s, ${mean([a['u'] for a, _ in first_calls]):.4f}; "
  f"repair {mean([a['to'] for a, _ in rep_calls]):.0f} out tokens, {mean([a['ms'] for a, _ in rep_calls]) / 1000:.1f} s, ${mean([a['u'] for a, _ in rep_calls]):.4f}"); p()

p("valid on the fork but nothing (or almost nothing) drawn in X_ITE")
vb = [i for i in items if fin(i)["ok"] and not draws(fin(i)["r"])]
table(["model", "prompt", "attempts", "pixels differing", "frames", "X_ITE said"], [[short(i["m"]), i["p"], len(i["A"]), fin(i)["r"].get("nb"), fin(i)["r"].get("frames"), "; ".join(fin(i)["r"].get("msgs") or [])[:90]] for i in vb])
inv = [i for i in items if not fin(i)["ok"] and draws(fin(i)["r"])]
p(f"invalid on the fork but X_ITE draws something: {len(inv)} of {sum(1 for i in items if not fin(i)['ok'])}")
fd = [i for i in items if i["A"][0]["ok"] and not draws(i["A"][0]["r"])]
p(f"first attempt valid but blank: {len(fd)} of {sum(1 for i in items if i['A'][0]['ok'])}"); p()

tot = sum(a["u"] for i in items for a in i["A"])
p(f"estimated spend of the scenes on the page: ${tot:.2f}")
print("\n".join(out))
