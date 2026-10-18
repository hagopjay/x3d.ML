"""Ingest test-run evidence into x3dprov chains (plan: docs/INTEGRATION-SUITE-PHYSICS.md).
  suite    an X3D export-suite run (x3d_suite_manifest.json + exported .x3d files + validate_x3d_export.py results):
           each exported file gets ingest -> validate -> summary, written to <outdir> as <file>.stamped.x3d
  physics  a physics-stress directory (metrics/*.jsonl, findings/*.json, report/): a ledger scene with no geometry,
           ingest -> measure per (agent, suite) -> judge per findings file -> summary
  verify   verify() a stamped file; with --source also audit() it against the files it was made from
audit() rebuilds the expected steps from the sources and diffs them against the record: verify() says the chain is intact,
audit() says the record still matches the evidence (a metric edited in a JSONL leaves the chain intact).
Run with a python that has lxml (x3dprov needs it), e.g. x3d_mcp/.venv/bin/python.
Usage: python3 ingest_runs.py suite <suite-run/out> <outdir> [--blender-io REPO] [--validator-json FILE]
       python3 ingest_runs.py physics <physics-stress-dir> <outdir>
       python3 ingest_runs.py verify <stamped.x3d> [--source DIR] [--blender-io REPO] [--validator-json FILE]"""
import sys, os, re, json, glob, hashlib, argparse, subprocess, tempfile, statistics
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P

IGNORE = {"agent_ref", "repo"}                           # facts about the ingesting machine, not about the evidence
CHAIN = {"prev", "input_sha256", "output_sha256"}
SUITE_SCRIPT, VALIDATOR_SCRIPT = "tests/suite/x3d_test_suite.py", "tests/suite/validate_x3d_export.py"
FAIL_VERDICTS = ("FAIL", "ERROR")
CARRIER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D version="4.0" profile="Interchange">
  <head>
    <meta name="title" content="%(name)s evidence ledger"/>
    <meta name="description" content="No geometry: this scene carries an x3dprov chain over test-run metrics. The chain is the content."/>
    <meta name="generator" content="x3d.ML ingest_runs.py"/>
  </head>
  <Scene>
    <WorldInfo title="%(name)s evidence ledger"/>
  </Scene>
</X3D>
"""
_dumps = P._dumps


def _sha(b) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def file_sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def git_ref(repo, created=None):
    """sha, branch and tracked-file dirtiness of a checkout AT INGEST; predates_run compares the commit date with the run's start."""
    if not repo:
        return None
    def g(*a):
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True).stdout.strip()
    sha = g("rev-parse", "--short=7", "HEAD")
    if not sha:
        return None
    ref = {"name": os.path.basename(os.path.abspath(repo)), "sha": sha, "branch": g("branch", "--show-current"),
           "dirty_tracked": len(g("status", "--porcelain", "--untracked-files=no").splitlines()), "commit_date": g("log", "-1", "--format=%cI")}
    for k, rel in (("validator_sha256", VALIDATOR_SCRIPT), ("suite_script_sha256", SUITE_SCRIPT)):
        p = os.path.join(repo, rel)
        if os.path.exists(p):
            ref[k] = file_sha(p)
    if created:
        ref["predates_run"] = datetime.fromisoformat(ref["commit_date"]) <= datetime.fromisoformat(created).astimezone()
    return ref


# ---- export suite -------------------------------------------------------------------------------------------------

