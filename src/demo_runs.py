"""Demonstration run: stamp the real local export-suite runs and the physics-stress data, verify, audit and tamper with them.
Usage: python3 demo_runs.py <work-dir> <outdir> <stamped-dir> [--blender-io REPO]
  work-dir     holds suite-run-*/out and physics-stress/ (default layout of ~/Projects/x3d/work)
  outdir       small committed evidence: result.json, the physics ledger, the steps of the newest suite run
  stamped-dir  the large stamped scenes (5 to 7 MB each), not for committing
Run with a python that has lxml, e.g. x3d_mcp/.venv/bin/python."""
import sys, os, re, json, glob, shutil, argparse, tempfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P
import ingest_runs as R


def core_line(log):
    """'CORE conformance: 143/147 passed' from the run's own validate.log, as an independent cross-check of our re-validation."""
    m = re.findall(r"CORE conformance: (\d+)/(\d+)", open(log).read()) if os.path.exists(log) else []
    return list(map(int, m[-1])) if m else None


def main(work, outdir, stamped, bio):
    os.makedirs(outdir, exist_ok=True); res = {"suite_runs": [], "tamper": {}}
    runs = sorted(glob.glob(work + "/suite-run-*/out"), key=lambda p: json.load(open(p + "/x3d_suite_manifest.json"))["created"])
    for out in runs:
        name = os.path.basename(os.path.dirname(out)); sd = os.path.join(stamped, name); rows = R.stamp_suite(out, sd, bio)
        m = json.load(open(out + "/x3d_suite_manifest.json")); core = sum(r["counts"].get("CORE:PASS", 0) for r in rows); tot = core + sum(r["counts"].get("CORE:FAIL", 0) + r["counts"].get("CORE:ERROR", 0) for r in rows)
        res["suite_runs"].append({"run": name, "created": m["created"], "blender": m["blender"], "cases": len(m["cases"]), "core_pass_total": [core, tot],
                                  "core_in_validate_log": core_line(os.path.join(os.path.dirname(out), "validate.log")), "profiles": rows})
    newest = runs[-1]; nsd = os.path.join(stamped, os.path.basename(os.path.dirname(newest)))
    for f in glob.glob(nsd + "/*.steps.json"):
        shutil.copy(f, outdir)
    # physics ledger
    ph = work + "/physics-stress"; ledger = R.stamp_physics(ph, outdir, os.path.dirname(os.path.abspath(__file__)))
    steps = P.summary(ledger)
    res["physics"] = {"verify": P.verify(ledger), "audit": R.audit_physics(ledger, ph)["status"], "ledger_bytes": len(ledger.encode()), "tools": steps[0]["tools"],
                      "steps": [{"n": i, "op": s["op"], **{k: s[k] for k in ("agent", "suite", "records", "findings_total") if k in s}, **({"groups": len(s["groups"])} if "groups" in s else {})} for i, s in enumerate(steps, 1)]}
    # tamper: physics (one metric inside the record, one in the source, the last step)
    n = next(i for i, s in enumerate(steps, 1) if s.get("suite") == "stability")
    old = steps[n - 1]["groups"][0]
    t = R.edit_step(ledger, n, lambda s: s["groups"][0].__setitem__(4, "tampered" if isinstance(old[4], bool) else old[4] * 10))
    tmp = tempfile.mkdtemp(); cp = os.path.join(tmp, "physics-stress")
    shutil.copytree(ph, cp, ignore=shutil.ignore_patterns("out", "scripts", "dashboard.html", "*.log"))
    mf = cp + "/metrics/blender.jsonl"; lines = open(mf).read().splitlines(); key = lambda r: (r["suite"], r["case"], r["metric"], json.dumps(r["params"], sort_keys=True))
    once = collections.Counter(key(json.loads(l)) for l in lines)       # a record with no repeats, so the group median moves and audit can name the metric
    i = next(i for i, l in enumerate(lines) if isinstance(json.loads(l)["value"], float) and once[key(json.loads(l))] == 1)
    r = json.loads(lines[i]); r["value"] = r["value"] * 1.01; lines[i] = json.dumps(r); open(mf, "w").write("\n".join(lines) + "\n")
    a = R.audit_physics(ledger, cp); last = R.edit_step(ledger, len(steps), lambda s: s.__setitem__("records_total", s["records_total"] - 1))
    res["tamper"]["physics"] = {
        "pristine": P.verify(ledger)["status"],
        "metric edited inside the record (stability group 0)": {"verify": P.verify(t)["status"], "first_problem": P.verify(t)["problems"][0]},
        "one single-repeat float value +1% in the source JSONL": {"verify_of_record": P.verify(ledger)["status"], "audit": a["status"], "named": a["problems"][:2]},
        "LAST step edited (no successor, unsigned)": {"verify": P.verify(last)["status"], "audit_with_sources": R.audit_physics(last, ph)["status"]}}
    # tamper: the newest suite run, main profile
    out = newest; sx = open(nsd + "/x3d_suite_main.stamped.x3d", encoding="utf-8").read(); v = [s for s in P.summary(sx)][1]
    flip = next(i for i, c in enumerate(v["cases"]) if c[1] != "PASS")
    t1 = R.edit_step(sx, 2, lambda s: s["cases"][flip].__setitem__(1, "PASS"))
    t2 = re.sub(r'(<Transform [^>]*?translation=")([^"]*)', r"\g<1>9 9 9", sx, count=1); assert t2 != sx
    res["tamper"]["suite_main"] = {"pristine": P.verify(sx)["status"], "audit": R.audit_suite(sx, out, bio)["status"],
                                   "a non-passing case (%s) flipped to PASS inside the record" % v["cases"][flip][0]: P.verify(t1)["status"],
                                   "a Transform translation edited in the scene": P.verify(t2)["status"]}
    json.dump(res, open(os.path.join(outdir, "result.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({"suite": [(r["run"], r["core_pass_total"], r["core_in_validate_log"], [p["chain_status"] for p in r["profiles"]]) for r in res["suite_runs"]],
                      "physics": [res["physics"]["verify"]["status"], res["physics"]["audit"], res["physics"]["ledger_bytes"]], "tamper": res["tamper"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("outdir"); ap.add_argument("stamped"); ap.add_argument("--blender-io", required=True)
    a = ap.parse_args(); main(a.work, a.outdir, a.stamped, a.blender_io)
