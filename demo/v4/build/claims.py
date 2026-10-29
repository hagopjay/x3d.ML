"""STATS for Tether Firehose 4 (SPEC section 0 rule 1 claim chips, section 8 step 4): every headline claim's `expected` value, the rule behind it in words (printed in the
page's proof drawer), its grade (Confirmed / Likely / Suspected), and the LIVESTATS / REALSTATS tables the v3 page computed in JS, ported here line for line so the page's
compute() must equal these or the chip goes red. Nothing here is typed in: every number is computed from
  demo/data/live.json (201 chains, 358 calls, verdicts fork@eb4b4b4, renders X_ITE 16.5.0), demo/data/replay.json (174 scenes of 11 Oct), demo/v4/data/events.json (build_events.py),
  demo/v4/data/renders.151.json (merge_renders.py), drift/verdicts-8dd0d3e.json (the canary baseline) and one run of drift/canary.py against an x3d_mcp checkout.
Writes demo/v4/data/stats.json = {claims:{id:{expected, text, rule, grade, source, validator, renderer}}, LIVESTATS, REALSTATS, lanes[], sankey, seven[], canary, meta}.
Usage: python3 -I demo/v4/build/claims.py [--tree <x3d_mcp checkout>]   (default tree: $X3D_MCP_TREE; without a tree the canary claim is written with flips null, never guessed)"""
import collections, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
D, V4 = os.path.join(ROOT, "demo/data"), os.path.join(ROOT, "demo/v4/data")
OUT = os.path.join(V4, "stats.json")
TREE = sys.argv[sys.argv.index("--tree") + 1] if "--tree" in sys.argv else os.environ.get("X3D_MCP_TREE")
live = json.load(open(D + "/live.json")); LIVE, LM = live["items"], live["meta"]; REAL = json.load(open(D + "/replay.json"))
EV = json.load(open(V4 + "/events.json")); R151 = json.load(open(V4 + "/renders.151.json")); R150 = json.load(open(V4 + "/renders.series.json")); RUNJ = json.load(open(os.path.join(ROOT, "runs/live-2026-10-17/run.json"))); BASE = json.load(open(os.path.join(ROOT, "drift/verdicts-8dd0d3e.json")))
slug = lambda m: m.replace("/", "_")
for it in LIVE: f = it["A"][-1]; it["r"] = f["r"]; it["ok"] = f["ok"]; it["key"] = f"{slug(it['m'])}/{it['p']}_a{len(it['A'])}.x3d"

# ---- the page's helpers, ported (JS median = sorted non-null values, element at n >> 1; JS Math.round for percentages)
med = lambda a: (lambda s: s[len(s) >> 1] if s else None)(sorted(v for v in a if v is not None))
pct = lambda a, b: int(100 * a / b + 0.5) if b else None
DRAWS = lambda i: not i["r"].get("err") and (i["r"].get("nb") or 0) >= .005
drew = lambda r: bool(r) and not r.get("err") and (r.get("nb") or 0) >= .005
DROP_RE = re.compile(r"Unknown node type|Unknown named or imported node|Container field|insufficient component")
dropped = lambda i: (i["r"].get("unknown") or 0) > 0 or any(DROP_RE.search(m) for m in i["r"].get("msgs") or [])
kindOf = lambda i: "unparseable" if i["r"].get("err") else "draws" if (i["r"].get("nb") or 0) >= .005 else "nothing drawable" if (i["r"].get("nf") or dropped(i)) else "blank frame"
CODE = re.compile(r"\*\*\[([\w-]+)\]\*\*")
def codesOf(a):
    c = [] if a["x"] else ["xsd"]
    for l in a.get("se") or []:
        m = CODE.search(l)
        if m and m.group(1) not in c: c.append(m.group(1))
    return c
TRUNC = re.compile(r"length|max_tokens", re.I)

