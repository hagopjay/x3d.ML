"""x3dprov op "trace": value-level evidence (quote -> value) as one non-mutating step of the chain. Reference glue, engine-agnostic:
the FIND / COMPARE / LOCATE engine (x3dtrace) is passed in as `recheck`, so this file only builds, seals and audits the record.

Record (DESIGN.md section 11):
  op "trace", engine "x3dtrace/0.1", input_sha256 == output_sha256 (a trace reads the scene, it never changes it; audit_trace checks it),
  sources [{id, kind text|pdf|x3d|json, sha256, bytes, name}], claims_sha256 (what the model gave: field, value, quote, source),
  report_sha256 (the checked items), summary {verified, check, reworded, unchecked, total, values, cited}, policy {...},
  items [...] inline when the canonical JSON is <= INLINE_CAP bytes, else only in a sidecar named <scene>.trace.json (same sha).
Hashed objects hold no floats (JSON float text differs between Python and JS): rects are integers in 1/10000 of the page.
"""
import json, os, re, sys
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P
import x3dtrace as X

ENGINE = X.SCHEMA
VERDICTS = ("verified", "check", "reworded", "unchecked")
INLINE_CAP = 65536
CLAIM_KEYS = ("field", "value", "quote", "source", "hints")
RECHECK_KEYS = ("status", "value_status", "verdict", "span", "occurrences", "derivation", "disambiguated_by", "locus", "selectors", "note", "target")


_ILLEGAL = re.compile("[\ud800-\udfff\ufffe\uffff]")           # not XML 1.0 characters / not encodable: a scene carrying one stops parsing


def clean(obj):
    """Replace U+FFFE, U+FFFF and lone surrogates by U+FFFD in every string of a record (PDF text layers do carry them: measured, an
    x3dprov step holding U+FFFF makes the scene unparsable and verify() says stale). Everything else, controls included, is JSON-escaped."""
    if isinstance(obj, str):
        return _ILLEGAL.sub("\ufffd", obj)
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, dict):
        return {clean(k): clean(v) for k, v in obj.items()}
    return obj


def locate(xml, xpath):
    """The strings an XPath 1.0 finds in the scene as the content hash sees it (comments and x3dprov metas removed): [] if the scene is not
    well-formed or the path is invalid. A trace item's `field` is such a path, e.g. //*[@DEF='Pier3']/@translation."""
    try:
        root = P._strip_prov(P._parse(xml))
        return [str(r) for r in root.xpath(xpath)]
    except (etree.XMLSyntaxError, etree.XPathError):
        return []


def claims_of(items):
    """What the writer gave, as the claims hash sees it (the hints that choose between repeated quotes are part of it)."""
    return [{k: it.get(k) for k in CLAIM_KEYS if k != "hints" or it.get(k)} for it in items]


def _no_floats(obj, where="record"):
    """Everything that is hashed must mean the same in Python and JavaScript: no floats, no integers beyond 2**53."""
    if isinstance(obj, float):
        raise ValueError("%s holds a float (%r); carry numbers as text or integers" % (where, obj))
    if isinstance(obj, int) and not isinstance(obj, bool) and abs(obj) >= 2 ** 53:
        raise ValueError("%s holds an integer beyond 2**53 (%r); carry it as text" % (where, obj))
    if isinstance(obj, list):
        for k, v in enumerate(obj):
            _no_floats(v, "%s[%d]" % (where, k))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _no_floats(v, "%s.%s" % (where, k))


def summarize(items, values=None):
    c = {v: sum(1 for it in items if it["verdict"] == v) for v in VERDICTS}
    cited = sum(1 for it in items if it.get("quote") is not None or it.get("quote_sha256"))
    amb = sum(1 for it in items if (it.get("occurrences") or 0) > 1 and not it.get("disambiguated_by"))
    return {**c, "total": len(items), "values": len(items) if values is None else values, "cited": cited, "ambiguous": amb}


def make_record(items, sources, policy=None, engine=ENGINE, values=None, inline_cap=INLINE_CAP, **extra):
    """-> (record, sidecar items or None). `values` = how many scene values could have had a quote (coverage = cited / values)."""
    items, sources, policy = clean(items), clean(sources), clean(policy or {})
    _no_floats(items, "items"); _no_floats(sources, "sources"); _no_floats(policy, "policy")
    rec = {"op": "trace", "engine": engine, "sources": sources, "claims_sha256": P._sha(P._dumps(claims_of(items)).encode("utf-8")),
           "report_sha256": P._sha(P._dumps(items).encode("utf-8")), "summary": summarize(items, values), "policy": policy or {}, **extra}
    inline = len(P._dumps(items).encode("utf-8")) <= inline_cap
    if inline:
        rec["items"] = items
    return rec, (None if inline else items)


def scene_text(xml):
    """The scene as a reader of it saw it: every x3dprov meta removed, so quote offsets do not move when a step is added."""
    return P._META_RE.sub("", xml)


