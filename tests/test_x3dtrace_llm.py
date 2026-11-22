"""Tests for x3dtrace_llm: cited values of an LLM trace checked with x3dtrace.

Fixture: tests/fixtures/llm-trace/langfuse-rag-support-agent.synthetic.json, a SYNTHETIC Langfuse export (ObservationV2 +
v1 Score) built by make_trace.py in the same folder. Its answer cites 7 values; one is planted wrong ("ships within 5 business
days" against the source's "7 to 10 business days").

Run:  python3 -I -m pytest tests -q -p no:cacheprovider
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import x3dtrace_llm as L  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "llm-trace" / "langfuse-rag-support-agent.synthetic.json"


@pytest.fixture()
def doc():
    return json.loads(FIX.read_text(encoding="utf-8"))


def _items(rep):
    return {it["field"]: it for g in rep["generations"] for it in g["items"]}


def test_planted_value_is_check_and_the_rest_verified(doc):
    rep = L.check_trace(doc)
    assert rep["summary"] == {"verified": 6, "check": 1, "reworded": 0, "unchecked": 0, "moved": 0}
    it = _items(rep)["replacement_ship_business_days"]
    assert it["verdict"] == "check" and it["status"] == "found" and it["value_status"] == "mismatch"


def test_sources_are_retrieved_documents_and_successful_tool_output(doc):
    rep = L.check_trace(doc)
    ids = [s["id"] for s in rep["sources"]]
    assert ids[:4] == ["kb-warranty-0412", "kb-service-0137", "kb-claims-0098", "kb-accessories-0551"]
    assert ids.count("tool:order-api") == 1            # the ERROR attempt is not a source; the retry is


def test_tool_output_is_a_quotable_source(doc):
    it = _items(L.check_trace(doc))["delivered_at"]
    assert it["source"] == "tool:order-api" and it["verdict"] == "verified"


def test_answer_span_is_whole_token_not_first_hit(doc):
    rep = L.check_trace(doc)
    ans = next(o for o in L.observations(doc) if o["id"] == "obs-10")["output"]["answer"]
    it = _items(rep)["replacement_ship_business_days"]
    s, e = it["answer_span"]
    assert ans[s:e] == "5" and ans[e:e + 14] == " business days"      # not the 5 inside 2025-05-12
    assert ans.find("5") < s


def test_every_value_located_once(doc):
    for f, it in _items(L.check_trace(doc)).items():
        assert it["answer_candidates"] == 1, f
        assert it["answer_span"] is not None, f


def test_ambiguous_value_reports_candidates_and_picks_by_quote():
    ans = "Plan A costs 24 euros. Battery warranty lasts 24 months."
    span, n = L.answer_span(ans, {"value": 24, "quote": "warranty lasts 24 months"})
    assert n == 2 and ans[span[0]:span[1] + 7] == "24 months"


def test_citing_a_source_that_does_not_exist_is_flagged(doc):
    d = copy.deepcopy(doc)
    gen = next(o for o in L.observations(d) if o["id"] == "obs-10")
    gen["output"]["citations"][0]["source"] = "kb-does-not-exist"
    rep = L.check_trace(d)
    it = _items(rep)["warranty_months"]
    assert it["status"] == "moved" and it["source_moved"] is True       # engine keeps the verdict (BUG-31 behaviour) ...
    assert it["cited_source"] == "kb-does-not-exist" and it["source"] == "kb-warranty-0412"
    assert rep["summary"]["moved"] == 1                                  # ... the adapter makes the wrong citation countable


def test_no_sources_means_unchecked_not_wrong(doc):
    d = copy.deepcopy(doc)
    d["observations"]["data"] = [o for o in L.observations(d) if o["type"] not in ("RETRIEVER", "TOOL")]
    rep = L.check_trace(d)
    assert rep["summary"]["unchecked"] == 7 and rep["summary"]["check"] == 0


def test_bare_list_and_no_citations(doc):
    obs = L.observations(doc)
    assert L.check_trace(obs)["summary"]["verified"] == 6
    plain = [o for o in obs if o["type"] != "GENERATION" or o["id"] != "obs-10"]
    assert L.check_trace(plain)["generations"] == []


def test_cli_prints_json(doc, capsys):
    assert L.main([str(FIX)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == L.SCHEMA and out["summary"]["check"] == 1