def run_validator(repo, out_dir):
    """Run the suite's own stdlib-only validator; exit code 1 just means a CORE case failed."""
    tmp = os.path.join(tempfile.mkdtemp(), "v.json")
    r = subprocess.run([sys.executable, "-I", os.path.join(repo, VALIDATOR_SCRIPT), out_dir, "--json", tmp, "--no-color"], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise RuntimeError("validator failed: " + r.stderr[-400:])
    return json.load(open(tmp))


def suite_steps(out_dir, vjson, profile, repo=None):
    """-> (steps, file path) for one exported profile file. The validator result must belong to this run's manifest."""
    m = json.load(open(os.path.join(out_dir, "x3d_suite_manifest.json")))
    vm = vjson["manifest"]
    if (vm["created"], vm["suite_version"]) != (m["created"], m["suite_version"]) or {c["id"] for c in vjson["results"]} != {c["id"] for c in m["cases"]}:
        raise ValueError("validator result does not belong to this manifest (created / suite_version / case ids differ)")
    path = os.path.join(out_dir, m["profiles"][profile]["file"])
    res = [r for r in vjson["results"] if r["profile"] == profile]
    exp = m.get("export_results", {}).get(profile, {}); ingest_repo = git_ref(repo, m["created"])
    ingest = {"op": "ingest", "kind": "suite-export", "agent": "x3d-blender-io", "agent_ref": ingest_repo and ingest_repo["sha"],
              "origin": os.path.basename(os.path.dirname(os.path.abspath(out_dir))) + "/" + os.path.basename(os.path.abspath(out_dir)) + "/" + os.path.basename(path),
              "profile": profile, "file_sha256": file_sha(path), "bytes": os.path.getsize(path), "bytes_match_manifest": os.path.getsize(path) == exp.get("bytes"),
              "exporter": vjson["generator"], "tool": "Blender " + m["blender"], "suite_version": m["suite_version"], "run_created": m["created"],
              "export": m["profiles"][profile]["export"], "export_seconds": exp.get("seconds"), "export_result": exp.get("result"),
              "manifest_sha256": file_sha(os.path.join(out_dir, "x3d_suite_manifest.json")), "cases_in_manifest": len(m["cases"]), "repo": ingest_repo}
    counts = {}
    for r in res:
        counts[r["tier"] + ":" + r["verdict"]] = counts.get(r["tier"] + ":" + r["verdict"], 0) + 1
    failed = [r for r in res if r["tier"] == "CORE" and r["verdict"] in FAIL_VERDICTS]
    val = {"op": "validate", "validator": "validate_x3d_export.py", "validator_ref": vjson["validator"], "agent_ref": ingest_repo and ingest_repo["sha"],
           "profile": profile, "verdict": "invalid" if failed else "valid", "counts": dict(sorted(counts.items())),
           "failed_cases": {r["id"]: [c["msg"] for c in r["results"] if not c["ok"]][:3] for r in failed},
           "cases": [[r["id"], r["verdict"]] for r in res], "results_sha256": _sha(_dumps(res)),
           "artifacts": {n: file_sha(os.path.join(out_dir, "..", n)) for n in ("validate.log",) if os.path.exists(os.path.join(out_dir, "..", n))}
                        | {n: file_sha(os.path.join(out_dir, n)) for n in ("report.html",) if os.path.exists(os.path.join(out_dir, n))}}
    done = {"op": "summary", "agent": "ingest_runs.py", "profile": profile, "verdict": val["verdict"], "cases": len(res),
            "note": "redundant roll-up so the validate step has a successor (DESIGN.md section 3, limit 1)"}
    return [ingest, val, done], path


def suite_profiles(out_dir, vjson):
    m = json.load(open(os.path.join(out_dir, "x3d_suite_manifest.json")))
    have = {r["profile"] for r in vjson["results"]}
    return [p for p in m["profiles"] if p in have and os.path.exists(os.path.join(out_dir, m["profiles"][p]["file"]))]


def stamp_suite(out_dir, outdir, repo=None, vjson=None):
    """Stamp every exported profile file of a run; writes <file>.stamped.x3d and <file>.steps.json to outdir. -> list of summaries."""
    vjson = vjson or run_validator(repo, out_dir)
    os.makedirs(outdir, exist_ok=True); rows = []
    for prof in suite_profiles(out_dir, vjson):
        steps, path = suite_steps(out_dir, vjson, prof, repo)
        xml = open(path, encoding="utf-8").read()
        for s in steps:
            xml = P.add_step(xml, s)
        base = os.path.splitext(os.path.basename(path))[0]
        open(os.path.join(outdir, base + ".stamped.x3d"), "w", encoding="utf-8").write(xml)
        json.dump(P.summary(xml), open(os.path.join(outdir, base + ".steps.json"), "w"), indent=1, sort_keys=True)
        v = P.verify(xml)
        rows.append({"profile": prof, "file": os.path.basename(path), "bytes": steps[0]["bytes"], "file_sha256": steps[0]["file_sha256"], "chain_status": v["status"],
                     "steps": v["steps"], "verdict": steps[1]["verdict"], "counts": steps[1]["counts"], "failed_cases": sorted(steps[1]["failed_cases"])})
    return rows


# ---- physics stress ledger ----------------------------------------------------------------------------------------

def _read_jsonl(path):
    rows, bad = [], 0
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            bad += 1; continue
        if isinstance(r, dict) and all(k in r for k in ("suite", "case", "metric", "value")):
            rows.append(r)
        else:
            bad += 1
    return rows, bad


def _agg(vals):
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return statistics.median(vals)
    return vals[0] if all(v == vals[0] for v in vals) else "mixed"


def _groups(rows):
    """[case, metric, params-id, n repeats, median] per distinct (case, metric, params); params-id is 8 hex of the params, '-' for none."""
    g = {}
    for r in rows:
        p = r.get("params") or {}
        g.setdefault((r["case"], r["metric"], _sha(_dumps(p))[:8] if p else "-"), []).append(r["value"])
    return [[c, m, p, len(v), _agg(v)] for (c, m, p), v in g.items()]


def _tool_versions(env):
    """Machine facts from the runs' own env suites; short shas, Blender reduced to its version, so two agents agree or visibly conflict."""
    t = {}
    for agent, kv in env.items():
        for k, v in kv.items():
            name = k.split(".", 1)[1]
            if name == "blender" or name.startswith(("sha_", "x3d_py_version", "python")):
                if name == "blender":
                    v = (re.search(r"\d+\.\d+\.\d+", str(v)) or [str(v)])[0]
                elif name.startswith("sha_"):
                    v = str(v)[:7]
                t.setdefault(name, [])
                if v not in t[name]:
                    t[name].append(v)
    return dict(sorted(t.items()))


def physics_steps(root):
    """-> steps (without chain fields) for a physics-stress directory. Deterministic: same files, same steps."""
    mfiles = sorted(glob.glob(os.path.join(root, "metrics", "*.jsonl"))); ffiles = sorted(glob.glob(os.path.join(root, "findings", "*.json")))
    extra = [p for p in (os.path.join(root, "SCHEMA.md"), os.path.join(root, "report", "REPORT.md"), os.path.join(root, "report", "dashboard.html")) if os.path.exists(p)]
    files = {os.path.relpath(p, root): {"sha256": file_sha(p), "bytes": os.path.getsize(p)} for p in mfiles + ffiles + extra}
    steps, env, total, complete, bad_total, suites = [], {}, 0, {}, 0, 0
    measure = []
    for p in mfiles:
        rows, bad = _read_jsonl(p); agent = os.path.splitext(os.path.basename(p))[0]; order = {}
        for r in rows:
            order.setdefault(r["suite"], []).append(r)
        for suite, srows in order.items():
            if suite == "env":
                for r in srows:
                    env.setdefault(agent, {})[r["case"] + "." + r["metric"]] = r["value"]
            measure.append({"op": "measure", "agent": agent, "suite": suite, "source": os.path.relpath(p, root), "records": len(srows), "records_sha256": _sha("\n".join(_dumps(r) for r in srows)), "groups": _groups(srows)})
        files[os.path.relpath(p, root)].update(records=len(rows), malformed_lines=bad)
        complete[agent] = "done" in order; total += len(rows); suites += len(order); bad_total += bad
    steps.append({"op": "ingest", "kind": "physics-ledger", "agent": "ingest_runs.py", "origin": os.path.basename(os.path.abspath(root)), "carrier": "ledger scene, no geometry",
                  "files": files, "tools": _tool_versions(env), "env": env})
    steps += measure; nfind = 0
    for p in ffiles:
        fs = json.load(open(p)); agent = os.path.splitext(os.path.basename(p))[0]; nfind += len(fs)
        sev = {}
        for f in fs:
            sev[f["severity"]] = sev.get(f["severity"], 0) + 1
        steps.append({"op": "judge", "agent": agent, "source": os.path.relpath(p, root), "by_severity": dict(sorted(sev.items())), "findings_sha256": _sha(_dumps(fs)),
                      "findings": [[f["id"], f["severity"], f["component"], _sha(_dumps([f.get(k) for k in ("title", "evidence", "impact", "suggested_fix")]))[:8]] for f in fs]})
    steps.append({"op": "summary", "agent": "ingest_runs.py", "files": len(files), "metrics_files": len(mfiles), "records_total": total, "suites": suites, "malformed_lines": bad_total,
                  "findings_total": nfind, "complete": complete, "files_sha256": _sha(_dumps(files)),
                  "note": "redundant roll-up so every informative step has a successor (DESIGN.md section 3, limit 1)"})
    return steps


def stamp_physics(root, outdir, repo=None):
    name = os.path.basename(os.path.abspath(root))
    xml = CARRIER % {"name": name}
    for i, s in enumerate(physics_steps(root)):
        if i == 0 and repo:
            s["agent_ref"] = (git_ref(repo) or {}).get("sha")
        xml = P.add_step(xml, s)
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, name + ".ledger.x3d"), "w", encoding="utf-8").write(xml)
    return xml