# ---- LIVESTATS (v3 template, const LIVESTATS)
fin = lambda i: i["A"][-1]
per = []
for m in LM["models"]:
    s = [i for i in LIVE if i["m"] == m["id"]]; bad1 = [i for i in s if not i["A"][0]["ok"]]
    per.append({"id": m["id"], "prov": m["prov"], "kind": m["kind"], "n": len(s), "calls": sum(len(i["A"]) for i in s), "first": sum(1 for i in s if i["A"][0]["ok"]), "valid": sum(1 for i in s if fin(i)["ok"]),
                "bad1": len(bad1), "rep": sum(1 for i in bad1 if fin(i)["ok"]), "blankValid": sum(1 for i in s if fin(i)["ok"] and not DRAWS(i)), "usd": round(sum(a["u"] for i in s for a in i["A"]), 6),
                "tin": sum(a["ti"] for i in s for a in i["A"]), "tout": sum(a["to"] for i in s for a in i["A"]), "lat": med([a["ms"] for i in s for a in i["A"]]), "vmed": med([a["vms"] for i in s for a in i["A"]]),
                "truncated": sum(1 for i in s for a in i["A"] if TRUNC.search(a.get("fin") or "")), "failed": sum(1 for f in EV["failed"] if f["m"] == m["id"]), "cut": sum(1 for c in EV["cut"] if c["m"] == m["id"]),
                "stopped": LM.get("lanes", {}).get(m["id"])})
valid = [i for i in LIVE if fin(i)["ok"]]; firstValid = [i for i in LIVE if i["A"][0]["ok"]]
kinds = collections.Counter(kindOf(i) for i in LIVE)
LIVESTATS = {"n": len(LIVE), "calls": sum(len(i["A"]) for i in LIVE), "valid": len(valid), "validNoDraw": sum(1 for i in valid if not DRAWS(i)), "first": len(firstValid), "firstNoDraw": sum(1 for i in firstValid if not drew(i["A"][0]["r"])),
             "bad1": len(LIVE) - len(firstValid), "rep": sum(1 for i in LIVE if not i["A"][0]["ok"] and fin(i)["ok"]), "invDraw": sum(1 for i in LIVE if not fin(i)["ok"] and DRAWS(i)), "draws": sum(1 for i in LIVE if DRAWS(i)),
             "kinds": {k: kinds.get(k, 0) for k in ("draws", "blank frame", "nothing drawable", "unparseable")}, "per": per, "usd": round(sum(p["usd"] for p in per), 6), "tin": sum(p["tin"] for p in per), "tout": sum(p["tout"] for p in per),
             "blankMax": max([0] + [i["r"].get("nb") or 0 for i in LIVE if not i["r"].get("err") and not DRAWS(i)]), "vmed": med([a["vms"] for i in LIVE for a in i["A"]]), "mmed": med([a["ms"] for i in LIVE for a in i["A"]]),
             "blankCat": dict(collections.Counter(i["c"] for i in valid if not DRAWS(i))), "repCalls": sum(len(i["A"]) - 1 for i in LIVE), "multi": sum(1 for i in LIVE if len(i["A"]) > 1), "giveUp": sum(1 for i in LIVE if not fin(i)["ok"]),
             "truncated": sum(1 for i in LIVE for a in i["A"] if TRUNC.search(a.get("fin") or ""))}

# ---- REALSTATS (v3 template, const REALSTATS) + the 16.5.1 agreement line
f = []
for name, fn in (("svc@11Oct", lambda i: i["x"] and i["s"]), ("fork@8c0a457", lambda i: i["f1"][0]), ("fork@eb4b4b4", lambda i: i["f2"][0])):
    v = [i for i in REAL if fn(i)]; d = sum(1 for i in v if DRAWS(i)); f.append({"n": name, "valid": len(v), "draws": d, "nodraw": len(v) - d})
