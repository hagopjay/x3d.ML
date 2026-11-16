"""One-off generator for trace_conformance.json (kept for provenance; the tests read the JSON only).

Run:  python3 -I make_trace_conformance.py <gaik build dir> <out.json>

gaik_expected comes from GAIK's own code (run, not recalled): the 75 value_status rows, 12 token rows,
13 number-reading rows, 11 date-part rows, 17 verdict rows and the check_text scenario are taken from
gaik_conformance_vectors.json (made by running GAIK source_tracing at git 394a94b); the extra rows below
are evaluated here with GAIK's value_status.

x3dtrace_expected is what the INTENT of x3dtrace says (not what the code returns today). Rows where the two
columns differ carry a `reason`. Rows whose x3dtrace_expected is not met by the current code are listed in
the test file (KNOWN_BUGS), not here.

GAIK is MIT, Copyright (c) 2026 GAIK - GenAI for knowledge mgt; the rows derived from its tests and README
keep that attribution (see "gaik_licence" in the output).
"""
import json
import sys
from decimal import Decimal

B = sys.argv[1]
OUT = sys.argv[2]
sys.path[:0] = [B + "/pkg", B + "/site"]
from gaik.software_components.source_tracing import TracePolicy as GP  # noqa: E402
from gaik.software_components.source_tracing.matching import value_status, tokens  # noqa: E402

V = json.load(open(B + "/vectors/gaik_conformance_vectors.json"))

# index in V["value_status"] -> (x3dtrace_expected, reason, mode, policy)
OVR = {
    34: ("mismatch", "code_values_unchecked is off by default (GAIK parity switch); see row vs-034b", None, None),
    45: ("mismatch", "sign is part of the number token: 5 is not -5", None, None),
    46: ("mismatch", "sign is part of the number token", None, None),
    47: ("mismatch", "a minus sign elsewhere in the quote does not license a negative value", None, None),
    49: ("mismatch", "vectors are compared per component in order, never read as dates", None, None),
    50: ("mismatch", "vectors are compared per component in order, never read as dates", None, None),
    52: ("mismatch", "no whitespace-concatenation reading: 1 2 3 is not 123", None, None),
    53: ("mismatch", "no whitespace-concatenation reading", None, None),
    54: ("mismatch", "no whitespace-concatenation reading (newline is not a thousands separator)", None, None),
    55: ("mismatch", "a numeric string with a leading zero is an identifier: 007 is not 7", None, None),
    56: ("match", "exponent notation is one number token", None, None),
    57: ("match", "exponent notation is one number token", None, None),
    59: ("match", "round_to_printed: a value with more decimals than the quote matches the rounded display", None, None),
    63: ("mismatch", "code_values_unchecked is off by default; a wrong lower-case word is a mismatch", None, None),
    65: ("mismatch", "month names are whole English words (marble is not March)", None, None),
    66: ("mismatch", "the month must be evidenced apart from the day (parts are consumed once each)", None, None),
    71: ("match", "x3d mode decodes XML entities: &amp; is &", "x3d", None),
    72: ("match", "words are NFC-normalised", None, None),
    73: ("match", "words are casefolded (ss == ss)", None, None),
    74: ("mismatch", "whole-token rule: v1 is one token, 1.2.3 is not in the quote", None, None),
}
MODE = {62: "x3d", 71: "x3d"}

rows = []
for i, r in enumerate(V["value_status"]):
    exp, reason, mode, pol = OVR.get(i, (r["expected"], "", None, None))
    mode = mode or MODE.get(i, "prose")
    pol = pol or r.get("policy") or {}
    rows.append({"id": "vs-%03d" % i, "value": r["value"], "quote": r["quote"], "mode": mode, "sem": None,
                 "policy": pol, "origin": r["origin"], "source": r["source"],
                 "gaik_expected": r["expected"], "x3dtrace_expected": exp, "reason": reason if exp != r["expected"] else ""})
    if i == 34:
        rows.append({"id": "vs-034b", "value": r["value"], "quote": r["quote"], "mode": "prose", "sem": None,
                     "policy": {"code_values_unchecked": True}, "origin": "gaik-test", "source": r["source"],
                     "gaik_expected": "unchecked", "x3dtrace_expected": "unchecked", "reason": ""})

