"""Numbers for the write-up of a recorded live run, computed from data/live.json (what the page embeds), so the text and the page cannot disagree.
A chain's steps (A) are model calls (st "model"), the fork's deterministic repair (st "autofix": a step, never a call) and, in a --keep-failures build, failed calls (st "fail").
Rates count chains; a lane is one model x one arm; with --samples the same prompt appears once per sample.
Usage: python3 analyze.py <live.json> [--md]   Prints plain text, or Markdown tables with --md."""
import collections, json, re, statistics, sys

d = json.load(open(sys.argv[1])); meta = d["meta"]
MD = "--md" in sys.argv
ST = lambda a: a.get("st", "model")
va = lambda i: [a for a in i["A"] if ST(a) != "fail"]            # steps with a verdict
ma = lambda i: [a for a in i["A"] if ST(a) == "model"]           # model calls
vb = lambda i: [b for a, b in zip(i["A"], i["B"]) if ST(a) != "fail"]
items = [i for i in d["items"] if va(i)]; only_fail = len(d["items"]) - len(items)
draws = lambda r: (not r.get("err")) and (r.get("nb") or 0) >= 0.005
fin = lambda i: va(i)[-1]; first = lambda i: ma(i)[0]
code = lambda l: (re.search(r"\*\*\[([\w-]+)\]\*\*", l) or [None, None])[1]
codes = lambda a: ([] if a["x"] else ["xsd"]) + [c for c in dict.fromkeys(code(l) for l in a["se"]) if c]
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
short = lambda m: re.sub(r"^(z-ai|nvidia|openai|deepseek-ai|moonshotai|minimaxai|mistralai|google|qwen|meta)/", "", m)
lanes = [(l["m"], l["arm"]) for l in meta.get("lane_list", [])] or [(m["id"], "A") for m in meta["models"]]
multi = len({a for _, a in lanes}) > 1
label = lambda m, arm: short(m) + (f" {arm}" if multi else "")
sel = lambda m, arm: [i for i in items if i["m"] == m and i.get("arm", "A") == arm]
out = []
def p(*a): out.append(" ".join(str(x) for x in a) if a else "")
def table(head, rows):
    if MD:
        p("| " + " | ".join(head) + " |"); p("|" + "|".join("---" if i == 0 else "---:" for i in range(len(head))) + "|")
        for r in rows: p("| " + " | ".join(str(x) for x in r) + " |")
    else:
        w = [max(len(str(x)) for x in col) for col in zip(head, *rows)] if rows else [len(h) for h in head]
        p("  ".join(str(h).ljust(w[i]) for i, h in enumerate(head)))
        for r in rows: p("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))
    p()

n = len(items); calls = sum(len(ma(i)) for i in items); nfix = sum(1 for i in items for a in i["A"] if ST(a) == "autofix"); nfail = sum(1 for i in items for a in i["A"] if ST(a) == "fail")
p(f"{n} chains from {calls} model calls, {len(lanes)} lane(s) ({len(meta['models'])} models, arms {','.join(meta.get('arms', ['A']))}, samples {meta.get('samples', 1)}), {meta['t_total']:.0f} s run clock ({meta['idle_collapsed_s']:.0f} s idle collapsed), "
  f"validator {meta['validator']}, failed call rows {meta['failed_calls']}" + (f" ({nfail} shown as steps)" if nfail else "") + (f", {nfix} autofix steps" if nfix else "") + (f", {meta.get('cut_chains', 0)} cut chains kept" if meta.get("cut_chains") else "") + (f", {only_fail} chains with no verdict at all" if only_fail else ""))
p()
rows = []
for m, arm in lanes:
    s = sel(m, arm); c = sum(len(ma(i)) for i in s)
    f1 = sum(1 for i in s if first(i)["ok"]); end = sum(1 for i in s if fin(i)["ok"]); bad1 = [i for i in s if not first(i)["ok"]]
    rep = sum(1 for i in bad1 if fin(i)["ok"]); blank = sum(1 for i in s if fin(i)["ok"] and not draws(fin(i)["r"])); dr = sum(1 for i in s if draws(fin(i)["r"]))
    usd = sum(a["u"] for i in s for a in ma(i)); tin = sum(a["ti"] for i in s for a in ma(i)); tout = sum(a["to"] for i in s for a in ma(i))
    lat = sorted(a["ms"] for i in s for a in ma(i)); tft = sorted(a["tft"] for i in s for a in ma(i) if a.get("tft") is not None)
    rows.append([label(m, arm), len(s), c, f"{f1} ({pct(f1, len(s))})", f"{rep}/{len(bad1)}", f"{end} ({pct(end, len(s))})", blank, dr, f"{tin:,}", f"{tout:,}", f"${usd:.2f}", f"{statistics.median(lat) / 1000:.1f} s" if lat else "-", f"{statistics.median(tft) / 1000:.1f} s" if tft else "-"])
table(["lane", "chains", "calls", "valid first try", "repaired", "valid at end", "valid+blank", "draw", "tokens in", "tokens out", "est. spend", "median call", "median first token"], rows)

# valid by attempt, cost per valid scene, calls cut off at the output limit
rows = []
for m, arm in lanes:
    s = sel(m, arm)
    if not s: continue
    def by(k):      # valid within the first k model attempts (an attempt's autofix step counts with it); an old live.json has no att field, so there the first k steps
        return sum(1 for i in s if any(a["ok"] for a in va(i) if a.get("att", va(i).index(a) + 1) <= k))
    usd = sum(a["u"] for i in s for a in ma(i)); v = by(3)
    cut = sum(1 for i in s for a in ma(i) if re.search(r"length|max_tokens", a.get("fin") or "", re.I))
    rows.append([label(m, arm), len(s), f"{by(1)} ({pct(by(1), len(s))})", f"{by(2)} ({pct(by(2), len(s))})", f"{by(3)} ({pct(by(3), len(s))})", f"${usd / v:.3f}" if v and usd else "-", cut])
p("valid within 1, 2, 3 model attempts (arm B: the autofix step counts with attempt 1); list-price estimate per valid scene; calls cut off at the output-token limit")
table(["lane", "chains", "valid at attempt 1", "by attempt 2", "by attempt 3", "est. $ per valid scene", "calls cut at limit"], rows)

# arm B: what the deterministic repair did before any model repair
fx = [(i, a) for i in items for a in i["A"] if ST(a) == "autofix"]
if fx:
    rows = []
    for m, arm in lanes:
        s = [(i, a) for i, a in fx if i["m"] == m and i.get("arm", "A") == arm]
        if not s: continue
        ok = sum(1 for i, a in s if a["ok"]); ms = sorted(a["ms"] for _, a in s); nch = sorted(a["fix"]["n"] for _, a in s)
        kinds = collections.Counter(k for _, a in s for k, v in a["fix"]["kinds"].items() for _ in range(v)); unf = sum(1 for _, a in s if a["fix"]["unfixable"]); err = sum(1 for _, a in s if a["fix"]["err"])
        after = [i for i, a in s if not a["ok"]]; saved = sum(1 for i in after if fin(i)["ok"])
        rows.append([label(m, arm), len(s), f"{ok} ({pct(ok, len(s))})", f"{saved}/{len(after)}", f"{statistics.median(ms):.0f} ms" if ms else "-", f"{statistics.median(nch):.0f}", ", ".join(f"{k} {v}" for k, v in kinds.most_common(5)), unf, err])
    p("autofix step (arm B): chains that were invalid at attempt 1 and went through the fork's deterministic repair before any model repair")
    table(["lane", "autofix steps", "valid right after autofix", "model repaired the rest", "median ms", "median changes", "change kinds", "with unfixable", "fixer errors"], rows)

# the same prompts for every paid model (a fair comparison; the free lanes are partial)
paid = [m["id"] for m in meta["models"] if m["prov"] != "nvidia"]
common = set.intersection(*[{i["p"] for i in items if i["m"] == m} for m in paid]) if paid else set()
if paid and common:
    rows = []
    for m in paid:
        s = [i for i in items if i["m"] == m and i["p"] in common]
        rows.append([short(m), len(s), f"{sum(1 for i in s if first(i)['ok'])} ({pct(sum(1 for i in s if first(i)['ok']), len(s))})", f"{sum(1 for i in s if fin(i)['ok'])} ({pct(sum(1 for i in s if fin(i)['ok']), len(s))})"])
    p(f"the {len(common)} prompts every paid model finished")
    table(["model", "scenes", "valid first try", "valid at end"], rows)

# by prompt category, all lanes
cat = collections.defaultdict(lambda: [0, 0, 0])
for i in items:
    c = cat[i["c"]]; c[0] += 1; c[1] += int(first(i)["ok"]); c[2] += int(fin(i)["ok"])
p("by prompt category (all lanes)")
table(["category", "chains", "valid first try", "valid at end"], [[k, v[0], f"{v[1]} ({pct(v[1], v[0])})", f"{v[2]} ({pct(v[2], v[0])})"] for k, v in sorted(cat.items(), key=lambda x: x[1][1] / x[1][0])])

cf = collections.Counter(); cfix = collections.Counter(); cmodel = collections.defaultdict(collections.Counter)
for i in items:
    a = first(i)
    if not a["ok"]:
        for c in codes(a): cf[c] += 1; cmodel[c][short(i["m"])] += 1
    steps = va(i)
    for k in range(1, len(steps)):
        prev, now = steps[k - 1], steps[k]
        for c in codes(prev): cfix[(c, now["ok"] or c not in codes(now))] += 1
p("first-try failure codes (chains carrying the code, all lanes)")
table(["code", "chains", "by model"], [[c, k, ", ".join(f"{m} {v}" for m, v in cmodel[c].most_common())] for c, k in cf.most_common(12)])
p("next step's outcome per code the previous step had (a model repair or the autofix step): gone / still there")
agg = collections.defaultdict(lambda: [0, 0])
for (c, gone), k in cfix.items(): agg[c][0 if gone else 1] += k
table(["code", "gone", "still there"], [[c, v[0], v[1]] for c, v in sorted(agg.items(), key=lambda x: -sum(x[1]))[:10]])

# how much of a scene a repair rewrites: first attempt against the final one, one tag per line (the unit the page's Tether diff uses)
import difflib
tags = lambda b: re.findall(r"<[^>]+>", b or "")
ch, fr = [], []
for i in items:
    bodies = vb(i)
    if len(bodies) > 1 and fin(i)["ok"]:
        a0, a1 = tags(bodies[0]), tags(bodies[-1]); sm = difflib.SequenceMatcher(None, a0, a1, autojunk=False)
        c = sum((i2 - i1) if op in ("replace", "delete") else 0 for op, i1, i2, j1, j2 in sm.get_opcodes()) + sum((j2 - j1) if op in ("replace", "insert") else 0 for op, i1, i2, j1, j2 in sm.get_opcodes())
        ch.append(c); fr.append(c / max(1, len(a0)))
if ch:
    ch.sort(); fr.sort()
    p(f"repairs that ended valid: {len(ch)}; changed tag lines (added + removed) median {statistics.median(ch):.0f}, p90 {ch[int(.9 * len(ch))]}; share of the first attempt's tags: median {100 * statistics.median(fr):.0f}%, p90 {100 * fr[int(.9 * len(fr))]:.0f}%; "
      f"rewrote more than half: {sum(1 for f in fr if f > .5)}"); p()

att = collections.Counter(len(ma(i)) for i in items)
p("model calls per chain:", dict(sorted(att.items())))
never = [i for i in items if not fin(i)["ok"]]
p(f"not valid at the end: {len(never)}", [f"{short(i['m'])}{'/' + i['arm'] if multi else ''}/{i['p']}" + (f" (cut: {i['cut']})" if i.get("cut") else "") for i in never][:20]); p()
rep_calls = [(a, i) for i in items for k, a in enumerate(ma(i)) if k > 0]; first_calls = [(a, i) for i in items for a in ma(i)[:1]]
mean = lambda xs: sum(xs) / len(xs) if xs else 0
p(f"mean call: first {mean([a['to'] for a, _ in first_calls]):.0f} out tokens, {mean([a['ms'] for a, _ in first_calls]) / 1000:.1f} s, ${mean([a['u'] for a, _ in first_calls]):.4f}; "
  f"repair {mean([a['to'] for a, _ in rep_calls]):.0f} out tokens, {mean([a['ms'] for a, _ in rep_calls]) / 1000:.1f} s, ${mean([a['u'] for a, _ in rep_calls]):.4f}"); p()
if nfail:
    fails = [a for i in items for a in i["A"] if ST(a) == "fail"]; st = collections.Counter(str(a.get("status") or (a["err"] or "")[:40]) for a in fails)
    p("failed calls shown as steps, by status:", ", ".join(f"{k}: {v}" for k, v in st.most_common(8))); p()

p("valid on the fork but nothing (or almost nothing) drawn in X_ITE")
vbk = [i for i in items if fin(i)["ok"] and not draws(fin(i)["r"])]
table(["lane", "prompt", "steps", "pixels differing", "frames", "X_ITE said"], [[label(i["m"], i.get("arm", "A")), i["p"], len(va(i)), fin(i)["r"].get("nb"), fin(i)["r"].get("frames"), "; ".join(fin(i)["r"].get("msgs") or [])[:90]] for i in vbk])
inv = [i for i in items if not fin(i)["ok"] and draws(fin(i)["r"])]
p(f"invalid on the fork but X_ITE draws something: {len(inv)} of {sum(1 for i in items if not fin(i)['ok'])}")
fd = [i for i in items if first(i)["ok"] and not draws(first(i)["r"])]
p(f"first attempt valid but blank: {len(fd)} of {sum(1 for i in items if first(i)['ok'])}"); p()

tot = sum(a["u"] for i in items for a in ma(i))
p(f"estimated spend of the chains on the page: ${tot:.2f}")
print("\n".join(out))