def edit_step(xml, n, fn):
    """Rewrite step n's JSON in place with fn(record), leaving every other byte alone: an in-file edit with no re-chaining (tamper tests, demos)."""
    old = dict(P.read_steps(xml))[n]; rec = json.loads(old); fn(rec)
    return xml.replace(P._attr(old), P._attr(_dumps(rec)), 1)


# ---- audit ----------------------------------------------------------------------------------------------------------

def _diff_list(i, rec, exp, label):
    """Name the rows (keyed by their leading fields) that differ between two lists of lists."""
    n = 3 if label == "groups" else 1                       # leading fields that identify a row; the rest is its value
    key, val = (lambda r: tuple(r[:n])), (lambda r: r[n:])
    a, b = {key(r): val(r) for r in rec}, {key(r): val(r) for r in exp}
    out = [f"step {i}: {label} {'/'.join(map(str, k))}: record {a.get(k, '<absent>')} vs source {b.get(k, '<absent>')}" for k in list(a) + [k for k in b if k not in a] if a.get(k, "\0") != b.get(k, "\0")]
    return out[:5] + ([f"step {i}: ... {len(out) - 5} more {label} differ"] if len(out) > 5 else [])


def audit(xml, expected):
    """verify() plus: every recorded step must equal the step rebuilt from the sources (ignoring facts about the ingesting machine).
    status: verified | evidence-mismatch | any verify() failure status (chain problems come first)."""
    chain = P.verify(xml); rec = P.summary(xml); problems = []
    if len(rec) != len(expected):
        problems.append(f"{len(rec)} recorded steps, {len(expected)} expected from the sources")
    for i, (r, e) in enumerate(zip(rec, expected), 1):
        for k in sorted((set(r) | set(e)) - CHAIN - IGNORE):
            if r.get(k) == e.get(k):
                continue
            if k in ("groups", "findings", "cases") and isinstance(r.get(k), list) and isinstance(e.get(k), list):
                problems += _diff_list(i, r[k], e[k], k)
            else:
                problems.append(f"step {i} ({r.get('op')}): field {k} differs from the source")
    status = chain["status"] if not chain["ok"] else ("evidence-mismatch" if problems else "verified")
    return {"ok": chain["ok"] and not problems, "status": status, "chain": chain["status"], "steps": chain["steps"], "problems": chain["problems"] + problems}


