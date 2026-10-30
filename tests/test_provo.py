"""Tests for src/x3dprov_provo.py (PROV-O / OWL-Time) and src/x3dprov_openlineage.py, over every chain in the repo.
A chain in the repo = every runs/**/*.x3d that carries x3dprov step metas (179) and every runs/**/*.steps.json (3).
demo/ holds no chain at rest: its pages build chains in the browser.
Needs lxml, rdflib, pyshacl, jsonschema (+ rfc3339-validator, rfc3987 for format checks); `prov` is optional.
Run: python3 -m pytest tests/ -q"""
import glob, json, os, re, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
import x3dprov as P
import x3dprov_provo as M
import x3dprov_openlineage as O
import ingest_runs as R


def _chains():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "**", "*.x3d"), recursive=True)):
        x = open(f, encoding="utf-8").read()
        if P.read_steps(x):
            out.append((os.path.relpath(f, ROOT), x))
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "**", "*.steps.json"), recursive=True)):
        out.append((os.path.relpath(f, ROOT), json.load(open(f))))
    return out


CHAINS = _chains()
SCENES = [(f, x) for f, x in CHAINS if isinstance(x, str)]


def _graph(name, x):
    return M.to_graph(M.chain_of(x), chain_id=name, current_hash=None if isinstance(x, list) else P.content_hash(x))


def test_the_repo_has_the_chains_we_think():
    assert len(SCENES) == 179 and len(CHAINS) == 182
    assert all(P.verify(x)["status"] == "verified" for _, x in SCENES)


# ---- 1. PROV-O: lossless, valid ---------------------------------------------------------------------------------------

def test_round_trip_every_chain_turtle_and_jsonld_byte_identical():
    """chain -> PROV (Turtle and JSON-LD text) -> chain: same record bytes, same record hashes, and the scene rebuilt from
    the graph's records is byte-identical to the file."""
    for name, x in CHAINS:
        ch = M.chain_of(x)
        g = _graph(name, x)
        for fmt, text in (("turtle", g.serialize(format="turtle")), ("json-ld", g.serialize(format="json-ld", context=M.CONTEXT))):
            back = M.from_graph(M.parse(text, fmt))
            assert back == ch, (name, fmt)
            assert [P._sha(t.encode()) for _, t in back["steps"]] == [P._sha(t.encode()) for _, t in ch["steps"]]
        if isinstance(x, str):
            skel = M.blank_record(x)
            assert P.read_steps(skel) == [(n, "") for n, _ in ch["steps"]]          # the record is really gone
            assert M.refill(skel, M.from_graph(g)) == x, name
            assert P.verify(M.refill(skel, M.from_graph(g)))["status"] == "verified"


def test_structure_is_load_bearing():
    """prev / input / output are not stored as literals: they come back from derivations and scene versions."""
    g = _graph(*SCENES[0])
    assert not any(str(p).endswith(("#prev", "#input_sha256", "#output_sha256")) for p in g.predicates())


def test_shacl_and_constraints_clean_on_every_chain():
    bad = []
    for name, x in CHAINS:
        g = _graph(name, x)
        ok, msgs = M.shacl(g)
        cons = M.constraints(g)
        if not ok or cons:
            bad.append((name, msgs[:2], cons[:2]))
    assert bad == []


def test_mapping_terms_and_roles():
    from rdflib.namespace import PROV, RDF
    g = _graph(*next(c for c in SCENES if c[0].endswith("cube/5-final.x3d")))
    acts = {str(a).rsplit("/", 1)[1]: a for a in g.subjects(RDF.type, PROV.Activity)}
    assert (acts["5"], RDF.type, M.X3DP.Transform) in g                    # Blender round trip
    assert (acts["3"], RDF.type, M.X3DP.Repair) in g and (acts["2"], RDF.type, M.X3DP.Validate) in g
    roles = {str(r) for r in g.objects(None, PROV.hadRole)}
    assert {str(M.X3DP.ValidatorRole), str(M.X3DP.ToolRole)} <= roles
    revs = list(g.subject_objects(PROV.wasRevisionOf))
    assert len(revs) == 2                                                    # repair and Blender changed content; validate did not
    assert len(list(g.subjects(RDF.type, PROV.SoftwareAgent))) == 5       # ingest, autofix, validator, bridge, Blender
    gen = _graph(*next(c for c in SCENES if "gpu-phase" in c[0]))
    assert list(gen.subjects(RDF.type, M.X3DP.Prompt)) and list(gen.subjects(RDF.type, M.X3DP.NoScene))
    assert (None, PROV.hadRole, M.X3DP.ModelRole) in gen