# extra rows: (id, value, quote, mode, sem, policy, x3dtrace_expected, reason)
X = [
    ("x-deg-1", 1.5708, "90 degrees", "prose", "angle", {}, "match", "typed conversion: 90 degrees is 1.5708 rad (evidence in the quote)"),
    ("x-deg-2", 1.5708, "90°", "prose", "angle", {}, "match", "typed conversion: degree sign"),
    ("x-deg-3", 90, "90 degrees", "prose", "angle", {}, "mismatch", "angle written in degrees where radians are expected"),
    ("x-deg-4", 1.5708, "90", "prose", "angle", {}, "mismatch", "no unit evidence in the quote: no conversion"),
    ("x-pct-1", 0.5, "50 %", "prose", "fraction", {}, "match", "typed conversion: 50 % is 0.5"),
    ("x-pct-2", 0.5, "50 percent", "prose", "fraction", {}, "match", "typed conversion: percent word"),
    ("x-pct-3", 0.5, "50", "prose", "fraction", {}, "mismatch", "no unit evidence in the quote"),
    ("x-ft-1", 0.6096, "2 ft", "prose", "length", {}, "match", "typed conversion: 2 ft is 0.6096 m"),
    ("x-ft-2", 2, "2 ft", "prose", "length", {}, "mismatch", "length in feet written into a metre scene"),
    ("x-ft-3", 2, "2 m", "prose", "length", {}, "match", "same unit"),
    ("x-ft-4", 0.6096, "2 m", "prose", "length", {}, "mismatch", "no feet in the quote"),
    ("x-ft-5", 3.2808, "1 m", "prose", "length", {"length_scale": 0.3048}, "match", "feet scene: 1 m is 3.2808 scene units"),
    ("x-nw-1", 4, "four", "prose", None, {}, "match", "number word"),
    ("x-nw-2", 4, "Four cubes", "prose", None, {}, "match", "number words are casefolded"),
    ("x-nw-3", 5, "four", "prose", None, {}, "mismatch", "number word with a different number"),
    ("x-nw-4", 0.5, "half", "prose", None, {}, "match", "number word"),
    ("x-nw-5", 4, "four", "prose", None, {"conversions": []}, "mismatch", "conversions off (strict profile)"),
    ("x-rot-1", "0 0 1 1.5708", "rotate about z by 90 degrees", "prose", "rotation", {}, "match", "axis letter plus angle becomes an SFRotation"),
    ("x-rot-2", "0 1 0 1.5708", "90 degrees around y", "prose", "rotation", {}, "match", "axis letter plus angle"),
    ("x-rot-3", "0 -1 0 1.5708", "90 degrees around y", "prose", "rotation", {}, "mismatch", "the sign of the axis matters: this turns the other way"),
    ("x-rot-4", "0 1 0 -1.5708", "90 degrees around y", "prose", "rotation", {}, "mismatch", "the sign of the angle matters"),
    ("x-rot-5", "0 -1 0 -1.5708", "90 degrees around y", "prose", "rotation", {}, "match", "(-axis, -angle) is the same rotation"),
    ("x-rot-6", "0 1 0 1.5708", "around y", "prose", "rotation", {}, "unchecked", "no number in the quote: nothing to compare"),
    ("x-rot-7", "0 1 0 90", "rotate 90 degrees about y", "prose", "rotation", {}, "mismatch", "degrees written where radians are expected"),
    ("x-bc-1", "2 2 2", "a 2 m cube", "prose", "length", {}, "match", "one number broadcast to equal components"),
    ("x-bc-2", "2 3 4", "a 2 m cube", "prose", "length", {}, "mismatch", "unequal components are not a broadcast"),
    ("x-bc-3", "2 2 2", "a 2 m cube", "prose", "length", {"conversions": []}, "mismatch", "broadcast is a typed conversion; off in the strict profile"),
    ("x-col-1", "1 0 0", "red", "prose", "color", {}, "match", "colour name, exact RGB"),
    ("x-col-2", "0.8 0.1 0.1", "red", "prose", "color", {}, "near", "colour name, same hue class only"),
    ("x-col-3", "0 1 0", "red", "prose", "color", {}, "mismatch", "the quote names another colour"),
    ("x-col-4", "1 0 0", "#ff0000", "prose", "color", {}, "match", "hex colour"),
    ("x-col-5", "0.8 0.2 0.1", "204 51 26", "prose", "color", {}, "match", "rgb 0-255"),
    ("x-col-6", "0.8 0.2 0.1", "rgb(204, 51, 26)", "prose", "color", {}, "match", "rgb 0-255"),
    ("x-col-7", "1 0 0", "red", "prose", "color", {"conversions": []}, "unchecked", "conversions off: nothing to compare"),
    ("x-vec-1", "0 2 0", "2 m above", "prose", "length", {}, "near", "zero-fill: only the non-zero component is quoted"),
    ("x-vec-2", "0 2 0", 'translation="2 0 0"', "x3d", "length", {}, "mismatch", "the quote states all components; the axis differs"),
    ("x-vec-3", "1 2 3", "1 2 3", "prose", None, {}, "match", "vector copy"),
    ("x-vec-4", [0, -1, 0], 'translation="0 -1 0"', "x3d", None, {}, "match", "list value"),
    ("x-vec-5", "0 1 0", 'translation="0 -1 0"', "x3d", None, {}, "mismatch", "sign kept per component"),
    ("x-vec-6", "0 0 1.5708", 'rotation="0 1 0 1.5708"', "x3d", None, {}, "mismatch", "a component of the quote may not be skipped"),
    ("x-vec-7", "1 3", "1 2 3", "prose", None, {}, "mismatch", "components must be consecutive numbers of the quote"),
    ("x-vec-8", "2 2 2", "a 2 ft cube", "prose", "length", {}, "mismatch", "feet written into a metre scene (vector)"),
    ("x-vec-9", "0.6096 0.6096 0.6096", "a 2 ft cube", "prose", "length", {}, "match", "typed conversion per component plus broadcast"),
    ("x-num-1", 0.5, 'x="0 5"', "x3d", None, {}, "mismatch", "0.5 is not '0 5'"),
    ("x-num-2", 1e-05, 'transparency="1e-05"', "x3d", None, {}, "match", "exponent"),
    ("x-num-3", 0.30000001, "0.3", "prose", None, {}, "match", "float32 noise"),
    ("x-num-4", 1e308, "1e308", "prose", None, {}, "match", "huge but finite"),
    ("x-num-5", float("nan"), "nan", "prose", None, {}, "mismatch", "NaN never matches"),
    ("x-num-6", 2, "radius 2 in the middle", "prose", "length", {}, "match", "'in' here is a preposition, not inches"),
    ("x-num-7", 120, "2 minutes", "prose", "time", {}, "match", "time unit"),
    ("x-num-8", 2, "2 minutes", "prose", "time", {}, "mismatch", "minutes written where seconds are expected"),
    ("x-num-9", 0.04, "transparency 0.0", "prose", None, {}, "near", "a value more precise than its quote is at best 'near'"),
    ("x-id-1", "Ball", 'DEF="Ball"', "x3d", None, {}, "match", "identifier, same case"),
    ("x-id-2", "ball", 'DEF="Ball"', "x3d", None, {}, "mismatch", "identifiers are case-sensitive"),
    ("x-id-3", "Ball", 'DEF="ball"', "x3d", None, {}, "mismatch", "identifiers are case-sensitive"),
    ("x-id-4", "my_node", 'DEF="my_node"', "x3d", None, {}, "match", "underscore is a name character in x3d mode"),
    ("x-id-5", "my_node", 'DEF="my"', "x3d", None, {}, "mismatch", "whole token"),
    ("x-ent-1", "A &amp; B", 'name="A &amp; B"', "x3d", None, {}, "match", "entities decode on both sides"),
    ("x-set-1", "ok", "Everything is OK", "prose", None, {}, "match", "prose is casefolded"),
]
for (rid, v, q, mode, sem, pol, exp, reason) in X:
    gp = GP(**{k: w for k, w in pol.items() if k in ("number_tolerance", "match_reformatted_identifiers")}) if pol else GP()
    try:
        gv = value_status(v, q, gp)
    except Exception as e:  # pragma: no cover
        gv = "raises:%s" % type(e).__name__
    rows.append({"id": rid, "value": v, "quote": q, "mode": mode, "sem": sem,
                 "policy": pol, "origin": "x3dtrace", "source": "x3dtrace tests", "gaik_expected": gv,
                 "x3dtrace_expected": exp, "reason": reason if exp != gv else ""})
