"""x3dprov chain -> OpenLineage RunEvents (spec 2-0-2), so an MLOps lineage server (Marquez or any OpenLineage consumer)
can ingest an X3D generation loop. Read-only view: the file stays the source of truth.

Shape (DESIGN.md section 10):
  one parent run per chain    job <namespace>/<chain name>; START, then COMPLETE, or FAIL when verify() is not `verified`
                              or the last validate verdict is not valid (ErrorMessageRunFacet says which)
  one run per step            job <namespace>/<pipeline>.<op>; START (inputs) then COMPLETE (inputs, outputs), or FAIL
                              when verify() puts a problem on that step or the step's own record says its tool failed;
                              ParentRunFacet links it to the chain run
  datasets                    the scene: namespace "x3d", name = scene name, DatasetVersionDatasetFacet = content sha256;
                              a generate step also reads the prompt (namespace "x3d-prompt", version = prompt_sha256)
  custom run facets           x3dprov_step (the whole record, its sha256 and the eventTime source),
                              x3dprov_validation (validator, ref, verdict, codes), x3dprov_repair (kind, round, report shown,
                              fixes); schemas/x3dprov-openlineage-facets.json
  eventTime                   x3dprov 0.1 records carry no step time; started_at / ended_at / t are used when present,
                              otherwise base_time + one second per step, marked "synthetic-order" in x3dprov_step
Usage: python3 x3dprov_openlineage.py <scene.x3d|steps.json> [name]  -> JSON lines"""
import json, os, sys, uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P
from x3dprov_provo import chain_of

SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"
PRODUCER = "https://x3dprov.example/x3dprov_openlineage/0.1"
FACETS = "https://x3dprov.example/0.1/openlineage-facets.json#/$defs/"
STD = {"parent": "https://openlineage.io/spec/facets/1-2-0/ParentRunFacet.json#/$defs/ParentRunFacet",
       "errorMessage": "https://openlineage.io/spec/facets/1-0-1/ErrorMessageRunFacet.json#/$defs/ErrorMessageRunFacet",
       "version": "https://openlineage.io/spec/facets/1-0-1/DatasetVersionDatasetFacet.json#/$defs/DatasetVersionDatasetFacet",
       "jobType": "https://openlineage.io/spec/facets/2-0-4/JobTypeJobFacet.json#/$defs/JobTypeJobFacet"}
NS_RUN = uuid.UUID("6d1f7e2a-2c4b-5b8e-9a51-7c3d0e4f8a10")      # fixed namespace for deterministic runIds


def _f(_std, _def, **kw):
    return {"_producer": PRODUCER, "_schemaURL": STD.get(_std) or FACETS + _def, **kw}


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _iso(d):
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _tool_failed(rec):
    if rec.get("load_ok") is False or rec.get("ok") is False:
        return "record says the tool failed (load_ok/ok false)"
    if "export_result" in rec and rec["export_result"] != ["FINISHED"]:
        return "export_result %s" % rec["export_result"]
    return None


