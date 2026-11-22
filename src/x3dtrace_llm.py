"""x3dtrace_llm 0.1: check the cited values of an LLM trace with x3dtrace (FIND, COMPARE, LOCATE), with no model in the loop.

A generation that was asked to cite returns, beside its answer, claims of the x3dtrace shape
{field, value, quote, source}. The trace already records what the generation read: the documents a retriever returned
and the outputs of tool calls. This module collects those as sources, runs x3dtrace.check_claims on every generation's
citations, and adds one thing the engine does not do: where each cited value sits in the answer text.

Input: a Langfuse export envelope {"trace": {...}, "observations": {"data": [ObservationV2, ...]}, "scores": [...]}
(Langfuse public API: ObservationsV2Response and the v1 Score), or a bare list of ObservationV2 objects.
  sources   RETRIEVER observations whose output.documents is a list of {id, text, ...}  -> source id = document id
            TOOL observations below level ERROR with a non-empty output                -> source id = "tool:<name>",
                                                                                          text = the output as JSON
  claims    GENERATION observations whose output.citations is a list of claims
Answer location: the value is matched as a whole token (a "5" inside "2025-05-12" is not the value); of several matches,
the one whose three words on either side share most words with the quote wins. The number of candidates is reported, so a
value that occurs several times is visible as ambiguous instead of silently taking the first hit.
Wrong source: x3dtrace keeps a quote found in another source as verified with status "moved" (BUG-31 behaviour). For an LLM
that is the model citing the wrong document, so each item also carries cited_source and source_moved, and the summary
counts "moved".

What this cannot show (same limits as x3dtrace): that the quote is the right place, that the value is true, or that the
generation actually used the source it cites. A verified citation means the quote is in that source and the value is in
the quote.

Usage:  python3 -I x3dtrace_llm.py TRACE.json        -> JSON report on stdout
Standard library only, Python 3.10 or newer.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dtrace as X  # noqa: E402

SCHEMA = "x3dtrace-llm/0.1"


def observations(doc):
    if isinstance(doc, list):
        return doc
    obs = doc.get("observations")
    if isinstance(obs, dict):
        return obs.get("data") or []
    return obs or []


def collect_sources(obs):
    """[(source id, text, meta)] from retriever documents and successful tool outputs, in trace order."""
    out, seen = [], set()
    for o in obs:
        res = o.get("output")
        if o.get("type") == "RETRIEVER" and isinstance(res, dict) and isinstance(res.get("documents"), list):
            for d in res["documents"]:
                if isinstance(d, dict) and "id" in d and isinstance(d.get("text"), str) and d["id"] not in seen:
                    seen.add(d["id"])
                    out.append((d["id"], d["text"], {"kind": "document", "observation": o.get("id"), "title": d.get("title")}))
        elif o.get("type") == "TOOL" and res and o.get("level") != "ERROR":
            sid = "tool:" + str(o.get("name"))
            if sid not in seen:
                seen.add(sid)
                out.append((sid, json.dumps(res), {"kind": "tool output", "observation": o.get("id")}))
    return out


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def answer_span(answer: str, claim: dict):
    """(span or None, number of whole-token candidates) for the claim's value inside the answer text. Of several candidates,
    the one whose three words before and after share most words with the quote wins (ties: the earliest)."""
    vs = str(claim.get("value", ""))
    if not vs or not answer:
        return None, 0
    hits = [m.span() for m in re.finditer(r"(?<![\w.\-])%s(?![\w\-]|\.\d)" % re.escape(vs), answer)]
    if not hits:
        return None, 0
    qw = set(_words(str(claim.get("quote", ""))))

    def score(h):
        near = _words(answer[:h[0]])[-3:] + _words(answer[h[1]:])[:3]
        return (sum(1 for w in near if w in qw), -h[0])
    best = max(hits, key=score)
    return [best[0], best[1]], len(hits)


def check_trace(doc, policy=None) -> dict:
    obs = observations(doc)
    srcs = collect_sources(obs)
    sources = [X.Source(sid, text) for sid, text, _ in srcs]
    gens = []
    for o in obs:
        res = o.get("output")
        if o.get("type") == "GENERATION" and isinstance(res, dict) and isinstance(res.get("citations"), list) and res["citations"]:
            rep = X.check_claims(res["citations"], sources, policy=policy) if sources else None
            items = []
            for i, c in enumerate(res["citations"]):
                it = rep.items[i].to_dict() if rep else {"field": c.get("field"), "value": c.get("value"), "verdict": "unchecked",
                                                         "note": "no sources recorded in the trace"}
                it["cited_source"] = c.get("source")
                it["source_moved"] = it.get("status") == "moved"          # quote found, but not in the source the model cited
                span, n = answer_span(res.get("answer", ""), c)
                it["answer_span"], it["answer_candidates"] = span, n
                items.append(it)
            gens.append({"observation": o.get("id"), "name": o.get("name"), "model": o.get("model"), "items": items,
                         "summary": {**{v: sum(1 for it in items if it["verdict"] == v) for v in X.VERDICTS},
                                     "moved": sum(1 for it in items if it["source_moved"])}})
    return {"schema": SCHEMA, "engine": X.SCHEMA, "sources": [{"id": sid, "bytes": len(text.encode()), **meta} for sid, text, meta in srcs],
            "generations": gens,
            "summary": {k: sum(g["summary"][k] for g in gens) for k in (*X.VERDICTS, "moved")}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        print("usage: python3 -I x3dtrace_llm.py TRACE.json", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        rep = check_trace(json.load(f))
    json.dump(rep, sys.stdout, indent=1, ensure_ascii=False, default=str)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
