"""M-C: what catches what. Tamper detection of audit_trace (x3d.ML carrier + x3dtrace engine) and the cost per claim.

usage: python3 -I -B m_tamper.py <x3dml_src_dir> <repos_dir> <out.json> [n_scenes=40] [seed=20261116]

Per scene: a generate step, up to 25 claims taken from the scene itself (quote = attr="value" copied from the scene, field = its XPath),
the engine check, a trace step (items inline or in a sidecar) with or without the sealing summary step after it. Then single mutations of
copies; an attack is DETECTED when audit_trace(...)["status"] is not "verified". Each row says which layer caught it.

Attack families (name -> what the attacker does):
  A sidecar items edited, step untouched                      (7 edits)
  B items edited AND the last step patched to match (report_sha256, claims_sha256, summary re-hashed); sealed / unsealed
  C inline item edited in the step text, nothing re-hashed     (verdict flip, span shift); sealed / unsealed
  D claim fields edited inside the items (value, quote)        (claims_sha256 and the replay)
  E consistent forgery: a fresh honest trace of other claims in place of the old one:
      E1 last step only, no seal | E2 trace step replaced, later steps untouched | E3 trace and every later step re-chained
  F scene edited after the trace (digit in a claimed value, formatting only, comment, an unclaimed edit)
"""
import sys, os, json, random, time, copy, hashlib, collections, subprocess, re

SRC, root, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 40
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 20261116
sys.path.insert(0, SRC)
import x3dprov as P, x3dprov_trace as T, x3dtrace as X
rnd = random.Random(SEED)
REPOS = ["x3d.ml", "x3d.loom", "x3d.demo", "x3d.docs", "x3d-blender-io", "x3d.lab", "x3d.castle"]

pool, seen = [], set()
for r in REPOS:
    for p in subprocess.check_output(["git", "-C", os.path.join(root, r), "ls-files", "*.x3d"], text=True).splitlines():
        raw = open(os.path.join(root, r, p), "rb").read()
        h = hashlib.sha256(raw).hexdigest()
        if h in seen or not (1000 <= len(raw) <= 120000):
            continue
        seen.add(h)
        try:
            t = raw.decode("utf-8")
        except Exception:
            continue
        if t.lstrip("﻿ \t\r\n").startswith("<") and X.SceneIndex(t).ok:
            pool.append((r, p, t))
rnd.shuffle(pool)

def mk_claims(text, limit=25):
    out = []
    for row in X.inventory(text)[:limit]:
        vs, ve = row["span"]
        s = text.rfind(row["attr"], 0, vs)
        out.append({"field": row["field"], "value": row["value"], "quote": text[s:ve + 1], "source": "scene"})
    return out

def step_text(xml, n):
    return [t for k, t in P.read_steps(xml) if k == n][0]

def swap_step(xml, n, new_text):
    old = step_text(xml, n)
    out = xml.replace(P._attr(old), P._attr(new_text), 1)
    assert out != xml
    return out

def last_trace_n(xml):
    return [k for k, t in P.read_steps(xml) if json.loads(t).get("op") == "trace"][-1]

def rhash(xml):
    return [r for r in P.summary(xml) if r.get("op") == "trace"][-1]["report_sha256"]

def audit(xml, side=None):
    return T.audit_trace(xml, {"scene": T.scene_text(xml)}, sidecars=side)

def resealed_rec(rec, items):
    """what an attacker with write access to the last step does: new report hash, claims hash and summary for edited items"""
    r2 = {k: v for k, v in rec.items() if k not in ("prev", "input_sha256", "output_sha256", "items")}
    r2["report_sha256"] = P._sha(P._dumps(items).encode())
    r2["claims_sha256"] = P._sha(P._dumps(T.claims_of(items)).encode())
    r2["summary"] = T.summarize(items, rec["summary"].get("values"))
    return r2

stats = collections.defaultdict(collections.Counter)
hist = collections.defaultdict(collections.Counter)
timing = collections.Counter()
used, skipped, base_fail, base_fail_why = [], 0, 0, []
skipped_stale_on_stamp = 0

def rec_(cls, status):
    stats[cls]["n"] += 1
    stats[cls]["detected"] += status != "verified"
    hist[cls][status] += 1

VERD = list(X.VERDICTS)
def flip(v):
    return VERD[(VERD.index(v) + 1) % 4]