def audit_suite(xml, out_dir, repo=None, vjson=None):
    steps = P.summary(xml); prof = steps[0]["profile"]
    vjson = vjson or run_validator(repo, out_dir)
    return audit(xml, suite_steps(out_dir, vjson, prof, repo)[0])


def audit_physics(xml, root):
    return audit(xml, physics_steps(root))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suite"); s.add_argument("out_dir"); s.add_argument("outdir")
    p = sub.add_parser("physics"); p.add_argument("root"); p.add_argument("outdir"); p.add_argument("--repo", help="x3d.ML checkout, recorded as agent_ref")
    v = sub.add_parser("verify"); v.add_argument("stamped"); v.add_argument("--source")
    for q in (s, v):
        q.add_argument("--blender-io", help="x3d-blender-io checkout: runs the validator, records repo sha and script hashes"); q.add_argument("--validator-json")
    a = ap.parse_args(argv)
    vj = json.load(open(a.validator_json)) if getattr(a, "validator_json", None) else None
    if a.cmd == "suite":
        for r in stamp_suite(a.out_dir, a.outdir, a.blender_io, vj):
            print(f"{r['file']}: {r['chain_status']} ({r['steps']} steps), verdict {r['verdict']}, failed {r['failed_cases']}")
    elif a.cmd == "physics":
        r = P.verify(stamp_physics(a.root, a.outdir, a.repo)); print("ledger:", r["status"], r["steps"], "steps")
    else:
        xml = open(a.stamped, encoding="utf-8").read(); first = P.summary(xml)[0] if P.read_steps(xml) else {}
        if a.source and first.get("kind") == "suite-export":
            r = audit_suite(xml, a.source, a.blender_io, vj)
        elif a.source and first.get("kind") == "physics-ledger":
            r = audit_physics(xml, a.source)
        else:
            r = P.verify(xml)
        print(json.dumps(r, indent=1)); return 0 if r["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