for r in rows:
    if isinstance(r["value"], float) and r["value"] != r["value"]:
        r["value"] = {"$float": "nan"}

# tokens: (text, mode, x3dtrace tokens, reason)
TOK_OVR = {
    "-1.5": (["-1.5"], "x3d", "sign and decimal point stay in the number token"),
    "0 1 2 -1": (["0", "1", "2", "-1"], "x3d", "sign kept: coordIndex terminators"),
    "1.234,50": (["1.234,50"], "prose", "one number token (read both ways at compare time)"),
    "$27,578.55": (["27,578.55"], "prose", "one number token"),
    "A &amp; B": (["A", "B"], "x3d", "x3d mode decodes entities (case kept)"),
    "Kärki": (["kärki"], "prose", "NFC normalised"),
}
tokens_rows = []
for r in V["tokens"]:
    t = r["text"]
    if t in TOK_OVR and (t != "A &amp; B" or True):
        exp, mode, reason = TOK_OVR[t]
    else:
        exp, mode, reason = r["tokens"], "prose", ""
    tokens_rows.append({"text": t, "mode": mode, "gaik_expected": r["tokens"], "x3dtrace_expected": exp,
                        "reason": reason if exp != r["tokens"] else ""})
tokens_rows.append({"text": "A &amp; B", "mode": "prose", "gaik_expected": ["a", "amp", "b"],
                    "x3dtrace_expected": ["a", "amp", "b"], "reason": ""})
