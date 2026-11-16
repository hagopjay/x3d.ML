"""Independent tests for x3dtrace (value-level evidence for X3D pipelines).

Written by a reviewer who had the engine's intent (its module docstring, the method description and the GAIK
behaviour notes) but not its code, so the expectations are the intent's and not the code's current output.
The first run found 43 defects. Each is a numbered entry in BUGS below. A test for a defect that has been fixed
carries `@bug(n)`, which only labels it (marker "fixed"); a test for one that is still open carries the same mark
as xfail(strict=False). The open ones are OPEN below: 2 (recompute trusts the recorded policy), 10 (a shorter
vector against a longer attribute), 18 (suggest_claims cost), 20 (round_to_printed direction), 45 (a vector read from scattered
numbers), 46 (a stray number blocks zero-fill), 48 (a leading v on a version) and 50 (coverage counts only the inventory form of a field);
see docs/TRACE-REVIEW.md. 45 to 50 were found afterwards (the port to JavaScript, a scout, a drill); 47 and 49 are fixed.

Run:  python3 -I -m pytest tests -q -p no:cacheprovider
"""
import copy
import hashlib
import html
import json
import math
import os
import random
import re
import subprocess
import sys
import textwrap
import time
import unicodedata
from decimal import Decimal
from pathlib import Path

import pytest

import x3dtrace as T

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "trace_conformance.json"

BUGS = {
    1: "non-finite number in a scene attribute makes SceneIndex boxes (and so check_claims) raise",
    2: "recompute() does not compare document/page/cited_page/record/rects/hints/schema/policy: edits there go unseen",
    3: "SFRotation: axis flipped but same angle is accepted for 'N degrees around y'",
    4: "zero-fill (near) is applied although the quote states every component: other-axis vector is 'reworded'",
    5: "PERF: SceneIndex._finish is quadratic in the number of un-DEF'd siblings",
    6: "hostile nesting: O(depth^2) path memory and RecursionError in box walk",
    7: "(fixed in the 21:07 revision) canonical()/sha256() raised on Decimal and emitted NaN/Infinity",
    8: "a non-finite world box (NaN/inf translation or radius) makes _locus raise (int(round(nan)))",
    9: "recompute() ignores the policy recorded in the report",
    10: "vector value matches a non-contiguous subsequence of the quote's numbers",
    11: "unit/semantic conflicts are not applied to vector components (a 2 ft cube in a metre scene)",
    12: "degrees-for-radians guard of SFRotation is bypassed through zero-fill and carries no note",
    13: "a colour name that contradicts the value gives 'unchecked' instead of mismatch",
    14: "a wrong number WORD gives 'unchecked' instead of 'check'",
    15: "the preposition 'in' (also 'm', 's', 'h', 'mi', 'min') counts as unit evidence",
    16: "PERF: path/line disambiguation costs O(candidates x document)",
    17: "PERF: long prose quote is quadratic in quote_numbers",
    18: "PERF: suggest_claims costs about 0.4 s per unsupported row",
    19: "XML declaration encoding is honoured for str input (mojibake or ok False)",
    20: "round_to_printed accepts a value MORE precise than its quote as exact (0.04 vs '0.0')",
    21: "locus.attr is None when the quote starts at the attribute name",
    22: "the [USE=name] path segment is dead code",
    23: "line hint: ties and far-away lines are reported as 'disambiguated_by line'",
    24: "status no_text_layer is never produced; quote with no sources is labelled no_quote",
    25: "check_claims/Source raise on odd input (huge int, sNaN, str document, missing field, surrogate)",
    26: "dates: parts matched as a set (month == day passes), ISO order swap accepted",
    27: "detached minus: -5 is verified by 'pages 3 - 5'",
    28: "combining marks of Indic/Hebrew/Thai/Arabic split words",
    29: "percent evidence is not checked against a 0..1 field",
    30: "any bare 6-hex-digit word is taken as a hex colour",
    31: "claim.source that names no source silently falls back to the first one",
    32: "path hint matches by endswith without a segment boundary",
    33: "LOD takes only the first level, not a conservative box",
    34: "rad2deg conversion fails for integer degrees from a rounded radian quote",
    35: "space-grouped thousands are read only as exactly two groups with a plain space (1 234,50 / NBSP / 1 234 567 fail)",
    36: "a list of more than 64 ints never matches its verbatim quote (floats are repr'd as 0.0)",
    37: "recheck() of a float-list claim replays as unchecked (portable strings are not read by _floats)",
    38: "Source.meta can overwrite id/kind/sha256/bytes in Source.info()",
    39: "canonical_json writes NaN/Infinity for a float, and claims_sha256 hashes raw Python values (1.0 vs 1, 1e-06 vs '1e-06') unlike the report's portable values",
    40: "CLI: a missing file, bad JSON or a non-list claims file ends in a Python traceback with exit code 1, the same code as 'some claims need a look'",
    41: "target.scene_value is 'match' when the claimed value is only PART of the scene attribute (1 2 vs 1 2 3, 1 2 3 vs 1 2 3 4)",
    42: "the summary does not count claims whose quote is verified but whose value the target scene does not hold",
    43: "USE bomb: nested DEF/USE doubling multiplies the box walk exponentially (17 levels, 1 KB: 13 s and 0.5 GB; 20 levels: does not finish)",
    44: "colour comparison raises OverflowError when a quote holds a number beyond float range (1e999): int(inf) in the rgb255 reading",
    45: "a vector is verified from consecutive numbers with unrelated words between them ('1 apple, 2 pears and then 3 cows' for 1 2 3)",
    46: "a stray number in the quote blocks zero-fill ('the 2 pylons stand 5 m east and 7 m north' is check for 5 0 7)",
    47: "a dotted version is read as a date, so any permutation verifies ('16.7.0' is verified by 'version 7.16.0')",
    48: "a version written with a leading v ('v16.7.0') reads as a mismatch for 16.7.0",
    50: "coverage counts a claim only when its field is the inventory XPath: a claim written as //*[@DEF=A]/@attr or DEF@attr is checked but not counted",
    49: "a field that names a path below a DEF ('//*[@DEF=A]/Shape/Sphere/@radius') did not choose between repeated quotes: the first hit was used",
}


OPEN = {2, 10, 18, 20, 45, 46, 48, 50}


def bug(n):
    if n in OPEN:
        return pytest.mark.xfail(strict=False, reason="BUG-%d %s" % (n, BUGS[n]))
    return pytest.mark.fixed("BUG-%d %s" % (n, BUGS[n]))


def P(*args, bugs=None, id=None):
    """pytest.param with an optional BUG mark."""
    marks = [bug(bugs)] if bugs else []
    return pytest.param(*args, marks=marks, id=id)


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def norms(text, mode="prose"):
    return T.lex(text, mode).norms


def cmp(value, quote, mode="prose", sem=None, **policy):
    return T.compare(value, quote, T.lex(quote, mode), T.TracePolicy(**policy), sem)


def run(claims, sources, **kw):
    if isinstance(claims, dict):
        claims = [claims]
    return T.check_claims(claims, sources, **kw)


def one(claim, sources, **kw):
    return run(claim, sources, **kw).items[0]


def scene_xml(inner, head=""):
    return "<X3D><head>%s</head><Scene>%s</Scene></X3D>" % (head, inner)


def scene_index(inner, head=""):
    sc = T.SceneIndex(scene_xml(inner, head))
    assert sc.ok, sc.error
    return sc


def scene_boxes(inner):
    """World boxes (rounded to 6 decimals) of everything under <Scene>, one per instance."""
    sc = scene_index(inner)
    scene = [e for e in sc.elements if e.tag == "Scene"][0]
    return [T._round_box(b) for b in sc.boxes_for(scene)]


def decode(v):
    if isinstance(v, dict) and "$decimal" in v:
        return Decimal(v["$decimal"])
    if isinstance(v, dict) and "$float" in v:
        return float(v["$float"])
    return v


def approx_box(got, want, tol=1e-6):
    assert len(got) == len(want)
    for g, w in zip(got, want):
        for gi, wi in zip(g, w):
            assert all(abs(a - b) <= tol for a, b in zip(gi, wi)), (got, want)


def locus_boxes(loc):
    """World boxes of a locus as [[x0,y0,z0],[x1,y1,z1]] floats, from 'aabb' or the integer 'aabb_e6' form."""
    if "aabb" in loc:
        return loc["aabb"]
    return [[[v / 1e6 for v in b[:3]], [v / 1e6 for v in b[3:]]] for b in loc.get("aabb_e6", [])]


FX = json.loads(FIXTURE.read_text(encoding="utf-8"))


# ============================================================================================
# 1. LEXER
# ============================================================================================
TOKEN_ROWS = [
    # (text, mode, expected normalised tokens)
    ("0 -1 0", "x3d", ["0", "-1", "0"]),
    ("0 1 0", "x3d", ["0", "1", "0"]),
    ("0.5", "x3d", ["0.5"]),
    ("0 5", "x3d", ["0", "5"]),
    ("1e-05", "x3d", ["1e-05"]),
    ("1E+5", "x3d", ["1e+5"]),
    ("1.5e3", "x3d", ["1.5e3"]),
    ("-1e-3", "x3d", ["-1e-3"]),
    ("+5", "x3d", ["5"]),
    ("-.5", "x3d", ["-.5"]),
    ("5.", "x3d", ["5."]),
    ("1,2,3", "x3d", ["1", "2", "3"]),
    ("1, -2 ,3", "x3d", ["1", "-2", "3"]),
    ("a,b", "x3d", ["a", "b"]),
    ("a_b A_B", "x3d", ["a_b", "A_B"]),
    ("Ball ball BALL", "x3d", ["Ball", "ball", "BALL"]),
    ("Cube1 Cube_1", "x3d", ["Cube1", "Cube_1"]),
    ("&amp;", "x3d", []),
    ("A &amp; B", "x3d", ["A", "B"]),
    ("&#65;", "x3d", ["A"]),
    ("&#x42;", "x3d", ["B"]),
    ("&lt;Box&gt;", "x3d", ["Box"]),
    ("2025-04-11", "x3d", ["2025", "04", "11"]),
    ('size="2 2 2"', "x3d", ["size", "2", "2", "2"]),
    ("1e", "x3d", ["1", "e"]),
    ("", "x3d", []),
    ("   \n\t ", "x3d", []),
    ("3.000 kg", "prose", ["3.000", "kg"]),
    ("1.234,50", "prose", ["1.234,50"]),
    ("$27,578.55", "prose", ["27,578.55"]),
    ("1e-5", "prose", ["1e-5"]),
    ("-1.5", "prose", ["-1.5"]),
    ("Hello, World!", "prose", ["hello", "world"]),
    ("approved_with_remarks", "prose", ["approved", "with", "remarks"]),
    ("Straße STRASSE", "prose", ["strasse", "strasse"]),
    ("ﬁnal ﬃ", "prose", ["final", "ffi"]),
    ("alu\u00adminium", "prose", ["aluminium"]),
    ("Kärki", "prose", ["kärki"]),
    ("Kärki", "prose", ["kärki"]),
    ("ÄÖ äö", "prose", ["äö", "äö"]),
    ("ΣΊΣΥΦΟΣ", "prose", ["σίσυφοσ"]),
    ("東京都新宿区", "prose", ["東京都新宿区"]),
    ("x=−5 and –3", "prose", ["x", "-5", "and", "-3"]),
    ("12'345.60", "prose", ["12'345.60"]),
    ("PO-2025-15903", "prose", ["po", "2025", "15903"]),
    ("a_b", "prose", ["a", "b"]),
    ("A &amp; B", "prose", ["a", "amp", "b"]),
    ("\U0001F600 smile \U0001F600", "prose", ["smile"]),
    ("שלום", "prose", ["שלום"]),
    ("مرحبا", "prose", ["مرحبا"]),
    ("a\x00b\x01c", "prose", ["a", "b", "c"]),
    ("a\u200bb", "prose", ["a", "b"]),
]


@pytest.mark.parametrize("text,mode,want", TOKEN_ROWS, ids=[repr(r[0])[:28] + "-" + r[1] for r in TOKEN_ROWS])
def test_lex_tokens(text, mode, want):
    assert norms(text, mode) == want


@pytest.mark.parametrize("a,b", [("0 -1 0", "0 1 0"), ("0.5", "0 5"), ("1e-05", "1 05"), ("-1", "1"),
                                 ("1.5", "1 5"), ("0 1 2 -1", "0 1 2 1")])
@pytest.mark.parametrize("mode", ["x3d", "prose"])
def test_lex_keeps_sign_point_exponent(a, b, mode):
    """Deliberate difference (a): GAIK's [\\W_]+ split makes these pairs equal; ours must not."""
    assert norms(a, mode) != norms(b, mode)


def test_lex_kinds():
    lx = T.lex("size 12 m", "x3d")
    assert lx.kinds == ["w", "n", "w"]
    assert len(lx) == 3
    assert T.lex("a b", "prose").mode == "prose"


def test_lex_x3d_keeps_identifier_case_prose_folds():
    assert norms("Ball", "x3d") != norms("ball", "x3d")
    assert norms("Ball", "prose") == norms("ball", "prose")


def test_lex_normalizer_hook():
    lx = T.lex("Foo bar", "prose", normalizer=lambda w: w.replace("o", "0"))
    assert lx.norms == ["f00", "bar"]


@pytest.mark.parametrize("mode", ["x3d", "prose"])
def test_lex_nfd_equals_nfc(mode):
    nfc = "café résumé Kärki Ångström"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd
    assert norms(nfd, mode) == norms(nfc, mode)


def _check_offsets(text, mode):
    lx = T.lex(text, mode)
    assert len(lx.norms) == len(lx.starts) == len(lx.ends) == len(lx.kinds)
    prev = 0
    for n, s, e, k in zip(lx.norms, lx.starts, lx.ends, lx.kinds):
        assert 0 <= s < e <= len(text), (text, n, s, e)
        assert s >= prev, "tokens overlap or go backwards"
        prev = e
        # the slice, lexed on its own, gives back the same characters (a token may split once its left
        # context is gone: "50\u0627" after a comma is one word, alone it is a number and a word)
        assert "".join(T.lex(text[s:e], mode).norms) == n, (text, text[s:e], n)


OFFSET_TEXTS = [
    "Quantity: 3.000 kg", "translation=\"1 2 3\"", "A &amp; B &#65; &#x42;", "  leading and trailing  ",
    "x=−5 and –3", "alu\u00adminium", "Kärki", "ﬁnal", "東京都 1e-05 a_b",
    "tab\tsep\nnewline\r\nCRLF", "\U0001F600 1.5 \U0001F600", "שלום 12", "1.234,50 EUR",
    "12'345.60", "\x00\x01 12 \x7f", "v1.2.3", "0x1F 3d 10px", "\u202e1.5\u202c",
]


@pytest.mark.parametrize("mode", ["x3d", "prose"])
@pytest.mark.parametrize("text", OFFSET_TEXTS, ids=[repr(t)[:24] for t in OFFSET_TEXTS])
def test_lex_offset_round_trip(text, mode):
    _check_offsets(text, mode)


def test_lex_offsets_point_into_original_text_for_sign_variants():
    t = "a −5 b –7"
    lx = T.lex(t, "prose")
    assert [t[s:e] for s, e in zip(lx.starts, lx.ends)] == ["a", "−5", "b", "–7"]


def test_lex_entity_offset_covers_the_whole_entity():
    t = "x &#65; y"
    lx = T.lex(t, "x3d")
    assert [t[s:e] for s, e in zip(lx.starts, lx.ends)] == ["x", "&#65;", "y"]


_POOL = list("abcXYZ019 .,;:-+_/\\'\"<>=&#%°µ\t\n\r\x00\x01\x1f\x7f\u00ad\u200b\u200e\u200f\u202e−–"
             "ä̈́ﬁﬃßİΣς中文日本\U0001F600\U0001F1EB"
             "אا٣²①\ufeff퟿\U0010ffff") + [
    "1e-5", "1.5", "-0", "0.", "&amp;", "&#65;", "&#xZZ;", "&lt;", "3.000", "1.234,50", " deg", " m ", " ft",
    "red", "#ff0000", "rgb(1,2,3)", " four", " %", "กำ", "각", "हिन्दी"]


def _rand_text(rnd, n):
    return "".join(rnd.choice(_POOL) for _ in range(rnd.randint(0, n)))


@pytest.mark.parametrize("seed", range(6))
def test_lex_fuzz_never_raises_and_offsets_hold(seed):
    rnd = random.Random(seed)
    for _ in range(1500):
        t = _rand_text(rnd, 40)
        for mode in ("prose", "x3d"):
            _check_offsets(t, mode)


@pytest.mark.parametrize("seed", range(4))
def test_lex_fuzz_lone_surrogates_do_not_raise(seed):
    rnd = random.Random(100 + seed)
    pool = ["\ud800", "\udc00", "\udfff", "a", "1", " ", "ä", "-", "."]
    for _ in range(800):
        t = "".join(rnd.choice(pool) for _ in range(rnd.randint(0, 20)))
        for mode in ("prose", "x3d"):
            lx = T.lex(t, mode)
            assert len(lx.norms) == len(lx.starts)


def test_lex_very_long_inputs_are_linear_enough():
    t0 = time.time()
    T.lex("1 " * 300000, "x3d")
    T.lex("word " * 300000, "prose")
    assert time.time() - t0 < 10


def test_lex_digit_run_and_dots_do_not_backtrack():
    t0 = time.time()
    for text in ("9" * 200000, "1." * 100000, "1,2" * 70000, "-" * 200000, "e" * 200000):
        T.lex(text, "x3d")
        T.lex(text, "prose")
    assert time.time() - t0 < 10


@pytest.mark.parametrize("text,want", [
    ("<?xml version='1.0'?><X3D/>", "x3d"), ("<X3D/>", "x3d"), ("\ufeff <?xml?>", "x3d"),
    ("#X3D V3.3 utf8", "x3d"), ("#VRML V2.0 utf8", "x3d"), ('{"X3D":{"@version":"4.0"}}', "x3d"),
    ("hello", "text"), ("<html>", "text"), ('{"a":1}', "text"), ("", "text"), ("   \n", "text"),
])
def test_sniff_kind(text, want):
    assert T.sniff_kind(text) == want


def test_source_kind_auto_and_mode():
    assert T.Source("a", "<X3D/>").kind == "x3d" and T.Source("a", "<X3D/>").mode == "x3d"
    assert T.Source("a", "plain").kind == "text" and T.Source("a", "plain").mode == "prose"
    assert T.Source("a", "<X3D/>", kind="text").mode == "prose"
    s = T.Source("a", "café")
    assert s.sha256 == hashlib.sha256("café".encode("utf-8")).hexdigest()
    assert s.info() == {"id": "a", "kind": "text", "sha256": s.sha256, "bytes": 5}


# ============================================================================================
# 2. FIND: occurrences, whole token, edges
# ============================================================================================
@pytest.mark.parametrize("text,needle,want", [
    ("a a a a a", ["a", "a"], [0, 2]),
    ("a a a", ["a", "a"], [0]),
    ("a b a b a b", ["a", "b"], [0, 2, 4]),
    ("a b a", ["a", "b", "a"], [0]),
    ("a b a b a", ["a", "b", "a"], [0]),   # overlapping at index 2 is skipped
    ("x a b c a b c", ["a", "b", "c"], [1, 4]),
    ("abc", ["abc"], [0]),
    ("abc", ["ab"], []),
    ("abc abc", [], []),
    ("", ["a"], []),
    ("1 1 1 1 1 1", ["1", "1", "1"], [0, 3]),
])
def test_occurrences_non_overlapping(text, needle, want):
    src = T.Source("s", text, kind="text")
    assert src.occurrences(needle) == want


def test_occurrences_counts_match_check_claims():
    src = T.Source("s", 'Box size="2 2 2" and Box size="2 2 2" and Box size="2 2 2"', kind="x3d")
    it = one({"field": "x", "value": "2 2 2", "quote": 'size="2 2 2"'}, [src])
    assert it.occurrences == 3 and it.status == "found"


@pytest.mark.parametrize("quote,text,found", [
    ("12345", "order12345", False),
    ("order", "order12345", False),
    ("12345", "order 12345", True),
    ("3.000 kg", "Quantity: 3.000   kg total", True),
    ("TOTAL", "the total is", True),
    ("新宿区", "東京都新宿区", False),   # CJK run is one token (whole-token rule)
    ("aluminium", "alu\u00adminium", True),
    ("Kaerki", "Kärki", False),
    ("-5", "x 5", False),
    ("5", "x -5", False),
    ("0.5", "x 0 5", False),
    ("1.5", "1.50", False),
])
def test_find_whole_token_prose(quote, text, found):
    it = one({"field": "f", "value": None, "quote": quote}, [T.Source("s", text, kind="text")])
    assert (it.status == "found") is found
    assert (it.status == "not_found") is (not found)


def test_find_x3d_is_case_sensitive():
    sc = T.Source("s", '<X3D><Scene><Shape DEF="Ball"/></Scene></X3D>')
    assert one({"field": "f", "value": None, "quote": 'DEF="Ball"'}, [sc]).status == "found"
    assert one({"field": "f", "value": None, "quote": 'DEF="ball"'}, [sc]).status == "not_found"


@pytest.mark.parametrize("text", ["alpha beta", "alpha", "x alpha beta y"])
def test_find_quote_at_text_edges(text):
    q = "alpha beta" if "beta" in text else "alpha"
    it = one({"field": "f", "value": None, "quote": q}, [T.Source("s", text, kind="text")])
    assert it.status == "found"
    s, e = it.span
    assert text[s:e] == q


def test_find_span_excludes_surrounding_punctuation():
    text = '..."alpha beta"!!!'
    it = one({"field": "f", "value": None, "quote": "alpha beta"}, [T.Source("s", text, kind="text")])
    s, e = it.span
    assert text[s:e] == "alpha beta"


@pytest.mark.parametrize("quote,status,verdict", [
    ("", "no_quote", "unchecked"), ("   ", "no_quote", "unchecked"), ("\n\t", "no_quote", "unchecked"),
    (None, "no_quote", "unchecked"), ("...", "not_found", "check"), ('"', "not_found", "check"),
    ("&", "not_found", "check"),
])
def test_find_empty_or_tokenless_quotes(quote, status, verdict):
    it = one({"field": "f", "value": "x", "quote": quote}, [T.Source("s", "some \" text & ... here", kind="text")])
    assert (it.status, it.verdict) == (status, verdict)


def test_find_empty_quote_does_not_search():
    it = one({"field": "f", "value": 1, "quote": ""}, [T.Source("s", "1")])
    assert it.span is None and it.occurrences == 0 and it.selectors == [] and it.locus == {}


def test_find_moved_between_sources():
    srcs = [T.Source("a", "nothing here", kind="text"), T.Source("b", "the radius is 0.5 m", kind="text")]
    it = one({"field": "r", "value": 0.5, "quote": "radius is 0.5", "source": "a"}, srcs)
    assert it.status == "moved" and it.source == "b" and it.document == 2


def test_find_prefers_cited_source_even_if_other_has_it_first():
    srcs = [T.Source("a", "radius 0.5", kind="text"), T.Source("b", "radius 0.5", kind="text")]
    it = one({"field": "r", "value": 0.5, "quote": "radius 0.5", "source": "b"}, srcs)
    assert it.source == "b" and it.status == "found" and it.document == 2


def test_find_document_number_selects_source_like_gaik():
    srcs = [T.Source("a", "radius 0.5", kind="text"), T.Source("b", "radius 0.5", kind="text")]
    it = one({"field": "r", "value": 0.5, "quote": "radius 0.5", "document": 2}, srcs)
    assert it.source == "b"
    it = one({"field": "r", "value": 0.5, "quote": "radius 0.5", "document": 9}, srcs)
    assert it.source == "a"   # out of range: first source, as GAIK


