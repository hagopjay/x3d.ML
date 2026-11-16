"""Tests for op "trace" (src/x3dprov_trace.py and its PROV-O / SHACL / OpenLineage views). Fixtures are synthetic and built here.
Needs lxml, rdflib, pyshacl, jsonschema. Run: python3 -m pytest tests/test_trace.py -q"""
import json, os, re, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import x3dprov as P
import x3dprov_provo as M
import x3dprov_openlineage as O
import x3dprov_trace as T

SCENE = """<?xml version="1.0" encoding="UTF-8"?>
<X3D version="4.0" profile="Interchange"><head><meta name="title" content="pier"/></head><Scene>
<Transform DEF="Pier3" translation="3.5 0 1.2"><Shape><Box size="0.4 6 0.4"/></Shape></Transform></Scene></X3D>
"""
SPEC = "Pier 3 stands at 3,5 m east and 1,2 m north.\nIts section is 0.4 m x 0.4 m, height 6 m. Cost: $$5 & C:\\new\\table."
SRC = {"s1": SPEC}


def words(t):
    return re.findall(r"[0-9]+(?:[.,][0-9]+)?|[^\W\d_]+", t.lower())


def engine(items, texts):
    """a tiny reference FIND (unbroken run of lowercase words) so the audit has something to recompute with; not the real engine"""
    out = []
    for it in items:
        it = dict(it); q, t = words(it["quote"] or ""), words(texts[it["source"]])
        hit = [i for i in range(len(t) - len(q) + 1) if q and t[i:i + len(q)] == q]
        it["verdict"] = "unchecked" if it["quote"] is None else "verified" if hit else "check"; it["occurrences"] = len(hit); it["span"] = None
        out.append(it)
    return out


def items(verdict2="verified"):
    base = [{"field": "Transform[DEF=Pier3]/@translation", "value": "3.5 0 1.2", "quote": "3,5 m east and 1,2 m north", "source": "s1", "verdict": "verified", "occurrences": 1, "span": None, "derivation": [{"kind": "decimal-comma"}]},
            {"field": "Box/@size", "value": "0.4 6 0.4", "quote": "0.4 m x 0.4 m, height 6 m", "source": "s1", "verdict": verdict2, "occurrences": 1, "span": None},
            {"field": "WorldInfo/@title", "value": "Cost: $$5 & C:\\new\\table.\nline", "quote": "Cost: $$5 & C:\\new\\table.", "source": "s1", "verdict": "verified", "occurrences": 1, "span": None},
            {"field": "Material/@diffuseColor", "value": "0.8 0.2 0.2", "quote": None, "source": "s1", "verdict": "unchecked", "occurrences": 0, "span": None}]
    return base


def sources():
    return [{"id": "s1", "kind": "text", "sha256": P._sha(SPEC.encode()), "bytes": len(SPEC.encode()), "name": "spec.txt"}]


def chain(n_items=None):
    x = P.add_step(SCENE, {"op": "generate", "model": "model-a", "prompt_sha256": "cd" * 32, "input_sha256": "none"}, SCENE)
    its = items() if n_items is None else n_items
    rec, side = T.make_record(its, sources(), policy={"min_quote_words": 1}, values=5)
    return T.add_trace(x, rec), rec, its


def test_bytes_with_backslash_newline_dollar_survive_add_step():
    """src/x3dprov.py _inject_meta used re.sub with a replacement string: backslash-n, backslash-backslash and control characters in a
    record were turned into newlines, single backslashes or a PatternError. A quote copied from a PDF has all three."""
    x = P.add_step(SCENE, {"op": "trace", "v": "a\nb\tc\\d\\\\e $& $$ \x01"})
    assert P.verify(x)["status"] == "verified"
    assert P.summary(x)[0]["v"] == "a\nb\tc\\d\\\\e $& $$ \x01"


def test_trace_step_is_nonmutating_and_chain_verifies_unchanged_verify():
    x, rec, its = chain()
    st = P.summary(x)
    assert [s["op"] for s in st] == ["generate", "trace", "summary"]
    assert st[1]["input_sha256"] == st[1]["output_sha256"] == st[0]["output_sha256"]
    assert P.verify(x)["status"] == "verified"
    assert P.verify(x.replace('title" content="pier"', 'title" content="pier2"'))["status"] == "stale"