tokens_rows.append({"text": '<Box size="2 2 2"/>', "mode": "x3d", "gaik_expected": ["box", "size", "2", "2", "2"],
                    "x3dtrace_expected": ["Box", "size", "2", "2", "2"], "reason": "x3d identifiers are case-sensitive"})
tokens_rows.append({"text": "Straße", "mode": "prose", "gaik_expected": tokens("Straße"),
                    "x3dtrace_expected": ["strasse"], "reason": "casefold, not lower"})
tokens_rows.append({"text": "ﬁnal", "mode": "prose", "gaik_expected": tokens("ﬁnal"),
                    "x3dtrace_expected": ["final"], "reason": "casefold expands the ligature"})
tokens_rows.append({"text": "alu­minium", "mode": "prose", "gaik_expected": tokens("alu­minium"),
                    "x3dtrace_expected": ["aluminium"], "reason": "soft hyphen removed"})
tokens_rows.append({"text": "1e-05 a_b", "mode": "x3d", "gaik_expected": tokens("1e-05 a_b"),
                    "x3dtrace_expected": ["1e-05", "a_b"], "reason": "exponent kept; underscore is a name character"})
tokens_rows.append({"text": "0.5", "mode": "x3d", "gaik_expected": tokens("0.5"),
                    "x3dtrace_expected": ["0.5"], "reason": "0.5 is one token, not '0 5'"})

# number readings (prose): x3dtrace values as sorted list
RD_OVR = {
    "010 6061-T6": ([10.0, 6061.0], "no whitespace concatenation; T6 is a word"),
    "1e-5": ([1e-05], "exponent is one number"),
    "-1.5": ([-1.5], "sign kept"),
    "5\n12": ([5.0, 12.0], "a newline is not a thousands separator"),
}
readings_rows = []
for r in V["number_readings"]:
    exp, reason = RD_OVR.get(r["text"], (r["readings"], ""))
    readings_rows.append({"text": r["text"], "gaik_expected": r["readings"], "x3dtrace_expected": sorted(exp),
                          "reason": reason if sorted(exp) != sorted(r["readings"]) else ""})

DT_OVR = {"31.12.99": (None, "a dotted triple with no four-digit year is a version (16.7.0, 5.8.4), not a date: every permutation of a version would verify")}
dates_rows = []
for r in V["date_parts"]:
    exp, reason = DT_OVR.get(r["text"], (r["parts"], ""))
    dates_rows.append({"text": r["text"], "gaik_expected": r["parts"], "x3dtrace_expected": exp, "reason": reason if exp != r["parts"] else ""})

verdict_rows = []
V_OVR = {7: ("check", "verdict_of has no digit test; the number-in-words rule lives in check_claims"),
         9: ("check", "verdict_of has no digit test; the number-in-words rule lives in check_claims")}
for i, r in enumerate(V["verdict_of"]):
    exp, reason = V_OVR.get(i, (r["verdict"], ""))
    verdict_rows.append({**r, "gaik_expected": r["verdict"], "x3dtrace_expected": exp,
                         "reason": reason if exp != r["verdict"] else ""})

out = {"generated_by": "make_trace_conformance.py (python3 -I) from gaik_conformance_vectors.json plus rows evaluated with GAIK value_status",
       "gaik_licence": V["gaik_licence"],
       "columns": "value, quote, gaik_expected, x3dtrace_expected, reason (non-empty whenever the two expectations differ)",
       "value_status": rows, "tokens": tokens_rows, "number_readings": readings_rows, "date_parts": dates_rows,
       "verdict_of": verdict_rows, "check_text_scenario": V["check_text_scenario"]}
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, allow_nan=False)
print("rows", len(rows), "tokens", len(tokens_rows), "readings", len(readings_rows), "dates", len(dates_rows),
      "verdicts", len(verdict_rows))