def test_prov_package_reads_every_graph():
    prov = pytest.importorskip("prov.model")
    import warnings
    for name, x in CHAINS[::20]:
        g = _graph(name, x)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d = prov.ProvDocument.deserialize(content=g.serialize(format="turtle"), format="rdf", rdf_format="turtle")
        kinds = {}
        for r in d.get_records():
            kinds[type(r).__name__] = kinds.get(type(r).__name__, 0) + 1
        n = len(M.chain_of(x)["steps"])
        assert kinds["ProvActivity"] == n and kinds["ProvUsage"] >= n and kinds["ProvMembership"] == n


# ---- OWL-Time ---------------------------------------------------------------------------------------------------------

def _timed_chain():
    x = R.CARRIER % {"name": "timed"}
    x = P.add_step(x, {"op": "generate", "model": "model-a", "provider": "lab-a", "prompt_sha256": "ab" * 32, "prompt_id": "p1",
                       "input_sha256": "none", "started_at": "2026-10-29T10:00:00Z", "ended_at": "2026-10-29T10:00:04.5Z", "t": "2026-10-29T10:00:05Z"})
    x = P.add_step(x, {"op": "validate", "validator": "v", "validator_ref": "abc1234", "verdict": "invalid", "xsd_valid": True,
                       "semantic_error_codes": ["profile-component"], "started_at": "2026-10-29T10:00:05Z", "ended_at": "2026-10-29T10:00:05.002Z"})
    y = x.replace("<WorldInfo", "<WorldInfo info='\"fixed\"'")
    x = P.add_step(x, {"op": "repair", "kind": "model", "model": "model-a", "round": 1, "report_shown": True, "fixes": ["profile-component"],
                       "human": "reviewer-1", "run_created": "2026-10-29T10:00:06"}, y)
    x = P.add_step(x, {"op": "validate", "validator": "v", "validator_ref": "abc1234", "verdict": "valid", "xsd_valid": True, "semantic_error_codes": []})
    return x


def test_owl_time_dates_and_order():
    from rdflib.namespace import PROV, RDF, TIME, XSD
    x = _timed_chain()
    assert P.verify(x)["status"] == "verified"
    g = _graph("timed", x)
    assert M.from_graph(g) == M.chain_of(x)
    stamps = sorted(str(o) for o in g.objects(None, TIME.inXSDDateTimeStamp))
    assert stamps == ["2026-10-29T10:00:00Z", "2026-10-29T10:00:04.5Z", "2026-10-29T10:00:05.002Z", "2026-10-29T10:00:05Z", "2026-10-29T10:00:05Z"]
    naive = list(g.objects(None, TIME.inXSDDateTime))
    assert [str(n) for n in naive] == ["2026-10-29T10:00:06"] and naive[0].datatype == XSD.dateTime
    assert len(list(g.subject_objects(PROV.startedAtTime))) == 2 and len(list(g.subject_objects(PROV.generatedAtTime))) == 1
    assert len(list(g.subject_objects(TIME.before))) == 3                    # 4 records, ordered by the hash chain
    assert (None, RDF.type, PROV.Person) in g                                # the human reviewer
    ok, msgs = M.shacl(g)
    assert ok, msgs
    assert M.constraints(g) == []


def test_start_after_end_is_a_constraint_violation():
    x = R.CARRIER % {"name": "bad-time"}
    x = P.add_step(x, {"op": "render", "renderer": "r", "started_at": "2026-10-29T10:00:05Z", "ended_at": "2026-10-29T10:00:00Z"})
    assert any(c.startswith("start-precedes-end") for c in M.constraints(_graph("bad-time", x)))


# ---- 2. OpenLineage ---------------------------------------------------------------------------------------------------

CHECK = O.validator()


def test_openlineage_every_chain_schema_valid_and_lossless():
    counts = {}
    for name, x in CHAINS:
        evs = O.to_events(x, name)
        n = len(M.chain_of(x)["steps"])
        assert len(evs) == 2 * n + 2
        for e in evs:
            assert CHECK(e) == [], (name, e["eventType"], CHECK(e)[:3])
            counts[e["eventType"]] = counts.get(e["eventType"], 0) + 1
        assert O.chain_from_events(evs)["steps"] == M.chain_of(x)["steps"]
        runs = {}
        for e in evs:                                                        # exactly one START and one terminal event per run
            runs.setdefault(e["run"]["runId"], []).append(e["eventType"])
        assert all(v[0] == "START" and len(v) == 2 and v[1] in ("COMPLETE", "FAIL") for v in runs.values())
    assert counts == {"START": 766, "COMPLETE": 646, "FAIL": 120}            # 120 = gpu-phase chains whose last verdict is invalid


