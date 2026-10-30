"""x3dprov <-> W3C PROV-O (Turtle, JSON-LD), with OWL-Time for dates. Lossless: chain -> graph -> chain gives the same
record bytes, and refilling a scene's step metas from the graph gives the same file bytes (tests/test_provo.py).

Mapping (DESIGN.md section 10):
  chain                       x3dp:Chain, prov:Collection, prov:Entity; x3dp:schema; prov:hadMember each record
  step record N               x3dp:StepRecord, prov:Entity, IRI ni:///sha-256;<hash of its JSON text> (RFC 6920);
                              prov:wasGeneratedBy step N; prov:wasDerivedFrom ni:<prev>  (the hash link, as a derivation)
  step N (op)                 prov:Activity + x3dp:<Op> (Generate, Validate, Repair, Transform = Blender round trip, ...);
                              every record field k as x3df:<k> (typed literal; lists, dicts and null as rdf:JSON)
  prompt (generate)           prov:used ni:<prompt_sha256> (x3dp:Prompt); input_sha256 "none" -> version 0 is x3dp:NoScene
  scene version               x3dp:SceneVersion, prov:Entity, <chain>/scene/N (output of step N; 0 = input of step 1);
                              x3dp:contentSha256; prov:specializationOf ni:<content hash> (x3dp:SceneContent: the join key)
  step N in / out             prov:used vIn, prov:generated vOut; vOut prov:wasDerivedFrom vIn (qualified, hadActivity step N);
                              prov:wasRevisionOf when the content hash changed
  untracked change            input_sha256 of step N != output of step N-1: vIn is its own version <chain>/scene/N-in,
                              derived from N-1 with no activity: SHACL reports an unaccounted derivation
  file as found (optional)    <chain>/scene/as-found, derived from the last version; same rule when its hash differs (stale)
  agent / agent_ref, tool,    prov:SoftwareAgent (prov:Person for `human`) <agents>/<name>/<ref>; qualified association
  validator(_ref), model,     with prov:hadRole x3dp:ToolRole / ValidatorRole / ModelRole / RendererRole / HumanRole
  renderer, human
  dates                       OWL-Time: step N time:hasTime an interval; started_at / ended_at as its beginning / end
                              (time:inXSDDateTimeStamp, plus prov:startedAtTime / endedAtTime); record time:hasTime an
                              instant, instant N time:before instant N+1 (the hash chain proves that order); `t` dates the
                              record (prov:generatedAtTime); run_created dates the source run (time:inXSDDateTime if no zone)
Structural fields (op is kept as a field) are NOT stored as literals: prev, input_sha256 and output_sha256 are read back
from the graph's derivations and versions, so a round trip that matches proves the PROV structure carries the chain.
Usage: python3 x3dprov_provo.py <scene.x3d|steps.json> [--jsonld] [--check]"""
import base64, json, os, re, sys
from datetime import datetime
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, RDFS, TIME, XSD

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3dprov as P

BASE = "https://x3dprov.example/"                      # placeholder (RFC 2606 .example); a registered namespace is the Consortium's call
X3DP = Namespace(BASE + "0.1#")                        # mapping vocabulary
X3DF = Namespace(BASE + "0.1/field#")                  # one property per x3dprov record field
SHAPES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "x3dprov-prov.shacl.ttl")
CONTEXT = {"prov": str(PROV), "time": str(TIME), "xsd": str(XSD), "rdfs": str(RDFS), "x3dp": str(X3DP), "x3df": str(X3DF)}
STRUCT = ("prev", "input_sha256", "output_sha256")
OPS = {"ingest": "Ingest", "generate": "Generate", "validate": "Validate", "repair": "Repair", "render": "Render",
       "transform": "Transform", "judge": "Judge", "measure": "Measure", "summary": "Summary"}
ROLES = (("agent", "agent_ref", "ToolRole"), ("tool", None, "ToolRole"), ("validator", "validator_ref", "ValidatorRole"),
         ("model", None, "ModelRole"), ("renderer", None, "RendererRole"), ("human", None, "HumanRole"))
_HEX = re.compile(r"^[0-9a-f]{64}$")
_VERSION_META = re.compile(r"""<meta\s+name=(["'])x3dprov\.version\1\s+content=(["'])(.*?)\2\s*/>""", re.S)