def test_prov_round_trip_lossless_and_shacl_clean():
    x, rec, its = chain()
    ch = M.chain_of(x); g = M.to_graph(ch, "t", P.content_hash(x))
    for fmt in ("turtle", "json-ld"):
        assert M.from_graph(M.parse(g.serialize(format=fmt, **({"context": M.CONTEXT} if fmt == "json-ld" else {})), fmt)) == ch
    assert M.refill(M.blank_record(x), M.from_graph(g)) == x
    ok, msgs = M.shacl(g); assert ok, msgs
    assert M.constraints(g) == []
    from rdflib.namespace import PROV, RDF
    assert len(list(g.subjects(RDF.type, M.X3DP.TracedValue))) == 4 and len(list(g.subjects(RDF.type, M.X3DP.Quote))) == 3
    assert len(list(g.subject_objects(PROV.wasQuotedFrom))) == 3 and len(list(g.subjects(RDF.type, PROV.Quotation))) == 3
    assert (None, RDF.type, M.X3DP.Trace) in g


def test_sidecar_items_give_the_same_graph_and_record_without_inline_items():
    its = items(); rec, side = T.make_record(its, sources(), values=5, inline_cap=10)
    assert side == its and "items" not in rec
    x = P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE); x = T.add_trace(x, rec)
    g = M.to_graph(M.chain_of(x), "t", P.content_hash(x), sidecars={rec["report_sha256"]: its})
    ok, msgs = M.shacl(g); assert ok, msgs
    from rdflib.namespace import RDF
    assert len(list(g.subjects(RDF.type, M.X3DP.TracedValue))) == 4
    assert T.audit_trace(x, SRC, engine, sidecars={rec["report_sha256"]: its})["status"] == "verified"
    assert "sidecar" in " ".join(T.audit_trace(x, SRC, engine)["problems"])


def _msgs(x, **kw):
    return M.shacl(M.to_graph(M.chain_of(x), "t", P.content_hash(x), **kw))[1]


def test_shacl_refuses_a_verified_value_without_a_quote_and_a_lying_total():
    bad = items(); bad[3]["verdict"] = "verified"                      # claims verified, has no quote
    x, _, _ = chain(bad)
    assert any("evidence gap" in m for m in _msgs(x))
    its = items(); rec, _ = T.make_record(its, sources(), values=5); rec["summary"]["total"] = 9
    y = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), rec)
    assert any("different number of values" in m for m in _msgs(y))


def test_shacl_refuses_a_trace_that_changes_the_scene():
    rec, _ = T.make_record(items(), sources(), values=5)
    x = P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE)
    x = P.add_step(x, rec, SCENE.replace("0.4 6 0.4", "0.5 6 0.4"))
    assert any("changed the scene" in m for m in _msgs(x))
    assert any("changed the scene" in p for p in T.audit_trace(x, SRC, engine)["problems"])


def test_audit_catches_a_flipped_verdict_in_the_last_step_that_verify_misses():
    """limit 1 of DESIGN.md section 3 for a trace: the verdict is recomputable from the sources, so editing it is still caught."""
    its = items(verdict2="check")                                       # honest record: the second quote does not match the text below
    its[1]["quote"] = "0.4 m x 0.5 m, height 6 m"; its[1]["occurrences"] = 0
    rec, _ = T.make_record(its, sources(), values=5)
    x = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), rec, seal=False)    # the trace IS the last step
    assert T.audit_trace(x, SRC, engine)["status"] == "verified"
    tampered = x.replace(P._attr(P.read_steps(x)[-1][1]), P._attr(P.read_steps(x)[-1][1].replace('"verdict":"check"', '"verdict":"verified"')), 1)
    assert P.verify(tampered)["status"] == "verified"                    # the chain cannot see it
    a = T.audit_trace(tampered, SRC, engine)
    assert a["status"] == "evidence-mismatch" and any("Box/@size" in p and "verdict" in p for p in a["problems"])
    assert T.audit_trace(x, {"s1": SPEC + " edited"}, engine)["status"] == "evidence-mismatch"      # a source that changed


