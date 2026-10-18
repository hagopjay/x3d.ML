"""Tests for src/ingest_runs.py: fixtures are tiny and built here; the real-data tests skip when the local runs are absent.
Run: x3d_mcp/.venv/bin/python -m pytest tests/ -q      (x3dprov needs lxml)"""
import os, sys, json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import x3dprov as P
import ingest_runs as R

W = os.path.expanduser("~/Projects/x3d/work")
PHYS, SUITE_OUT, BIO = W + "/physics-stress", W + "/suite-run-upstream/out", os.path.expanduser("~/Projects/x3d/x3d-blender-io")


def jl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("\n".join(json.dumps(r) if isinstance(r, dict) else r for r in rows) + "\n")


def rec(agent, suite, case, metric, value, **params):
    return {"agent": agent, "suite": suite, "case": case, "metric": metric, "value": value, "unit": "ms", "params": params, "repeat": 0, "ts": "2026-10-16T00:00:00Z"}


@pytest.fixture
def phys(tmp_path):
    r = str(tmp_path / "physics-stress")
    jl(r + "/metrics/blender.jsonl", [rec("blender", "env", "machine", "blender", "5.1.0"), rec("blender", "env", "machine", "sha_x3d_blender_io", "5da2707"),
        *[rec("blender", "rigid_scale", "spheres", "step_ms", v, n_bodies=100) for v in (1.0, 2.0, 9.0)], rec("blender", "rigid_scale", "spheres", "step_ms", 5.0, n_bodies=200),
        rec("blender", "stability", "tunnel", "speed", True), rec("blender", "done", "all", "complete", True), "not json {"])
    jl(r + "/metrics/x3d.jsonl", [rec("x3d", "env", "machine", "blender", "Blender 5.1.0 (hash adfe2921d5f3)"), rec("x3d", "env", "machine", "sha_x3d_blender_io", "5da2707ed0b26ce4527cb3911221897b971feacf"),
        rec("x3d", "detection", "valid_scenes", "count", 48), rec("x3d", "done", "all", "complete", True)])
    os.makedirs(r + "/findings"); open(r + "/SCHEMA.md", "w").write("schema\n")
    json.dump([{"id": "B-01", "severity": "major", "component": "blender-physics", "title": "t", "evidence": "e", "impact": "i"},
               {"id": "B-02", "severity": "info", "component": "x3d_mcp", "title": "t2", "evidence": "e2", "impact": "i2"}], open(r + "/findings/blender.json", "w"))
    return r


tamper = R.edit_step


def stamp_phys(root, tmp_path):
    return R.stamp_physics(root, str(tmp_path / "out"))


# ---- physics ledger -----------------------------------------------------------------------------------------------

def test_ledger_verifies_and_is_deterministic(phys, tmp_path):
    a = stamp_phys(phys, tmp_path)
    assert P.verify(a)["status"] == "verified"
    ops = [(s["op"], s.get("suite")) for s in P.summary(a)]
    assert ops == [("ingest", None), ("measure", "env"), ("measure", "rigid_scale"), ("measure", "stability"), ("measure", "done"), ("measure", "env"), ("measure", "detection"),
                   ("measure", "done"), ("judge", None), ("summary", None)]
    assert a == R.stamp_physics(phys, str(tmp_path / "out2"))          # same files, same bytes


def test_groups_are_medians_over_repeats_and_params_split_groups(phys, tmp_path):
    step = next(s for s in P.summary(stamp_phys(phys, tmp_path)) if s.get("suite") == "rigid_scale")
    assert sorted((g[3], g[4]) for g in step["groups"]) == [(1, 5.0), (3, 2.0)]    # n=3 repeats -> median 2.0 (the 9.0 outlier ignored); n=1 -> 5.0
    assert step["records"] == 4 and len({g[2] for g in step["groups"]}) == 2


def test_tools_and_malformed_lines_recorded(phys, tmp_path):
    first = P.summary(stamp_phys(phys, tmp_path))[0]
    assert first["tools"]["blender"] == ["5.1.0"] and first["tools"]["sha_x3d_blender_io"] == ["5da2707"]    # two agents, two spellings, one fact
    assert first["files"]["metrics/blender.jsonl"]["malformed_lines"] == 1 and P.summary(stamp_phys(phys, tmp_path))[-1]["malformed_lines"] == 1
    assert P.summary(stamp_phys(phys, tmp_path))[-1]["complete"] == {"blender": True, "x3d": True}