def item_edits(items, i):
    out = {}
    m = copy.deepcopy(items); m[i]["verdict"] = flip(m[i]["verdict"]); out["flip_verdict"] = m
    m = copy.deepcopy(items)
    if m[i].get("span"):
        m[i]["span"] = [m[i]["span"][0] + 1, m[i]["span"][1] + 1]
    out["shift_span"] = m
    m = copy.deepcopy(items); del m[i]; out["drop_item"] = m
    m = copy.deepcopy(items); m.append(copy.deepcopy(m[i])); out["dup_item"] = m
    m = copy.deepcopy(items); m[i]["value_status"] = "mismatch" if m[i]["value_status"] != "mismatch" else "match"; out["flip_value_status"] = m
    m = copy.deepcopy(items); m[i]["locus"] = dict(m[i]["locus"], node="Shape"); out["edit_locus"] = m
    m = copy.deepcopy(items); m[i]["occurrences"] = m[i]["occurrences"] + 1; out["edit_occurrences"] = m
    return {k: v for k, v in out.items() if v != items}

for r, p, text in pool:
    if len(used) >= N:
        break
    has_chain = bool(P.read_steps(text))
    x0 = text if has_chain else P.add_step(text, {"op": "generate", "agent": "measure", "input_sha256": "none"}, text)
    if P.verify(x0)["status"] != "verified":
        skipped_stale_on_stamp += 1            # x3dprov limitation: a scene with no <head> goes stale the moment it is stamped
        continue
    claims = mk_claims(T.scene_text(x0))
    if len(claims) < 6:
        skipped += 1
        continue
    srct = {"scene": T.scene_text(x0)}
    t0 = time.perf_counter()
    rep = X.check_claims(claims, [X.Source("scene", srct["scene"], "x3d")])
    t1 = time.perf_counter()
    variants = {}
    for mode, cap in (("sidecar", 0), ("inline", 10 ** 9)):
        for seal in (True, False):
            xv, side, _ = T.trace_claims(x0, claims, srct, kinds={"scene": "x3d"}, inline_cap=cap, seal=seal)
            variants[(mode, seal)] = (xv, side)
    t2 = time.perf_counter()
    x_sc, side_sc = variants[("sidecar", True)]
    a = audit(x_sc, {rhash(x_sc): side_sc})
    t3 = time.perf_counter()
    if a["status"] != "verified":
        base_fail += 1
        base_fail_why.append(["%s:%s" % (r, p), a["status"], a["problems"][:2]])
        continue
    used.append("%s:%s" % (r, p))
    timing["scenes"] += 1; timing["claims"] += len(claims); timing["bytes"] += len(srct["scene"].encode())
    timing["check_s_x1e6"] += int((t1 - t0) * 1e6); timing["trace_claims_s_x1e6"] += int((t2 - t1) * 1e6 / 4)
    timing["audit_s_x1e6"] += int((t3 - t2) * 1e6)
    items = rep.to_dict()["sources"]
    n = len(items)
    for _ in range(2):
        i, j = rnd.randrange(n), rnd.randrange(n)
        # A: sidecar items edited, step untouched
        for name, mi in item_edits(items, i).items():
            for seal in (True, False):
                xv, side = variants[("sidecar", seal)]
                rh = rhash(xv)
                rec_("A:sidecar_items_edited[%s,%s]" % (name, "sealed" if seal else "unsealed"), audit(xv, {rh: mi})["status"])
        # B: items edited and the last step patched to match
        for name, mi in item_edits(items, i).items():
            for seal in (True, False):
                xv, side = variants[("sidecar", seal)]
                tn = last_trace_n(xv)
                rec = json.loads(step_text(xv, tn))
                r2 = resealed_rec(rec, mi)
                r2.update({k: rec[k] for k in ("prev", "input_sha256", "output_sha256")})
                xb = swap_step(xv, tn, P._dumps(r2))
                rec_("B:step_patched_to_match[%s,%s]" % (name, "sealed" if seal else "unsealed"), audit(xb, {r2["report_sha256"]: mi})["status"])
        # C: inline item edited inside the step text, nothing re-hashed
        for name in ("flip_verdict", "shift_span"):
            for seal in (True, False):
                xv, _ = variants[("inline", seal)]
                tn = last_trace_n(xv)
                rec = json.loads(step_text(xv, tn))
                if name == "flip_verdict":
                    rec["items"][i]["verdict"] = flip(rec["items"][i]["verdict"])
                elif rec["items"][i].get("span"):
                    rec["items"][i]["span"] = [rec["items"][i]["span"][0] + 1, rec["items"][i]["span"][1] + 1]
                xc = swap_step(xv, tn, P._dumps(rec))
                rec_("C:inline_item_edited[%s,%s]" % (name, "sealed" if seal else "unsealed"), audit(xc)["status"])
        # D: claim fields edited inside the items (the report hash is left alone, and then also re-hashed)
        for name in ("value", "quote"):
            mi = copy.deepcopy(items)
            if name == "value":
                mi[i]["value"] = str(mi[i]["value"]) + " 9"
            else:
                mi[i]["quote"] = items[j]["quote"]
            if mi == items:
                continue
            xv, _ = variants[("sidecar", True)]
            rh = rhash(xv)
            rec_("D:claim_edited[%s]" % name, audit(xv, {rh: mi})["status"])
            xv2, _ = variants[("sidecar", False)]
            tn = last_trace_n(xv2)
            rec = json.loads(step_text(xv2, tn))
            r2 = resealed_rec(rec, mi); r2.update({k: rec[k] for k in ("prev", "input_sha256", "output_sha256")})
            rec_("D:claim_edited_and_rehashed[%s,unsealed]" % name, audit(swap_step(xv2, tn, P._dumps(r2)), {r2["report_sha256"]: mi})["status"])
        # E: consistent forgery (a fresh honest trace of other claims)
        fc = copy.deepcopy(claims); fc[i]["value"] = str(fc[i]["value"]) + " 9"
        xf1, _, _ = T.trace_claims(x0, fc, srct, kinds={"scene": "x3d"}, inline_cap=10 ** 9, seal=False)
        rec_("E1:consistent_forgery_last_step_unsealed", audit(xf1)["status"])
        xs, _ = variants[("inline", True)]
        tn = last_trace_n(xs)
        xf2 = swap_step(xs, tn, step_text(xf1, last_trace_n(xf1)))       # forged trace step; the summary step after it is untouched
        rec_("E2:forged_trace_step_later_step_untouched", audit(xf2)["status"])
        xf3, _, _ = T.trace_claims(x0, fc, srct, kinds={"scene": "x3d"}, inline_cap=10 ** 9, seal=True)
        rec_("E3:trace_and_later_steps_rechained", audit(xf3)["status"])
        # F: scene edits after the trace
        xv, side = variants[("sidecar", True)]
        rh = rhash(xv)
        em = {}
        ci = claims[i]
        vs = xv.find(ci["quote"])
        digits = [k for k, ch in enumerate(ci["quote"]) if ch.isdigit()]
        if vs >= 0 and digits:
            k = vs + rnd.choice(digits)
            em["claimed_value_digit_edit"] = xv[:k] + str((int(xv[k]) + 1) % 10) + xv[k + 1:]
        body = xv.find("<Scene")
        k2 = xv.find("/>", body)
        em["formatting_only_space_before_slash_gt"] = xv[:k2] + " " + xv[k2:] if k2 >= 0 else None
        k3 = xv.find(">", body)
        em["comment_inserted"] = xv[:k3 + 1] + "<!-- note -->" + xv[k3 + 1:] if k3 >= 0 else None
        em["unclaimed_head_meta_added"] = xv.replace("<head>", '<head><meta name="title" content="x"/>', 1) if "<head>" in xv else None
        for name, xm in em.items():
            if xm and xm != xv:
                rec_("F:scene_edited[%s]" % name, T.audit_trace(xm, {"scene": T.scene_text(xm)}, sidecars={rh: side})["status"])