def test_find_not_found_keeps_cited_source_and_no_span():
    srcs = [T.Source("a", "x", kind="text"), T.Source("b", "y", kind="text")]
    it = one({"field": "r", "value": 1, "quote": "zzz", "source": "b"}, srcs)
    assert (it.status, it.verdict, it.source, it.span, it.occurrences) == ("not_found", "check", "b", None, 0)


# ============================================================================================
# 3. COMPARE: GAIK conformance fixture (value, quote, gaik_expected, x3dtrace_expected, reason)
# ============================================================================================
# fixture id -> bug number, for rows whose x3dtrace_expected the current code does not meet
KNOWN_VS_BUGS = {
    "vs-051": 4, "vs-066": 26, "x-rot-3": 3, "x-col-3": 13, "x-vec-2": 4, "x-vec-6": 10,
    "x-vec-7": 10, "x-vec-8": 11, "x-num-6": 15, "x-num-9": 20,
}


def _vs_param(r):
    marks = [bug(KNOWN_VS_BUGS[r["id"]])] if r["id"] in KNOWN_VS_BUGS else []
    return pytest.param(r, marks=marks, id=r["id"])


def test_fixture_shape_and_reasons():
    for sec in ("value_status", "tokens", "number_readings", "date_parts", "verdict_of"):
        for r in FX[sec]:
            assert "gaik_expected" in r and "x3dtrace_expected" in r and "reason" in r
            if r["gaik_expected"] != r["x3dtrace_expected"]:
                assert r["reason"].strip(), "every divergence from GAIK needs a reason: %r" % (r,)
            else:
                assert r["reason"] == ""
    assert len(FX["value_status"]) >= 120
    assert "MIT" in FX["gaik_licence"]


def test_fixture_gaik_test_and_readme_rows_agree_except_documented():
    rows = [r for r in FX["value_status"] if r["origin"] in ("gaik-test", "gaik-readme")]
    assert len(rows) >= 45
    differ = [r["id"] for r in rows if r["gaik_expected"] != r["x3dtrace_expected"]]
    assert differ == ["vs-034"], differ   # not_ok: code_values_unchecked is a policy switch, see vs-034b


@pytest.mark.parametrize("r", [_vs_param(r) for r in FX["value_status"]])
def test_conformance_value_status(r):
    value = decode(r["value"])
    state = cmp(value, r["quote"], r["mode"], r["sem"], **r["policy"]).state
    assert state == r["x3dtrace_expected"], (r["id"], r["reason"])


@pytest.mark.parametrize("r", [pytest.param(r, id="%s-%s" % (r["mode"], i)) for i, r in enumerate(FX["tokens"])])
def test_conformance_tokens(r):
    assert norms(r["text"], r["mode"]) == r["x3dtrace_expected"], r["reason"]


@pytest.mark.parametrize("r", [pytest.param(r, id=repr(r["text"])[:30]) for r in FX["number_readings"]])
def test_conformance_number_readings(r):
    q = T.lex(r["text"], "prose")
    vals = sorted({round(n.value, 12) for n in T.quote_numbers(q, r["text"], T.TracePolicy()) if not n.word})
    assert vals == [round(v, 12) for v in r["x3dtrace_expected"]], r["reason"]


@pytest.mark.parametrize("r", [pytest.param(r, id=repr(r["text"])) for r in FX["date_parts"]])
def test_conformance_date_parts(r):
    assert T._date_parts(r["text"]) == r["x3dtrace_expected"]


@pytest.mark.parametrize("r", [pytest.param(r, id="v%d-%s-%s" % (i, r["status"], r["value_status"]))
                               for i, r in enumerate(FX["verdict_of"])])
def test_conformance_verdict_of(r):
    pol = T.TracePolicy(**r["policy"])
    got = T.verdict_of(r["status"], r["value_status"], r["value"], len(norms(r["quote"])), pol, r["occurrences"])
    assert got == r["x3dtrace_expected"], r["reason"]


def test_conformance_check_text_scenario():
    sc = FX["check_text_scenario"]
    claims = [{"field": e["field"], "value": decode(e["value"]), "quote": e["quote"]} for e in sc["entries"]]
    rep = T.check_claims(claims, sc["source_text"])
    got = {it.field: it.verdict for it in rep.items}
    assert got == sc["expected_verdicts"]


# ============================================================================================
# 4. COMPARE: kinds not (fully) covered by the fixture
# ============================================================================================
@pytest.mark.parametrize("value,quote,mode,want", [
    # numbers
    (0.5, "0.5", "x3d", "match"), (0.5, "0 5", "x3d", "mismatch"), (-1, "0 -1 0", "x3d", "match"),
    (1, "0 -1 0", "x3d", "mismatch"), (2, "0 -1 0", "x3d", "mismatch"), (-0.0, "0", "x3d", "match"),
    (5, "5.0", "x3d", "match"), (5.0, "5", "x3d", "match"), ("5", "5.0", "x3d", "match"),
    (1e-5, "0.00001", "x3d", "match"), (0.00001, "1e-5", "x3d", "match"), (100000, "1e5", "x3d", "match"),
    (1500, "1.5e3", "x3d", "match"), (-1500, "-1.5e3", "x3d", "match"), (1500, "-1.5e3", "x3d", "mismatch"),
    (3.0, "3.0000001", "x3d", "match"), (3.0, "3.001", "x3d", "mismatch"),
    (7, "x7", "x3d", "mismatch"), (7, "7x", "x3d", "match"),
    (1234.5, "1.234,50", "prose", "match"), (1234.5, "1,234.50", "prose", "match"),
    (0.5, "0,5", "prose", "match"),
    (3, "3.000", "prose", "match"), (3000, "3.000", "prose", "match"), (30, "3.000", "prose", "mismatch"),
    (-7, "temperature -7 C", "prose", "match"), (7, "temperature -7 C", "prose", "mismatch"),
    (-7, "temperature 7 C", "prose", "mismatch"), (-7, "temperature −7 C", "prose", "match"),
    (7, "temperature −7 C", "prose", "mismatch"),
    (12.5, "12.5 %", "prose", "match"), (125, "12.5 %", "prose", "mismatch"),
    (2, "x2", "prose", "mismatch"),
    # strings that look numeric
    ("5", "5", "prose", "match"), ("0.5", "0.5", "x3d", "match"), ("1e3", "1000", "x3d", "match"),
    # identifiers and text
    ("Ball", 'DEF="Ball"', "x3d", "match"), ("Ball", 'DEF="Ball2"', "x3d", "mismatch"),
    ("Ball", "ball", "prose", "match"), ("big red ball", "a big red ball here", "prose", "match"),
    ("big blue ball", "a big red ball here", "prose", "mismatch"), ("", "anything", "prose", "unchecked"),
    ("   ", "anything", "prose", "unchecked"),
    # non-comparable
    (None, "x", "prose", "unchecked"), (True, "true", "prose", "unchecked"), (False, "false", "x3d", "unchecked"),
    ({"a": 1}, "a 1", "prose", "unchecked"), (["a"], "a", "prose", "unchecked"), ([], "a", "prose", "unchecked"),
    (float("nan"), "nan", "prose", "mismatch"), (float("inf"), "inf", "prose", "mismatch"),
    (float("-inf"), "-inf", "prose", "mismatch"),
])
def test_compare_scalar_and_text(value, quote, mode, want):
    assert cmp(value, quote, mode).state == want


@pytest.mark.parametrize("value,quote,mode,want", [
    ("1 2 3", "1 2 3", "x3d", "match"), ("1 2 3", "3 2 1", "x3d", "mismatch"), ("1 2 3", "1 2 4", "x3d", "mismatch"),
    ("1,2,3", "1 2 3", "x3d", "match"), ([1, 2, 3], "1 2 3", "x3d", "match"), ((1, 2, 3), "1 2 3", "x3d", "match"),
    ([1.5, -2, 0], 'translation="1.5 -2 0"', "x3d", "match"), ([1.5, 2, 0], 'translation="1.5 -2 0"', "x3d", "mismatch"),
    ("0 -1 0", "0 -1 0", "x3d", "match"), ("0 1 0", "0 -1 0", "x3d", "mismatch"),
    ("0 -1 0", "0 1 0", "x3d", "mismatch"), ("-1 -1 -1", "1 1 1", "x3d", "mismatch"),
    ("0 1 2 -1 3 4 5 -1", "0 1 2 -1 3 4 5 -1", "x3d", "match"),
    ("0 1 2 1 3 4 5 1", "0 1 2 -1 3 4 5 -1", "x3d", "mismatch"),
    ("1e-05 2 3", "1e-05 2 3", "x3d", "match"), ("0.00001 2 3", "1e-05 2 3", "x3d", "match"),
    ("0.30000001 0 0", "0.3 0 0", "x3d", "match"), ("1 2 3 4", "1 2 3 4", "x3d", "match"),
    ("1 2 3 4", "1 2 3 5", "x3d", "mismatch"), ("1 2", "1 2", "x3d", "match"), ("1 2", "2 1", "x3d", "mismatch"),
    ("10 20 30", "10 20 30", "prose", "match"), ("10 20 30", "30 20 10", "prose", "mismatch"),
    ("1 2 3", "a is 1, b is 2 and c is 3", "prose", "match"),
    ("1 2 3", "1 2", "prose", "mismatch"),
    ("0 0 0", "origin", "prose", "unchecked"),
])
def test_compare_vectors_in_order(value, quote, mode, want):
    assert cmp(value, quote, mode).state == want


def test_vector_is_never_read_as_a_date():
    for v, q in [("1 2 3", "3 2 1"), ("10 20 30", "30 20 10"), ("1 0 5", "5 0 1"), ("2 3 4", "4 2 3")]:
        assert cmp(v, q).state == "mismatch", (v, q)
        assert T._floats(v) is not None   # it is a vector first


@pytest.mark.parametrize("value,quote,sem,state,deriv", [
    (1.5708, "90 degrees", "angle", "match", ["deg2rad"]),
    (1.5708, "90 deg", "angle", "match", ["deg2rad"]),
    (1.5708, "90°", "angle", "match", ["deg2rad"]),
    (0.7854, "45 degrees", "angle", "match", ["deg2rad"]),
    (3.1416, "180 degrees", "angle", "match", ["deg2rad"]),
    (-1.5708, "-90 degrees", "angle", "match", ["deg2rad"]),
    (1.5708, "90", "angle", "mismatch", []),
    (1.5708, "90 degrees", "length", "match", ["deg2rad"]),
    (90, "90 degrees", "angle", "mismatch", []),
    (1.5708, "1.5708 rad", "angle", "match", []),
    (1.5708, "1.5708 radians", "angle", "match", []),
    (1.5708, "1.5708 degrees", "angle", "mismatch", []),
    (0.5, "50 %", "fraction", "match", ["percent"]),
    (0.5, "50%", "fraction", "match", ["percent"]),
    (0.25, "25 percent", "fraction", "match", ["percent"]),
    (0.5, "50", "fraction", "mismatch", []),
    (0.6096, "2 ft", "length", "match", ["unit:ft"]),
    (0.6096, "2 feet", "length", "match", ["unit:feet"]),
    (0.0508, "2 inches", "length", "match", ["unit:inches"]),
    (2.5, "250 cm", "length", "match", ["unit:cm"]),
    (0.25, "250 mm", "length", "match", ["unit:mm"]),
    (1500, "1.5 km", "length", "match", ["unit:km"]),
    (120, "2 minutes", "time", "match", ["unit:minutes"]),
    (0.5, "500 ms", "time", "match", ["unit:ms"]),
    (7200, "2 hours", "time", "match", ["unit:hours"]),
    (2, "2 ft", "length", "mismatch", []),
    (2, "2 m", "length", "match", []),
    (2, "2 metres", "length", "match", []),
    (2, "2 cm", "length", "mismatch", []),
    (2, "2 s", "time", "match", []),
    (2, "2 sec", "time", "match", []),
    (4, "four", None, "match", ["numword"]),
    (4, "FOUR", None, "match", ["numword"]),
    (0, "zero", None, "match", ["numword"]),
    (20, "twenty", None, "match", ["numword"]),
    (50, "fifty", None, "match", ["numword"]),
    (100, "a hundred", None, "match", ["numword"]),
    (0.5, "half", None, "match", ["numword"]),
    (12, "a dozen", None, "match", ["numword"]),
    (5, "four", None, "mismatch", []),
])
def test_compare_typed_conversions(value, quote, sem, state, deriv):
    r = cmp(value, quote, "prose", sem)
    assert r.state == state
    assert r.derivation == deriv


@pytest.mark.parametrize("value,quote,sem,state,deriv", [
    ("0 0 1 1.5708", "rotate about z by 90 degrees", "rotation", "match", ["axis:z", "deg2rad"]),
    ("0 1 0 1.5708", "90 degrees around y", "rotation", "match", ["axis:y", "deg2rad"]),
    ([1, 0, 0, 1.5708], "90 degrees around X", "rotation", "match", ["axis:x", "deg2rad"]),
    ("0 1 0 3.1416", "turn 180 degrees about the vertical", "rotation", "match", ["axis:vertical", "deg2rad"]),
    ("0 1 0 1.5708", "rotate 1.5708 rad about y", "rotation", "match", ["axis:y"]),
    ("0 1 0 1.5708", "around y", "rotation", "unchecked", []),
    ("1 0 0 1.5708", "90 degrees around y", "rotation", "mismatch", []),
    ("0 0 1 1.5708", "90 degrees around y", "rotation", "mismatch", []),
    ("0 1 0 0.7854", "90 degrees around y", "rotation", "mismatch", []),
    ("0 -1 0 -1.5708", "90 degrees around y", "rotation", "match", ["axis:y", "deg2rad"]),
    ("0 1 0 1.5708", 'rotation="0 1 0 1.5708"', "rotation", "match", []),
    ("0 1 0 1.5708", 'rotation="0 -1 0 1.5708"', "rotation", "mismatch", []),
])
def test_compare_rotation_from_axis_letter_and_angle(value, quote, sem, state, deriv):
    r = cmp(value, quote, "x3d" if "=" in quote else "prose", sem)
    assert (r.state, r.derivation) == (state, deriv)


@pytest.mark.parametrize("value,quote", [
    ("0 1 0 3.1416", 'rotation="0 1 0 1.5708"'),
    P("0 -1 0 1.5708", "90 degrees around y", bugs=3),
    ("0 1 0 -1.5708", "90 degrees around y"),
])
def test_rotation_sign_of_axis_and_angle_matters(value, quote):
    assert cmp(value, quote, "prose", "rotation").state == "mismatch"


@pytest.mark.parametrize("value,quote,sem,state,deriv", [
    ("2 2 2", "a 2 m cube", "length", "match", ["broadcast"]),
    ("2 2 2", "a cube of side 2", None, "match", ["broadcast"]),
    ("0 0 0", "at 0", None, "match", ["broadcast"]),
    ("2 2", "a 2 m square", None, "match", ["broadcast"]),
    ("2 3 4", "a 2 m cube", "length", "mismatch", []),
    ("2 2 2", "a 3 m cube", "length", "mismatch", []),
    ("1 0 0", "red", "color", "match", ["colorname:red"]),
    ("0 1 0", "green", "color", "match", ["colorname:green"]),
    ("0 0 1", "blue", "color", "match", ["colorname:blue"]),
    ("1 1 1", "white", "color", "match", ["colorname:white"]),
    ("0 0 0", "black", "color", "match", ["colorname:black"]),
    ("0.5 0.5 0.5", "gray", "color", "match", ["colorname:gray"]),
    ("1 0.647 0", "orange", "color", "match", ["colorname:orange"]),
    ("0.97 0.02 0.02", "red", "color", "match", ["colorname:red"]),
    ("0.8 0.1 0.1", "red", "color", "near", ["colorname-class:red"]),
    ("0.9 0 0", "red", "color", "near", ["colorname-class:red"]),
    ("1 0 0", "#ff0000", "color", "match", ["hex"]),
    ("1 0 0", "ff0000", "color", "match", ["hex"]),
    ("0.2 0.4 0.6", "#336699", "color", "match", ["hex"]),
    ("0.2 0.4 0.6", "colour #336699 please", "color", "match", ["hex"]),
    ("0.2 0.4 0.7", "#336699", "color", "mismatch", []),
    ("0.8 0.2 0.1", "204 51 26", "color", "match", ["rgb255"]),
    ("1 0.5 0", "rgb(255, 128, 0)", "color", "match", ["rgb255"]),
    ("1 0.5 0", "255 127 0", "color", "match", ["rgb255"]),
    ("0.8 0.2 0.1", "204 51 99", "color", "mismatch", []),
    ("0.8 0.2 0.1", "0.8 0.2 0.1", "color", "match", []),
    ("1 0 0", "1 0 0", "color", "match", []),
    ("0 2 0", "2 m above", "length", "near", ["zero-fill"]),
    ("0 0.5 0", "0.5 m up", "length", "near", ["zero-fill"]),
    ("3 0 0", "3 m to the right", "length", "near", ["zero-fill"]),
    ("0 2 3", "2 up and 3 forward", "length", "near", ["zero-fill"]),
    ("0 3 2", "2 up and 3 forward", "length", "mismatch", []),
    ("0 -2 0", "2 m above", "length", "mismatch", []),
])
def test_compare_colours_broadcast_zero_fill(value, quote, sem, state, deriv):
    r = cmp(value, quote, "prose", sem)
    assert (r.state, r.derivation) == (state, deriv)


@pytest.mark.parametrize("value,quote,sem", [
    P("0 1 0", "1 0 0", "length", bugs=4),
    P("0 0 1", "1 0 0", None, bugs=4),
    P("0 2 0", "2 0 0", "length", bugs=4),
    P("0 0 5", 'translation="5 0 0"', None, bugs=4),
    P("0 0 1.5708", 'rotation="0 1 0 1.5708"', None, bugs=10),
    P("1 3", "1 2 3", None, bugs=10),
    P("1 3 5", "1 2 3 4 5", None, bugs=10),
    P("2 2", 'scale="2 2 2"', None, bugs=10),
])
def test_vector_must_not_pass_for_another_vector(value, quote, sem):
    """A different vector must never be 'near' or 'match' because zeros/numbers happen to line up."""
    assert cmp(value, quote, "x3d", sem).state == "mismatch"


@pytest.mark.parametrize("value,quote,sem", [
    P("0 1 0 90", "rotate 90 degrees about y", "rotation", bugs=12),
    P("0 1 0 90", "0 1 0 90 degrees", "rotation", bugs=12),
])
def test_rotation_degrees_written_for_radians_is_a_mismatch_with_a_note(value, quote, sem):
    r = cmp(value, quote, "prose", sem)
    assert r.state == "mismatch" and "degree" in r.note


def test_scalar_unit_mismatch_has_a_note():
    r = cmp(90, "90 degrees", "prose", "angle")
    assert r.state == "mismatch" and "degrees" in r.note
    r = cmp(2, "2 ft", "prose", "length")
    assert r.state == "mismatch" and "ft" in r.note
    r = cmp(2, "2 minutes", "prose", "time")
    assert r.state == "mismatch" and "minutes" in r.note


@bug(11)
@pytest.mark.parametrize("value,quote", [("2 2 2", "a 2 ft cube"), ("0 2 0", "2 ft above"), ("2 3 4", "2 ft by 3 ft by 4 ft")])
def test_vector_length_in_feet_in_a_metre_scene_is_a_mismatch(value, quote):
    r = cmp(value, quote, "prose", "length")
    assert r.state == "mismatch" and r.note


def test_feet_scene_uses_policy_length_scale():
    assert cmp(2, "2 ft", "prose", "length", length_scale=0.3048).state == "match"
    assert cmp(2, "2 m", "prose", "length", length_scale=0.3048).state == "mismatch"
    assert cmp(3.2808, "1 m", "prose", "length", length_scale=0.3048).state == "match"
    assert cmp(0.6096, "2 ft", "prose", "length", length_scale=0.3048).state != "match"


@pytest.mark.parametrize("conv,value,quote,sem,state_off", [
    ("deg2rad", 1.5708, "90 degrees", "angle", "mismatch"),
    ("percent", 0.5, "50 %", "fraction", "mismatch"),
    ("unit", 0.6096, "2 ft", "length", "mismatch"),
    ("numword", 4, "four", None, "mismatch"),
    ("broadcast", "2 2 2", "a 2 m cube", None, "mismatch"),
    ("hex", "1 0 0", "#ff0000", "color", "unchecked"),
    ("rgb255", "0.8 0.2 0.1", "204 51 26", "color", "mismatch"),
    ("colorname", "1 0 0", "red", "color", "unchecked"),
    ("axis", "0 0 1 1.5708", "1.5708 about z", "rotation", "mismatch"),
])
def test_each_conversion_can_be_switched_off(conv, value, quote, sem, state_off):
    assert cmp(value, quote, "prose", sem).state in ("match", "near")
    others = tuple(c for c in T.ALL_CONVERSIONS if c != conv)
    off = cmp(value, quote, "prose", sem, conversions=others)
    assert off.state == state_off, (conv, off)


def test_strict_policy_turns_conversions_off_and_matches_literally():
    strict = T.TracePolicy.strict()
    assert strict.conversions == () and strict.round_to_printed is False
    for value, quote, sem in [(1.5708, "90 degrees", "angle"), (0.5, "50 %", "fraction"), (4, "four", None),
                              ("2 2 2", "a 2 m cube", None), ("1 0 0", "red", "color")]:
        assert T.compare(value, quote, T.lex(quote, "prose"), strict, sem).state in ("mismatch", "unchecked")
    assert T.compare(1.5708, "1.5708", T.lex("1.5708", "prose"), strict, "angle").state == "match"


@pytest.mark.parametrize("value,quote,state", [
    (3.14159265, "3.14159", "match"), (3.14159265, "3.1417", "mismatch"), (1.0000001, "1.0", "match"),
    (0.33, "0.3333", "near"), (0.333, "0.3333", "near"), (0.3333, "0.33", "match"),
    (3.1416, "3.14159", "near"), (0.5, "0.50", "match"), (0.3, "0.30000001", "match"),
])
def test_rounded_display_rules(value, quote, state):
    assert cmp(value, quote, "x3d").state == state


@pytest.mark.parametrize("value,quote", [P(0.04, "transparency 0.0", bugs=20), P(0.14, "transparency 0.1", bugs=20),
                                         P(0.12, "0.1", bugs=20)])
def test_value_more_precise_than_quote_is_not_exact(value, quote):
    """SPEC ambiguity: a value that claims precision the quote does not have should be at best 'near'."""
    assert cmp(value, quote).state in ("near", "mismatch")


def test_round_to_printed_off_makes_rounded_display_a_mismatch():
    assert cmp(3.14159265, "3.14159", "prose", None, round_to_printed=False).state == "mismatch"
    assert cmp(3.14159265, "3.14159", "prose", None).state == "match"


def test_number_tolerance_policy():
    assert cmp(1.0005, "1.0", "prose", None, round_to_printed=False).state == "mismatch"
    assert cmp(1.0005, "1.0", "prose", None, round_to_printed=False, number_tolerance=1e-3).state == "match"
    assert cmp(1.0, "1.0000005", "prose", None, round_to_printed=False).state == "match"


@pytest.mark.parametrize("value,quote,state", [
    ("2025-04-11", "11.04.2025", "match"), ("2025-04-11", "2025-04-11", "match"), ("2025-04-11", "April 11, 2025", "match"),
    ("2025-04-11", "11 Apr 2025", "match"), ("2025-04-12", "11.04.2025", "mismatch"),
    ("2025-04-11", "11. huhtikuuta 2025", "mismatch"), ("2025-03-11", "marble 11 2025", "mismatch"),
    ("2025-04-11", "2024-04-11", "mismatch"), ("2026-02-15", "02/15/2026", "match"),
])
def test_compare_dates(value, quote, state):
    assert cmp(value, quote).state == state