# ---- chain in and out of a scene ----------------------------------------------------------------------------------

def chain_of(src):
    """Chain from a stamped scene (str/bytes) or from a list of step dicts (a *.steps.json): {schema, steps: [(n, text)]}."""
    if isinstance(src, list):
        return {"schema": P.SCHEMA, "steps": [(i, P._dumps(s)) for i, s in enumerate(src, 1)]}
    text = src.decode("utf-8") if isinstance(src, bytes) else src
    m = _VERSION_META.search(text)
    return {"schema": m.group(3) if m else None, "steps": P.read_steps(text)}


def blank_record(xml):
    """The scene with every step meta's content emptied: what is left once the record is taken out."""
    return P._STEP_META.sub(lambda m: '<meta name="x3dprov.step.%s" content=""/>' % m.group(2), xml)


def refill(skeleton, chain):
    """Put a chain's records back into the emptied step metas of blank_record(); byte-exact for canonical metas."""
    texts = dict(chain["steps"])
    return re.sub(r'<meta name="x3dprov\.step\.(\d+)" content=""/>',
                  lambda m: '<meta name="x3dprov.step.%s" content=%s/>' % (m.group(1), P._attr(texts[int(m.group(1))])), skeleton)


# ---- IRIs ---------------------------------------------------------------------------------------------------------

def ni(hexhash):
    """RFC 6920 Named Information IRI for a sha-256 given in hex."""
    return URIRef("ni:///sha-256;" + base64.urlsafe_b64encode(bytes.fromhex(hexhash)).decode().rstrip("="))


def ni_hex(iri):
    s = str(iri)
    if not s.startswith("ni:///sha-256;"):
        raise ValueError("not an ni sha-256 IRI: " + s)
    b = s.split(";", 1)[1]
    return base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).hex()


def _q(s):
    from urllib.parse import quote
    return quote(str(s), safe="")


# ---- values -------------------------------------------------------------------------------------------------------

def _lit(v):
    if isinstance(v, bool):
        return Literal(v)
    if isinstance(v, int):
        return Literal(str(v), datatype=XSD.integer)
    if isinstance(v, float):
        return Literal(json.dumps(v), datatype=XSD.double)
    if isinstance(v, str):
        return Literal(v)
    return Literal(P._dumps(v), datatype=RDF.JSON)                          # list, dict, null


def _val(lit):
    dt, lex = lit.datatype, str(lit)
    if dt == RDF.JSON:
        return json.loads(lex)
    if dt == XSD.boolean:
        return lex in ("true", "1")
    if dt == XSD.integer:
        return int(lex)
    if dt == XSD.double:
        return float(lex)
    return lex


def _is_dt(s):
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except (TypeError, ValueError):
        return False


def _instant(g, node, s):
    """OWL-Time instant: zoned -> inXSDDateTimeStamp; no zone -> inXSDDateTime (time zone unknown, said so)."""
    g.add((node, RDF.type, TIME.Instant))
    zoned = datetime.fromisoformat(s.replace("Z", "+00:00")).tzinfo is not None
    g.add((node, TIME.inXSDDateTimeStamp if zoned else TIME.inXSDDateTime, Literal(s, datatype=XSD.dateTimeStamp if zoned else XSD.dateTime)))
    if not zoned:
        g.add((node, RDFS.comment, Literal("recorded without a time zone")))
    return zoned


# ---- chain -> graph -----------------------------------------------------------------------------------------------