rk = collections.Counter(kindOf(i) for i in REAL); flip = [i for i in REAL if i["x"] and i["s"] and not i["f1"][0]]
both = [i for i in REAL if not i["r"].get("err") and i["r"].get("cb") is not None and i["r"].get("shot") is not None]
bl = [i for i in REAL if not i["r"].get("err") and (i["r"].get("nb") or 0) < .005]; dr = [i for i in REAL if DRAWS(i)]
cls = lambda err, nb: "u" if err else "b" if (nb or 0) < .005 else "d"
r151 = R151["replay"]
REALSTATS = {"n": len(REAL), "f": f, "kinds": {k: rk.get(k, 0) for k in ("draws", "blank frame", "nothing drawable", "unparseable")}, "draws": len(dr), "flip": len(flip), "flipNoDraw": sum(1 for i in flip if not DRAWS(i)), "wf": sum(1 for i in REAL if i.get("wf")),
             "agree": sum(1 for i in both if (i["r"]["cb"] < .005) == (i["r"]["shot"] < .005)), "both": len(both), "blankMax": max([0] + [i["r"].get("nb") or 0 for i in bl]),
             "blankFrames": med([i["r"].get("frames") for i in bl]), "blankLast": med([i["r"].get("last") for i in bl]), "drawFrames": med([i["r"].get("frames") for i in dr]), "drawLast": med([i["r"].get("last") for i in dr]),
             "dropDraw": sum(1 for i in dr if dropped(i)), "extN": sum(1 for i in REAL if "ext" in i["r"]), "extBlank": sum(1 for i in REAL if "ext" in i["r"] and i["r"]["ext"] < .005),
             "v164n": sum(1 for i in REAL if "nb164" in i["r"]), "v164a": sum(1 for i in REAL if "nb164" in i["r"] and cls(i["r"].get("err164"), i["r"]["nb164"]) == cls(i["r"].get("err"), i["r"].get("nb"))),
             "v151n": sum(1 for i in REAL if i["k"] in r151), "v151a": sum(1 for i in REAL if i["k"] in r151 and cls(r151[i["k"]]["err"], r151[i["k"]]["nb"]) == cls(i["r"].get("err"), i["r"].get("nb")))}

# ---- the dark seven: finals valid on the fork, under 0.5 % of pixels on BOTH passes (hanim-01's rule is nb === 0 over its 4 frames; it satisfies the general rule too)
seven = []
for i in valid:
    a = R151["live"].get(i["key"]) or {}
    if not i["r"].get("err") and (i["r"].get("nb") or 0) < .005 and a.get("err") is None and (a.get("nb") or 0) < .005:
        seven.append({"key": i["key"], "m": i["m"], "p": i["p"], "c": i["c"], "nb": i["r"].get("nb"), "nb151": a.get("nb"), "frames": i["r"].get("frames"), "frames151": a.get("frames"), "zero": (i["r"].get("nb") or 0) == 0 and (a.get("nb") or 0) == 0})
only150 = [i["key"] for i in valid if not i["r"].get("err") and (i["r"].get("nb") or 0) < .005]
assert sorted(only150) == sorted(s["key"] for s in seven), ("16.5.1 disagrees with 16.5.0 on a valid-blank final", only150)

# ---- Sankey: first-try codes (one count per chain per code) and what happened to each after the repairs
codes1 = collections.Counter(); outcome = collections.defaultdict(collections.Counter)
for i in LIVE:
    cs = [codesOf(a) for a in i["A"]]
    for c in cs[0]:
        codes1[c] += 1
        o = "gone after repair 1" if len(cs) > 1 and c not in cs[1] else "gone after repair 2" if len(cs) > 2 and c not in cs[2] else "gave up"     # every chain on the page ended valid or at attempt 3
        outcome[c][o] += 1
        if o != "gone after repair 1": outcome[c]["still there"] += 1        # the intermediate node: present after repair 1, then gone after repair 2 or still there when the loop gave up
sankey = {"codes1": dict(codes1.most_common()), "outcome": {c: dict(v) for c, v in outcome.items()},
          "rule": "codes of attempt 1 per chain (xsd when the XSD failed, then each semantic code once); gone after repair 1 = absent from attempt 2's codes; still there = present in attempt 2's, then gone after repair 2 = absent from attempt 3's, or gave up = still in the third attempt's codes"}

# ---- canary (drift/canary.py against the committed baseline)
groups = collections.Counter("replay" if k.startswith("replay/") else "live" if "/x3d/" in k else "ledger" for k in BASE["verdicts"])
canary = {"baseline": os.path.basename(os.path.join(ROOT, "drift/verdicts-8dd0d3e.json")), "tree": BASE["tree"], "bodies": BASE["n"], "set": dict(groups), "flips": None, "code_changes": None, "ran": False}
if TREE and os.path.isdir(TREE):
    p = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "drift/canary.py"), "--tree", TREE, "--baseline", os.path.join(ROOT, "drift/verdicts-8dd0d3e.json")], capture_output=True, text=True, cwd=ROOT)
    m = re.search(r"verdict flips (\d+), code changes (\d+), new bodies (\d+), missing (\d+)", p.stdout); t = re.search(r"canary: tree (\S+) bodies (\d+)", p.stdout)
    if m: canary.update(flips=int(m.group(1)), code_changes=int(m.group(2)), new_bodies=int(m.group(3)), missing=int(m.group(4)), ran=True, tree_now=t.group(1), bodies_in_tree_now=int(t.group(2)), ok="CANARY: OK" in p.stdout)
    else: canary["error"] = (p.stdout + p.stderr)[-400:]