def trace_claims(xml, claims, source_texts, kinds=None, names=None, policy=None, values=None, expected=None, seal=True, inline_cap=INLINE_CAP):
    """Check `claims` [{field, value, quote, source, ...}] against `source_texts` {id: text} with the x3dtrace engine and append the
    trace step to `xml`. Use scene_text(xml) as a source text when the scene itself is what the quotes are taken from.
    -> (new xml, sidecar items or None, TraceReport). `expected` lists the fields the writer was asked to evidence (coverage)."""
    pol = policy or X.TracePolicy()
    srcs = [X.Source(i, t, (kinds or {}).get(i, "auto")) for i, t in source_texts.items()]
    rep = X.check_claims(claims, srcs, pol, expected, X.Source("scene", scene_text(xml), "x3d"))
    srecs = [{**s.info(), **({"name": names[s.id]} if names and s.id in names else {})} for s in srcs]
    rec, side = make_record(rep.to_dict()["sources"], srecs, policy=pol.to_dict(), values=len(expected) if expected else None, inline_cap=inline_cap)
    return add_trace(xml, rec, seal), side, rep


def add_trace(xml, rec, seal=True):
    """Append the trace step (non-mutating: xml_after is xml_before) and, by default, a redundant summary step so the trace has a successor
    (the last record has none: DESIGN.md section 3, limit 1; ingest_runs.py does the same)."""
    out = P.add_step(xml, rec)
    return P.add_step(out, {"op": "summary", "agent": "x3dprov_trace", "note": "successor of the trace step"}) if seal else out


def audit_trace(xml, source_texts, recheck=None, sidecars=None, scene=False):
    """verify() plus, for every trace step: non-mutating, items present and hashing to report_sha256, claims hash, sources unchanged,
    (scene=True: each XPath `field` resolves to one node whose text equals `value`), verdicts and summary RECOMPUTED by `recheck(items, source_texts) -> items` and compared. Names the field that differs.
    status: verified | evidence-mismatch | any verify() failure status."""
    chain, problems = P.verify(xml), []
    for i, r in enumerate(P.summary(xml), 1):
        if r.get("op") != "trace":
            continue
        if r.get("input_sha256") != r.get("output_sha256"):
            problems.append("step %d: trace step changed the scene" % i)
        items = r.get("items") if r.get("items") is not None else (sidecars or {}).get(r.get("report_sha256"))
        if items is None:
            problems.append("step %d: items not inline and no sidecar with report_sha256 %s" % (i, str(r.get("report_sha256"))[:12])); continue
        if P._sha(P._dumps(items).encode("utf-8")) != r.get("report_sha256"):
            problems.append("step %d: items do not hash to report_sha256 (report edited)" % i)
        if P._sha(P._dumps(claims_of(items)).encode("utf-8")) != r.get("claims_sha256"):
            problems.append("step %d: claims_sha256 does not match the items' claims" % i)
        seen_keys = {}
        for it in items:
            key = (it.get("field"), P._dumps(it.get("record")))
            if key in seen_keys:
                problems.append("step %d: field %s is traced twice (same record)" % (i, it.get("field")))
            seen_keys[key] = True
        for s in r.get("sources", []):
            t = source_texts.get(s.get("id"))
            if t is not None and P._sha(t.encode("utf-8")) != s.get("sha256"):
                problems.append("step %d: source %s differs from the recorded sha256" % (i, s.get("id")))
        if scene:                                     # the claim is about THIS scene: its field path must resolve to one node holding `value`
            for it in items:
                if str(it.get("field", "")).startswith("/") and it.get("value") is not None:
                    hit = locate(xml, it["field"])
                    if len(hit) != 1:
                        problems.append("step %d: %s resolves to %d nodes in the scene, expected 1" % (i, it["field"], len(hit)))
                    elif hit[0] != str(it["value"]):
                        problems.append("step %d: %s is %r in the scene, the trace says %r" % (i, it["field"], hit[0], it["value"]))
        kinds = {s.get("id"): s.get("kind") for s in r.get("sources", []) if s.get("kind") in ("x3d", "text")}
        pol = X.TracePolicy.from_dict(r["policy"]) if r.get("policy") else None
        fresh = recheck(items, source_texts) if recheck else X.recheck(items, source_texts, pol, kinds, scene_text(xml))
        for a, b in zip(items, fresh):
            for k in RECHECK_KEYS:
                if k in b and a.get(k) != b.get(k):
                    problems.append("step %d: %s: %s recorded %r, recomputed %r" % (i, a.get("field"), k, a.get(k), b.get(k)))
        if r.get("summary") != summarize(fresh, (r.get("summary") or {}).get("values")):
            problems.append("step %d: summary differs from the recomputed one" % i)
    status = chain["status"] if not chain["ok"] else ("evidence-mismatch" if problems else "verified")
    return {"ok": chain["ok"] and not problems, "status": status, "chain": chain["status"], "steps": chain["steps"], "problems": chain["problems"] + problems}