def fam(cls):
    return cls.split("[")[0]

by_class = {k: {"n": v["n"], "detected": v["detected"], "rate": round(v["detected"] / v["n"], 4)} for k, v in sorted(stats.items())}
by_family = collections.defaultdict(lambda: {"n": 0, "detected": 0})
for k, v in stats.items():
    f = fam(k)
    by_family[f]["n"] += v["n"]; by_family[f]["detected"] += v["detected"]
by_family = {k: {**v, "rate": round(v["detected"] / v["n"], 4)} for k, v in sorted(by_family.items())}
res = {"engine_sha256": hashlib.sha256(open(os.path.join(SRC, "x3dtrace.py"), "rb").read()).hexdigest()[:16],
       "python": sys.version.split()[0], "seed": SEED, "scenes_used": len(used), "scenes_skipped_few_claims": skipped, "scenes_skipped_stale_on_stamp": skipped_stale_on_stamp,
       "baseline_failures": base_fail, "baseline_failure_reasons": base_fail_why, "scenes": used, "by_family": by_family, "by_class": by_class,
       "status_histogram": {k: dict(v) for k, v in sorted(hist.items())},
       "timing": {"scenes": timing["scenes"], "claims": timing["claims"], "scene_bytes": timing["bytes"],
                  "ms_per_claim_engine_check": round(timing["check_s_x1e6"] / 1000 / timing["claims"], 3),
                  "ms_per_claim_trace_claims": round(timing["trace_claims_s_x1e6"] / 1000 / timing["claims"], 3),
                  "ms_per_claim_audit": round(timing["audit_s_x1e6"] / 1000 / timing["claims"], 3)}}
json.dump(res, open(out_path, "w"), indent=1)
print(json.dumps({k: res[k] for k in res if k not in ("scenes", "by_class", "status_histogram")}, indent=1))