def test_openlineage_column_lineage_and_trace_facet_schema_valid_and_lossless():
    x, rec, its = chain()
    evs = O.to_events(x, "t"); check = O.validator()
    assert all(check(e) == [] for e in evs)
    end = next(e for e in evs if e["job"]["name"].endswith(".trace") and e["eventType"] == "COMPLETE")
    cl = end["outputs"][0]["facets"]["columnLineage"]["fields"]
    assert set(cl) == {i["field"] for i in its}
    f = cl["Transform[DEF=Pier3]/@translation"]["inputFields"][0]
    assert f["name"] == "spec.txt" and f["transformations"][0] == {"type": "DIRECT", "subtype": "TRANSFORMATION", "masking": False, "description": "decimal-comma"}
    assert cl["Box/@size"]["inputFields"][0]["transformations"][0]["subtype"] == "IDENTITY"
    assert cl["Material/@diffuseColor"]["inputFields"] == []            # no quote: the gap is visible in the lineage graph
    chk = items(verdict2="check"); rec2, _ = T.make_record(chk, sources(), values=5)
    y = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), rec2)
    end2 = next(e for e in O.to_events(y, "t") if e["job"]["name"].endswith(".trace") and e["eventType"] == "COMPLETE")
    assert end2["outputs"][0]["facets"]["columnLineage"]["fields"]["Box/@size"]["inputFields"] == []       # check: no unproven edge
    assert [d["namespace"] for d in end["inputs"]] == ["x3d", "x3d-source"] and end["inputs"][1]["facets"]["version"]["datasetVersion"] == sources()[0]["sha256"]
    assert end["run"]["facets"]["x3dprov_trace"]["summary"]["verified"] == 3
    assert O.chain_from_events(evs)["steps"] == M.chain_of(x)["steps"]
    bad = json.loads(json.dumps(end)); bad["run"]["facets"]["x3dprov_trace"]["summary"].pop("total")
    assert check(bad)                                                   # the custom facet schema is enforced


def test_span_shape_refuses_end_before_start_and_trace_shapes_stay_core_only():
    """Two guards in one: the span rule fires, and no trace shape uses SPARQL (pyshacl ran the SPARQL form in 28.0 s for 1000 values, the
    core form in 1.2 s: measured, rdflib 7.6.0, pyshacl 0.40.2)."""
    for span, ok in (([10, 40], True), ([40, 10], False)):
        its = items(); its[0]["span"] = span
        x, _, _ = chain(its)
        assert (not any("oa:end is before oa:start" in m for m in _msgs(x))) == ok
    from rdflib import Graph, Namespace
    sg = Graph().parse(M.SHAPES, format="turtle"); S = Namespace("https://x3dprov.example/0.1/shapes#"); SH = Namespace("http://www.w3.org/ns/shacl#")
    for name in ("TraceReportShape", "TracedValueShape", "QuoteShape", "SpanShape", "SourceDocumentShape"):
        assert (S[name], SH.sparql, None) not in sg or name == "TraceReportShape", name      # the one-node-per-report count may use SPARQL


def test_characters_that_are_not_xml_are_cleaned_before_they_reach_the_scene():
    from lxml import etree
    its = items(); its[1]["quote"] = "0.4 m x 0.4 m,\uffff height 6 m\ud800"
    rec, _ = T.make_record(its, sources(), values=5)
    x = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), rec)
    etree.fromstring(x.encode("utf-8"))                                    # still well-formed
    assert P.verify(x)["status"] == "verified" and "\ufffd" in P.summary(x)[1]["items"][1]["quote"]
    assert M.from_graph(M.parse(M.to_graph(M.chain_of(x)).serialize(format="turtle"), "turtle")) == M.chain_of(x)


def test_audit_scene_locator_binds_the_claim_to_the_scene():
    its = [{"field": "//*[@DEF='Pier3']/@translation", "value": "3.5 0 1.2", "quote": "3,5 m east and 1,2 m north", "source": "s1", "verdict": "verified", "occurrences": 1, "span": None},
           {"field": "//Box/@size", "value": "0.4 6 0.4", "quote": "0.4 m x 0.4 m, height 6 m", "source": "s1", "verdict": "verified", "occurrences": 1, "span": None}]
    rec, _ = T.make_record(its, sources(), values=2)
    x = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), rec)
    assert T.audit_trace(x, SRC, engine, scene=True)["status"] == "verified"
    assert T.locate(x, "//Box/@size") == ["0.4 6 0.4"]
    wrong = T.add_trace(P.add_step(SCENE, {"op": "generate", "input_sha256": "none"}, SCENE), T.make_record([{**its[0], "value": "3.5 0 9"}, its[1]], sources(), values=2)[0])
    assert any("is '3.5 0 1.2' in the scene, the trace says '3.5 0 9'" in p for p in T.audit_trace(wrong, SRC, engine, scene=True)["problems"])
    amb = SCENE.replace("</Scene>", '<Transform><Shape><Box size="1 1 1"/></Shape></Transform></Scene>')   # //Box/@size now finds two
    y = T.add_trace(P.add_step(amb, {"op": "generate", "input_sha256": "none"}, amb), rec)
    assert any("resolves to 2 nodes" in p for p in T.audit_trace(y, SRC, engine, scene=True)["problems"])