def to_events(src, name, namespace="x3dprov", pipeline="x3d-loop", base_time="1970-01-01T00:00:00Z", scene_ns="x3d"):
    """-> list of RunEvent dicts in emission order. src: a stamped scene (str) or a list of step dicts."""
    ch = chain_of(src)
    v = P.verify(src) if isinstance(src, str) else None
    step_problems = {}
    for p in (v or {}).get("problems", []):
        if p.startswith("step "):
            step_problems.setdefault(int(p.split()[1].rstrip(":")), []).append(p)
    base = _t(base_time)
    chain_run = str(uuid.uuid5(NS_RUN, name + "/" + (ch["steps"][0][1] if ch["steps"] else "")))
    chain_job = {"namespace": namespace, "name": name,
                 "facets": {"jobType": _f("jobType", "", processingType="BATCH", integration="X3DPROV", jobType="SCENE_CHAIN")}}
    parent = _f("parent", "", run={"runId": chain_run}, job={"namespace": namespace, "name": name})

    def ds(h, ns=scene_ns, nm=name):
        d = {"namespace": ns, "name": nm, "facets": {}}
        if isinstance(h, str):
            d["facets"]["version"] = _f("version", "", datasetVersion=h)
        return d

    recs = [(n, text, json.loads(text)) for n, text in ch["steps"]]
    times = []
    for i, (n, _, r) in enumerate(recs):
        s = r.get("started_at") or r.get("t")
        e = r.get("ended_at") or r.get("t") or s
        if isinstance(s, str) and isinstance(e, str):
            times.append((_t(s), _t(e), "record"))
        else:
            times.append((base + timedelta(seconds=i + 1), base + timedelta(seconds=i + 1, milliseconds=500), "synthetic-order"))
    out = [{"eventType": "START", "eventTime": _iso(times[0][0] - timedelta(milliseconds=1) if times else base),
            "producer": PRODUCER, "schemaURL": SCHEMA_URL, "run": {"runId": chain_run, "facets": {}}, "job": chain_job,
            "inputs": [ds(recs[0][2].get("input_sha256"))] if recs else [], "outputs": []}]
    last_verdict = None
    for (n, text, r), (ts, te, tsrc) in zip(recs, times):
        rid = str(uuid.uuid5(NS_RUN, chain_run + "/%d/" % n + P._sha(text.encode("utf-8"))))
        job = {"namespace": namespace, "name": "%s.%s" % (pipeline, r.get("op")), "facets": {}}
        ins = [ds(r.get("input_sha256"))]
        if isinstance(r.get("prompt_sha256"), str):
            ins.append(ds(r["prompt_sha256"], ns="x3d-prompt", nm=str(r.get("prompt_id") or r["prompt_sha256"])))
        facets = {"parent": parent,
                  "x3dprov_step": _f(None, "X3dprovStepRunFacet", step=n, op=r.get("op"), recordSha256=P._sha(text.encode("utf-8")),
                                     record=text, eventTimeSource=tsrc)}
        if r.get("op") == "validate":
            last_verdict = r.get("verdict")
            facets["x3dprov_validation"] = _f(None, "X3dprovValidationRunFacet", validator=r.get("validator"), validatorRef=r.get("validator_ref"),
                                              verdict=r.get("verdict"), xsdValid=r.get("xsd_valid"),
                                              semanticErrorCodes=r.get("semantic_error_codes", []))
        if r.get("op") == "repair":
            facets["x3dprov_repair"] = _f(None, "X3dprovRepairRunFacet", kind=r.get("kind"), round=r.get("round"),
                                          reportShown=r.get("report_shown"), fixes=r.get("fixes"))
        start = {"eventType": "START", "eventTime": _iso(ts), "producer": PRODUCER, "schemaURL": SCHEMA_URL,
                 "run": {"runId": rid, "facets": {"parent": parent}}, "job": job, "inputs": ins, "outputs": []}
        why = step_problems.get(n) or ([_tool_failed(r)] if _tool_failed(r) else [])
        if why:
            facets["errorMessage"] = _f("errorMessage", "", message="; ".join(why), programmingLanguage="python")
        end = {"eventType": "FAIL" if why else "COMPLETE", "eventTime": _iso(te), "producer": PRODUCER, "schemaURL": SCHEMA_URL,
               "run": {"runId": rid, "facets": facets}, "job": job, "inputs": ins, "outputs": [ds(r.get("output_sha256"))]}
        out += [start, end]
    why = []
    if v is not None and v["status"] != "verified":
        why.append("verify(): %s: %s" % (v["status"], "; ".join(v["problems"])))
    if last_verdict not in (None, "valid"):
        why.append("last validate verdict: %s" % last_verdict)
    run_f = {"x3dprov_chain": _f(None, "X3dprovChainRunFacet", steps=len(recs), schema=ch["schema"],
                                 verify=v["status"] if v else "not-run (steps only)", lastVerdict=last_verdict)}
    if why:
        run_f["errorMessage"] = _f("errorMessage", "", message="; ".join(why), programmingLanguage="python")
    out.append({"eventType": "FAIL" if why else "COMPLETE", "eventTime": _iso((times[-1][1] if times else base) + timedelta(milliseconds=1)),
                "producer": PRODUCER, "schemaURL": SCHEMA_URL, "run": {"runId": chain_run, "facets": run_f}, "job": chain_job,
                "inputs": [], "outputs": [ds(recs[-1][2].get("output_sha256"))] if recs else []})
    return out


def chain_from_events(events):
    """The records back out of the x3dprov_step facets: {schema, steps}; lossless by construction, tested."""
    steps = sorted((e["run"]["facets"]["x3dprov_step"]["step"], e["run"]["facets"]["x3dprov_step"]["record"])
                   for e in events if "x3dprov_step" in e["run"].get("facets", {}))
    schema = next((e["run"]["facets"]["x3dprov_chain"]["schema"] for e in events if "x3dprov_chain" in e["run"].get("facets", {})), None)
    return {"schema": schema, "steps": steps}


# ---- schema validation ----------------------------------------------------------------------------------------------

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")


def validator():
    """-> check(event) returning a list of errors: the event against RunEvent, every standard facet against its own schema,
    every x3dprov facet against schemas/x3dprov-openlineage-facets.json. Offline: the spec files are vendored."""
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    docs = {}
    for root, _, files in os.walk(os.path.join(SCHEMA_DIR, "openlineage")):
        for fn in files:
            if fn.endswith(".json"):
                d = json.load(open(os.path.join(root, fn)))
                docs[d["$id"]] = d
    own = json.load(open(os.path.join(SCHEMA_DIR, "x3dprov-openlineage-facets.json")))
    docs[own["$id"]] = own
    reg = Registry().with_resources([(k, Resource.from_contents(d)) for k, d in docs.items()])
    fc = FormatChecker()
    def sub(url):
        return Draft202012Validator({"$ref": url}, registry=reg, format_checker=fc)
    core = sub(SCHEMA_URL)
    cache = {}
    def check(ev):
        errs = [e.message for e in core.iter_errors(ev)]
        facet_sets = [ev["run"].get("facets", {}), ev["job"].get("facets", {})]
        for d in ev.get("inputs", []) + ev.get("outputs", []):
            facet_sets.append(d.get("facets", {}))
        for fs in facet_sets:
            for k, f in fs.items():
                url = f["_schemaURL"]
                if url not in cache:
                    cache[url] = sub(url)
                errs += ["%s: %s" % (k, e.message) for e in cache[url].iter_errors(f)]
        return errs
    return check


if __name__ == "__main__":
    path = sys.argv[1]
    raw = open(path, encoding="utf-8").read()
    src = json.loads(raw) if path.endswith(".json") else raw
    for ev in to_events(src, sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)):
        print(json.dumps(ev, ensure_ascii=False))