def test_metric_edited_inside_the_record_breaks_the_chain(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    t = tamper(xml, 4, lambda s: s["groups"][0].__setitem__(4, 999.0))              # step 4 = stability: one metric of one group
    v = P.verify(t)
    assert v["status"] == "broken-chain" and any("step 5" in p for p in v["problems"])      # the successor no longer links to it


def test_metric_edited_in_the_source_is_caught_by_audit_not_by_verify(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    assert R.audit_physics(xml, phys)["status"] == "verified"
    lines = open(phys + "/metrics/blender.jsonl").read().replace('"value": 2.0', '"value": 3.0')
    open(phys + "/metrics/blender.jsonl", "w").write(lines)
    assert P.verify(xml)["status"] == "verified"                                    # the chain cannot see a file it does not carry
    a = R.audit_physics(xml, phys)
    assert a["status"] == "evidence-mismatch" and any("spheres/step_ms" in p and "record [3, 2.0] vs source [3, 3.0]" in p for p in a["problems"])


def test_a_repeat_that_leaves_the_median_alone_still_changes_the_record_digest(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    open(phys + "/metrics/blender.jsonl", "w").write(open(phys + "/metrics/blender.jsonl").read().replace('"value": 9.0', '"value": 8.0'))
    a = R.audit_physics(xml, phys)
    assert a["status"] == "evidence-mismatch" and any("records_sha256" in p for p in a["problems"])


def test_removed_step_and_edited_finding_break_the_chain(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    gone = xml.replace(P._attr(dict(P.read_steps(xml))[3]), P._attr("{}"), 1)
    assert P.verify(gone)["status"] == "broken-chain"
    t = tamper(xml, 9, lambda s: s["findings"][0].__setitem__(1, "info"))           # step 9 = judge, still has the summary after it
    assert P.verify(t)["status"] == "broken-chain"


def test_last_step_edit_is_the_documented_hole_and_audit_closes_it(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    t = tamper(xml, 10, lambda s: s.__setitem__("records_total", 1))
    assert P.verify(t)["status"] == "verified"                                      # DESIGN.md section 3, limit 1: no successor
    assert R.audit_physics(t, phys)["status"] == "evidence-mismatch"                # with the sources the last step is checked too


def test_source_file_hash_covers_findings_text(phys, tmp_path):
    xml = stamp_phys(phys, tmp_path)
    d = json.load(open(phys + "/findings/blender.json")); d[0]["impact"] = "worse"; json.dump(d, open(phys + "/findings/blender.json", "w"))
    assert any("findings" in p or "files" in p for p in R.audit_physics(xml, phys)["problems"])


# ---- export suite -------------------------------------------------------------------------------------------------

SCENE = '''<?xml version="1.0" encoding="UTF-8"?>
<X3D version="4.0" profile="Immersive"><head><meta name="generator" content="X3D Blender I/O v2.6.1"/></head>
<Scene><Transform DEF="A"><Shape><Box size="1 1 1"/></Shape></Transform></Scene></X3D>
'''


def make_suite(root, fail=False):
    out = os.path.join(root, "suite-run-x", "out"); os.makedirs(out)
    open(out + "/main.x3d", "w").write(SCENE)
    json.dump({"created": "2026-10-15T22:34:21", "suite_version": "2.0.0", "blender": "5.1.0", "profiles": {"main": {"file": "main.x3d", "export": {"x3d_version": "X3D40"}}},
               "cases": [{"id": "Z00.a"}, {"id": "Z00.b"}, {"id": "Z01.c"}], "export_results": {"main": {"result": ["FINISHED"], "seconds": 1.5, "bytes": len(SCENE.encode())}}}, open(out + "/x3d_suite_manifest.json", "w"))
    res = lambda i, tier, v, ok=True: {"id": i, "zone": i[:3], "tier": tier, "profile": "main", "verdict": v, "results": [{"ok": ok, "msg": "m " + i, "kind": "k"}]}
    v = {"manifest": {"created": "2026-10-15T22:34:21", "suite_version": "2.0.0"}, "generator": "X3D Blender I/O v2.6.1", "validator": "2.0.0",
         "results": [res("Z00.a", "CORE", "PASS"), res("Z00.b", "FIDELITY", "WARN", False), res("Z01.c", "CORE", "FAIL" if fail else "PASS", not fail)]}
    return out, v


def test_suite_chain_verifies_and_verdict_follows_core_failures(tmp_path):
    for fail, verdict in ((False, "valid"), (True, "invalid")):
        out, v = make_suite(str(tmp_path / str(fail)), fail)
        rows = R.stamp_suite(out, str(tmp_path / ("o" + str(fail))), vjson=v)
        assert [(r["chain_status"], r["steps"], r["verdict"]) for r in rows] == [("verified", 3, verdict)]
    steps = P.summary(open(str(tmp_path / "oTrue" / "main.stamped.x3d")).read())
    assert steps[1]["failed_cases"] == {"Z01.c": ["m Z01.c"]} and steps[1]["counts"] == {"CORE:FAIL": 1, "CORE:PASS": 1, "FIDELITY:WARN": 1}
    assert steps[0]["bytes_match_manifest"] and steps[0]["tool"] == "Blender 5.1.0" and steps[0]["exporter"] == "X3D Blender I/O v2.6.1"


def test_suite_case_verdict_flipped_in_the_record_breaks_the_chain(tmp_path):
    out, v = make_suite(str(tmp_path))
    R.stamp_suite(out, str(tmp_path / "o"), vjson=v); xml = open(str(tmp_path / "o" / "main.stamped.x3d")).read()
    t = tamper(xml, 2, lambda s: s["cases"][1].__setitem__(1, "PASS"))
    assert P.verify(t)["status"] == "broken-chain"


def test_suite_scene_edit_is_stale_and_edited_export_fails_audit(tmp_path):
    out, v = make_suite(str(tmp_path))
    R.stamp_suite(out, str(tmp_path / "o"), vjson=v); xml = open(str(tmp_path / "o" / "main.stamped.x3d")).read()
    assert P.verify(xml.replace('size="1 1 1"', 'size="9 9 9"'))["status"] == "stale"
    assert R.audit_suite(xml, out, vjson=v)["status"] == "verified"
    open(out + "/main.x3d", "w").write(SCENE.replace("1 1 1", "2 2 2"))              # the export on disk changes after ingest
    a = R.audit_suite(xml, out, vjson=v)
    assert a["status"] == "evidence-mismatch" and any("file_sha256" in p for p in a["problems"])


def test_suite_verdict_edited_in_validator_result_fails_audit(tmp_path):
    out, v = make_suite(str(tmp_path))
    R.stamp_suite(out, str(tmp_path / "o"), vjson=v); xml = open(str(tmp_path / "o" / "main.stamped.x3d")).read()
    v["results"][1]["verdict"] = "PASS"
    a = R.audit_suite(xml, out, vjson=v)
    assert a["status"] == "evidence-mismatch" and any("Z00.b" in p for p in a["problems"])


def test_validator_result_of_another_run_is_refused(tmp_path):
    out, v = make_suite(str(tmp_path))
    v["manifest"]["created"] = "2026-10-16T00:00:00"
    with pytest.raises(ValueError):
        R.stamp_suite(out, str(tmp_path / "o"), vjson=v)


def test_cli_roundtrip(phys, tmp_path, capsys):
    assert R.main(["physics", phys, str(tmp_path / "o")]) == 0
    led = str(tmp_path / "o" / "physics-stress.ledger.x3d")
    assert R.main(["verify", led, "--source", phys]) == 0
    open(phys + "/SCHEMA.md", "w").write("changed\n")
    assert R.main(["verify", led, "--source", phys]) == 1 and "evidence-mismatch" in capsys.readouterr().out


# ---- the real local data (skipped where it is not) -----------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(PHYS + "/metrics/blender.jsonl"), reason="local physics-stress data not present")
def test_real_physics_ledger(tmp_path):
    xml = R.stamp_physics(PHYS, str(tmp_path))
    assert P.verify(xml)["ok"] and R.audit_physics(xml, PHYS)["ok"]
    assert P.summary(xml)[-1]["records_total"] >= 3000 and len(xml) < 1_000_000


@pytest.mark.skipif(not (os.path.exists(SUITE_OUT + "/x3d_suite_manifest.json") and os.path.exists(BIO + "/" + R.VALIDATOR_SCRIPT)), reason="local suite run or validator not present")
def test_real_suite_run(tmp_path):
    rows = R.stamp_suite(SUITE_OUT, str(tmp_path), BIO)
    assert {r["profile"] for r in rows} == {"main", "crease", "x41"} and all(r["chain_status"] == "verified" for r in rows)
    xml = open(str(tmp_path / "x3d_suite_main.stamped.x3d"), encoding="utf-8").read()
    assert R.audit_suite(xml, SUITE_OUT, BIO)["ok"] and P.summary(xml)[0]["cases_in_manifest"] == 194