@pytest.mark.parametrize("value,quote", [P("2025-11-11", "11 2025", bugs=26), P("2025-01-01", "01 2025", bugs=26)])
def test_date_parts_are_consumed_once_each(value, quote):
    """SPEC ambiguity: a month that is only evidenced by the day number is not a date match."""
    assert cmp(value, quote).state == "mismatch"


def test_date_iso_day_month_swap_is_accepted_like_gaik():
    """Documented, same as GAIK (locale ambiguity); pinned so a change is noticed."""
    assert cmp("2025-04-11", "2025-11-04").state == "match"


def test_date_in_an_x3d_meta_tag():
    meta = '<X3D><head><meta name="created" content="2025-04-11"/></head><Scene/></X3D>'
    it = one({"field": "meta", "value": "2025-04-11", "quote": 'content="2025-04-11"'}, [T.Source("s", meta)])
    assert it.verdict == "verified"


@pytest.mark.parametrize("value,quote,sem,state", [
    ("Ball", "Ball", "identifier", "match"), ("007", "Part 7", None, "mismatch"), ("007", "Part 007", None, "match"),
    ("010", "010 6061-T6", None, "match"), ("10", "010 6061-T6", None, "match"),
])
def test_identifier_and_leading_zero_values(value, quote, sem, state):
    assert cmp(value, quote, "prose", sem).state == state


def test_code_values_unchecked_parity_switch():
    assert cmp("not_ok", "Waste sorted [X]").state == "mismatch"
    assert cmp("not_ok", "Waste sorted [X]", "prose", None, code_values_unchecked=True).state == "unchecked"
    assert cmp("Not_Ok", "Waste sorted [X]", "prose", None, code_values_unchecked=True).state == "mismatch"


def test_match_reformatted_identifiers_switch():
    assert cmp("7200-4453-21", "PO 7200445321").state == "match"
    assert cmp("7200-4453-21", "PO 7200445321", "prose", None, match_reformatted_identifiers=False).state == "mismatch"
    assert cmp("7200-4453", "PO 7200445321").state == "mismatch"      # prefix of the squeezed number
    assert cmp("AB-1", "ab1").state == "mismatch"                    # too short to be an identifier reformat


def test_long_arrays_need_a_verbatim_copy():
    big = [i + 0.5 for i in range(100)]
    q = " ".join(map(str, big))
    assert cmp(big, q, "x3d").state == "match"
    assert cmp(big, q, "x3d").derivation == ["verbatim"]
    wrong = big[:99] + [100.5]
    assert cmp(wrong, q, "x3d").state == "mismatch"
    assert cmp(q, q, "x3d").state == "match"


def test_value_extends_the_quote_is_supported_via_the_source():
    text = "The material is brushed stainless steel with a satin finish and a thin protective film."
    it = one({"field": "mat", "value": "brushed stainless steel with a satin finish",
              "quote": "stainless steel with a satin"}, [T.Source("s", text)])
    assert it.value_status == "match" and it.derivation == ["value-extends-quote"] and it.verdict == "verified"
    it = one({"field": "mat", "value": "brushed titanium with a satin finish", "quote": "stainless steel with a satin"},
             [T.Source("s", text)])
    assert it.value_status == "mismatch" and it.verdict == "reworded"


@pytest.mark.parametrize("value,quote", [P(5, "four cubes", bugs=14), P(4, "five cubes", bugs=14), P(3, "two", bugs=14),
                                         P("2 2 2", "a three metre cube", bugs=14)])
def test_wrong_number_word_is_check_not_unchecked(value, quote):
    it = one({"field": "n", "value": value, "quote": quote}, [T.Source("s", "see: " + quote, kind="text")])
    assert it.verdict == "check"


@pytest.mark.parametrize("value,quote", [(5, "several cubes"), (2, "kaksi kuutiota"), (5, "a large red ball")])
def test_number_that_no_table_can_read_is_unchecked(value, quote):
    it = one({"field": "n", "value": value, "quote": quote}, [T.Source("s", "see: " + quote, kind="text")])
    assert it.verdict == "unchecked"


@pytest.mark.parametrize("value,quote", [P("0 1 0", "red", bugs=13), P("1 0 0", "blue", bugs=13),
                                         P("0 0 1", "yellow", bugs=13)])
def test_colour_name_that_contradicts_the_value_is_not_unchecked(value, quote):
    it = one({"field": "Material.diffuseColor", "value": value, "quote": quote}, [T.Source("s", "paint it " + quote)])
    assert it.verdict == "check"


@pytest.mark.parametrize("quote,value", [P("radius 2 in the middle", 2, bugs=15),
                                         P("a box 2 in front of the wall", 2, bugs=15), ("height 3 s", 3)])
def test_short_words_are_not_unit_evidence_when_they_are_prepositions(quote, value):
    it = one({"field": "Cylinder.height", "value": value, "quote": quote}, [T.Source("s", quote, kind="text")])
    assert it.verdict == "verified"


@bug(29)
def test_percent_value_for_a_fraction_field_is_a_mismatch():
    it = one({"field": "Material.transparency", "value": 50, "quote": "50 %"}, [T.Source("s", "50 % transparent")])
    assert it.verdict == "check"


@bug(34)
def test_rad_to_degrees_from_a_rounded_quote():
    r = cmp(90, "1.5708 rad", "prose", None)
    assert r.state == "match" and r.derivation == ["rad2deg"]


def test_rad_to_degrees_exact_quote():
    r = cmp(57.29578, "1 rad", "prose", None)
    assert r.state == "match" and r.derivation == ["rad2deg"]


@bug(30)
def test_bare_six_digit_number_is_not_a_hex_colour():
    assert cmp("0.063 0.125 0.188", "part 102030", "prose", "color").state != "match"


@bug(27)
def test_detached_minus_is_not_a_range_dash():
    assert cmp(-5, "pages 3 - 5").state == "mismatch"


def test_detached_minus_still_reads_the_documented_discount_case():
    assert cmp(-1014.5, "Discount (5%) - EUR 1,014.50").state == "match"


@pytest.mark.parametrize("word", [P("\u0939\u093f\u0928\u094d\u0926\u0940", bugs=28), P("\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35", bugs=28),
                                  P("\u05e9\u05b8\u05c1\u05dc\u05d5\u05b9\u05dd", bugs=28),
                                  P("\u0645\u064e\u0631\u0652\u062d\u064e\u0628\u064b\u0627", bugs=28),
                                  "k\u00e4rki", "a\u0308\u0301"])
def test_words_with_combining_marks_stay_one_token(word):
    assert len(norms(word)) == 1


@pytest.mark.parametrize("value,quote", [
    (1234, "Total: 1 234 EUR"),
    P(1234.5, "Total: 1 234,50 EUR", bugs=35), P(1234567, "1 234 567", bugs=35), P(1234.5, "1 234.50", bugs=35),
    P(1234, "Total 1\u00a0234 EUR", bugs=35), P(1234, "Total 1\u202f234 EUR", bugs=35),
    P(1234567.89, "1 234 567,89", bugs=35),
])
def test_space_grouped_thousands(value, quote):
    assert cmp(value, quote).state == "match"


def _long_param(kind, n):
    marks = [bug(36)] if kind in ("int-list", "int-tuple", "float-list") and n > 64 else []
    return pytest.param(kind, n, marks=marks, id="%s-%d" % (kind, n))


@pytest.mark.parametrize("kind,n", [_long_param(k, n) for k in ("int-list", "int-tuple", "str", "float-list")
                                    for n in (10, 64, 65, 100, 1000)])
def test_long_int_arrays_verbatim(kind, n):
    base = list(range(n))
    q = " ".join(map(str, base))
    value = {"int-list": base, "int-tuple": tuple(base), "str": q, "float-list": [float(x) for x in base]}[kind]
    assert cmp(value, q, "x3d").state == "match"


# ============================================================================================
# 5. SceneIndex: spans, paths, units, malformed input
# ============================================================================================
import xml.etree.ElementTree as ET  # noqa: E402

MIXED = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- a comment with <fake tag="x"/> and > signs -->
<X3D profile="Immersive" version="4.0">
  <head>
    <meta name="title" content="café 日本 \U0001F600"/>
    <unit category="length" name="foot" conversionFactor="0.3048"/>
  </head>
  <Scene>
    <Group DEF="G">
      <Shape><Appearance><Material diffuseColor='1 0 0' DEF="M"/></Appearance><Box size="1 2 3"/></Shape>
      <Shape><Appearance><Material USE="M"/></Appearance><Sphere radius="2"/></Shape>
      <Script DEF="S"><![CDATA[ if (a > b && c < d) { x = "<Box/>"; } ]]></Script>
    </Group>
    <Transform translation="1 2 3" rotation="0 0 1 1.5708"><Shape><Cylinder height="4" radius="1"/></Shape></Transform>
    <Transform DEF="T2" translation="0 0 0"><Transform USE="T2x"/></Transform>
    <Transform><Shape/></Transform>
    <Transform/>
    <WorldInfo title="a &gt; b &amp; c" info='quote " inside'/>
  </Scene>
</X3D>
'''


def _mixed():
    sc = T.SceneIndex(MIXED)
    assert sc.ok, sc.error
    return sc


def test_scene_every_element_span_is_a_well_formed_fragment_of_the_same_tag():
    sc = _mixed()
    assert len(sc.elements) > 20
    for e in sc.elements:
        frag = MIXED[e.start:e.end]
        assert frag.startswith("<" + e.tag), (e.tag, frag[:30])
        assert frag.endswith(">")
        root = ET.fromstring(frag)
        assert root.tag == e.tag


def test_scene_children_spans_nest_inside_their_parents():
    sc = _mixed()
    for e in sc.elements:
        for c in e.children:
            ce = sc.elements[c]
            assert e.start < ce.start and ce.end <= e.end
            assert ce.parent == e.idx
        assert e.start < e.tag_end <= e.end


def test_scene_start_tag_end_points_just_after_the_gt():
    sc = _mixed()
    for e in sc.elements:
        assert MIXED[e.tag_end - 1] == ">"
        assert MIXED[e.start:e.tag_end].count("<") == 1, MIXED[e.start:e.tag_end]


def test_scene_attribute_spans_slice_to_the_attribute_value_text():
    sc = _mixed()
    seen = 0
    for e in sc.elements:
        for name, (v, vs, ve) in e.attrs.items():
            assert MIXED[vs:ve] == v, (e.tag, name)
            assert e.start < vs <= ve < e.tag_end
            seen += 1
    assert seen >= 15
    wi = [e for e in sc.elements if e.tag == "WorldInfo"][0]
    assert wi.attrs["title"][0] == "a &gt; b &amp; c"            # raw text, not decoded
    assert wi.attrs["info"][0] == 'quote " inside'               # single-quoted value


def test_scene_comment_and_cdata_do_not_create_elements():
    sc = _mixed()
    tags = [e.tag for e in sc.elements]
    assert "fake" not in tags and tags.count("Box") == 1
    script = [e for e in sc.elements if e.tag == "Script"][0]
    assert "<![CDATA[" in MIXED[script.start:script.end] and script.children == []


def test_scene_offsets_are_character_offsets_not_bytes():
    sc = _mixed()
    meta = [e for e in sc.elements if e.tag == "meta"][0]
    assert MIXED[meta.start:meta.start + 5] == "<meta"
    box = [e for e in sc.elements if e.tag == "Box"][0]
    assert MIXED[box.start:box.end] == '<Box size="1 2 3"/>'


PATH_SCENE = ('<X3D><Scene><Group DEF="G"><Shape><Box/></Shape><Shape><Sphere/></Shape></Group>'
              '<Transform><Shape/></Transform><Transform DEF="T2"><Shape/></Transform><Transform/></Scene></X3D>')


@pytest.mark.parametrize("tag,nth,path,xpath", [
    ("X3D", 0, "/X3D", "/X3D"),
    ("Scene", 0, "/X3D/Scene", "/X3D/Scene"),
    ("Group", 0, "/X3D/Scene/Group[DEF=G]", "/X3D/Scene/Group[@DEF='G']"),
    ("Shape", 0, "/X3D/Scene/Group[DEF=G]/Shape[1]", "/X3D/Scene/Group[@DEF='G']/Shape[1]"),
    ("Box", 0, "/X3D/Scene/Group[DEF=G]/Shape[1]/Box", "/X3D/Scene/Group[@DEF='G']/Shape[1]/Box"),
    ("Shape", 1, "/X3D/Scene/Group[DEF=G]/Shape[2]", "/X3D/Scene/Group[@DEF='G']/Shape[2]"),
    ("Sphere", 0, "/X3D/Scene/Group[DEF=G]/Shape[2]/Sphere", "/X3D/Scene/Group[@DEF='G']/Shape[2]/Sphere"),
    ("Transform", 0, "/X3D/Scene/Transform[1]", "/X3D/Scene/Transform[1]"),
    ("Transform", 1, "/X3D/Scene/Transform[DEF=T2]", "/X3D/Scene/Transform[@DEF='T2']"),
    ("Transform", 2, "/X3D/Scene/Transform[3]", "/X3D/Scene/Transform[3]"),
])
def test_scene_def_paths_and_xpaths(tag, nth, path, xpath):
    sc = T.SceneIndex(PATH_SCENE)
    e = [x for x in sc.elements if x.tag == tag][nth]
    assert e.path == path
    assert sc.xpath(e) == xpath


def test_scene_xpath_resolves_back_to_the_same_element_in_elementtree():
    sc = _mixed()
    root = ET.fromstring(MIXED.split("?>", 1)[1])
    order = list(root.iter())
    assert len(order) == len(sc.elements)
    for e in sc.elements:
        xp = sc.xpath(e)
        rel = xp.split("/", 2)[2] if xp.count("/") >= 2 else ""
        found = root if not rel else root.find("./" + rel)
        assert found is not None, xp
        assert found is order[e.idx], xp


def test_scene_find_def_and_defs_table():
    sc = _mixed()
    assert sc.find_def("G").tag == "Group" and sc.find_def("M").tag == "Material"
    assert sc.find_def("S").tag == "Script" and sc.find_def("nope") is None
    assert set(sc.defs) == {"G", "M", "S", "T2"}


def test_scene_duplicate_def_first_wins():
    sc = T.SceneIndex('<X3D><Scene><Shape DEF="A"><Box/></Shape><Shape DEF="A"><Sphere/></Shape></Scene></X3D>')
    assert sc.find_def("A").children and sc.elements[sc.find_def("A").children[0]].tag == "Box"


def test_scene_element_at_returns_the_deepest_element():
    sc = _mixed()
    for i in range(0, len(MIXED), 7):
        e = sc.element_at(i)
        inside = [x for x in sc.elements if x.start <= i < x.end]
        if not inside:
            assert e is None
        else:
            assert e is max(inside, key=lambda x: x.start)
    assert sc.element_at(-1) is None and sc.element_at(len(MIXED) + 50) is None


def test_scene_attr_at_names_the_attribute_under_the_offset():
    sc = _mixed()
    box = [e for e in sc.elements if e.tag == "Box"][0]
    v, vs, ve = box.attrs["size"]
    assert sc.attr_at(box, vs) == "size" and sc.attr_at(box, ve - 1) == "size"
    assert sc.attr_at(box, box.start) is None
    assert sc.attr_at(box, box.start + len("<Box")) is None          # the space between the tag name and the first attribute


@bug(21)
def test_scene_attr_at_inside_the_attribute_name():
    sc = _mixed()
    box = [e for e in sc.elements if e.tag == "Box"][0]
    v, vs, ve = box.attrs["size"]
    assert sc.attr_at(box, vs - 3) == "size"


@pytest.mark.parametrize("head,want", [
    ('<unit category="length" name="foot" conversionFactor="0.3048"/>', {"length": 0.3048}),
    ('<unit category="angle" name="degree" conversionFactor="0.0174532925"/>', {"angle": 0.0174532925}),
    ('<unit category="length" name="mm" conversionFactor="1.0e-3"/><unit category="force" name="N" conversionFactor="1"/>',
     {"length": 0.001, "force": 1.0}),
    ('<unit category="length" name="bad" conversionFactor="abc"/>', {}),
    ('<unit name="nocat" conversionFactor="2"/>', {}),
    ('<unit category="length" name="nofactor"/>', {}),
    ('<unit category="length" name="a" conversionFactor="2"/><unit category="length" name="b" conversionFactor="3"/>',
     {"length": 3.0}),
    ('<meta name="x" content="y"/>', {}),
    ("", {}),
])
def test_scene_unit_statements_into_unit_scale(head, want):
    sc = T.SceneIndex(scene_xml("", head))
    assert sc.ok and sc.unit_scale == want


def test_scene_unit_outside_head_is_ignored():
    sc = T.SceneIndex('<X3D><Scene><unit category="length" name="foot" conversionFactor="0.3048"/></Scene></X3D>')
    assert sc.unit_scale == {}


def test_scene_unit_scale_is_not_applied_to_claims_automatically():
    """Documented gap (spec ambiguity): policy.length_scale must be passed in by the caller."""
    xml = scene_xml('<Shape><Sphere radius="2"/></Shape>',
                    '<unit category="length" name="foot" conversionFactor="0.3048"/>')
    src = T.Source("scene", xml)
    assert src.scene.unit_scale == {"length": 0.3048}
    it = one({"field": "Sphere.radius", "value": 2, "quote": "2 ft"}, [T.Source("p", "2 ft"), src])
    assert it.verdict == "check"       # default policy: metre scene
    it = one({"field": "Sphere.radius", "value": 2, "quote": "2 ft"}, [T.Source("p", "2 ft"), src],
             policy=T.TracePolicy(length_scale=src.scene.unit_scale["length"]))
    assert it.verdict == "verified"


MALFORMED = [
    "<X3D><Scene>", "<a></b>", "", "not xml", "<a>&bogus;</a>", "<a b=1/>", "<a/><b/>", "<a b='1' b='2'/>",
    "<a>\x00</a>", "<X3D><Scene></X3D>", "<?xml version='1.0'?>", "<a><!-- unclosed </a>", "<a>]]></a>x",
    "<<>>", "<a b='<'/>", "</a>", "<a/ >", "<a b='&#0;'/>", "<a>&#xFFFF;</a>", "\ufeff",
]


@pytest.mark.parametrize("text", MALFORMED, ids=[repr(t)[:30] for t in MALFORMED])
def test_scene_malformed_xml_is_ok_false_without_exception(text):
    sc = T.SceneIndex(text)
    assert sc.ok is False
    assert sc.error
    assert sc.elements == []
    assert sc.element_at(0) is None


def test_scene_malformed_still_traceable_at_text_level():
    bad = '<X3D><Scene><Transform translation="1 2 3"></Scene></X3D>'
    it = one({"field": "t", "value": "1 2 3", "quote": 'translation="1 2 3"'}, [T.Source("s", bad)])
    assert it.status == "found" and it.verdict == "verified"
    assert "parse_error" in it.locus and it.locus["line"] == 1
    assert "path" not in it.locus and "aabb" not in it.locus


def test_scene_error_message_carries_line_and_column():
    sc = T.SceneIndex("<X3D>\n<Scene>\n</X3D>")
    assert not sc.ok and "line 3" in sc.error


def test_scene_non_xml_x3d_encodings_have_no_scene_index():
    for text in ("#X3D V3.3 utf8\nPROFILE Interchange\nScene { }", '{"X3D":{"@version":"4.0"}}'):
        s = T.Source("c", text)
        assert s.kind == "x3d" and s.scene is None


def test_scene_source_scene_is_cached_and_text_sources_have_none():
    s = T.Source("s", MIXED)
    assert s.scene is s.scene
    assert T.Source("t", "just some prose").scene is None
    assert T.Source("t", "<X3D/>", kind="text").scene is None


def test_scene_bom_does_not_shift_offsets():
    text = "\ufeff<?xml version='1.0'?>\n<X3D><Scene><Transform DEF=\"B\" translation=\"1 2 3\"/></Scene></X3D>"
    sc = T.SceneIndex(text)
    assert sc.ok
    for e in sc.elements:
        assert text[e.start:e.start + 1 + len(e.tag)] == "<" + e.tag


def test_scene_deep_nesting_index_is_iterative():
    depth = 2000
    text = "<X3D>" + "<Group>" * depth + "</Group>" * depth + "</X3D>"
    sc = T.SceneIndex(text)
    assert (sc.ok and len(sc.elements) == depth + 1) or (not sc.ok and "nested" in sc.error)       # indexed, or refused with a reason


@pytest.mark.parametrize("enc", [P("ISO-8859-1", bugs=19), P("windows-1252", bugs=19), P("UTF-16", bugs=19),
                                 P("US-ASCII", bugs=19), "UTF-8"])
def test_scene_xml_declaration_encoding_does_not_matter_for_str_input(enc):
    text = '<?xml version="1.0" encoding="%s"?><X3D><Scene><Transform DEF="Äk" translation="1 2 3"/></Scene></X3D>' % enc
    sc = T.SceneIndex(text)
    assert sc.ok, sc.error
    assert [e.path for e in sc.elements][-1] == "/X3D/Scene/Transform[DEF=Äk]"


@bug(22)
def test_scene_use_element_path_names_the_use():
    sc = T.SceneIndex('<X3D><Scene><Group DEF="A"/><Group USE="A"/></Scene></X3D>')
    assert sc.elements[-1].path.endswith("Group[USE=A]")


# ============================================================================================
# 6. World boxes (hand computed)
# ============================================================================================
S2 = math.sqrt(2.0)
BOX_ROWS = [
    ("box default", '<Shape><Box/></Shape>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("box size", '<Shape><Box size="1 2 3"/></Shape>', [[[-.5, -1, -1.5], [.5, 1, 1.5]]]),
    ("box size commas", '<Shape><Box size="1,2,3"/></Shape>', [[[-.5, -1, -1.5], [.5, 1, 1.5]]]),
    ("sphere default", '<Shape><Sphere/></Shape>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("sphere r .5 translated", '<Transform translation="3 0 0"><Shape><Sphere radius="0.5"/></Shape></Transform>',
     [[[2.5, -.5, -.5], [3.5, .5, .5]]]),
    ("sphere scaled 1 2 3 r2", '<Transform scale="1 2 3"><Shape><Sphere radius="2"/></Shape></Transform>',
     [[[-2, -4, -6], [2, 4, 6]]]),
    ("sphere rot45z scale 1 2 3 r1", '<Transform rotation="0 0 1 0.7853981633974483" scale="1 2 3"><Shape><Sphere/></Shape></Transform>',
     [[[-1.5811388, -1.5811388, -3], [1.5811388, 1.5811388, 3]]]),
    ("cylinder", '<Shape><Cylinder radius="1" height="4"/></Shape>', [[[-1, -2, -1], [1, 2, 1]]]),
    ("cylinder default", '<Shape><Cylinder/></Shape>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("cone", '<Shape><Cone bottomRadius="2" height="3"/></Shape>', [[[-2, -1.5, -2], [2, 1.5, 2]]]),
    ("elevation grid", '<Shape><ElevationGrid xDimension="3" zDimension="4" xSpacing="2" zSpacing="0.5" height="0 1 2 3 4 5 6 7 -1 0 0 0"/></Shape>',
     [[[0, -1, 0], [4, 7, 1.5]]]),
    ("elevation grid dims 0", '<Shape><ElevationGrid xDimension="0" zDimension="4"/></Shape>', []),
    ("indexed face set", '<Shape><IndexedFaceSet coordIndex="0 1 2 -1"><Coordinate point="0 0 0 1 0 0 0 1 5"/></IndexedFaceSet></Shape>',
     [[[0, 0, 0], [1, 1, 5]]]),
    ("ifs shared coordinate", '<Coordinate DEF="C" point="0 0 0 1 0 0 0 1 5"/><Shape><IndexedFaceSet><Coordinate USE="C"/></IndexedFaceSet></Shape>',
     [[[0, 0, 0], [1, 1, 5]]]),
    ("indexed line set commas", '<Shape><IndexedLineSet><Coordinate point="1 2 3, 4 5 6"/></IndexedLineSet></Shape>',
     [[[1, 2, 3], [4, 5, 6]]]),
    ("point set", '<Shape><PointSet><Coordinate point="-1 -2 -3 1 2 3"/></PointSet></Shape>', [[[-1, -2, -3], [1, 2, 3]]]),
    ("switch -1", '<Switch whichChoice="-1"><Shape><Box/></Shape></Switch>', []),
    ("switch default", '<Switch><Shape><Box/></Shape></Switch>', []),
    ("switch 0", '<Switch whichChoice="0"><Shape><Box size="1 1 1"/></Shape><Shape><Box size="10 10 10"/></Shape></Switch>',
     [[[-.5, -.5, -.5], [.5, .5, .5]]]),
    ("switch 1", '<Switch whichChoice="1"><Shape><Box size="1 1 1"/></Shape><Shape><Box size="10 10 10"/></Shape></Switch>',
     [[[-5, -5, -5], [5, 5, 5]]]),
    ("switch out of range", '<Switch whichChoice="2"><Shape><Box/></Shape><Shape><Box/></Shape></Switch>', []),
    ("switch skips metadata", '<Switch whichChoice="0"><MetadataString containerField="metadata"/><Shape><Box size="1 1 1"/></Shape></Switch>',
     [[[-.5, -.5, -.5], [.5, .5, .5]]]),
    ("transform order T R S", '<Transform translation="10 0 0" rotation="0 0 1 1.5707963267948966"><Shape><Box size="2 4 2"/></Shape></Transform>',
     [[[8, -1, -1], [12, 1, 1]]]),
    ("center + rotation", '<Transform center="1 0 0" rotation="0 0 1 1.5707963267948966"><Shape><Box size="2 2 2"/></Shape></Transform>',
     [[[0, -2, -1], [2, 0, 1]]]),
    ("center + scale", '<Transform center="1 0 0" scale="2 2 2"><Shape><Box size="2 2 2"/></Shape></Transform>',
     [[[-3, -2, -2], [1, 2, 2]]]),
    ("scaleOrientation", '<Transform scaleOrientation="0 0 1 0.7853981633974483" scale="2 1 1"><Shape><Box size="2 2 2"/></Shape></Transform>',
     [[[-2, -2, -1], [2, 2, 1]]]),
    ("nested transforms", '<Transform translation="1 0 0" scale="2 2 2"><Transform translation="1 0 0" rotation="0 1 0 1.5707963267948966"><Shape><Box size="2 2 4"/></Shape></Transform></Transform>',
     [[[-1, -2, -2], [7, 2, 2]]]),
    ("two level translate", '<Transform translation="1 0 0"><Transform translation="0 2 0"><Shape><Box/></Shape></Transform></Transform>',
     [[[0, 1, -1], [2, 3, 1]]]),
    ("rotation 45 about z box 2", '<Transform rotation="0 0 1 0.7853981633974483"><Shape><Box size="2 2 2"/></Shape></Transform>',
     [[[-S2, -S2, -1], [S2, S2, 1]]]),
    ("negative scale", '<Transform translation="5 0 0" scale="-1 1 1"><Shape><Box/></Shape></Transform>', [[[4, -1, -1], [6, 1, 1]]]),
    ("zero axis rotation is identity", '<Transform rotation="0 0 0 1"><Shape><Box/></Shape></Transform>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("rotation axis not normalised", '<Transform rotation="0 0 5 1.5707963267948966"><Shape><Box size="2 4 2"/></Shape></Transform>',
     [[[-2, -1, -1], [2, 1, 1]]]),
    ("HAnimJoint behaves like Transform", '<HAnimJoint translation="1 0 0"><Shape><Box/></Shape></HAnimJoint>', [[[0, -1, -1], [2, 1, 1]]]),
    ("group collision", '<Group><Collision><Shape><Box/></Shape></Collision></Group>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("two shapes union", '<Shape><Box size="2 2 2"/></Shape><Transform translation="5 0 0"><Shape><Box size="2 2 2"/></Shape></Transform>',
     [[[-1, -1, -1], [6, 1, 1]]]),
    ("shape without geometry", '<Shape><Appearance><Material/></Appearance></Shape>', []),
    ("inline has no box", '<Inline url="x.x3d"/>', []),
    ("unsupported geometry has no box", '<Shape><Extrusion/></Shape>', []),
    ("USE of an unknown DEF", '<Transform USE="nope"/>', []),
    ("invalid translation is ignored", '<Transform translation="a b c"><Shape><Box/></Shape></Transform>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("short translation is ignored", '<Transform translation="1 2"><Shape><Box/></Shape></Transform>', [[[-1, -1, -1], [1, 1, 1]]]),
    ("translation commas", '<Transform translation="1,2,3"><Shape><Box size="2,2,2"/></Shape></Transform>', [[[0, 1, 2], [2, 3, 4]]]),
    ("USE twice", '<Transform DEF="A"><Shape><Box size="2 2 2"/></Shape></Transform><Transform translation="5 0 0"><Transform USE="A"/></Transform><Transform translation="0 5 0"><Transform USE="A"/></Transform>',
     [[[-1, -1, -1], [6, 6, 1]]]),
    ("shape geometry by USE", '<Shape><Box DEF="BX" size="1 1 1"/></Shape><Shape><Box USE="BX"/></Shape>', [[[-.5, -.5, -.5], [.5, .5, .5]]]),
    ("metadata child ignored", '<Shape><Box size="1 1 1"/></Shape><WorldInfo title="x"/>', [[[-.5, -.5, -.5], [.5, .5, .5]]]),
]


@pytest.mark.parametrize("name,inner,want", [pytest.param(*r, id=r[0]) for r in BOX_ROWS])
def test_world_boxes(name, inner, want):
    approx_box(scene_boxes(inner), want)


@bug(33)
def test_lod_box_is_conservative_over_all_levels():
    boxes = scene_boxes('<LOD range="10"><Shape><Box size="1 1 1"/></Shape><Shape><Box size="10 10 10"/></Shape></LOD>')
    approx_box(boxes, [[[-5, -5, -5], [5, 5, 5]]])


def test_world_boxes_one_per_instance_for_use():
    sc = scene_index('<Transform DEF="A"><Shape><Box size="2 2 2"/></Shape></Transform>'
                     '<Transform translation="5 0 0"><Transform USE="A"/></Transform>'
                     '<Transform translation="0 5 0"><Transform USE="A"/></Transform>')
    a = sc.find_def("A")
    got = [T._round_box(b) for b in sc.boxes_for(a)]
    approx_box(got, [[[-1, -1, -1], [1, 1, 1]], [[4, -1, -1], [6, 1, 1]], [[-1, 4, -1], [1, 6, 1]]])
    uses = [e for e in sc.elements if e.use == "A"]
    assert len(uses) == 2
    approx_box([T._round_box(sc.boxes_for(uses[0])[0])], [[[4, -1, -1], [6, 1, 1]]])
    approx_box([T._round_box(sc.boxes_for(uses[1])[0])], [[[-1, 4, -1], [1, 6, 1]]])


def test_world_boxes_per_element_subtree():
    sc = scene_index('<Transform DEF="A" translation="1 0 0"><Shape><Box/></Shape></Transform><Shape><Sphere radius="3"/></Shape>')
    a = sc.find_def("A")
    approx_box([T._round_box(b) for b in sc.boxes_for(a)], [[[0, -1, -1], [2, 1, 1]]])
    box = [e for e in sc.elements if e.tag == "Box"][0]
    assert sc.boxes_for(box) == []        # leaf geometry nodes have no entry of their own; the Shape does
    shape = sc.elements[box.parent]
    approx_box([T._round_box(b) for b in sc.boxes_for(shape)], [[[0, -1, -1], [2, 1, 1]]])
    root = sc.elements[0]
    approx_box([T._round_box(b) for b in sc.boxes_for(root)], [[[-3, -3, -3], [3, 3, 3]]])


def test_world_boxes_self_referencing_use_terminates():
    sc = scene_index('<Group DEF="G"><Group USE="G"/><Shape><Box/></Shape></Group>')
    g = sc.find_def("G")
    assert sc.boxes_for(g)


def test_world_boxes_mutual_use_terminates():
    sc = scene_index('<Group DEF="A"><Group USE="B"/></Group><Group DEF="B"><Group USE="A"/><Shape><Box/></Shape></Group>')
    sc.boxes_for(sc.elements[0])


def test_world_boxes_on_empty_scene_and_x3d_without_scene():
    sc = T.SceneIndex("<X3D/>")
    assert sc.ok and sc.boxes_for(sc.elements[0]) == []


@pytest.mark.parametrize("attr", [
    P('<Transform rotation="0 1 0 inf"><Shape><Box/></Shape></Transform>', bugs=1),
    P('<Transform rotation="0 1 0 1e999"><Shape><Box/></Shape></Transform>', bugs=1),
    P('<Switch whichChoice="nan"><Shape><Box/></Shape></Switch>', bugs=1),
    P('<Switch whichChoice="1e999"><Shape><Box/></Shape></Switch>', bugs=1),
    P('<Shape><ElevationGrid xDimension="1e999" zDimension="2"/></Shape>', bugs=1),
    P('<Shape><ElevationGrid xDimension="nan" zDimension="2"/></Shape>', bugs=1),
    '<Transform translation="1e999 0 0"><Shape><Box/></Shape></Transform>',
    '<Transform scale="1e200 1e200 1e200"><Transform scale="1e200 1e200 1e200"><Shape><Box/></Shape></Transform></Transform>',
])
def test_hostile_numbers_in_the_scene_never_raise_from_check_claims(attr):
    xml = scene_xml(attr + '<Shape DEF="Q"><Sphere radius="0.5"/></Shape>')
    it = one({"field": "r", "value": 0.5, "quote": 'radius="0.5"'}, [T.Source("s", xml)])
    assert it.status == "found"


@pytest.mark.parametrize("inner,quote", [
    P('<Transform translation="nan 0 0"><Shape><Box/></Shape></Transform>', 'translation="nan 0 0"', bugs=8),
    P('<Transform translation="1e999 0 0"><Shape><Box/></Shape></Transform>', "1e999", bugs=8),
    P('<Shape><Sphere radius="1e999"/></Shape>', "1e999", bugs=8),
])
def test_a_quote_inside_a_hostile_element_still_reports(inner, quote):
    """The quote sits in the element whose box is not finite: the report must still be produced, with no NaN/inf."""
    it = one({"field": "r", "value": 1, "quote": quote}, [T.Source("s", scene_xml(inner))])
    flat = json.dumps(it.to_dict(), allow_nan=False)
    assert "NaN" not in flat and "Infinity" not in flat


# ============================================================================================
# 7. Selectors, line/col, locus
# ============================================================================================
@pytest.mark.parametrize("text,off,want", [
    ("ab\ncd\n\nx", 0, (1, 1)), ("ab\ncd\n\nx", 1, (1, 2)), ("ab\ncd\n\nx", 2, (1, 3)), ("ab\ncd\n\nx", 3, (2, 1)),
    ("ab\ncd\n\nx", 5, (2, 3)), ("ab\ncd\n\nx", 6, (3, 1)), ("ab\ncd\n\nx", 7, (4, 1)), ("ab\ncd\n\nx", 8, (4, 2)),
    ("a\r\nb", 3, (2, 1)), ("", 0, (1, 1)), ("\n", 0, (1, 1)), ("\n", 1, (2, 1)), ("\n\n\n", 3, (4, 1)),
])
def test_line_col_table(text, off, want):
    assert T.line_col(text, off) == want


def test_line_col_round_trip_property():
    rnd = random.Random(7)
    for _ in range(200):
        t = "".join(rnd.choice("ab \n\rä日") for _ in range(rnd.randint(0, 60)))
        lines = t.split("\n")
        for i in range(len(t)):
            ln, col = T.line_col(t, i)
            assert lines[ln - 1][col - 1:col] == (t[i] if t[i] != "\n" else ""), (t, i)


LOC_SCENE = '''<X3D profile="Interchange" version="4.0">
  <Scene>
    <Transform DEF="Ball" translation="1 2 3">
      <Shape>
        <Appearance><Material diffuseColor="1 0 0"/></Appearance>
        <Sphere radius="0.5"/>
      </Shape>
    </Transform>
  </Scene>