def to_graph(chain, chain_id=None, current_hash=None):
    """PROV-O graph of a chain. chain_id names the chain (default: hash of record 1); current_hash adds the file as found."""
    steps = chain["steps"]
    chain_id = chain_id or (P._sha(steps[0][1].encode("utf-8"))[:16] if steps else "empty")
    C = Namespace(BASE + "chain/" + _q(chain_id) + "/")
    A = Namespace(BASE + "agent/")
    g = Graph()
    for k, v in CONTEXT.items():
        g.bind(k, v)
    ch = C["chain"]
    for t in (X3DP.Chain, PROV.Collection, PROV.Entity):
        g.add((ch, RDF.type, t))
    if chain["schema"] is not None:
        g.add((ch, X3DP.schema, Literal(chain["schema"])))
    g.add((ch, X3DP.chainId, Literal(chain_id)))

    def version(name, h):
        v = C["scene/" + name]
        g.add((v, RDF.type, X3DP.SceneVersion)); g.add((v, RDF.type, PROV.Entity))
        if isinstance(h, str):
            g.add((v, X3DP.contentSha256, Literal(h)))
            if h == "none":                                               # generate: no scene before the model call
                g.add((v, RDF.type, X3DP.NoScene))
            if _HEX.match(h):
                g.add((v, PROV.specializationOf, ni(h)))
                g.add((ni(h), RDF.type, X3DP.SceneContent)); g.add((ni(h), RDF.type, PROV.Entity))
        return v

    def derive(b, a, act=None, revision=False):
        g.add((b, PROV.wasDerivedFrom, a))
        if act is not None:
            q = BNode()
            g.add((b, PROV.qualifiedDerivation, q)); g.add((q, RDF.type, PROV.Derivation))
            g.add((q, PROV.entity, a)); g.add((q, PROV.hadActivity, act))
        if revision:
            g.add((b, PROV.wasRevisionOf, a))

    prev_out, prev_v, prev_inst = None, None, None
    for i, (n, text) in enumerate(steps):
        rec = json.loads(text)
        act, rhash = C["step/%d" % n], P._sha(text.encode("utf-8"))
        r = ni(rhash)
        g.add((ch, PROV.hadMember, r))
        for t in (X3DP.StepRecord, PROV.Entity):
            g.add((r, RDF.type, t))
        g.add((r, X3DP.sha256, Literal(rhash))); g.add((r, X3DP.stepIndex, Literal(n)))
        g.add((r, PROV.wasGeneratedBy, act))
        if "prev" in rec:
            if rec["prev"] != P.ZERO:
                tgt = ni(rec["prev"]) if isinstance(rec["prev"], str) and _HEX.match(rec["prev"]) else Literal(rec["prev"])
                if isinstance(tgt, Literal):
                    g.add((r, X3DP.prevLiteral, tgt))
                else:
                    g.add((r, PROV.wasDerivedFrom, tgt))
        else:
            g.add((r, X3DP.noPrev, Literal(True)))
        # activity and its fields
        g.add((act, RDF.type, PROV.Activity)); g.add((act, RDF.type, X3DP.Step))
        if isinstance(rec.get("op"), str) and rec["op"] in OPS:
            g.add((act, RDF.type, X3DP[OPS[rec["op"]]]))
        g.add((act, X3DP.stepIndex, Literal(n)))
        for k, v in rec.items():
            if k not in STRUCT:
                g.add((act, X3DF[k], _lit(v)))
        # scene versions
        if i == 0:
            vin = version("0", rec.get("input_sha256"))
        elif "input_sha256" in rec and rec.get("input_sha256") == prev_out:
            vin = prev_v
        else:                                                             # untracked change between steps N-1 and N
            vin = version("%d-in" % n, rec.get("input_sha256"))
            derive(vin, prev_v)
        vout = version(str(n), rec.get("output_sha256"))
        g.add((act, PROV.used, vin)); g.add((act, PROV.generated, vout)); g.add((vout, PROV.wasGeneratedBy, act))
        if "input_sha256" not in rec:
            g.add((act, X3DP.noInput, Literal(True)))
        if "output_sha256" not in rec:
            g.add((act, X3DP.noOutput, Literal(True)))
        derive(vout, vin, act, revision=rec.get("input_sha256") != rec.get("output_sha256"))
        if isinstance(rec.get("prompt_sha256"), str) and _HEX.match(rec["prompt_sha256"]):
            pr = ni(rec["prompt_sha256"])                                 # the prompt is what a generate step really used
            g.add((pr, RDF.type, X3DP.Prompt)); g.add((pr, RDF.type, PROV.Entity)); g.add((act, PROV.used, pr))
        # agents
        for key, refkey, role in ROLES:
            name = rec.get(key)
            if not isinstance(name, str):
                continue
            ref = rec.get(refkey) if refkey else None
            ag = A[_q(name) + ("/" + _q(ref) if isinstance(ref, str) else "")]
            g.add((ag, RDF.type, PROV.Agent)); g.add((ag, RDF.type, PROV.Person if key == "human" else PROV.SoftwareAgent))
            g.add((ag, X3DP.name, Literal(name)))
            if isinstance(ref, str):
                g.add((ag, X3DP.ref, Literal(ref)))
            g.add((act, PROV.wasAssociatedWith, ag))
            q = BNode()
            g.add((act, PROV.qualifiedAssociation, q)); g.add((q, RDF.type, PROV.Association))
            g.add((q, PROV.agent, ag)); g.add((q, PROV.hadRole, X3DP[role]))
        # time
        iv = C["step/%d/time" % n]
        g.add((act, TIME.hasTime, iv)); g.add((iv, RDF.type, TIME.ProperInterval))
        for key, rel, pprop in (("started_at", TIME.hasBeginning, PROV.startedAtTime), ("ended_at", TIME.hasEnd, PROV.endedAtTime)):
            if isinstance(rec.get(key), str) and _is_dt(rec[key]):
                inst = C["step/%d/time/%s" % (n, key)]
                g.add((iv, rel, inst))
                if _instant(g, inst, rec[key]):
                    g.add((act, pprop, Literal(rec[key], datatype=XSD.dateTime)))
        if isinstance(rec.get("run_created"), str) and _is_dt(rec["run_created"]):
            inst = C["step/%d/source-run-created" % n]
            g.add((act, X3DP.sourceRunCreated, inst)); _instant(g, inst, rec["run_created"])
        rinst = C["record/%d/written" % n]
        g.add((r, TIME.hasTime, rinst)); g.add((rinst, RDF.type, TIME.Instant))
        if isinstance(rec.get("t"), str) and _is_dt(rec["t"]):
            if _instant(g, rinst, rec["t"]):
                g.add((r, PROV.generatedAtTime, Literal(rec["t"], datatype=XSD.dateTime)))
        if prev_inst is not None:
            g.add((prev_inst, TIME.before, rinst))
        prev_out, prev_v, prev_inst = rec.get("output_sha256"), vout, rinst
    if current_hash is not None and prev_v is not None:
        found = version("as-found", current_hash)
        g.add((found, RDF.type, X3DP.FileAsFound))
        derive(found, prev_v)
    return g


