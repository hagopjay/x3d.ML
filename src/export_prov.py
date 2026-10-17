"""Project an x3dprov record onto W3C PROV-JSON and OpenLineage RunEvents (read-only views; the file stays the source).
Usage: python3 export_prov.py <scene.x3d> <outdir>"""
import sys, os, json, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P

def to_prov_json(xml, scene_name):
    steps = P.summary(xml); doc = {"prefix": {"x3d": "https://example.invalid/x3dprov#"}, "entity": {}, "activity": {}, "agent": {},
                                    "wasGeneratedBy": {}, "used": {}, "wasDerivedFrom": {}, "wasAssociatedWith": {}}
    for i, s in enumerate(steps, 1):
        ent_in, ent_out, act = f"x3d:scene/{s['input_sha256'][:12]}", f"x3d:scene/{s['output_sha256'][:12]}", f"x3d:step/{i}-{s['op']}"
        doc["entity"][ent_in] = {"x3d:sha256": s["input_sha256"]}; doc["entity"][ent_out] = {"x3d:sha256": s["output_sha256"]}
        doc["activity"][act] = {k: v for k, v in s.items() if k not in ("input_sha256", "output_sha256", "prev", "agent", "agent_ref")}
        doc["used"][f"_:u{i}"] = {"prov:activity": act, "prov:entity": ent_in}
        doc["wasGeneratedBy"][f"_:g{i}"] = {"prov:entity": ent_out, "prov:activity": act}
        if ent_in != ent_out: doc["wasDerivedFrom"][f"_:d{i}"] = {"prov:generatedEntity": ent_out, "prov:usedEntity": ent_in, "prov:activity": act}
        ag = s.get("agent") or s.get("validator")
        if ag:
            a = f"x3d:agent/{ag}@{s.get('agent_ref') or s.get('validator_ref', '')}"; doc["agent"][a] = {"prov:type": "prov:SoftwareAgent"}
            doc["wasAssociatedWith"][f"_:w{i}"] = {"prov:activity": act, "prov:agent": a}
    return doc

def to_openlineage(xml, scene_name, namespace="x3d.pipeline"):
    out = []
    for i, s in enumerate(P.summary(xml), 1):
        out.append({"eventType": "COMPLETE", "eventTime": "1970-01-01T00:00:00Z", "producer": "x3dprov/0.1",
                    "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent",
                    "run": {"runId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{scene_name}/{i}/{s['output_sha256']}")),
                            "facets": {"x3dprov_step": {"_producer": "x3dprov/0.1", "_schemaURL": "x3dprov/0.1#step", **s}}},
                    "job": {"namespace": namespace, "name": f"{s['op']}"},
                    "inputs": [{"namespace": namespace, "name": s["input_sha256"], "facets": {}}],
                    "outputs": [{"namespace": namespace, "name": s["output_sha256"], "facets": {}}]})
    return out

if __name__ == "__main__":
    xml = open(sys.argv[1], encoding="utf-8").read(); os.makedirs(sys.argv[2], exist_ok=True); n = os.path.basename(sys.argv[1])
    json.dump(to_prov_json(xml, n), open(os.path.join(sys.argv[2], "prov.json"), "w"), indent=1)
    json.dump(to_openlineage(xml, n), open(os.path.join(sys.argv[2], "openlineage.json"), "w"), indent=1)
    print("ok", len(P.summary(xml)), "steps")