else: canary["note"] = "no x3d_mcp checkout given (--tree or $X3D_MCP_TREE): the canary was not re-run; bodies and tree come from the committed baseline"

# ---- the claims
paid = [p for p in per if p["prov"] != "nvidia"]
SRC, VAL = "RECORDED 17 Oct", "fork@eb4b4b4 recorded"
claims = {
 "c.rates": {"expected": [{"id": p["id"], "n": p["n"], "first": p["first"], "valid": p["valid"], "firstPct": pct(p["first"], p["n"]), "validPct": pct(p["valid"], p["n"])} for p in paid],
             "text": " · ".join(f"{pct(p['first'], p['n'])} → {pct(p['valid'], p['n'])}" for p in paid), "sub": f"% valid, first try → end of loop, three paid lanes ({' / '.join(str(p['n']) for p in paid)} scenes)",
             "rule": "per paid lane (provider not nvidia): chains whose attempt 1 is valid on fork@eb4b4b4, and chains whose final attempt is valid, each as a rounded percent of the lane's chains on the page",
             "grade": "S", "why": "one run of each prompt per lane; a rate from one sample", "source": SRC, "validator": VAL, "renderer": "none"},
 "c.seven": {"expected": len(seven), "of": len(valid), "ids": [s["key"] for s in seven], "text": f"{len(seven)} of {len(valid)}", "sub": "valid on the fork, nothing drawn · X_ITE 16.5.0 and 16.5.1",
             "rule": "final attempts valid on fork@eb4b4b4 whose measured frame differs from the background on fewer than 0.5 % of pixels on BOTH offline passes (16.5.0 and 16.5.1); hanim-01 is exactly 0 over its 4 frames on both",
             "grade": "C", "why": "measured on both passes for these scenes", "source": SRC, "validator": VAL, "renderer": "X_ITE 16.5.0 offline + 16.5.1 offline"},
 "c.ratio": {"expected": {"vmed": LIVESTATS["vmed"], "mmed": LIVESTATS["mmed"], "x": int(LIVESTATS["mmed"] / LIVESTATS["vmed"] + 0.5) if LIVESTATS["vmed"] else None},
             "text": f"{LIVESTATS['vmed']} ms vs {LIVESTATS['mmed'] / 1000:.0f} s", "sub": f"validator median vs model-call median, {LIVESTATS['calls']} calls · ×{int(LIVESTATS['mmed'] / LIVESTATS['vmed'] + 0.5):,}",
             "rule": f"median of A[].vms (validator ms, in process) and median of A[].ms (model call ms) over all {LIVESTATS['calls']} calls; median = sorted value at index n >> 1; the factor is their ratio rounded",
             "grade": "C", "why": "both timings recorded per call", "source": SRC, "validator": VAL, "renderer": "none"},
 "c.calls": {"expected": LIVESTATS["calls"], "rule": "sum of A[].length over the 201 chains on the page", "grade": "C", "source": SRC, "validator": VAL, "renderer": "none"},
 "c.failed": {"expected": len(EV["failed"]), "kinds": EV["kinds"], "rule": "rows of runs/live-2026-10-17/events.jsonl with an error field, each reduced to a kind at build", "grade": "C", "source": SRC, "validator": "none", "renderer": "none"},
 "c.cut": {"expected": len(EV["cut"]), "calls": EV["reconcile"]["cut_calls"], "reasons": EV["cut_reasons"], "rule": "chains with at least one recorded call that ended neither valid nor at the third attempt (the cap or the time box stopped the lane)", "grade": "C", "source": SRC, "validator": VAL, "renderer": "none"},
 "c.canary": {"expected": {"bodies": canary["bodies"], "flips": canary["flips"]}, "set": canary["set"], "text": f"{canary['bodies']} bodies · {canary['flips']} flips",
              "rule": "every recorded body (174 replay + 383 live attempts + the physics ledger) validated with fork@8dd0d3e and compared with the verdicts recorded for it; a flip is a changed valid or XSD-valid flag",
              "grade": "C" if canary["ran"] else "L", "source": "RE-RUN at build (drift/canary.py)", "validator": "fork@8dd0d3e canary", "renderer": "none"},
 "c.truncated": {"expected": LIVESTATS["truncated"], "rule": "calls whose finish reason matches /length|max_tokens/i", "grade": "C", "source": SRC, "validator": "none", "renderer": "none"},
 "c.replay17": {"expected": f[0]["nodraw"], "of": f[0]["valid"], "rule": "replay scenes the 11 Oct service called valid (x and s set) whose X_ITE 16.5.0 frame is under 0.5 %", "grade": "C", "source": "RECORDED 11 Oct", "validator": "svc@11Oct recorded", "renderer": "X_ITE 16.5.0 offline"},
 "c.lockstep": {"expected": None, "rule": "page text-normalised hash vs repo lxml C14N hash over the 175 stamped heads; prints n/175 until module 04_c14n ships (SPEC section 9)", "grade": "S", "source": "not built", "validator": "none", "renderer": "none"},
}
# ---- c.flips151: the 16.5.1 pass re-measured every renders row; a flip is a row whose draw verdict (nb >= 0.005 and no error) differs from the 16.5.0 pass
draw = lambda r: bool(r) and not r.get("err") and (r.get("nb") or 0) >= 0.005
pairs151 = len(R151["live"]) + len(R151["replay"])
LIVE_R150 = {it["key"]: it["r"] for it in LIVE}   # the 16.5.0 pass is the item's own r (renders.series carries the frame series, not the verdict)
flips151 = [k for k, r in R151["live"].items() if k in LIVE_R150 and draw(r) != draw(LIVE_R150[k])]
REAL_R150 = {i["k"]: i.get("r") for i in REAL}   # the replay's 16.5.0 record rides on each item
flips151 += [k for k, r in R151["replay"].items() if k in REAL_R150 and draw(r) != draw(REAL_R150[k])]
claims["c.flips151"] = {"expected": {"pairs": pairs151, "flips": len(flips151)}, "flipped": flips151, "text": f"{pairs151} rows re-measured on X_ITE 16.5.1 · {len(flips151)} draw-verdict flips",
                        "rule": "renders.151 rows (live + replay) whose draw verdict (nonblank >= 0.5 % and no parse error) differs between the 16.5.0 pass (renders.series / replay r) and the 16.5.1 pass",
                        "grade": "C", "source": "MEASURED 24 Oct", "validator": "none", "renderer": "X_ITE 16.5.0 offline + 16.5.1 offline"}