# ---- graph -> chain -----------------------------------------------------------------------------------------------

def from_graph(g):
    """Inverse of to_graph: {schema, steps: [(n, text)]}. Reads prev / input / output from the PROV structure."""
    ch = next(g.subjects(RDF.type, X3DP.Chain))
    schema = g.value(ch, X3DP.schema)
    out = []
    for r in g.objects(ch, PROV.hadMember):
        n = int(g.value(r, X3DP.stepIndex))
        act = g.value(r, PROV.wasGeneratedBy)
        rec = {}
        for p, o in g.predicate_objects(act):
            if str(p).startswith(str(X3DF)):
                rec[str(p)[len(str(X3DF)):]] = _val(o)
        if g.value(r, X3DP.noPrev) is None:
            d, lit = g.value(r, PROV.wasDerivedFrom), g.value(r, X3DP.prevLiteral)
            rec["prev"] = ni_hex(d) if d is not None else (_val(lit) if lit is not None else P.ZERO)
        if g.value(act, X3DP.noInput) is None:
            vin = next(e for e in g.objects(act, PROV.used) if (e, RDF.type, X3DP.SceneVersion) in g)
            rec["input_sha256"] = _val(g.value(vin, X3DP.contentSha256))
        if g.value(act, X3DP.noOutput) is None:
            rec["output_sha256"] = _val(g.value(g.value(act, PROV.generated), X3DP.contentSha256))
        out.append((n, P._dumps(rec)))
    return {"schema": None if schema is None else str(schema), "steps": sorted(out)}


def to_turtle(chain, **kw):
    return to_graph(chain, **kw).serialize(format="turtle")


def to_jsonld(chain, **kw):
    return to_graph(chain, **kw).serialize(format="json-ld", context=CONTEXT, indent=1)


def parse(text, fmt):
    g = Graph()
    g.parse(data=text, format=fmt)
    return g


# ---- checks -------------------------------------------------------------------------------------------------------