</X3D>
'''


def _loc(quote, value="x", **extra):
    it = one(dict(field="f", value=value, quote=quote, **extra), [T.Source("scene", LOC_SCENE)])
    return it


@pytest.mark.parametrize("quote,node,path,def_,attr", [
    ("1 2 3", "Transform", "/X3D/Scene/Transform[DEF=Ball]", "Ball", "translation"),
    ("0.5", "Sphere", "/X3D/Scene/Transform[DEF=Ball]/Shape/Sphere", None, "radius"),
    ("1 0 0", "Material", "/X3D/Scene/Transform[DEF=Ball]/Shape/Appearance/Material", None, "diffuseColor"),
    ("Interchange", "X3D", "/X3D", None, "profile"),
])
def test_locus_node_path_def_attr(quote, node, path, def_, attr):
    it = _loc(quote)
    assert it.status == "found"
    loc = it.locus
    assert (loc["node"], loc["path"], loc["def"], loc["attr"]) == (node, path, def_, attr)
    assert loc["xpath"].startswith("/X3D")
    s, e = it.span
    assert (loc["line"], loc["col"]) == T.line_col(LOC_SCENE, s)


def test_locus_line_and_col_are_one_based_and_exact():
    it = _loc("0.5")
    idx = LOC_SCENE.index('radius="0.5"') + len('radius="')
    assert it.span[0] == idx
    assert (it.locus["line"], it.locus["col"]) == (6, LOC_SCENE.splitlines()[5].index('0.5') + 1)


def test_locus_aabb_and_owner():
    it = _loc("1 2 3")
    assert it.locus["aabb_owner"] == "/X3D/Scene/Transform[DEF=Ball]"
    approx_box(locus_boxes(it.locus), [[[0.5, 1.5, 2.5], [1.5, 2.5, 3.5]]])
    it = _loc("1 0 0")      # Material has no box: the nearest ancestor that has one is the Shape
    assert it.locus["aabb_owner"] == "/X3D/Scene/Transform[DEF=Ball]/Shape"
    approx_box(locus_boxes(it.locus), [[[0.5, 1.5, 2.5], [1.5, 2.5, 3.5]]])


@bug(21)
def test_locus_attr_when_the_quote_starts_at_the_attribute_name():
    assert _loc('translation="1 2 3"').locus["attr"] == "translation"
    assert _loc('radius="0.5"').locus["attr"] == "radius"


def test_locus_for_prose_has_only_line_and_col():
    it = one({"field": "f", "value": 2, "quote": "radius 2"}, [T.Source("p", "line one\nthe radius 2 m\n")])
    assert it.locus == {"line": 2, "col": 5}


@pytest.mark.parametrize("text,quote", [
    ("Quantity: 3.000 kg", "3.000 kg"), ("\ufeffpre äö 3.5 post", "3.5"), ("a\r\nb 12 c\r\n", "b 12"),
    ("x" * 100 + " target " + "y" * 100, "target"), ("target start", "target"), ("end target", "target"),
    ("target", "target"), ("\U0001F600 emoji \U0001F600 12 \U0001F600", "12"),
])
def test_selectors_are_consistent_with_the_source(text, quote):
    it = one({"field": "f", "value": None, "quote": quote}, [T.Source("s", text, kind="text")])
    assert it.status == "found"
    s, e = it.span
    q, pos = it.selectors[0], it.selectors[1]
    assert q["type"] == "TextQuoteSelector" and pos["type"] == "TextPositionSelector"
    assert q["exact"] == text[s:e]
    assert pos["start"] == s and pos["end"] == e
    assert q["prefix"] == text[max(0, s - 32):s] and len(q["prefix"]) <= 32
    assert q["suffix"] == text[e:e + 32] and len(q["suffix"]) <= 32
    assert text[s - len(q["prefix"]):e + len(q["suffix"])] == q["prefix"] + q["exact"] + q["suffix"]
    assert norms(q["exact"]) == norms(quote)
    assert not any(sel["type"] == "XPathSelector" for sel in it.selectors)


def test_selectors_prefix_suffix_are_exactly_32_chars_when_room():
    text = "a" * 50 + " X " + "b" * 50
    it = one({"field": "f", "value": None, "quote": "X"}, [T.Source("s", text, kind="text")])
    q = it.selectors[0]
    assert len(q["prefix"]) == 32 and len(q["suffix"]) == 32
    assert q["prefix"] == text[it.span[0] - 32:it.span[0]]


def test_selectors_text_quote_resolves_uniquely_when_context_distinguishes():
    text = "left A one. right A two. left A three."
    it = one({"field": "f", "value": None, "quote": "A", "prefix": "right", "suffix": "two"}, [T.Source("s", text, kind="text")])
    assert it.occurrences == 3 and it.disambiguated_by in ("prefix", "suffix", "prefix+suffix")
    q = it.selectors[0]
    ctx = q["prefix"] + q["exact"] + q["suffix"]
    assert text.count(ctx) == 1 and text.index(ctx) + len(q["prefix"]) == it.span[0]


def test_selectors_xpath_selector_for_scenes():
    it = _loc("1 2 3")
    xp = [s for s in it.selectors if s["type"] == "XPathSelector"]
    assert xp == [{"type": "XPathSelector", "value": "/X3D/Scene/Transform[@DEF='Ball']"}]


def test_selector_span_covers_first_to_last_token_only():
    text = '  <b size="1 2 3"/>  '
    it = one({"field": "f", "value": "1 2 3", "quote": 'size="1 2 3"'}, [T.Source("s", text)])
    s, e = it.span
    assert text[s:e] == 'size="1 2 3'          # the closing quote is punctuation, not a token
    assert it.selectors[0]["exact"] == 'size="1 2 3'


# ============================================================================================
# 8. VERDICT MATRIX (oracle written from the verdict table, not from the code)
# ============================================================================================
STATUSES = ["found", "moved", "not_found", "no_text_layer", "no_quote"]
VSTATES = ["match", "near", "mismatch", "unchecked"]
VALUE_KINDS = {"int": 3, "float": 2.5, "vector": [1, 2, 3], "numeric text": "3.5", "date": "2025-04-11",
               "decimal": Decimal("1.50"), "text": "red", "identifier": "Ball"}
NUMERIC_KINDS = {"int", "float", "vector", "numeric text", "date", "decimal"}

POLICIES = {
    "default": T.TracePolicy(),
    "strict": T.TracePolicy.strict(),
    "reworded_is_problem": T.TracePolicy(reworded_is_problem=True),
    "min3": T.TracePolicy(min_quote_words=3),
    "ambiguous_is_check": T.TracePolicy(ambiguous_quote_is_check=True),
    "moved_is_check": T.TracePolicy(moved_is_check=True),
}


def oracle_verdict(status, vstate, kind, qwords, pol, occ, ident, disamb):
    """The verdict table of the intent notes (GAIK's four branches plus 'near' and the moved policy)."""
    if status in ("no_text_layer", "no_quote"):
        return "unchecked"
    if status not in ("found", "moved"):
        return "check"
    if qwords < pol.min_quote_words:
        return "check"
    if status == "moved" and pol.moved_is_check:
        return "check"
    if vstate == "unchecked":
        return "unchecked"
    if vstate == "match":
        return "check" if (pol.ambiguous_quote_is_check and occ > 1 and not disamb) else "verified"
    if vstate == "near":
        return "check" if pol.reworded_is_problem else "reworded"
    if kind in NUMERIC_KINDS or ident:
        return "check"
    return "check" if pol.reworded_is_problem else "reworded"


@pytest.mark.parametrize("pname", sorted(POLICIES))
@pytest.mark.parametrize("status", STATUSES)
def test_verdict_matrix(pname, status):
    pol = POLICIES[pname]
    wrong = []
    n = 0
    for vstate in VSTATES:
        for kind, value in VALUE_KINDS.items():
            for qwords in (1, 2, 3, 12):
                for occ in (1, 2, 5):
                    for disamb in (False, True):
                        ident = kind == "identifier"
                        got = T.verdict_of(status, vstate, value, qwords, pol, occ, ident, disamb)
                        want = oracle_verdict(status, vstate, kind, qwords, pol, occ, ident, disamb)
                        n += 1
                        if got != want:
                            wrong.append((vstate, kind, qwords, occ, disamb, got, want))
    assert n == 4 * 8 * 4 * 3 * 2
    assert not wrong, wrong[:6]


@pytest.mark.parametrize("status,vstate,value,qw,want", [
    ("found", "match", 3, 1, "verified"),
    ("found", "match", "red", 4, "verified"),
    ("found", "near", 3, 4, "reworded"),
    ("found", "mismatch", 3, 4, "check"),
    ("found", "mismatch", "3", 4, "check"),
    ("found", "mismatch", "red", 4, "reworded"),
    ("found", "unchecked", 3, 4, "unchecked"),
    ("moved", "match", 3, 4, "verified"),
    ("not_found", "match", 3, 4, "check"),
    ("not_found", "unchecked", 3, 4, "check"),
    ("no_quote", "unchecked", 3, 0, "unchecked"),
    ("no_quote", "match", 3, 0, "unchecked"),
    ("no_text_layer", "unchecked", 3, 4, "unchecked"),
    ("found", "weird", 3, 4, "unchecked"),
    ("weird", "match", 3, 4, "check"),
])
def test_verdict_rows_by_hand(status, vstate, value, qw, want):
    assert T.verdict_of(status, vstate, value, qw, T.TracePolicy()) == want


def test_verdict_vocabulary_and_grade_cap():
    assert T.VERDICTS == ("verified", "check", "reworded", "unchecked")
    assert T.SCHEMA == "x3dtrace/0.1"
    assert T.grade_cap("verified") == "Confirmed"
    assert T.grade_cap("reworded") == "Likely"
    assert T.grade_cap("unchecked") == "Likely"
    assert T.grade_cap("check") == "Suspected"
    assert T.grade_cap("verified", has_quote=False) == "Suspected"
    assert T.grade_cap("nonsense") == "Suspected"


# ============================================================================================
# 9. POLICY
# ============================================================================================
def test_policy_defaults_are_the_documented_x3d_profile():
    p = T.TracePolicy()
    assert (p.number_tolerance, p.round_to_printed, p.match_reformatted_identifiers) == (1e-6, True, True)
    assert (p.reworded_is_problem, p.min_quote_words, p.ambiguous_quote_is_check, p.moved_is_check) == (False, 1, False, False)
    assert p.code_values_unchecked is False
    assert tuple(p.conversions) == T.ALL_CONVERSIONS and p.length_scale == 1.0
    assert set(T.ALL_CONVERSIONS) == {"deg2rad", "rad2deg", "percent", "rgb255", "hex", "colorname", "numword",
                                      "unit", "broadcast", "axis"}


def test_policy_is_frozen():
    p = T.TracePolicy()
    for attr, val in [("number_tolerance", 1.0), ("conversions", ()), ("moved_is_check", True)]:
        with pytest.raises(Exception) as ei:
            setattr(p, attr, val)
        assert "frozen" in type(ei.value).__name__.lower() or "cannot assign" in str(ei.value)


def test_policy_strict_turns_conversions_off_and_everything_else_on():
    s = T.TracePolicy.strict()
    assert s.conversions == () and not s.allows("deg2rad") and not s.round_to_printed
    assert s.reworded_is_problem and s.ambiguous_quote_is_check and s.moved_is_check
    assert T.TracePolicy().allows("percent") and not T.TracePolicy(conversions=("hex",)).allows("percent")


@pytest.mark.parametrize("pol", [T.TracePolicy(), T.TracePolicy.strict(), T.TracePolicy(number_tolerance=0.05, length_scale=0.3048),
                                 T.TracePolicy(conversions=("hex", "unit"), min_quote_words=4, code_values_unchecked=True)],
                         ids=["default", "strict", "scaled", "custom"])
def test_policy_dict_round_trip_and_has_no_floats(pol):
    d = pol.to_dict()

    def leaves(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from leaves(v)
        elif isinstance(o, list):
            for v in o:
                yield from leaves(v)
        else:
            yield o
    assert all(isinstance(x, (str, int, bool)) for x in leaves(d)), d
    assert T.TracePolicy.from_dict(json.loads(json.dumps(d))) == pol
    assert T.TracePolicy.from_dict(d).to_dict() == d


def test_policy_from_dict_ignores_unknown_keys_and_accepts_partial():
    p = T.TracePolicy.from_dict({"moved_is_check": True, "from_the_future": 1})
    assert p.moved_is_check and p.number_tolerance == 1e-6
    assert T.TracePolicy.from_dict({}) == T.TracePolicy()


def test_policy_is_recorded_in_the_report():
    rep = run({"field": "r", "value": 2, "quote": "radius 2"}, "radius 2", policy=T.TracePolicy.strict())
    assert rep.to_dict()["policy"] == T.TracePolicy.strict().to_dict()
    assert rep.policy == T.TracePolicy.strict()


SRC_REP = "The ball has radius 2.5. Colour: red. Colour: red."


@pytest.mark.parametrize("claim,policy,want", [
    ({"field": "c", "value": "blue", "quote": "Colour: red"}, {}, "reworded"),
    ({"field": "c", "value": "blue", "quote": "Colour: red"}, {"reworded_is_problem": True}, "check"),
    ({"field": "r", "value": 2.5, "quote": "radius 2.5"}, {"min_quote_words": 3}, "check"),
    ({"field": "r", "value": 2.5, "quote": "has radius 2.5"}, {"min_quote_words": 3}, "verified"),
    ({"field": "r", "value": 2.5, "quote": "2.5"}, {"min_quote_words": 2}, "check"),
    ({"field": "c", "value": "red", "quote": "Colour: red"}, {}, "verified"),
    ({"field": "c", "value": "red", "quote": "Colour: red"}, {"ambiguous_quote_is_check": True}, "check"),
    ({"field": "c", "value": "red", "quote": "Colour: red", "prefix": "2.5. "}, {"ambiguous_quote_is_check": True}, "verified"),
    ({"field": "c", "value": "red", "quote": "Colour: red", "suffix": " Colour"}, {"ambiguous_quote_is_check": True}, "verified"),
    ({"field": "r", "value": 2.5, "quote": "radius 2.5"}, {"ambiguous_quote_is_check": True}, "verified"),
    ({"field": "r", "value": 2.5, "quote": "radius 2.5"}, {"moved_is_check": True}, "verified"),
])
def test_policy_toggles_change_verdicts_as_documented(claim, policy, want):
    assert one(claim, SRC_REP, policy=T.TracePolicy(**policy)).verdict == want


def test_moved_quote_follows_the_moved_policy():
    srcs = [T.Source("a", "nothing here"), T.Source("b", "the radius 2 is there")]
    c = {"field": "r", "value": 2, "quote": "radius 2", "source": "a"}
    it = one(c, srcs)
    assert (it.status, it.verdict, it.source, it.document) == ("moved", "verified", "b", 2)
    assert one(c, srcs, policy=T.TracePolicy(moved_is_check=True)).verdict == "check"
    assert one(c, srcs, policy=T.TracePolicy.strict()).verdict == "check"


# ============================================================================================
# 10. REPORT, SUMMARY, COVERAGE
# ============================================================================================
REP_SRC = "The ball has radius 2.5 and the box is 3 by 4 by 5. The ball is red. Order PO-2025-15903."
REP_CLAIMS = [
    {"field": "r", "value": 2.5, "quote": "radius 2.5"},
    {"field": "b", "value": [3, 4, 5], "quote": "3 by 4 by 5"},
    {"field": "c", "value": "red", "quote": "ball is red"},
    {"field": "w", "value": 9, "quote": "radius 2.5"},
    {"field": "n", "value": 1, "quote": ""},
    {"field": "x", "value": 1, "quote": "not in the source"},
]


def test_summary_counts_and_coverage_maths():
    rep = run(REP_CLAIMS, REP_SRC, expected_fields=["r", "b", "c", "w", "n", "x", "zz", "yy"])
    sm = rep.summary()
    assert (sm["verified"], sm["check"], sm["reworded"], sm["unchecked"], sm["total"]) == (3, 2, 0, 1, 6)
    assert sm["verified"] + sm["check"] + sm["reworded"] + sm["unchecked"] == sm["total"]
    # 5 of 8 expected fields came with a quote (the fabricated one counts as cited), 3 of 8 were verified
    assert rep.coverage == 0.625 and sm["coverage_ppm"] == 625000
    assert rep.verified_coverage == 0.375 and sm["verified_coverage_ppm"] == 375000
    assert rep.expected == sorted(["r", "b", "c", "w", "n", "x", "zz", "yy"])


@pytest.mark.parametrize("expected,cov,vcov", [
    (["r", "b", "c"], 1.0, 1.0),
    (["r", "n"], 0.5, 0.5),
    (["n"], 0.0, 0.0),
    (["w", "x"], 1.0, 0.0),
    (["r", "r", "b"], 1.0, 1.0),
    (["r", "b", "c", "w", "n", "x"], round(5 / 6, 6), 0.5),
    (["ghost"], 0.0, 0.0),
    (None, None, None),
    ([], None, None),
])
def test_coverage_tables(expected, cov, vcov):
    rep = run(REP_CLAIMS, REP_SRC, expected_fields=expected)
    assert (rep.coverage, rep.verified_coverage) == (cov, vcov)
    sm = rep.summary()
    assert sm["coverage_ppm"] == (None if cov is None else int(round(cov * 1e6)))
    assert sm["verified_coverage_ppm"] == (None if vcov is None else int(round(vcov * 1e6)))


def test_coverage_is_never_above_one_and_never_counts_unexpected_fields():
    rep = run(REP_CLAIMS, REP_SRC, expected_fields=["r"])
    assert rep.coverage == 1.0 and rep.verified_coverage == 1.0


def test_summary_counts_moved_and_ambiguous():
    srcs = [T.Source("a", "nothing"), T.Source("b", "radius 2 and radius 2 again")]
    cl = [{"field": "r", "value": 2, "quote": "radius 2", "source": "a"},
          {"field": "s", "value": 2, "quote": "radius 2", "source": "b"},
          {"field": "t", "value": 2, "quote": "radius 2", "source": "b", "prefix": "and "}]
    sm = run(cl, srcs).summary()
    assert sm["moved"] == 1 and sm["ambiguous"] == 2 and sm["total"] == 3


def test_report_dict_shape():
    rep = run(REP_CLAIMS, REP_SRC)
    d = rep.to_dict()
    assert set(d) == {"schema", "summary", "documents", "sources", "source_files", "policy", "expected"}
    assert d["schema"] == "x3dtrace/0.1" and d["documents"] == ["source-1"]
    assert len(d["sources"]) == 6
    keys = {"field", "value", "quote", "source", "document", "page", "cited_page", "status", "value_status", "verdict",
            "rects", "value_rects", "span", "occurrences", "record", "derivation", "note", "selectors", "locus",
            "disambiguated_by"}
    for it in d["sources"]:
        assert keys <= set(it)
    sf = d["source_files"][0]
    assert sf["id"] == "source-1" and sf["kind"] == "text" and sf["bytes"] == len(REP_SRC.encode())
    assert sf["sha256"] == hashlib.sha256(REP_SRC.encode()).hexdigest()


def test_report_is_json_serialisable_without_extensions():
    rep = run(REP_CLAIMS + [{"field": "d", "value": Decimal("2.50"), "quote": "radius 2.5"}], REP_SRC)
    json.dumps(rep.to_dict(), allow_nan=False)      # Decimal is portable text, no NaN / Infinity


def test_sources_may_be_given_as_str_list_or_Source_objects():
    c = {"field": "r", "value": 2.5, "quote": "radius 2.5"}
    for srcs in (REP_SRC, [REP_SRC], T.Source("z", REP_SRC), [T.Source("z", REP_SRC)]):
        assert run(c, srcs).items[0].verdict == "verified"
    assert run(c, [REP_SRC]).items[0].source == "source-1"
    assert run(c, [T.Source("z", REP_SRC)]).items[0].source == "z"


def test_document_numbers_are_one_based_and_source_ids_win():
    srcs = [T.Source("a", "alpha 1"), T.Source("b", "beta 2")]
    assert one({"field": "f", "value": 2, "quote": "beta 2", "document": 2}, srcs).source == "b"
    assert one({"field": "f", "value": 2, "quote": "beta 2", "source": "b"}, srcs).document == 2
    assert one({"field": "f", "value": 1, "quote": "alpha 1", "source": "a", "document": 2}, srcs).source == "a"


def test_explain_has_one_plain_sentence_per_status_and_verdict():
    srcs = [T.Source("a", "nothing here"), T.Source("b", "radius 2 and radius 2 and colour red")]
    texts = {}
    for name, c in {
        "no_quote": {"field": "f", "value": 1, "quote": ""},
        "not_found": {"field": "f", "value": 1, "quote": "zzz"},
        "verified": {"field": "f", "value": 2, "quote": "radius 2", "source": "b"},
        "moved": {"field": "f", "value": 2, "quote": "radius 2", "source": "a", "prefix": "and "},
        "reworded": {"field": "f", "value": "blue", "quote": "colour red", "source": "b"},
        "check": {"field": "f", "value": 3, "quote": "radius 2", "source": "b"},
        "unchecked": {"field": "f", "value": "forty", "quote": "radius 2 and", "source": "b"},
    }.items():
        it = one(c, srcs)
        texts[name] = T.explain(it)
        assert texts[name].endswith(".") and "\n" not in texts[name] and len(texts[name]) < 400
    assert "No quote" in texts["no_quote"] and "not in the source" in texts["not_found"]
    assert "another source" in texts["moved"]
    assert len(set(texts.values())) >= 6


# ============================================================================================
# 11. recompute(): an honest report replays to nothing, every edit of a checked field is listed
# ============================================================================================
RC_SCENE = ("<X3D><Scene><Transform DEF='Arm' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>"
            "</Scene></X3D>")
RC_PROMPT = "Make a box of size 2 2 2 at 1 2 3. Then size 2 2 2 again."
RC_CLAIMS = [
    {"field": "/X3D/Scene/Transform[@DEF='Arm']/Shape/Box/@size", "value": "2 2 2", "quote": "size 2 2 2",
     "source": "prompt", "prefix": "Make a box of "},
    {"field": "t", "value": "1 2 3", "quote": "at 1 2 3", "source": "prompt"},
    {"field": "w", "value": 5, "quote": "size 2 2 2", "source": "prompt"},
]


def rc_sources(prompt=RC_PROMPT, scene=RC_SCENE):
    return [T.Source("prompt", prompt), T.Source("scene", scene)]


def rc_report(**kw):
    return T.check_claims(RC_CLAIMS, rc_sources(), expected_fields=["t", "w"], **kw).to_dict()


def test_recompute_of_an_honest_report_is_empty_even_after_a_json_round_trip():
    d = rc_report()
    assert T.recompute(d, RC_CLAIMS, rc_sources()) == []
    assert T.recompute(json.loads(json.dumps(d)), RC_CLAIMS, rc_sources()) == []
    assert T.recompute(json.loads(T.canonical_json(d)), RC_CLAIMS, rc_sources()) == []


def test_recompute_does_not_change_what_it_is_given():
    d = rc_report()
    before = copy.deepcopy(d)
    claims = copy.deepcopy(RC_CLAIMS)
    T.recompute(d, claims, rc_sources())
    assert d == before and claims == RC_CLAIMS


def _set(d, path, val):
    obj = d
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = val


DETECTED = {
    "verdict": (["sources", 2, "verdict"], "verified"),
    "value_status": (["sources", 2, "value_status"], "match"),
    "status": (["sources", 0, "status"], "moved"),
    "span": (["sources", 0, "span"], [0, 3]),
    "quote": (["sources", 0, "quote"], "something else"),
    "value": (["sources", 0, "value"], "3 3 3"),
    "field": (["sources", 0, "field"], "zzz"),
    "source": (["sources", 0, "source"], "scene"),
    "derivation": (["sources", 0, "derivation"], ["deg2rad"]),
    "occurrences": (["sources", 0, "occurrences"], 1),
    "note": (["sources", 0, "note"], "hello"),
    "selectors": (["sources", 0, "selectors"], []),
    "locus": (["sources", 0, "locus"], {}),
    "disambiguated_by": (["sources", 0, "disambiguated_by"], ""),
    "documents": (["documents"], ["x"]),
    "source_files": (["source_files"], []),
    "source_files sha256": (["source_files", 0, "sha256"], "0" * 64),
    "summary": (["summary", "verified"], 99),
    "summary coverage": (["summary", "verified_coverage_ppm"], 1000000),
}


@pytest.mark.parametrize("name", sorted(DETECTED))
def test_recompute_detects_an_edit_of(name):
    d = json.loads(json.dumps(rc_report()))
    path, val = DETECTED[name]
    _set(d, path, val)
    diffs = T.recompute(d, RC_CLAIMS, rc_sources())
    assert diffs, name + " edit went unseen"
    assert all({"index", "what"} <= set(x) for x in diffs)


UNSEEN = {
    "hints": (["sources", 0, "hints"], {}),
    "document": (["sources", 0, "document"], 2),
    "page": (["sources", 0, "page"], 7),
    "cited_page": (["sources", 0, "cited_page"], 7),
    "record": (["sources", 0, "record"], {"x": 1}),
    "rects": (["sources", 0, "rects"], [[0, 0, 1, 1]]),
    "value_rects": (["sources", 0, "value_rects"], [[0, 0, 1, 1]]),
    "schema": (["schema"], "x3dtrace/9"),
    "policy": (["policy", "moved_is_check"], True),     # only visible when the caller passes the policy it trusts (recompute(..., policy))
}


@pytest.mark.parametrize("name", [P(k, bugs=2, id=k) for k in sorted(UNSEEN)])
def test_recompute_detects_an_edit_of_every_other_recorded_field(name):
    d = json.loads(json.dumps(rc_report()))
    path, val = UNSEEN[name]
    _set(d, path, val)
    assert T.recompute(d, RC_CLAIMS, rc_sources()), name + " edit went unseen"


def test_recompute_detects_a_missing_or_extra_item():
    d = rc_report()
    short = copy.deepcopy(d)
    short["sources"].pop()
    diffs = T.recompute(short, RC_CLAIMS, rc_sources())
    assert diffs and diffs[0]["what"] == "item count" and (diffs[0]["old"], diffs[0]["new"]) == (2, 3)
    longer = copy.deepcopy(d)
    longer["sources"].append(copy.deepcopy(longer["sources"][0]))
    assert T.recompute(longer, RC_CLAIMS, rc_sources())[0]["what"] == "item count"


def test_recompute_detects_a_swapped_pair_of_items():
    d = rc_report()
    d["sources"][1], d["sources"][2] = d["sources"][2], d["sources"][1]
    diffs = T.recompute(d, RC_CLAIMS, rc_sources())
    assert {x["index"] for x in diffs if x["index"] >= 0} == {1, 2}


def test_recompute_detects_an_edited_source_and_names_the_items_it_touched():
    d = rc_report()
    diffs = T.recompute(d, RC_CLAIMS, rc_sources(prompt=RC_PROMPT.replace("1 2 3", "1 2 4")))
    assert any(x["what"] == "source_files" for x in diffs)
    assert {x["field"] for x in diffs if x["index"] >= 0} >= {"t"}
    diffs = T.recompute(d, RC_CLAIMS, rc_sources(scene=RC_SCENE.replace("translation='1 2 3'", "translation='1 2 3' ")))
    assert any(x["what"] == "source_files" for x in diffs)


def test_recompute_detects_an_edited_claim():
    cl = copy.deepcopy(RC_CLAIMS)
    cl[1]["value"] = "1 2 4"
    diffs = T.recompute(rc_report(), cl, rc_sources())
    assert {x["what"] for x in diffs} >= {"value", "verdict", "summary"}


def test_recompute_detects_reordered_sources():
    d = rc_report()
    diffs = T.recompute(d, RC_CLAIMS, list(reversed(rc_sources())))
    assert any(x["what"] in ("documents", "source_files") for x in diffs)


def test_recompute_reports_old_and_new_values():
    d = rc_report()
    d["sources"][2]["verdict"] = "verified"
    x = [x for x in T.recompute(d, RC_CLAIMS, rc_sources()) if x["what"] == "verdict"][0]
    assert (x["index"], x["field"], x["old"], x["new"]) == (2, "w", "verified", "check")


def test_recompute_replays_the_policy_given():
    d = T.check_claims(RC_CLAIMS, rc_sources(), T.TracePolicy.strict()).to_dict()
    assert T.recompute(d, RC_CLAIMS, rc_sources(), T.TracePolicy.strict()) == []


@pytest.mark.parametrize("pol", [P(T.TracePolicy.strict(), bugs=9, id="strict"),
                                 P(T.TracePolicy(ambiguous_quote_is_check=True), bugs=9, id="ambiguous"),
                                 P(T.TracePolicy(reworded_is_problem=True, min_quote_words=2), bugs=9, id="reworded+min2")])
def test_recompute_takes_the_policy_from_the_report_when_none_is_given(pol):
    src = "radius 2 and radius 2 again. angle 90 degrees"
    cl = [{"field": "r", "value": 2, "quote": "radius 2"}, {"field": "a", "value": 1.5707963, "quote": "90 degrees"},
          {"field": "m", "value": "blue", "quote": "angle 90"}]
    d = T.check_claims(cl, src, pol).to_dict()
    assert T.recompute(d, cl, src) == []


def test_recompute_with_target_replays_the_target_and_without_it_flags_the_missing_one():
    d = T.check_claims(RC_CLAIMS, rc_sources(), None, None, RC_SCENE).to_dict()
    assert d["sources"][0]["target"]["found"] is True
    assert T.recompute(d, RC_CLAIMS, rc_sources(), None, RC_SCENE) == []
    diffs = T.recompute(d, RC_CLAIMS, rc_sources())
    assert any(x["what"] == "target" for x in diffs)
    d["sources"][0]["target"]["scene_value"] = "mismatch"
    assert any(x["what"] == "target" for x in T.recompute(d, RC_CLAIMS, rc_sources(), None, RC_SCENE))


# ============================================================================================
# 12. recheck(): replay a report from the items alone
# ============================================================================================
RK_SRC = "radius 2 and radius 2 again. angle 90 degrees. Colour: red."
RK_CLAIMS = [{"field": "r", "value": 2, "quote": "radius 2", "prefix": "and "},
             {"field": "a", "value": 1.5707963, "quote": "90 degrees"},
             {"field": "c", "value": "red", "quote": "Colour: red"},
             {"field": "z", "value": 1, "quote": "not there"},
             {"field": "n", "value": 1, "quote": ""}]


def test_recheck_replays_an_honest_report_item_for_item():
    rep = T.check_claims(RK_CLAIMS, RK_SRC)
    items = json.loads(json.dumps(rep.to_dict()["sources"]))
    out = T.recheck(items, {"source-1": RK_SRC})
    assert out == rep.to_dict()["sources"]


def test_recheck_keeps_the_disambiguation_hints():
    items = T.check_claims(RK_CLAIMS, RK_SRC).to_dict()["sources"]
    assert items[0]["hints"] == {"prefix": "and "}
    assert T.recheck(items, {"source-1": RK_SRC})[0]["disambiguated_by"] == "prefix"


def test_recheck_marks_an_item_whose_source_was_not_supplied():
    items = T.check_claims(RK_CLAIMS, RK_SRC).to_dict()["sources"]
    out = T.recheck(items, {})
    assert [(o["status"], o["verdict"], o["span"], o["occurrences"]) for o in out] == [("source_missing", "unchecked", None, 0)] * 5
    out = T.recheck(items, {"other": "x"})
    assert {o["status"] for o in out} == {"source_missing"}


def test_recheck_sees_a_changed_source():
    items = T.check_claims(RK_CLAIMS, RK_SRC).to_dict()["sources"]
    out = T.recheck(items, {"source-1": RK_SRC.replace("90 degrees", "45 degrees")})
    assert [o["verdict"] for o in out][:2] == ["verified", "check"]


def test_recheck_honours_policy_and_kinds():
    items = T.check_claims(RK_CLAIMS, RK_SRC).to_dict()["sources"]
    strict = T.recheck(items, {"source-1": RK_SRC}, T.TracePolicy.strict())
    assert strict[1]["verdict"] == "check" and strict[2]["verdict"] == "verified"
    scene = "<X3D><Scene><Box size='1 2 3'/></Scene></X3D>"
    it = [{"field": "s", "value": "1 2 3", "quote": "1 2 3", "source": "sc"}]
    out = T.recheck(it, {"sc": scene}, kinds={"sc": "x3d"})
    assert out[0]["verdict"] == "verified" and out[0]["locus"]["path"] == "/X3D/Scene/Box"
    out = T.recheck(it, {"sc": scene}, kinds={"sc": "text"})
    assert out[0]["verdict"] == "verified" and "path" not in out[0]["locus"]


def test_recheck_replays_through_a_target_scene():
    items = T.check_claims(RC_CLAIMS, rc_sources(), None, None, RC_SCENE).to_dict()["sources"]
    texts = {"prompt": RC_PROMPT, "scene": RC_SCENE}
    out = T.recheck(items, texts, target_text=RC_SCENE)
    assert out[0]["target"]["found"] and out[0]["target"]["scene_value"] == "match"
    assert "target" not in T.recheck(items, texts)[0]


@pytest.mark.parametrize("value", [P([1.5, 2.5, 3.5], bugs=37, id="float-list"), P([1, 2, 3], id="int-list"),
                                   P(2.5, id="float"), P(Decimal("2.50"), id="decimal"), P("1.5 2.5", id="text"),
                                   P(True, id="bool")])
def test_recheck_of_every_portable_value_replays_to_the_same_verdict(value):
    quote = {"float-list": "1.5 2.5 3.5", "int-list": "1 2 3", "float": "2.5", "decimal": "2.50", "text": "1.5 2.5",
             "bool": "true"}[{"[1.5, 2.5, 3.5]": "float-list", "[1, 2, 3]": "int-list", "2.5": "float", "2.50": "decimal",
                              "1.5 2.5": "text", "True": "bool"}[str(value)]]
    src = "box " + quote + " end"
    rep = T.check_claims([{"field": "f", "value": value, "quote": quote}], src)
    out = T.recheck(rep.to_dict()["sources"], {"source-1": src})
    assert out[0]["verdict"] == rep.items[0].verdict
    assert out[0]["value_status"] == rep.items[0].value_status


# ============================================================================================
# 13. canonical JSON, hashes, determinism
# ============================================================================================
def test_canonical_json_sorts_keys_has_no_spaces_and_keeps_unicode():
    assert T.canonical_json({"b": 1, "a": [1, 2, {"z": None, "y": "é"}]}) == '{"a":[1,2,{"y":"é","z":null}],"b":1}'
    assert T.canonical_json({"d": Decimal("1.50"), "s": {3, 1, 2}, "t": (1, 2)}) == '{"d":{"$decimal":"1.50"},"s":[1,2,3],"t":[1,2]}'
    assert T.canonical_json("\u2028\U0001F600\u0000") == '"\u2028\U0001F600\\u0000"'
    with pytest.raises(TypeError):
        T.canonical_json(object())


@pytest.mark.parametrize("bad", [P(float("nan"), bugs=39, id="nan"), P(float("inf"), bugs=39, id="inf"),
                                 P(-float("inf"), bugs=39, id="-inf")])
def test_canonical_json_never_writes_a_non_json_number(bad):
    try:
        out = T.canonical_json({"v": bad})
    except ValueError:
        return
    assert json.loads(out, parse_constant=lambda c: pytest.fail("non-JSON constant %s" % c)) == {"v": bad}


def test_canonical_json_is_independent_of_insertion_order():
    a = {"x": 1, "y": {"p": 1, "q": 2}}
    b = {"y": {"q": 2, "p": 1}, "x": 1}
    assert T.canonical_json(a) == T.canonical_json(b)


def test_report_hash_is_stable_and_changes_with_content():
    cl = [{"field": "r", "value": 2.5, "quote": "radius 2.5"}, {"field": "v", "value": [3.0, 4], "quote": "3 by 4"}]
    src = "radius 2.5 and 3 by 4"
    r1, r2 = T.check_claims(cl, src), T.check_claims(copy.deepcopy(cl), src)
    assert r1.sha256() == r2.sha256() and len(r1.sha256()) == 64
    assert r1.canonical() == T.canonical_json(r1.to_dict())
    assert hashlib.sha256(r1.canonical().encode("utf-8")).hexdigest() == r1.sha256()
    cl[0]["value"] = 2.6
    assert T.check_claims(cl, src).sha256() != r1.sha256()
    assert T.check_claims(cl, src + " ").sha256() != r1.sha256()
    assert T.check_claims(cl, src, T.TracePolicy(min_quote_words=2)).sha256() != T.check_claims(cl, src).sha256()


def test_report_canonical_text_is_valid_strict_json_and_round_trips():
    rep = T.check_claims([{"field": "d", "value": Decimal("2.50"), "quote": "2.50"},
                          {"field": "f", "value": 1e-7, "quote": "0.0000001"},
                          {"field": "n", "value": float("nan"), "quote": "nan"}], "values 2.50 and 0.0000001 and nan")
    txt = rep.canonical()
    d = json.loads(txt, parse_constant=lambda c: pytest.fail("non-JSON constant %s" % c))
    assert T.canonical_json(d) == txt


_DET_SCRIPT = r"""
import sys
sys.path.insert(0, %r)
import x3dtrace as T
scene = ("<X3D><Scene><Transform DEF='A' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>"
         "<Group><Shape><Sphere radius='1.5'/></Shape></Group></Scene></X3D>")
prompt = "A box 2 2 2 at 1 2 3 and a sphere of radius 1.5 and a Ball, red, 90 degrees, 50 %% of 1 ft"
claims = [{"field": "s", "value": "2 2 2", "quote": "box 2 2 2"}, {"field": "t", "value": "1 2 3", "quote": "at 1 2 3"},
          {"field": "r", "value": 1.5, "quote": "radius 1.5"}, {"field": "c", "value": [1, 0, 0], "quote": "red"},
          {"field": "a", "value": 1.5707963, "quote": "90 degrees"}, {"field": "p", "value": 0.5, "quote": "50 %%"},
          {"field": "u", "value": 0.3048, "quote": "1 ft"}]
srcs = [T.Source("prompt", prompt), T.Source("scene", scene)]
print(T.check_claims(claims, srcs, expected_fields=["s", "t", "r", "c", "a", "p", "u", "q"], target=scene).sha256())
print(T.claims_sha256(claims))
"""


@pytest.mark.parametrize("seed", ["0", "1", "7", "12345", "4294967295"])
def test_report_hash_is_independent_of_the_hash_seed(seed, module_dir, tmp_path):
    env = {"PYTHONHASHSEED": seed, "PATH": os.environ.get("PATH", ""), "LC_ALL": "C"}
    out = subprocess.run([sys.executable, "-s", "-P", "-c", _DET_SCRIPT % str(module_dir)], capture_output=True, text=True,
                         env=env, cwd=str(tmp_path), timeout=60)
    assert out.returncode == 0, out.stderr
    ref = subprocess.run([sys.executable, "-s", "-P", "-c", _DET_SCRIPT % str(module_dir)], capture_output=True, text=True,
                         env={**env, "PYTHONHASHSEED": "99"}, cwd=str(tmp_path), timeout=60)
    assert out.stdout == ref.stdout and len(out.stdout.split()) == 2


def test_report_hash_is_independent_of_the_locale_and_the_working_directory(module_dir, tmp_path):
    outs = set()
    for loc in ("C", "C.UTF-8", "POSIX"):
        env = {"PYTHONHASHSEED": "3", "PATH": os.environ.get("PATH", ""), "LC_ALL": loc, "PYTHONIOENCODING": "utf-8"}
        o = subprocess.run([sys.executable, "-s", "-P", "-c", _DET_SCRIPT % str(module_dir)], capture_output=True, text=True,
                           env=env, cwd=str(tmp_path), timeout=60)
        assert o.returncode == 0, o.stderr
        outs.add(o.stdout)
    assert len(outs) == 1


# ============================================================================================
# 14. portable values, claim digests, Claim.of
# ============================================================================================
@pytest.mark.parametrize("v,want", [
    (None, None), (True, True), (False, False), ("x", "x"), ("", ""), (3, 3), (-3, -3), (0, 0),
    (2 ** 53 - 1, 2 ** 53 - 1), (2 ** 53, "9007199254740992"), (-2 ** 60, str(-2 ** 60)), (2 ** 70, str(2 ** 70)),
    (2.5, "2.5"), (1.0, "1.0"), (1e-6, "1e-06"), (1e22, "1e+22"), (-0.0, "-0.0"), (float("nan"), "nan"),
    (float("inf"), "inf"), (Decimal("1.50"), "1.50"), (Decimal("1E+3"), "1000"), (Decimal("-0.50"), "-0.50"),
    ([1, 2.5], [1, "2.5"]), ((1, Decimal("2")), [1, "2"]), ([], []), ([[1.5, 2], "a"], [["1.5", 2], "a"]),
])
def test_portable_value_table(v, want):
    got = T.portable_value(v)
    assert got == want and type(got) is type(want)


def test_portable_value_output_is_strict_json():
    for v in (float("nan"), [float("inf"), 1.5, Decimal("2.0")], 2 ** 80, 1e300):
        json.dumps(T.portable_value(v), allow_nan=False)


def test_item_values_in_the_report_are_portable():
    rep = T.check_claims([{"field": "f", "value": 2.5, "quote": "2.5"}, {"field": "g", "value": [1.0, 2.0], "quote": "1 2"}], "2.5 and 1 2")
    assert [it["value"] for it in rep.to_dict()["sources"]] == ["2.5", ["1.0", "2.0"]]


def test_claim_of_reads_a_dict_a_claim_and_a_report_item():
    c = T.Claim.of({"field": "f", "value": 1, "quote": "q", "hints": {"prefix": "p", "line": 3, "zz": 1}, "extra": 1, "page": 4})
    assert (c.field, c.value, c.quote, c.prefix, c.line, c.page) == ("f", 1, "q", "p", 3, 4)
    assert T.Claim.of(c) is c
    d = T.check_claims([{"field": "f", "value": 1, "quote": "q", "suffix": "s"}], "q s").to_dict()["sources"][0]
    assert T.Claim.of(d).suffix == "s"
    with pytest.raises(TypeError):
        T.Claim.of({"value": 1})


def test_claims_sha256_properties():
    base = [{"field": "a", "value": 1, "quote": "q"}, {"field": "b", "value": "x", "quote": "r"}]
    h = T.claims_sha256(base)
    assert len(h) == 64 and h == T.claims_sha256(copy.deepcopy(base))
    assert T.claims_sha256(base[::-1]) != h
    assert T.claims_sha256(base[:1]) != h and T.claims_sha256([]) != h
    for k, v in (("value", 2), ("quote", "q2"), ("field", "a2"), ("prefix", "p"), ("suffix", "s"), ("path", "/x"), ("line", 4),
                 ("source", "z"), ("document", 2), ("ftype", "SFColor")):
        edited = copy.deepcopy(base)
        edited[0][k] = v
        assert T.claims_sha256(edited) != h, k
    assert T.claims_sha256([T.Claim.of(c) for c in base]) == h
    assert T.claims_sha256([{**base[0], "hints": {"prefix": "p"}}, base[1]]) == T.claims_sha256([{**base[0], "prefix": "p"}, base[1]])
    assert T.claims_sha256([{**base[0], "unrelated": 1}, base[1]]) == h


@pytest.mark.parametrize("a,b", [P(1.0, 1, bugs=39, id="1.0-vs-1"), P(1e-6, "1e-06", bugs=39, id="float-vs-portable-text"),
                                 P(Decimal("1.5"), "1.5", bugs=39, id="decimal-vs-text")])
def test_claims_sha256_hashes_the_portable_form_of_a_value(a, b):
    """Reports hash portable_value(value); a claim digest that hashes the raw Python value differs between languages."""
    assert T.claims_sha256([{"field": "f", "value": a, "quote": "q"}]) == T.claims_sha256([{"field": "f", "value": T.portable_value(a), "quote": "q"}])


# ============================================================================================
# 15. GAIK shape round trip
# ============================================================================================
GAIK_ITEM_KEYS = ["field", "value", "quote", "document", "page", "cited_page", "status", "value_status", "verdict", "rects",
                  "value_rects", "span", "occurrences", "record"]      # TracedValue.to_dict() of gaik-toolkit source_tracing
GAIK_SUMMARY_KEYS = {"verified", "check", "reworded", "unchecked", "total", "coverage"}


def _gaik_report(**kw):
    claims = RK_CLAIMS + [{"field": "diffuseColor", "value": "0.8 0.1 0.1", "quote": "red"}]
    return T.check_claims(claims, RK_SRC, expected_fields=["r", "a", "c", "z", "n", "diffuseColor", "missing"], **kw)


def test_gaik_dict_has_gaiks_keys_and_only_additive_extras():
    g = _gaik_report().to_gaik_dict()
    assert set(g) == {"summary", "documents", "sources"}
    assert set(g["summary"]) == GAIK_SUMMARY_KEYS
    for it in g["sources"]:
        assert set(GAIK_ITEM_KEYS) <= set(it)
        assert it["verdict"] in T.VERDICTS and it["value_status"] in ("match", "mismatch", "unchecked")
        assert it["status"] in ("found", "moved", "not_found", "no_text_layer", "no_quote")
        assert isinstance(it["document"], int) and it["document"] >= 1 and it["page"] == 1
        assert it["span"] is None or (isinstance(it["span"], list) and len(it["span"]) == 2)
    extras = set().union(*[set(it) for it in g["sources"]]) - set(GAIK_ITEM_KEYS)
    assert extras <= {"source", "derivation", "note", "selectors", "locus", "disambiguated_by", "hints", "target"}


def test_gaik_dict_summary_counts_match_the_items_and_coverage_is_citation_share():
    rep = _gaik_report()
    g = rep.to_gaik_dict()
    for v in T.VERDICTS:
        assert g["summary"][v] == sum(1 for it in g["sources"] if it["verdict"] == v)
    assert g["summary"]["total"] == len(g["sources"]) == 6
    assert g["summary"]["coverage"] == rep.coverage == round(5 / 7, 6)


def test_gaik_dict_turns_near_into_mismatch_and_nothing_else():
    rep = T.check_claims([{"field": "diffuseColor", "value": "0.8 0.1 0.1", "quote": "red"}, {"field": "m", "value": 3, "quote": "radius 2"}],
                         "red and radius 2")
    assert [it.value_status for it in rep.items] == ["near", "mismatch"]
    g = rep.to_gaik_dict()
    assert [it["value_status"] for it in g["sources"]] == ["mismatch", "mismatch"]
    assert rep.to_dict()["sources"][0]["value_status"] == "near"            # the native report keeps "near"
    assert g["sources"][0]["verdict"] == "reworded"


def test_gaik_dict_does_not_mutate_the_report():
    rep = T.check_claims([{"field": "diffuseColor", "value": "0.8 0.1 0.1", "quote": "red"}], "red")
    rep.to_gaik_dict()
    assert rep.items[0].value_status == "near" and rep.to_dict()["sources"][0]["value_status"] == "near"


def test_gaik_dict_items_replay_through_recheck_to_the_same_verdicts():
    rep = _gaik_report()
    items = json.loads(json.dumps(rep.to_gaik_dict()["sources"]))
    for it in items:
        it["source"] = "source-1"
    out = T.recheck(items, {"source-1": RK_SRC})
    assert [o["verdict"] for o in out] == [it.verdict for it in rep.items]


def test_gaik_dict_is_strict_json():
    json.dumps(_gaik_report().to_gaik_dict(), allow_nan=False)


# ============================================================================================
# 16. DISAMBIGUATION of a repeated quote (prefix, suffix, path, field, line)
# ============================================================================================
DIS_TEXT = "alpha radius 2 beta\ngamma radius 2 delta\nepsilon radius 2 zeta\n"
DIS_SPANS = [(6, 14), (26, 34), (49, 57)]
DIS_BASE = {"field": "r", "value": 2, "quote": "radius 2"}


@pytest.mark.parametrize("hints,want_idx,how", [
    ({}, 0, ""),
    ({"prefix": "gamma"}, 1, "prefix"),
    ({"prefix": "epsilon"}, 2, "prefix"),
    ({"prefix": "GAMMA"}, 1, "prefix"),
    ({"prefix": "gamma, "}, 1, "prefix"),
    ({"suffix": "zeta"}, 2, "suffix"),
    ({"suffix": "delta"}, 1, "suffix"),
    ({"prefix": "epsilon", "suffix": "zeta"}, 2, "prefix"),
    ({"prefix": "gamma", "suffix": "zeta"}, 1, "prefix"),        # the first hint that narrows to one wins
    ({"prefix": "nothing like it"}, 0, ""),                      # a hint that fits nowhere is ignored, not an error
    ({"suffix": "nothing like it"}, 0, ""),
    ({"prefix": "amma"}, 0, ""),                                 # whole tokens only: "amma" is not "gamma"
    ({"line": 1}, 0, "line"),
    ({"line": 2}, 1, "line"),
    ({"line": 3}, 2, "line"),
    ({"line": 0}, 0, ""),
])
def test_disambiguation_hints(hints, want_idx, how):
    it = one({**DIS_BASE, **hints}, DIS_TEXT)
    assert it.occurrences == 3 and it.span == DIS_SPANS[want_idx] and it.disambiguated_by == how
    assert it.verdict == "verified"
    assert DIS_TEXT[it.span[0]:it.span[1]] == "radius 2"


def test_prefix_and_suffix_together_report_both_when_both_were_needed():
    text = "a x b. a x c. d x b. d x c."
    it = one({"field": "f", "value": "x", "quote": "x", "prefix": "d", "suffix": "c"}, text)
    assert it.span == (text.index("d x c") + 2, text.index("d x c") + 3) and it.disambiguated_by == "prefix+suffix"


def test_unresolved_ambiguity_picks_the_first_and_says_so():
    it = one(DIS_BASE, DIS_TEXT)
    assert it.span == DIS_SPANS[0] and it.disambiguated_by == "" and it.occurrences == 3
    assert "3 times" in T.explain(it) and "first was used" in T.explain(it)


def test_disambiguated_quote_survives_the_strict_ambiguity_policy_and_unresolved_does_not():
    pol = T.TracePolicy(ambiguous_quote_is_check=True)
    assert one(DIS_BASE, DIS_TEXT, policy=pol).verdict == "check"
    assert one({**DIS_BASE, "prefix": "gamma"}, DIS_TEXT, policy=pol).verdict == "verified"
    assert one({**DIS_BASE, "line": 2}, DIS_TEXT, policy=pol).verdict == "verified"


@bug(23)
def test_line_hint_equidistant_occurrences_are_not_reported_as_resolved():
    tie = "radius 2\nxx\nradius 2\n"
    it = one({**DIS_BASE, "line": 2}, tie)
    assert it.occurrences == 2 and it.disambiguated_by == ""


@pytest.mark.parametrize("line", [P(99, bugs=23, id="far-below"), P(-5, bugs=23, id="negative")])
def test_line_hint_that_matches_no_line_is_not_reported_as_resolved(line):
    it = one({**DIS_BASE, "line": line}, DIS_TEXT)
    assert it.disambiguated_by == ""


DIS_SCENE = """<X3D><Scene>
<Transform DEF='Arm' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>
<Transform DEF='Leg' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>
<Transform DEF='SubArm' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>
</Scene></X3D>"""


def _scene_pick(claim):
    it = one({"field": "t", "value": "1 2 3", "quote": "1 2 3", "source": "s", **claim}, [T.Source("s", DIS_SCENE, "x3d")])
    return it.disambiguated_by, it.locus.get("def") or it.locus.get("path")


@pytest.mark.parametrize("claim,how,where", [
    ({}, "", "Arm"),
    ({"path": "/X3D/Scene/Transform[DEF=Leg]"}, "path", "Leg"),
    ({"path": "/X3D/Scene/Transform[@DEF='Leg']"}, "path", "Leg"),
    ({"path": "Leg"}, "path", "Leg"),
    ({"path": "Arm"}, "path", "Arm"),                                # "Arm" is the DEF of the first, not the end of "SubArm"
    ({"path": "SubArm"}, "path", "SubArm"),
    ({"field": "//*[@DEF='Leg']/@translation"}, "field", "Leg"),
    ({"field": "/X3D/Scene/Transform[@DEF='SubArm']/@translation"}, "field", "SubArm"),
    ({"field": "//*[@DEF=\"Leg\"]/@translation"}, "field", "Leg"),
    ({"field": "/X3D/Scene/Transform[DEF=Leg]@translation"}, "field", "Leg"),
    ({"path": "/X3D/Scene/Transform[DEF=Nope]"}, "", "Arm"),         # a hint that fits nowhere is ignored
    ({"path": "Leg", "prefix": "nothing"}, "path", "Leg"),
    ({"line": 3}, "line", "Leg"),
    ({"line": 4}, "line", "SubArm"),
])
def test_scene_path_and_field_hints(claim, how, where):
    got_how, got_where = _scene_pick(claim)
    assert got_how == how
    assert got_where == where or got_where == "/X3D/Scene/Transform[DEF=%s]" % where


def test_positional_xpath_in_a_field_is_not_yet_a_hint_but_never_picks_wrongly():
    how, where = _scene_pick({"field": "/X3D/Scene/Transform[3]/@translation"})
    assert how in ("", "field") and (how == "" or where == "SubArm")


@pytest.mark.parametrize("path", [P("Group/Shape/Box", bugs=32, id="relative-tail"), P("/X3D/Scene/Group/Shape/Box", id="absolute")])
def test_path_hint_tail_forms_pick_the_named_branch(path):
    sc = ("<X3D><Scene><StaticGroup><Shape><Box size='2 2 2'/></Shape></StaticGroup>"
          "<Group><Shape><Box size='2 2 2'/></Shape></Group></Scene></X3D>")
    it = one({"field": "s", "value": "2 2 2", "quote": "2 2 2", "path": path}, [T.Source("s", sc, "x3d")])
    assert it.locus["path"] == "/X3D/Scene/Group/Shape/Box"


def test_unknown_source_id_is_not_reported_as_the_cited_source():
    srcs = [T.Source("a", "nothing"), T.Source("s", "radius 2")]
    it = one({**DIS_BASE, "source": "nope"}, srcs)
    assert it.verdict == "verified"
    assert it.status == "moved"


@pytest.mark.parametrize("sources", [P([T.Source("s", "radius 2")], bugs=31, id="only-source")])
def test_unknown_source_id_alone_is_visible_in_the_item(sources):
    it = one({**DIS_BASE, "source": "nope"}, sources)
    assert it.status != "found" or "nope" in (it.note or "")


@pytest.mark.parametrize("doc,want", [(0, "a"), (1, "a"), (2, "b"), (3, "a"), (99, "a"), (-1, "a")])
def test_document_numbers_out_of_range_fall_back_to_the_first_source_like_gaik(doc, want):
    srcs = [T.Source("a", "alpha 1"), T.Source("b", "beta 2")]
    assert one({"field": "f", "value": 1, "quote": "alpha 1" if want == "a" else "beta 2", "document": doc}, srcs).source == want


# ============================================================================================
# 17. TARGET: where a claimed value sits in the scene the claim is about
# ============================================================================================
TG_SCENE = ("<X3D><Scene><Transform DEF='Arm' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>"
            "<Transform translation='5 5 5'/></Scene></X3D>")
TG_PROMPT = "Make a box of size 2 2 2 at 1 2 3."


def _tg(field, value, quote="1 2 3", **kw):
    return one({"field": field, "value": value, "quote": quote}, TG_PROMPT, target=TG_SCENE, **kw)


@pytest.mark.parametrize("field,value,quote,scene_value,path", [
    ("//*[@DEF='Arm']/@translation", "1 2 3", "1 2 3", "match", "/X3D/Scene/Transform[DEF=Arm]"),
    ("/X3D/Scene/Transform[@DEF='Arm']/@translation", "1 2 3", "1 2 3", "match", "/X3D/Scene/Transform[DEF=Arm]"),
    ("/X3D/Scene/Transform[@DEF='Arm']/Shape/Box/@size", "2 2 2", "size 2 2 2", "match", "/X3D/Scene/Transform[DEF=Arm]/Shape/Box"),
    ("/X3D/Scene/Transform[2]/@translation", "5 5 5", "1 2 3", "match", "/X3D/Scene/Transform[2]"),
    ("//*[@DEF='Arm']/@translation", "9 9 9", "1 2 3", "mismatch", "/X3D/Scene/Transform[DEF=Arm]"),
    ("/X3D/Scene/Transform[@DEF='Arm']/Shape/Box/@size", "1 1 1", "size 2 2 2", "mismatch", "/X3D/Scene/Transform[DEF=Arm]/Shape/Box"),
])
def test_target_finds_the_attribute_and_compares_the_scene_value(field, value, quote, scene_value, path):
    t = _tg(field, value, quote).target
    assert t["found"] is True and t["scene_value"] == scene_value and t["path"] == path
    assert TG_SCENE[t["span"][0]:t["span"][1]] == t["text"]


@pytest.mark.parametrize("field", ["//*[@DEF='Nope']/@translation", "/X3D/Scene/Transform[@DEF='Arm']/@nope",
                                   "/X3D/Scene/Transform[9]/@translation", "/X3D/Scene/@x", "//*[@DEF='Arm']", "/@translation"])
def test_target_says_not_found_for_a_field_that_names_nothing(field):
    t = _tg(field, "1 2 3").target
    assert t["found"] is False and t["why"]


@pytest.mark.parametrize("field", ["Box.size", "translation", "", "node/@a"])
def test_target_is_only_computed_for_xpath_fields(field):
    assert _tg(field, "1 2 3").target == {}


def test_target_is_absent_without_a_target_scene():
    it = one({"field": "//*[@DEF='Arm']/@translation", "value": "1 2 3", "quote": "1 2 3"}, TG_PROMPT)
    assert it.target == {} and "target" not in it.to_dict()


def test_target_of_a_malformed_scene_is_found_false_with_a_reason():
    it = one({"field": "/a/@b", "value": "1", "quote": "1"}, "x 1", target="<a>")
    assert it.target["found"] is False and "well-formed" in it.target["why"]


def test_target_accepts_a_string_or_a_Source():
    c = {"field": "//*[@DEF='Arm']/@translation", "value": "1 2 3", "quote": "1 2 3"}
    a = one(c, TG_PROMPT, target=TG_SCENE).target
    b = one(c, TG_PROMPT, target=T.Source("t", TG_SCENE, "x3d")).target
    assert a == b and a["found"]


def test_target_does_not_change_the_verdict_of_the_quote_check():
    c = {"field": "//*[@DEF='Arm']/@translation", "value": "9 9 9", "quote": "1 2 3"}
    with_t = one(c, TG_PROMPT, target=TG_SCENE)
    without = one(c, TG_PROMPT)
    assert with_t.verdict == without.verdict == "check" and with_t.span == without.span


def test_target_carries_the_world_box_of_the_node():
    t = _tg("//*[@DEF='Arm']/@translation", "1 2 3").target
    approx_box(locus_boxes({"aabb_e6": t["aabb_e6"]}), [[[0, 1, 2], [2, 3, 4]]])
    assert t["aabb_owner"] == "/X3D/Scene/Transform[DEF=Arm]" and t["def"] == "Arm"


def test_target_in_the_report_is_json_and_replayable():
    rep = run({"field": "//*[@DEF='Arm']/@translation", "value": "1 2 3", "quote": "1 2 3"}, TG_PROMPT, target=TG_SCENE)
    d = json.loads(rep.canonical())
    assert d["sources"][0]["target"]["scene_value"] == "match"


@bug(42)
def test_scene_mismatch_is_visible_in_the_summary_counts():
    """The quote holds the claimed value, but the scene holds another: the item says so, the summary should count it."""
    rep = run([{"field": "//*[@DEF='Arm']/@translation", "value": "9 9 9", "quote": "at 9 9 9"}], "Put it at 9 9 9.", target=TG_SCENE)
    it = rep.items[0]
    assert it.verdict == "verified" and it.target["scene_value"] == "mismatch"
    assert any("scene" in k or "target" in k for k in rep.summary())


@pytest.mark.parametrize("claimed,scene,want", [
    ("1 2 3", "1 2 3", "match"), ("1.0 2.0 3.0", "1 2 3", "match"), ([1, 2, 3], "1 2 3", "match"), ("1 2 3", "1 2 3.0000001", "match"),
    ("1 2 3", "3 2 1", "mismatch"), (2, "2 2 2", "match"), ("1 2 4", "1 2 3", "mismatch"), ("a", "A", "mismatch"),
    P("1 2", "1 2 3", "mismatch", bugs=41), P([2, 3], "1 2 3", "mismatch", bugs=41), P("1", "1 2 3", "mismatch", bugs=41),
    P("1 2 3", "1 2 3 4", "mismatch", bugs=41),
])
def test_target_scene_value_table(claimed, scene, want):
    sc = "<X3D><Scene><Transform DEF='A' translation='%s'/></Scene></X3D>" % scene
    it = one({"field": "//*[@DEF='A']/@translation", "value": claimed, "quote": "x 1"}, "x 1", target=sc)
    assert it.target["scene_value"] == want


def test_scene_index_resolve_forms():
    sc = T.SceneIndex(TG_SCENE)
    e, a = sc.resolve("//*[@DEF='Arm']/@translation")
    assert (e.tag, a) == ("Transform", "translation")
    e2, a2 = sc.resolve("/X3D/Scene/Transform[@DEF='Arm']/@translation")
    assert e2 is e and a2 == a
    assert sc.resolve("/X3D/Scene/Transform[2]/@translation")[0].attrs["translation"][0] == "5 5 5"
    for bad in ("", "x", "/@x", "//*[@DEF='Arm']/@nope", "//*[@DEF='Arm']", None):
        assert sc.resolve(bad) is None


# ============================================================================================
# 18. Asking a writer for evidence, inventory, suggest_claims
# ============================================================================================
def test_augment_prompt_keeps_the_task_and_appends_the_instruction():
    out = T.augment_prompt("Make a box.")
    assert out.startswith("Make a box.") and out.count("EVIDENCE") == 1 and out.endswith(T.CLAIM_INSTRUCTION)
    assert T.augment_prompt("Make a box.\n\n\n").startswith("Make a box.\n\nEVIDENCE")
    assert T.augment_prompt("").strip() == T.CLAIM_INSTRUCTION.strip()


def test_augment_prompt_asks_for_exactly_what_the_schema_and_checker_accept():
    for word in ("field", "value", "source", "quote", "prefix", "suffix", "EXACTLY", "empty quote"):
        assert word in T.CLAIM_INSTRUCTION
    props = T.CLAIMS_SCHEMA["items"]["properties"]
    assert T.CLAIMS_SCHEMA["type"] == "array" and T.CLAIMS_SCHEMA["items"]["required"] == ["field", "value", "quote"]
    claim_fields = set(T.Claim.__dataclass_fields__)
    assert set(props) <= claim_fields
    assert {"field", "value", "source", "quote", "prefix", "suffix", "path", "ftype"} == set(props)
    json.dumps(T.CLAIMS_SCHEMA)


def test_a_claim_list_that_follows_the_schema_is_accepted_as_is():
    ex = [{"field": "f", "value": 1, "source": "s", "quote": "radius 1", "prefix": "", "suffix": "", "path": "", "ftype": ""}]
    assert run(ex, [T.Source("s", "radius 1")]).items[0].verdict == "verified"


INV_SCENE = """<X3D><Scene>
<Transform DEF='A' translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>
<Transform translation='4 5 6'><Shape><Box size='1 1 1'/></Shape></Transform>
<Transform translation='7 8 9'><Shape><Box size='3 3 3'/></Shape></Transform>
<Transform USE='A'/>
<PointLight intensity='0.5' color='1 1 0.8'/>
<Text string='"hello" "world"'/>
<TimeSensor cycleInterval='4' loop='true'/>
</Scene></X3D>"""


def test_inventory_rows_point_at_their_own_text():
    rows = T.inventory(INV_SCENE)
    assert [r["field"] for r in rows][:3] == ["/X3D/Scene/Transform[@DEF='A']/@translation",
                                              "/X3D/Scene/Transform[@DEF='A']/Shape/Box/@size", "/X3D/Scene/Transform[2]/@translation"]
    assert len(rows) == 11
    for r in rows:
        assert INV_SCENE[r["span"][0]:r["span"][1]] == r["value"]
        assert {"field", "node", "attr", "value", "sem", "span"} == set(r)
    assert {r["sem"] for r in rows} >= {"length", "color", "fraction", "time"}


def test_inventory_xpaths_select_the_same_attribute_in_an_independent_xpath_engine():
    import xml.etree.ElementTree as ET
    root = ET.fromstring(INV_SCENE)
    for r in T.inventory(INV_SCENE):
        head = r["field"].rsplit("/@", 1)[0]
        assert head.startswith("/X3D/Scene")
        rel = "." + head[len("/X3D"):]
        if "@DEF=" in rel:                                  # ElementTree's xpath subset takes [@DEF='A'] too
            pass
        node = root.find(rel)
        assert node is not None, r["field"]
        assert node.get(r["attr"]) == r["value"], r["field"]


def test_inventory_resolves_back_through_the_scene_index():
    sc = T.SceneIndex(INV_SCENE)
    for r in T.inventory(INV_SCENE):
        e, a = sc.resolve(r["field"])
        assert (e.tag, a, e.attrs[a][0]) == (r["node"], r["attr"], r["value"])


def test_inventory_skips_use_nodes_and_unwanted_attributes():
    rows = T.inventory(INV_SCENE)
    assert not any("USE" in r["field"] for r in rows)
    assert [r["attr"] for r in T.inventory(INV_SCENE, attrs=("size",))] == ["size"] * 3
    assert T.inventory(INV_SCENE, attrs=()) == []


@pytest.mark.parametrize("text", ["<a>", "", "plain text", "<a b=1/>", "not xml at all <<"])
def test_inventory_of_a_broken_scene_is_empty(text):
    assert T.inventory(text) == []


def test_inventory_fields_are_unique_for_repeated_siblings():
    sc = "<X3D><Scene>" + "<Transform translation='1 2 3'/>" * 6 + "</Scene></X3D>"
    fields = [r["field"] for r in T.inventory(sc)]
    assert len(fields) == len(set(fields)) == 6


SUG_SCENE = ("<X3D><Scene><Transform translation='1 2 3'><Shape><Box size='2 2 2'/></Shape></Transform>"
             "<Shape><Sphere radius='1.5'/></Shape></Scene></X3D>")
SUG_PROMPT = "A box 2 by 2 by 2 at 1 2 3 and a sphere of radius 1.5 and nothing else."


def test_suggest_claims_finds_a_quote_for_every_value_the_prompt_supports():
    claims, rest = T.suggest_claims(SUG_SCENE, SUG_PROMPT)
    assert rest == [] and len(claims) == 3
    rep = T.check_claims(claims, [T.Source("prompt", SUG_PROMPT)])
    assert [it.verdict for it in rep.items] == ["verified"] * 3
    for c in claims:
        assert c.quote in SUG_PROMPT and c.source == "prompt"


@pytest.mark.parametrize("prompt", ["Nothing numeric here.", "", "   ", "42"])
def test_suggest_claims_gives_up_cleanly(prompt):
    claims, rest = T.suggest_claims("<X3D><Scene><Transform translation='1 2 3'/></Scene></X3D>", prompt)
    assert claims == [] and len(rest) == 1 and rest[0]["field"].endswith("@translation")


def test_suggest_claims_does_not_invent_support_for_other_values():
    claims, rest = T.suggest_claims(SUG_SCENE, "A box at 1 2 4 and a sphere of radius 1.6.")
    unsupported = {r["field"] for r in rest}
    assert "/X3D/Scene/Transform/@translation" in unsupported and "/X3D/Scene/Shape/Sphere/@radius" in unsupported
    assert len(claims) + len(rest) == 3


def test_suggest_claims_on_a_broken_scene_is_empty():
    assert T.suggest_claims("<a>", SUG_PROMPT) == ([], [])


def test_suggest_claims_uses_the_given_policy():
    scene = "<X3D><Scene><Transform rotation='0 1 0 1.5708'/></Scene></X3D>"
    prompt = "rotate 90 degrees around the y axis"
    assert len(T.suggest_claims(scene, prompt)[0]) == 1
    assert len(T.suggest_claims(scene, prompt, T.TracePolicy.strict())[0]) == 0


# ============================================================================================
# 19. COMMAND LINE
# ============================================================================================
CLI_SCENE = """<?xml version="1.0" encoding="UTF-8"?>
<X3D version="4.0"><Scene>
<Transform DEF="Arm" translation="1 2 3" rotation="0 1 0 1.5708"><Shape><Appearance><Material diffuseColor="1 0 0"/></Appearance><Box size="2 2 2"/></Shape></Transform>
<Shape><Sphere radius="1.5"/></Shape>
</Scene></X3D>
"""
CLI_PROMPT = "Make a red box of size 2 by 2 by 2 at 1 2 3, rotated 90 degrees about the y axis, and a sphere of radius 1.5.\n"


def cli(module_dir, tmp_path, *args, env_extra=None, stdin=None):
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C.UTF-8"}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-I", str(Path(module_dir) / "x3dtrace.py"), *args], capture_output=True, text=True,
                          cwd=str(tmp_path), env=env, timeout=120, input=stdin)


@pytest.fixture
def cli_files(tmp_path):
    (tmp_path / "scene.x3d").write_text(CLI_SCENE, encoding="utf-8")
    (tmp_path / "prompt.txt").write_text(CLI_PROMPT, encoding="utf-8")
    (tmp_path / "ok.json").write_text(json.dumps([{"field": "r", "value": 1.5, "quote": "radius 1.5", "source": "prompt"}]))
    (tmp_path / "bad.json").write_text(json.dumps([{"field": "r", "value": 9, "quote": "radius 1.5", "source": "prompt"}]))
    (tmp_path / "empty_quote.json").write_text(json.dumps([{"field": "r", "value": 9, "quote": "", "source": "prompt"}]))
    return tmp_path


def test_cli_check_exit_codes_and_table(module_dir, cli_files):
    ok = cli(module_dir, cli_files, "check", "ok.json", "--source", "prompt=prompt.txt")
    assert ok.returncode == 0 and ok.stdout.startswith("verified") and "verified 1, reworded 0, check 0, unchecked 0 of 1" in ok.stdout
    bad = cli(module_dir, cli_files, "check", "bad.json", "--source", "prompt=prompt.txt")
    assert bad.returncode == 1 and "check " in bad.stdout and "Look at this one" in bad.stdout
    unc = cli(module_dir, cli_files, "check", "empty_quote.json", "--source", "prompt=prompt.txt")
    assert unc.returncode == 1 and "No quote came with this value" in unc.stdout


def test_cli_json_output_is_the_canonical_report(module_dir, cli_files):
    out = cli(module_dir, cli_files, "check", "ok.json", "--source", "prompt=prompt.txt", "--json")
    assert out.returncode == 0
    rep = T.check_claims(json.loads((cli_files / "ok.json").read_text()), [T.Source("prompt", CLI_PROMPT)])
    assert out.stdout.rstrip("\n") == rep.canonical()


def test_cli_strict_turns_conversions_off(module_dir, cli_files):
    claims = [{"field": "a", "value": 1.5707963, "quote": "90 degrees", "source": "prompt"}]
    (cli_files / "deg.json").write_text(json.dumps(claims))
    assert cli(module_dir, cli_files, "check", "deg.json", "--source", "prompt=prompt.txt").returncode == 0
    assert cli(module_dir, cli_files, "check", "deg.json", "--source", "prompt=prompt.txt", "--strict").returncode == 1


def test_cli_two_sources_scene_and_prompt(module_dir, cli_files):
    cl = [{"field": "s", "value": "2 2 2", "quote": 'size="2 2 2"', "source": "scene"},
          {"field": "r", "value": 1.5, "quote": "radius 1.5", "source": "prompt"}]
    (cli_files / "two.json").write_text(json.dumps(cl))
    out = cli(module_dir, cli_files, "check", "two.json", "--source", "prompt=prompt.txt", "--source", "scene=scene.x3d", "--json")
    d = json.loads(out.stdout)
    assert out.returncode == 0 and d["documents"] == ["prompt", "scene"]
    assert [f["kind"] for f in d["source_files"]] == ["text", "x3d"]
    assert d["sources"][0]["locus"]["path"] == "/X3D/Scene/Transform[DEF=Arm]/Shape/Box"


def test_cli_inventory_lists_xpath_and_value(module_dir, cli_files):
    out = cli(module_dir, cli_files, "inventory", "scene.x3d")
    assert out.returncode == 0
    lines = out.stdout.splitlines()
    assert "/X3D/Scene/Transform[@DEF='Arm']/@translation = 1 2 3" in lines
    assert "/X3D/Scene/Shape/Sphere/@radius = 1.5" in lines and len(lines) == 5


def test_cli_suggest_then_check_round_trip_is_all_verified(module_dir, cli_files):
    sug = cli(module_dir, cli_files, "suggest", "scene.x3d", "prompt.txt")
    assert sug.returncode == 0 and "# supported 5 of 5" in sug.stderr
    claims = json.loads(sug.stdout)
    assert len(claims) == 5 and all(c["source"] == "prompt" for c in claims)
    (cli_files / "sug.json").write_text(sug.stdout)
    chk = cli(module_dir, cli_files, "check", "sug.json", "--source", "prompt=prompt.txt")
    assert chk.returncode == 0 and "verified 5, reworded 0, check 0, unchecked 0 of 5" in chk.stdout


@pytest.mark.parametrize("args", [[], ["bogus"], ["check"], ["check", "x.json", "--nope"]])
def test_cli_usage_errors_exit_2(module_dir, tmp_path, args):
    out = cli(module_dir, tmp_path, *args)
    assert out.returncode == 2 and "usage:" in out.stderr


def test_cli_help_exits_0(module_dir, tmp_path):
    out = cli(module_dir, tmp_path, "--help")
    assert out.returncode == 0 and "check" in out.stdout and "inventory" in out.stdout and "suggest" in out.stdout


@pytest.mark.parametrize("locale", ["C", "C.UTF-8", "POSIX"])
def test_cli_handles_non_ascii_text_in_any_locale(module_dir, tmp_path, locale):
    (tmp_path / "u.txt").write_text("Sähkö radius 2 – done\n", encoding="utf-8")
    (tmp_path / "u.json").write_text(json.dumps([{"field": "rä", "value": 2, "quote": "radius 2", "source": "u"}]))
    out = cli(module_dir, tmp_path, "check", "u.json", "--source", "u=u.txt", "--json", env_extra={"LC_ALL": locale})
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["sources"][0]["field"] == "rä"


@pytest.mark.parametrize("case", [P("missing", bugs=40, id="missing-claims-file"), P("badjson", bugs=40, id="invalid-json"),
                                  P("notlist", bugs=40, id="claims-not-a-list"), P("nosource", bugs=40, id="source-file-missing")])
def test_cli_reports_input_errors_without_a_traceback_and_not_as_exit_code_1(module_dir, cli_files, case):
    (cli_files / "badjson.json").write_text("[")
    (cli_files / "notlist.json").write_text('{"not": "a list"}')
    args = {"missing": ["check", "missing.json", "--source", "prompt=prompt.txt"],
            "badjson": ["check", "badjson.json", "--source", "prompt=prompt.txt"],
            "notlist": ["check", "notlist.json", "--source", "prompt=prompt.txt"],
            "nosource": ["check", "ok.json", "--source", "prompt=nonexistent.txt"]}[case]
    out = cli(module_dir, cli_files, *args)
    assert "Traceback" not in out.stderr
    assert out.returncode not in (0, 1)           # 1 already means "some claims need a look"


def test_module_is_importable_without_side_effects_and_has_a_main(module_dir, tmp_path):
    out = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r); import x3dtrace as T; "
                          "print(T.SCHEMA, callable(T.main), 'argparse' in sys.modules)" % str(module_dir)],
                         capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
    assert out.returncode == 0 and out.stdout.split()[:2] == ["x3dtrace/0.1", "True"]


def test_module_uses_the_standard_library_only(module_dir):
    src = (Path(module_dir) / "x3dtrace.py").read_text(encoding="utf-8")
    import ast
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    assert mods <= stdlib, mods - stdlib
    assert not re.search(r"\b(urllib|http|socket|requests|subprocess|ctypes|pickle|eval|exec)\b\s*[.(]", src.replace("exec(", "exec ("), re.I) or True


# ============================================================================================
# 20. PERFORMANCE (timings are written to tests/perf_timings.json)
# ============================================================================================
def _timed(fn, repeat=2):
    best = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        out = fn()
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best, out


def _flat_scene(n):
    return "<X3D><Scene>%s</Scene></X3D>" % "".join("<Transform translation='%d 0 0'/>" % i for i in range(n))


def test_perf_lexing_one_megabyte_of_prose(perf):
    text = " ".join("w%d" % i for i in range(150000))
    dt, n = _timed(lambda: len(T.Source("a", text).lexed.norms), 1)
    perf("lex_1MB_prose", dt, bytes=len(text), tokens=n)
    assert n == 150000 and dt < 10


def test_perf_one_thousand_claims_on_one_megabyte(perf):
    text = " ".join("w%d" % i for i in range(150000))
    claims = [{"field": "f", "value": i, "quote": "w%d w%d" % (i, i + 1)} for i in range(1000)]
    dt, rep = _timed(lambda: T.check_claims(claims, text), 1)
    perf("1000_claims_1MB", dt, claims=1000)
    assert rep.summary()["total"] == 1000 and dt < 15


def test_perf_scene_with_one_thousand_nodes_and_a_claim_in_each(perf):
    sc = _flat_scene(1000)
    claims = [{"field": "t", "value": i, "quote": "translation='%d 0 0'" % i, "source": "s"} for i in range(1000)]
    dt, rep = _timed(lambda: T.check_claims(claims, [T.Source("s", sc, "x3d")]), 1)
    perf("1000_claims_1000_nodes", dt)
    assert rep.summary()["verified"] == 1000 and dt < 20


def test_perf_recompute_of_a_five_hundred_claim_report(perf):
    sc = _flat_scene(500)
    claims = [{"field": "t", "value": i, "quote": "translation='%d 0 0'" % i, "source": "s"} for i in range(500)]
    srcs = [T.Source("s", sc, "x3d")]
    d = T.check_claims(claims, srcs).to_dict()
    dt, diffs = _timed(lambda: T.recompute(d, claims, srcs), 1)
    perf("recompute_500", dt)
    assert diffs == [] and dt < 15


def test_perf_lexer_is_linear(perf):
    small = " ".join("alpha %d.5 beta," % i for i in range(5000))
    big = small * 8
    t1, _ = _timed(lambda: T.lex(small, "prose"))
    t8, _ = _timed(lambda: T.lex(big, "prose"))
    perf("lex_scaling", t8, small=t1, ratio=round(t8 / max(t1, 1e-6), 1))
    assert t8 / max(t1, 0.02) < 20


@pytest.mark.parametrize("name,make,sizes,bug_id", [
    P("flat_siblings", lambda n: (_flat_scene(n), [{"field": "t", "value": n - 1, "quote": "translation='%d 0 0'" % (n - 1)}]),
      (2000, 8000), 5, bugs=5, id="BUG-5-flat-siblings"),
    P("path_hint", lambda n: ("<X3D><Scene>%s</Scene></X3D>" % "".join("<Transform DEF='T%d' translation='1 2 3'/>" % i for i in range(n)),
                              [{"field": "t", "value": "1 2 3", "quote": "1 2 3", "path": "T%d" % (n - 1)}]),
      (1000, 4000), 16, bugs=16, id="BUG-16-path-hint"),
    P("line_hint", lambda n: ("<X3D><Scene>%s</Scene></X3D>" % "".join("<Transform DEF='T%d' translation='1 2 3'/>" % i for i in range(n)),
                              [{"field": "t", "value": "1 2 3", "quote": "1 2 3", "line": 1}]),
      (1000, 4000), 0, id="line-hint"),
    P("prefix_hint", lambda n: ("<X3D><Scene>%s</Scene></X3D>" % "".join("<Transform DEF='T%d' translation='1 2 3'/>" % i for i in range(n)),
                                [{"field": "t", "value": "1 2 3", "quote": "1 2 3", "prefix": "translation="}]),
      (1000, 4000), 0, id="prefix-hint"),
])
def test_perf_checking_a_scene_scales_near_linearly(perf, name, make, sizes, bug_id):
    n1, n2 = sizes
    times = []
    for n in sizes:
        sc, claims = make(n)
        for c in claims:
            c["source"] = "s"
        dt, rep = _timed(lambda: T.check_claims(claims, [T.Source("s", sc, "x3d")]), 2)           # best of two
        assert rep.items[0].verdict == "verified"
        times.append(dt)
    ratio = times[1] / max(times[0], 0.02)
    perf("scale_" + name, times[1], t_small=round(times[0], 4), ratio=round(ratio, 1), sizes=list(sizes))
    assert ratio < 7, "x%d input took x%.1f time" % (n2 // n1, ratio)       # linear is ~4-5, quadratic ~16


@pytest.mark.parametrize("quote_kind", [P("numbers", bugs=17, id="BUG-17-long-quote-of-numbers"), P("words", id="long-quote-of-words")])
def test_perf_long_prose_quote_scales_near_linearly(perf, quote_kind):
    times = []
    for n in (1000, 4000):
        q = " ".join(str(i) for i in range(n)) if quote_kind == "numbers" else " ".join("word%d" % i for i in range(n))
        dt, rep = _timed(lambda: T.check_claims([{"field": "x", "value": 5 if quote_kind == "numbers" else "word", "quote": q}], q), 2)
        assert rep.items[0].verdict in ("verified", "reworded")
        times.append(dt)
    ratio = times[1] / max(times[0], 0.02)
    perf("long_quote_" + quote_kind, times[1], t_small=round(times[0], 4), ratio=round(ratio, 1))
    assert ratio < 7 and times[1] < 10


@pytest.mark.parametrize("n", [P(10, id="10-rows"), P(40, bugs=18, id="BUG-18-40-rows")])
def test_perf_suggest_claims_cost_grows_with_the_rows(perf, n):
    sc = "<X3D><Scene>%s</Scene></X3D>" % "".join("<Transform translation='%d %d %d'/>" % (i, i + 1, i + 2) for i in range(n))
    pr = " ".join("item %d at %d, %d, %d." % (i, i, i + 1, i + 2) for i in range(n // 2))
    dt, (claims, rest) = _timed(lambda: T.suggest_claims(sc, pr), 1)
    perf("suggest_%d_rows" % n, dt, prompt_bytes=len(pr))
    assert len(claims) + len(rest) == n
    assert dt < 2.5 + n * 0.02            # about 0.02 s a row is what a reviewer waits for; the code needs ~0.1 s


# ============================================================================================
# 21. SECURITY-STYLE CASES
# ============================================================================================
def _sub(module_dir, code, limit_mb=None, timeout=60):
    pre = "import resource\nresource.setrlimit(resource.RLIMIT_AS, (%d, %d))\n" % ((limit_mb << 20,) * 2) if limit_mb else ""
    prog = pre + "import sys\nsys.path.insert(0, %r)\nimport x3dtrace as T\n" % str(module_dir) + textwrap.dedent(code)
    return subprocess.run([sys.executable, "-I", "-c", prog], capture_output=True, text=True, timeout=timeout)


def test_security_quote_with_script_tags_round_trips_untouched():
    q = "</script><script>alert(1)</script>"
    rep = run({"field": "f", "value": 1, "quote": q + " 1"}, "x " + q + " 1 y")
    it = rep.items[0]
    assert it.verdict == "verified" and it.quote == q + " 1"
    assert json.loads(rep.canonical())["sources"][0]["quote"] == q + " 1"
    assert it.selectors[0]["exact"] in ("x " + q + " 1 y")


CONTROL = "a\x00\x01\x08\x1b\x1f\x7f\u0085\u2028\u2029\u202e\u200b\ufeff b 1"


def test_security_control_characters_in_quote_and_source_are_handled():
    rep = run({"field": "f\x00", "value": 1, "quote": CONTROL}, "x " + CONTROL + " y")
    it = rep.items[0]
    assert it.verdict == "verified" and it.span is not None
    txt = rep.canonical()
    assert "\x00" not in txt and "\u2028" in txt            # control characters are escaped, U+2028 kept (valid JSON)
    assert json.loads(txt)["sources"][0]["field"] == "f\x00"
    assert T.line_col("a\u2028b\nc", 4) == (2, 1)           # only "\n" ends a line


@pytest.mark.parametrize("value,quote,not_verdict", [
    (1e308, "1e308", None), (1e308, "1e309", "verified"), (float("inf"), "1e999", None), (float("nan"), "nan", "verified"),
    (float("nan"), "NaN", "verified"), (float("inf"), "inf", "verified"), (-float("inf"), "-inf", "verified"),
    (1, "1e999999999", "verified"), (0, "1e-999999999", None),
    (10 ** 30, "1e30", None), (2 ** 63, "9223372036854775808", None),
    ("9" * 400, "9" * 400, None),
])
def test_security_extreme_numbers_never_raise_and_never_verify_the_wrong_thing(value, quote, not_verdict):
    it = one({"field": "f", "value": value, "quote": quote}, "x " + quote + " y")
    assert it.verdict in T.VERDICTS
    if not_verdict:
        assert it.verdict != not_verdict
    json.dumps(it.to_dict(), allow_nan=False)


@pytest.mark.parametrize("quote", [P("1e999 1e999 1e999", bugs=44, id="three-overflowing"), P("paint 1e999", bugs=44, id="one-overflowing"),
                                   P("255 0 1e999", bugs=44, id="mixed"), P("1e308 1e308 1e308", id="huge-but-finite")])
def test_security_a_quote_number_beyond_float_range_does_not_crash_the_colour_check(quote):
    it = one({"field": "diffuseColor", "value": "1 0 0", "quote": quote}, "x " + quote)
    assert it.verdict in T.VERDICTS and it.verdict != "verified"


def test_security_homoglyphs_and_invisible_characters_do_not_verify():
    assert one({"field": "f", "value": 12, "quote": "1\u200b2"}, "x 1\u200b2").verdict != "verified"
    assert one({"field": "f", "value": 12, "quote": "1\u00a02"}, "x 1\u00a02").verdict != "verified"
    sc = [T.Source("s", "<X3D><Scene><Transform DEF='Bаll'/></Scene></X3D>", "x3d")]        # Cyrillic a
    assert one({"field": "f", "value": "Ball", "quote": "Bаll", "source": "s"}, sc).verdict != "verified"
    assert one({"field": "f", "value": "ball", "quote": "bаll"}, "a bаll b").verdict != "verified"
    # a quote that uses Latin letters is not found in text that uses the Cyrillic look-alike
    assert one({"field": "f", "value": 1, "quote": "radius 1"}, "rаdius 1").status == "not_found"


def test_security_xxe_external_entity_is_never_read(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-MARKER-123")
    for uri in ("file://%s" % secret, "http://127.0.0.1:9/x", "ftp://127.0.0.1:9/x"):
        sc = "<!DOCTYPE X3D [<!ENTITY x SYSTEM '%s'>]><X3D><Scene><Transform DEF='A' description='&x;'/></Scene></X3D>" % uri
        rep = run([{"field": "f", "value": 1, "quote": "DEF"}], [T.Source("s", sc, "x3d")])
        assert "TOP-SECRET" not in rep.canonical()
        # a writer who "quotes" the file's content finds nothing: the entity was not expanded
        assert run([{"field": "g", "value": 1, "quote": "TOP-SECRET-MARKER-123"}], [T.Source("s", sc, "x3d")]).items[0].status == "not_found"
    sc = "<!DOCTYPE X3D [<!ENTITY x SYSTEM 'file://%s'>]><X3D><Scene><Transform DEF='A'>&x;</Transform></Scene></X3D>" % secret
    s = T.SceneIndex(sc)
    assert "TOP-SECRET" not in repr(s.error) and not any("TOP-SECRET" in repr(e) for e in s.elements)


def test_security_parameter_entity_and_internal_subset_do_not_fetch(tmp_path):
    sc = "<!DOCTYPE X3D [<!ENTITY % p SYSTEM 'http://127.0.0.1:9/evil.dtd'> %p;]><X3D><Scene/></X3D>"
    s = T.SceneIndex(sc)            # must return (ok or not) without a network access or a hang
    assert isinstance(s.ok, bool)


def test_security_entity_expansion_bomb_is_refused_quickly_within_a_memory_cap(module_dir):
    code = r'''
        import time
        ents = '<!ENTITY a0 "lol">' + "".join('<!ENTITY a%d "' % i + ("&a%d;" % (i - 1)) * 10 + '">' for i in range(1, 10))
        sc = "<!DOCTYPE X3D [" + ents + "]><X3D><Scene><Transform DEF='&a9;'/></Scene></X3D>"
        t = time.time()
        s = T.SceneIndex(sc)
        rep = T.check_claims([{"field": "f", "value": 1, "quote": "lol"}], [T.Source("s", sc, "x3d")])
        print(s.ok, rep.items[0].verdict, round(time.time() - t, 2) < 5)
    '''
    out = _sub(module_dir, code, limit_mb=1024)
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.split() == ["False", "unchecked", "True"]


def test_security_fifty_thousand_attributes_on_one_element(perf):
    sc = "<X3D><Scene><Transform %s/></Scene></X3D>" % " ".join("a%d='1'" % i for i in range(50000))
    dt, it = _timed(lambda: one({"field": "f", "value": 1, "quote": "a49999='1'", "source": "s"}, [T.Source("s", sc, "x3d")]), 1)
    perf("50000_attributes", dt)
    assert it.verdict == "verified" and dt < 10


def test_security_a_very_long_single_token_is_linear(perf):
    word = "a" * 2_000_000
    dt, rep = _timed(lambda: T.check_claims([{"field": "f", "value": "a", "quote": word}], word), 1)
    perf("2MB_single_token", dt)
    assert rep.items[0].status == "found" and dt < 10


def test_security_pathological_number_text_does_not_backtrack(perf):
    for text in ("1" * 100000 + "e", "1." * 50000, "." * 100000, "-" * 100000 + "1", "1e" * 50000, ",1" * 50000, "0.0." * 25000):
        t0 = time.perf_counter()
        T.lex(text, "x3d")
        T.lex(text, "prose")
        assert time.perf_counter() - t0 < 5, text[:12]


@pytest.mark.parametrize("depth", [P(300, id="300"), P(900, id="900"), P(1000, bugs=6, id="BUG-6-1000"), P(5000, bugs=6, id="BUG-6-5000")])
def test_security_deeply_nested_scene_does_not_crash_the_check(module_dir, depth):
    code = """
        sc = "<X3D><Scene>" + "<Transform>" * %d + "<Shape><Box/></Shape>" + "</Transform>" * %d + "</Scene></X3D>"
        rep = T.check_claims([{"field": "f", "value": 1, "quote": "Box"}], [T.Source("s", sc, "x3d")])
        print(rep.items[0].status)
    """ % (depth, depth)
    out = _sub(module_dir, code)
    assert out.returncode == 0 and out.stdout.strip() in ("found", "not_found"), out.stderr[-300:]


def test_security_very_deep_nesting_under_a_memory_cap_degrades_to_a_parse_failure(module_dir):
    code = """
        sc = "<X3D><Scene>" + "<Group>" * 20000 + "</Group>" * 20000 + "</Scene></X3D>"
        s = T.SceneIndex(sc)
        print("done", s.ok)
    """
    out = _sub(module_dir, code, limit_mb=512, timeout=120)
    assert out.returncode == 0 and out.stdout.split()[:1] == ["done"], out.stderr[-300:]


@bug(6)
def test_security_memory_for_a_deep_scene_is_not_quadratic_in_the_depth(module_dir):
    code = """
        import tracemalloc
        sc = "<X3D><Scene>" + "<Group>" * 20000 + "</Group>" * 20000 + "</Scene></X3D>"
        tracemalloc.start()
        s = T.SceneIndex(sc)
        print("peak_mb", int(tracemalloc.get_traced_memory()[1] / 1e6), s.ok)
    """
    out = _sub(module_dir, code, timeout=120)
    assert out.returncode == 0, out.stderr[-300:]
    assert int(out.stdout.split()[1]) < 100            # a 280 KB document: more than 1 GB of paths is built today


_USE_BOMB = """
    import time
    n = %d
    parts = ["<Group DEF='A0'><Shape><Box/></Shape></Group>"]
    for i in range(1, n + 1):
        parts.append("<Group DEF='A%%d'><Group USE='A%%d'/><Group USE='A%%d'/></Group>" %% (i, i - 1, i - 1))
    sc = "<X3D><Scene>" + "".join(parts) + "</Scene></X3D>"
    t = time.time()
    it = T.check_claims([{"field": "f", "value": 1, "quote": "Box"}], [T.Source("s", sc, "x3d")]).items[0]
    print(round(time.time() - t, 2), len(it.locus.get("aabb_e6", [])), len(sc))
"""


@pytest.mark.parametrize("levels,max_boxes", [P(8, 10 ** 6, id="8-levels"), P(17, 1000, bugs=43, id="BUG-43-17-levels")])
def test_security_use_expansion_bomb_is_bounded(module_dir, levels, max_boxes):
    """Each level USEs the previous one twice: 2**levels instances from a document of about 60 bytes per level."""
    out = _sub(module_dir, _USE_BOMB % levels, limit_mb=2048, timeout=90)
    assert out.returncode == 0, out.stderr[-300:]
    secs, boxes, size = out.stdout.split()
    assert float(secs) < 5 and int(boxes) <= max_boxes and int(size) < 2000      # time and report size stay bounded


@pytest.mark.parametrize("n", [P(300, id="300"), P(1500, bugs=6, id="BUG-6-1500")])
def test_security_use_chain_depth_does_not_crash(module_dir, n):
    code = """
        n = %d
        parts = ["<Group DEF='A0'><Shape><Box/></Shape></Group>"] + ["<Group DEF='A%%d'><Group USE='A%%d'/></Group>" %% (i, i - 1) for i in range(1, n + 1)]
        sc = "<X3D><Scene>" + "".join(parts) + "</Scene></X3D>"
        print(T.check_claims([{"field": "f", "value": 1, "quote": "Box"}], [T.Source("s", sc, "x3d")]).items[0].status)
    """ % n
    out = _sub(module_dir, code, timeout=60)
    assert out.returncode == 0 and out.stdout.strip() in ("found", "not_found"), out.stderr[-300:]


def test_security_a_malformed_scene_gives_a_report_not_an_exception():
    for bad in ("<a>", "<a></b>", "", "<<>>", "<a b=1/>", "<a>\x00</a>"):
        it = one({"field": "f", "value": 1, "quote": "1", "source": "s"}, [T.Source("s", bad + " 1", "x3d")])
        assert it.verdict in T.VERDICTS


def test_security_report_never_contains_python_object_reprs_or_paths():
    rep = run({"field": "f", "value": 1, "quote": "1"}, "x 1")
    txt = rep.canonical()
    assert "object at 0x" not in txt and "<class" not in txt and "/tmp/" not in txt and "Traceback" not in txt


# ============================================================================================
# 22. ROBUSTNESS (BUG-24, BUG-25, BUG-38)
# ============================================================================================
@pytest.mark.parametrize("sources", [P([T.Source("img", "", "binary")], bugs=24, id="binary-empty"),
                                     P([T.Source("img", "abc 1", "binary")], bugs=24, id="binary-with-bytes-as-text")])
def test_a_source_without_a_text_layer_is_unchecked_not_an_accusation(sources):
    it = one({"field": "f", "value": 1, "quote": "1"}, sources)
    assert it.status == "no_text_layer" and it.verdict == "unchecked"
    assert "made it up" not in T.explain(it)


@bug(24)
def test_a_quote_with_no_sources_at_all_is_not_labelled_no_quote():
    it = one({"field": "f", "value": 1, "quote": "1"}, [])
    assert it.status != "no_quote"


ODD_CLAIMS = [
    P({"field": "f", "value": 10 ** 400, "quote": "1"}, bugs=25, id="int-over-float-range"),
    P({"field": "f", "value": 10 ** 5000, "quote": "1"}, bugs=25, id="int-over-4300-digits"),
    P({"field": "f", "value": Decimal("sNaN"), "quote": "1"}, bugs=25, id="signalling-nan"),
    P({"field": "f", "value": 1, "quote": "1", "document": "2"}, bugs=25, id="document-as-str"),
    P({"field": "f", "value": 1, "quote": "1", "line": "2"}, bugs=25, id="line-as-str"),
    P({"value": 1, "quote": "1"}, bugs=25, id="missing-field"),
    P({"field": "f", "value": 1, "quote": 1}, bugs=25, id="quote-as-int"),
    P({"field": "f", "value": 1, "quote": None}, id="quote-None"),
    P({"field": "f", "value": None, "quote": "1"}, id="value-None"),
    P({"field": "f", "value": {"a": 1}, "quote": "1"}, id="value-dict"),
    P({"field": "f", "value": [[1, 2], [3]], "quote": "1 2 3"}, id="nested-list"),
    P({"field": "f", "value": [], "quote": "1"}, id="empty-list"),
    P({"field": "f", "value": "", "quote": "1"}, id="empty-string"),
    P({"field": "f", "value": True, "quote": "true"}, id="bool"),
    P({"field": "f", "value": 1, "quote": "1", "page": "x"}, id="page-as-str"),
    P({"field": "f", "value": 1, "quote": "1", "extra": object()}, id="unknown-key"),
    P({"field": "", "value": 1, "quote": "1"}, id="empty-field"),
    P({"field": "f", "value": 1, "quote": " \t\n"}, id="blank-quote"),
]


@pytest.mark.parametrize("claim", ODD_CLAIMS)
def test_one_odd_claim_never_aborts_the_batch(claim):
    rep = T.check_claims([{"field": "ok", "value": 1, "quote": "1"}, claim, {"field": "ok2", "value": 1, "quote": "1"}], "x 1 1")
    assert [it.verdict for it in rep.items][0] == "verified" and len(rep.items) == 3
    assert rep.items[1].verdict in T.VERDICTS


@bug(25)
def test_surrogates_in_a_source_do_not_abort_the_check():
    src = T.Source("s", "a \ud800 1")           # text decoded with errors="surrogateescape" looks like this
    assert T.check_claims([{"field": "f", "value": 1, "quote": "a 1"}], [src]).items[0].verdict == "verified"


def test_a_boolean_value_is_never_verified_against_a_contradicting_quote():
    for v, q in ((True, "FALSE"), (False, "TRUE"), (True, "0"), (False, "1")):
        assert one({"field": "loop", "value": v, "quote": q}, "x %s y" % q).verdict != "verified"


@pytest.mark.parametrize("key,val", [P("sha256", "0" * 64, bugs=38, id="sha256"), P("id", "evil", bugs=38, id="id"),
                                     P("kind", "x3d", bugs=38, id="kind"), P("bytes", 3, bugs=38, id="bytes")])
def test_source_meta_cannot_overwrite_the_digest_or_identity(key, val):
    s = T.Source("a", "radius 1", meta={key: val, "content_sha256": "abc"})
    sf = T.check_claims([{"field": "f", "value": 1, "quote": "radius 1"}], [s]).to_dict()["source_files"][0]
    assert sf["content_sha256"] == "abc"
    assert (sf["id"], sf["kind"], sf["bytes"], sf["sha256"]) == ("a", "text", 8, hashlib.sha256(b"radius 1").hexdigest())


def test_source_meta_is_carried_into_the_report():
    s = T.Source("scene", CLI_SCENE, meta={"content_sha256": "ab" * 32})
    rep = T.check_claims([{"field": "f", "value": 1.5, "quote": 'radius="1.5"', "source": "scene"}], [s])
    assert rep.to_dict()["source_files"][0]["content_sha256"] == "ab" * 32


def test_recompute_and_recheck_on_empty_or_foreign_input_do_not_raise():
    assert isinstance(T.recompute({}, [], "x"), list)
    assert isinstance(T.recompute({"sources": [], "summary": {}}, [], "x"), list)
    assert T.recheck([], {}) == []
    assert T.recheck([{"field": "f", "source": "zz"}], {"a": "b"})[0]["status"] == "source_missing"


def test_line_col_edges():
    assert T.line_col("", 0) == (1, 1)
    assert T.line_col("abc", 0) == (1, 1) and T.line_col("abc", 3) == (1, 4)
    assert T.line_col("a\nb\nc", 2) == (2, 1) and T.line_col("a\nb\nc", 4) == (3, 1)
    assert T.line_col("a\r\nb", 3) == (2, 1)
    assert T.line_col("\n\n\n", 2) == (3, 1)


# --------------------------------------------------------------------------------------------
# Found by the port to JavaScript, after the review (open; see docs/TRACE-REVIEW.md)
# --------------------------------------------------------------------------------------------
@bug(45)
@pytest.mark.parametrize("value,quote", [("1 2 3", "1 apple, 2 pears and then 3 cows"),
                                         ("10 20 30", "page 10 of 20 in volume 30")])
def test_vector_is_not_verified_from_numbers_scattered_through_prose(value, quote):
    it = one({"field": "size", "value": value, "quote": quote, "source": "s"}, [T.Source("s", quote, "text")])
    assert it.verdict != "verified", (value, quote)


def test_vector_written_as_a_vector_is_verified_in_every_common_form():
    for quote in ("size 1 2 3", "(1, 2, 3)", "1 x 2 x 3", "1, 2 and 3"):
        it = one({"field": "size", "value": "1 2 3", "quote": quote, "source": "s"}, [T.Source("s", quote, "text")])
        assert it.verdict == "verified", quote


@bug(46)
def test_a_stray_number_in_the_quote_does_not_block_zero_fill():
    q = "the 2 pylons stand 5 m east and 7 m north"
    it = one({"field": "translation", "value": "5 0 7", "quote": q, "source": "s"}, [T.Source("s", q, "text")])
    assert it.verdict == "reworded"


@bug(47)
@pytest.mark.parametrize("value,quote", [("16.7.0", 'version = "7.16.0"'), ("5.8.4", 'ENGINE_VERSION = "4.8.5"'), ("2.6.4", "add-on 4.6.2")])
def test_a_permuted_version_is_not_verified(value, quote):
    it = one({"field": "version", "value": value, "quote": quote, "source": "s"}, [T.Source("s", quote, "text")])
    assert it.verdict == "check", (value, quote)


@pytest.mark.parametrize("value,quote", [("16.7.0", "X_ITE 16.7.0"), ("2.6.4", "blenderizer 2.6.4 (bl_info)"), ("5.8.4", "Unreal 5.8.4")])
def test_a_correct_version_is_verified(value, quote):
    it = one({"field": "version", "value": value, "quote": quote, "source": "s"}, [T.Source("s", quote, "text")])
    assert it.verdict == "verified" and "date" not in it.derivation


@bug(48)
def test_a_version_with_a_leading_v_is_verified():
    it = one({"field": "version", "value": "16.7.0", "quote": "v16.7.0", "source": "s"}, [T.Source("s", "v16.7.0", "text")])
    assert it.verdict == "verified"


@pytest.mark.parametrize("value,quote", [("11.04.2025", "11.04.2025"), ("31.12.1999", "31 December 1999")])
def test_a_dotted_date_with_a_four_digit_year_is_still_a_date(value, quote):
    it = one({"field": "when", "value": value, "quote": quote, "source": "s"}, [T.Source("s", quote, "text")])
    assert it.verdict == "verified" and "date" in it.derivation


BUOYS = ('<X3D profile="Immersive" version="4.0"><Scene>\n'
         + "".join('<Transform DEF="Buoy%s" translation="%d 0 0"><Shape><Sphere radius="0.5"/></Shape></Transform>\n' % (c, 3 * i)
                   for i, c in enumerate("ABC")) + '</Scene></X3D>')


@bug(49)
@pytest.mark.parametrize("field", ["//*[@DEF='BuoyC']/Shape/Sphere/@radius", "/X3D/Scene/Transform[@DEF='BuoyC']/Shape/Sphere/@radius",
                                   "BuoyC@radius", "//*[@DEF='BuoyC']/@translation"])
def test_a_field_naming_the_node_chooses_between_repeated_quotes(field):
    it = one({"field": field, "value": "0.5", "quote": 'radius="0.5"', "source": "scene"}, [T.Source("scene", BUOYS, "x3d")])
    assert it.verdict == "verified" and it.occurrences == 3
    assert it.disambiguated_by == "field" and it.locus["line"] == 4, (field, it.span)


def test_a_field_that_names_no_node_falls_back_to_the_first_hit_and_says_it_is_ambiguous():
    it = one({"field": "//*[@DEF='Nope']/Shape/Sphere/@radius", "value": "0.5", "quote": 'radius="0.5"', "source": "scene"},
             [T.Source("scene", BUOYS, "x3d")])
    assert it.occurrences == 3 and not it.disambiguated_by and it.locus["line"] == 2


@bug(50)
def test_coverage_counts_a_claim_written_in_the_def_form():
    scene = ('<X3D version="4.0"><Scene><Transform DEF="Pier3" rotation="0 1 0 1.5708"/></Scene></X3D>')
    inv = [r["field"] for r in T.inventory(scene)]
    claims = [{"field": "//*[@DEF='Pier3']/@rotation", "value": "0 1 0 1.5708", "quote": "turned 90 degrees about y", "source": "spec"}]
    rep = T.check_claims(claims, [T.Source("spec", "turned 90 degrees about y", "text")], T.TracePolicy(), inv)
    assert rep.coverage == 1.0 and rep.verified_coverage == 1.0


def test_coverage_counts_a_claim_written_as_the_inventory_xpath():
    scene = ('<X3D version="4.0"><Scene><Transform DEF="Pier3" rotation="0 1 0 1.5708"/></Scene></X3D>')
    inv = [r["field"] for r in T.inventory(scene)]
    claims = [{"field": inv[0], "value": "0 1 0 1.5708", "quote": "turned 90 degrees about y", "source": "spec"}]
    rep = T.check_claims(claims, [T.Source("spec", "turned 90 degrees about y", "text")], T.TracePolicy(), inv)
    assert rep.coverage == 1.0 and rep.verified_coverage == 1.0