STATS = {"built_from": ["demo/data/live.json", "demo/data/replay.json", "demo/v4/data/events.json", "demo/v4/data/renders.151.json", "drift/verdicts-8dd0d3e.json"], "claims": claims, "LIVESTATS": LIVESTATS, "REALSTATS": REALSTATS,
         "lanes": per, "sankey": sankey, "seven": seven, "canary": canary, "meta": {**{k: LM[k] for k in ("models", "lanes", "validator", "t_total", "idle_collapsed_s", "n_prompts", "max_attempts", "failed_calls", "date", "gaps") if k in LM},
                  "cap_usd": RUNJ.get("cap_usd"), "spent_usd_est": RUNJ.get("spent_usd_est"), "spend_src": "runs/live-2026-10-17/run.json (list-price estimate at run time)"}}
json.dump(STATS, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)

for cid, c in claims.items(): print(f"{cid:12} {c['grade']}  expected {json.dumps(c['expected'])}" + (f"  → {c['text']}" if c.get("text") else ""))
print("seven:", ", ".join(f"{s['key']} ({s['nb']}/{s['nb151']}, {s['frames']}/{s['frames151']} frames{', zero' if s['zero'] else ''})" for s in seven))
print("LIVESTATS", {k: v for k, v in LIVESTATS.items() if k != "per"})
print("REALSTATS", REALSTATS)
print("sankey codes1", sankey["codes1"]); print("sankey outcomes", sankey["outcome"])
print("canary", canary)
print(OUT, os.path.getsize(OUT), "B")