def test_openlineage_facets_and_times():
    x = _timed_chain()
    evs = O.to_events(x, "timed")
    assert all(CHECK(e) == [] for e in evs)
    gen_end = evs[2]
    assert gen_end["eventTime"] == "2026-10-29T10:00:04.500000Z" and gen_end["run"]["facets"]["x3dprov_step"]["eventTimeSource"] == "record"
    assert [d["namespace"] for d in gen_end["inputs"]] == ["x3d", "x3d-prompt"]
    v1 = evs[4]["run"]["facets"]["x3dprov_validation"]
    assert v1["verdict"] == "invalid" and v1["semanticErrorCodes"] == ["profile-component"]
    rep = evs[6]["run"]["facets"]["x3dprov_repair"]
    assert rep == {**rep, "kind": "model", "round": 1, "reportShown": True}
    assert evs[-1]["eventType"] == "COMPLETE" and evs[-1]["run"]["facets"]["x3dprov_chain"]["lastVerdict"] == "valid"
    assert evs[6]["inputs"][0]["facets"]["version"]["datasetVersion"] != evs[6]["outputs"][0]["facets"]["version"]["datasetVersion"]
    bad = json.loads(json.dumps(evs[2])); bad["run"]["facets"]["x3dprov_validation"] = {**v1, "verdict": "maybe"}
    assert CHECK(bad)                                                        # the custom facet schema is enforced


# ---- 3. tamper: one byte, caught by verify() and by the PROV graph ----------------------------------------------------

def _scene_byte(x, in_comment=False):
    """Change one digit of the scene body: the first one outside (or, in_comment=True, inside) an XML comment."""
    i = x.index("<Scene")
    spans = [(m.start(), m.end()) for m in re.finditer(r"<!--.*?-->", x, re.S)]
    for m in re.finditer(r"\d", x[i:]):
        k = i + m.start()
        if any(a <= k < b for a, b in spans) == in_comment:
            return x[:k] + ("1" if x[k] != "1" else "2") + x[k + 1:]
    return None


def _record_byte(x, n):
    """Change one byte in step n's record: the first letter of its op, upper-cased (the JSON stays valid)."""
    text = dict(P.read_steps(x))[n]
    i = text.index('"op":"') + 6
    new = text[:i] + text[i].upper() + text[i + 1:]
    assert len(new.encode()) == len(text.encode()) and sum(a != b for a, b in zip(new, text)) == 1
    return x.replace(P._attr(text), P._attr(new), 1)


def _derivation_msgs(name, x):
    ok, msgs = M.shacl(_graph(name, x))
    return ok, [m for m in msgs if "broken derivation" in m]


def test_one_byte_scene_edit_caught_by_verify_and_prov():
    for name, x in SCENES:
        y = _scene_byte(x)
        assert sum(a != b for a, b in zip(x, y)) == 1 and len(x) == len(y)
        assert P.verify(y)["status"] == "stale", name
        ok, msgs = _derivation_msgs(name, y)
        assert not ok and len(msgs) == 1 and "untracked edit" in msgs[0] and "/scene/as-found" in msgs[0], (name, msgs)


def test_one_byte_edit_inside_a_comment_is_not_content():
    """Limit 2 of DESIGN.md section 3, measured: the hash binds content, so a digit changed inside a comment verifies."""
    hit = [(n, _scene_byte(x, in_comment=True)) for n, x in SCENES]
    hit = [(n, y) for n, y in hit if y is not None]
    assert len(hit) == 16 and all(P.verify(y)["status"] == "verified" for _, y in hit)


def test_one_byte_record_edit_caught_by_verify_and_prov():
    for name, x in SCENES:
        y = _record_byte(x, 1)
        assert P.verify(y)["status"] == "broken-chain", name
        ok, msgs = _derivation_msgs(name, y)
        assert not ok and len(msgs) == 1 and "not in the chain" in msgs[0], (name, msgs)
        evs = O.to_events(y, name)
        assert evs[-1]["eventType"] == "FAIL" and "broken-chain" in evs[-1]["run"]["facets"]["errorMessage"]["message"]
        assert evs[4]["eventType"] == "FAIL" and all(CHECK(e) == [] for e in evs)      # step 2's run carries the problem


def test_deleted_step_and_untracked_change_between_steps():
    name, x = next(c for c in SCENES if c[0].endswith("cube/5-final.x3d"))
    y = re.sub(r'<meta name="x3dprov\.step\.2" content="[^"]*"/>', "", x)
    assert P.verify(y)["status"] == "broken-chain"
    ok, msgs = _derivation_msgs(name, y)
    assert not ok and any("not in the chain" in m for m in msgs)
    z = R.edit_step(x, 4, lambda r: r.update(input_sha256="0" * 63 + "1"))    # step 4 claims an input step 3 never produced
    ok, msgs = M.shacl(_graph(name, z))
    assert not ok and any("untracked edit" in m and "/scene/4-in" in m for m in msgs)


def test_last_record_edit_is_missed_by_both_same_limit():
    """DESIGN.md section 3, limit 1: the last record has no successor. The PROV view inherits the limit, it does not hide it."""
    name, x = next(c for c in SCENES if c[0].endswith("cube/5-final.x3d"))
    y = _record_byte(x, len(P.read_steps(x)))
    assert P.verify(y)["status"] == "verified"
    assert M.shacl(_graph(name, y))[0]