def shacl(g, shapes=SHAPES):
    """pyshacl against the mapping's shapes -> (conforms, [messages])."""
    from pyshacl import validate
    sg = Graph().parse(shapes, format="turtle")
    conforms, rg, _ = validate(g, shacl_graph=sg, inference="none", advanced=True)
    SH = Namespace("http://www.w3.org/ns/shacl#")
    msgs = sorted(f"{rg.value(res, SH.focusNode)}: {rg.value(res, SH.resultMessage)}" for res in rg.subjects(RDF.type, SH.ValidationResult))
    return conforms, msgs


def constraints(g):
    """A Python check of a named subset of W3C PROV-CONSTRAINTS (not the full set; see DESIGN.md section 10).
    -> list of violations, each "rule: detail"."""
    bad = []
    ents, acts = set(g.subjects(RDF.type, PROV.Entity)), set(g.subjects(RDF.type, PROV.Activity))
    for x in ents & acts:                                                           # Constraint 55 entity-activity-disjoint
        bad.append(f"entity-activity-disjoint: {x}")
    gens = {}
    for e, a in g.subject_objects(PROV.wasGeneratedBy):
        gens.setdefault(e, set()).add(a)
    for a, e in g.subject_objects(PROV.generated):
        gens.setdefault(e, set()).add(a)
    for e, s in gens.items():                                                       # Constraint 24 generation-uniqueness (one generating activity here)
        if len(s) > 1:
            bad.append(f"generation-uniqueness: {e} generated by {len(s)} activities")
    for b, a in g.subject_objects(PROV.wasRevisionOf):                              # revision is a derivation (Revision subtype of Derivation)
        if (b, PROV.wasDerivedFrom, a) not in g:
            bad.append(f"revision-is-derivation: {b}")
    idx = {a: int(g.value(a, X3DP.stepIndex)) for a in acts if g.value(a, X3DP.stepIndex) is not None}
    for b, a in g.subject_objects(PROV.wasDerivedFrom):                             # Constraint 45 derivation-generation-generation-ordering
        ga, gb = [idx.get(x) for x in gens.get(a, ())], [idx.get(x) for x in gens.get(b, ())]
        if ga and gb and None not in ga + gb and not max(ga) <= min(gb):
            bad.append(f"derivation-generation-generation-ordering: {b} generated before {a}")
    for a in acts:                                                                  # Constraint 32 usage-within-activity / 30 generation-precedes-usage, by step order
        for e in g.objects(a, PROV.used):
            for ga in gens.get(e, ()):
                if ga in idx and a in idx and idx[ga] >= idx[a]:
                    bad.append(f"generation-precedes-usage: {e} used by step {idx[a]} but generated by step {idx[ga]}")
    # derivation acyclicity: strict precedence of generations makes a derivation cycle impossible (Constraint 50 strict-cycle)
    edges = {}
    for b, a in g.subject_objects(PROV.wasDerivedFrom):
        edges.setdefault(b, set()).add(a)
    state = {}
    def visit(n):
        state[n] = 1
        for m in edges.get(n, ()):
            if state.get(m) == 1:
                bad.append(f"strict-cycle: derivation cycle through {m}")
            elif m not in state:
                visit(m)
        state[n] = 2
    for n in list(edges):
        if n not in state:
            visit(n)
    for a in acts:                                                                  # Constraint 33 start-precedes-end
        s, e = g.value(a, PROV.startedAtTime), g.value(a, PROV.endedAtTime)
        if s is not None and e is not None and datetime.fromisoformat(str(s).replace("Z", "+00:00")) > datetime.fromisoformat(str(e).replace("Z", "+00:00")):
            bad.append(f"start-precedes-end: {a}")
    return bad


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("--jsonld", action="store_true"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    raw = open(a.src, encoding="utf-8").read()
    src = json.loads(raw) if a.src.endswith(".json") else raw
    ch = chain_of(src)
    g = to_graph(ch, chain_id=os.path.basename(a.src), current_hash=None if isinstance(src, list) else P.content_hash(raw))
    if a.check:
        ok, msgs = shacl(g)
        print(json.dumps({"shacl_conforms": ok, "shacl": msgs, "constraints": constraints(g), "round_trip": from_graph(g) == ch}, indent=1))
    else:
        print(g.serialize(format="json-ld", context=CONTEXT, indent=1) if a.jsonld else g.serialize(format="turtle"))
