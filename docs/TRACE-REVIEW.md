# x3dtrace: independent review

This is the record of an independent test of `src/x3dtrace.py`. The reviewer had the engine's stated intent (its module
docstring, the method description from the article, and notes on how GAIK behaves) and **not its code**, and wrote the tests
from that intent. The suite is `tests/test_x3dtrace.py` (1,204 tests plus the conformance rows in
`tests/fixtures/trace_conformance.json`). The first run, against the engine as first built, found **43 defects**; the engine
was then changed in response and the suite re-run. Reading the engine again for a JavaScript port, a scout reading a receipt format and a drill written for the guide found **six more** (BUG-45 to BUG-50 below): two are fixed, four are open. Everything below is graded Confirmed: each defect has a minimal
repro in the suite and was observed to fail and then to pass.

| Run | Engine sha256 (prefix) | Result |
|---|---|---|
| first build, as reviewed | `a3bff20178e3edf8` | 1,066 passed, 138 expected-failures (xfail), which map to 43 defects |
| after the first round of fixes | `f4dc93846bebe99c` | 1,066 passed, 5 xfailed, 133 xpassed (the 133 are tests for defects now fixed; their marks were then turned into labels) |
| the engine in this repository (also fixes BUG-47 and BUG-49) | `dcba70d739007c0d` | `tests/` as a whole, with the later findings added: 1,240 passed, 2 skipped, 10 xfailed, 15 xpassed (the 10 xfailed and the 15 xpassed are the tests of the open items below: the 15 are parameters of those tests that already pass) |

Python 3.13, one container, `python -I -m pytest tests -q -p no:cacheprovider`; timings are wall clock and carry the usual jitter.

How to read the marks: a test for a defect that has been **fixed** carries `@bug(n)`, which only labels it (marker `fixed`).
A test for a defect that is **still open** carries the same mark as `xfail(strict=False)`; the open ones are the set `OPEN` at the top of the
test file. A non-strict xfail that passes shows as XPASS, so a later fix is visible without editing the test.

Severity: HIGH = a wrong value gets `verified`, or one hostile input crashes or exhausts the process; MEDIUM = a wrong verdict in a
narrower case, a gap in tamper detection, or a super-linear cost; LOW = cosmetic, rare or fails closed. Labels: **code bug**
(the engine does something the intent does not allow) and **spec ambiguity** (the intent allows more than one reading).

## What is still open, and why it is left

Eight items stay open: four decisions or low-severity gaps, and four weaknesses found afterwards that are not yet fixed.

- **BUG-2 / BUG-9, the recorded policy** (decision). `recompute` replays a report under the policy recorded in it, so an edit of that policy is invisible to the replay. The caller passes the policy it trusts (`verify(..., policy=...)`); the engine does not guess. The rest of BUG-9 (honest reports made under a strict policy are no longer flagged) is fixed.
- **BUG-10, a shorter vector against a longer attribute** (decision). `2 2` is accepted for `scale="2 2 2"`. Fine for prose, wrong for an attribute copied from a scene. Left because the broadcast rule in the method notes allows it. No policy refuses it today (checked with the default and the strict policy).
- **BUG-18, suggest_claims cost** (low). About 4 to 6 seconds for 40 unsupported rows against a 422-byte prompt. `suggest_claims` is a convenience for people, not part of a check.
- **BUG-20, `round_to_printed` direction** (decision). The value `0.12` is accepted as exact for the quote `0.1`; the reverse reading (the quote rounds to the value) would refuse it. The documented behaviour is kept for the default policy (a printed zero no longer supports a non-zero value); the strict policy turns `round_to_printed` off, and then `0.12` against `0.1` is `check` (checked).
- **BUG-45, a vector read from scattered numbers** (a weakness, not fixed; found by the port to JavaScript). A vector is matched on *consecutive number tokens*, with any text between them, so `size 1 2 3` is `verified` by "1 apple, 2 pears and then 3 cows" and `size 10 20 30` by "page 10 of 20 in volume 30". The same engine accepts "5 m east and 7 m north" for `translation 5 0 7` as `reworded`, which is why a plain word-count limit is not the fix. The honest rule is that components spread over prose can reach `reworded` (Likely) and not `verified` (Confirmed); until it is built, treat a `verified` vector from *prose* as weaker evidence than one copied from a scene attribute. Positive controls that must stay `verified` are in the suite (`size 1 2 3`, `(1, 2, 3)`, `1 x 2 x 3`, `1, 2 and 3`). Confirmed (reproduced on the engine here).
- **BUG-46, a stray number blocks zero-fill** (low, errs on the safe side). "5 m east and 7 m north" is `reworded` for `translation 5 0 7`; with "the 2 pylons stand" in front it is `check`. A `check` is the conservative error.
- **BUG-47, a dotted version read as a date** (fixed here, found by a scout who read a receipt format). `version = "7.16.0"` used to verify the value `16.7.0`, because three numbers that could be day, month and year matched in any order; the same held for `5.8.4` against `4.8.5`. A dotted triple with no four-digit year is now a version and is compared as text, and a wrong one is `check`. `31.12.99` is no longer read as a date either (a conformance row records the difference from GAIK, and `11.04.2025` is still a date). Confirmed.
- **BUG-48, a leading `v`** (low, fails closed). The value `16.7.0` against the quote `v16.7.0` is `check`, because the `v` is glued to the digits in the lexer. Writers who copy exactly get `check` and re-quote; the fix is a version token in the lexer.
- **BUG-49, a field below a DEF did not pick the node** (fixed here, found while writing a drill for the guide). `//*[@DEF='BuoyC']/Shape/Sphere/@radius` named the right sphere but the engine used the first of three equal quotes, so the item was `verified` at the wrong line with `occurrences: 3` and no `disambiguated_by`. The three forms the guide uses (`DEF@attr`, an absolute XPath, `//*[@DEF=..]` with or without a path below it) now choose the node; a field that names no node still falls back to the first hit and the item says it is ambiguous (the strict policy turns that into `check`). Confirmed.
- **BUG-50, coverage counts only the inventory form of a field** (medium, not fixed; found while writing a drill). `coverage` and `verified_coverage` compare each claim's `field` with the strings `inventory` writes (`/X3D/Scene/Transform[@DEF='Pier3']/@rotation`). A claim written as `//*[@DEF='Pier3']/@rotation` or `Pier3@rotation` is checked and traced but not counted, so a run whose claims all use the shorter form reads as 0 coverage. Four claims on a four-attribute scene gave coverage 1.0 and verified coverage 0.5 in the inventory form, and 0.5 and 0.0 with two of them in the DEF form. Write `field` as the inventory XPath when coverage matters; `scene_evidence` in x3d_mcp normalises the field itself. Confirmed.

## The defects

| Bug | Severity | Label | What | Tests | On the engine here |
|---|---|---|---|---|---|
| BUG-1 | HIGH | code bug | Non-finite or overflowing numbers in a scene attribute make check_claims raise | 6 | fixed |
| BUG-3 | HIGH | code bug | SFRotation: the opposite rotation is verified (axis flipped, same angle) | 2 | fixed |
| BUG-6 | HIGH | code bug | Deep nesting: RecursionError in the box walk, O(depth^2) path memory | 4 | fixed |
| BUG-8 | HIGH | code bug | A non-finite or huge world box makes _locus raise (int(round(nan))) | 3 | fixed |
| BUG-10 | HIGH | code bug | A vector matches a non-contiguous subsequence of the quote's numbers | 6 | open 1/6 |
| BUG-11 | HIGH | code bug | Unit conflicts are not applied to vector components (a 2 ft cube verified in a metre scene) | 4 | fixed |
| BUG-43 | HIGH | code bug | USE expansion bomb: nested DEF/USE doubling makes the box walk exponential | 1 | fixed |
| BUG-44 | HIGH | code bug | A quote number beyond float range (1e999) makes the colour comparison raise OverflowError | 3 | fixed |
| BUG-25 | MEDIUM-HIGH | code bug | One odd claim aborts the whole batch | 8 | fixed |
| BUG-2 | MEDIUM | code bug | recompute() does not compare document, page, cited_page, record, rects, value_rects, hints, schema | 9 | open 1/9 |
| BUG-4 | MEDIUM | code bug | Zero-fill is applied although the quote states every component | 6 | fixed |
| BUG-5 | MEDIUM | code bug | SceneIndex construction is quadratic in the number of un-DEF'd siblings | 1 | fixed |
| BUG-9 | MEDIUM | code bug | recompute() ignores the policy recorded in the report | 3 | fixed |
| BUG-12 | MEDIUM | code bug | The degrees-for-radians guard of SFRotation is bypassed through zero-fill and carries no note | 2 | fixed |
| BUG-13 | MEDIUM | code bug | A colour name that contradicts the value gives 'unchecked' (fails open) | 4 | fixed |
| BUG-14 | MEDIUM | code bug | A wrong number WORD gives 'unchecked' instead of 'check' (fails open) | 4 | fixed |
| BUG-15 | MEDIUM | code bug | The preposition 'in' counts as a unit (inch) and turns a correct value into a mismatch | 3 | fixed |
| BUG-16 | MEDIUM | code bug | Disambiguation by path or line costs O(candidates x document) | 1 | fixed |
| BUG-17 | MEDIUM | code bug | A long prose quote is quadratic in quote_numbers | 1 | fixed |
| BUG-26 | MEDIUM | code bug | Dates: parts are matched as a set (a repeated number is reused) | 3 | fixed |
| BUG-29 | MEDIUM | code bug | A percentage is verified for a 0..1 field (transparency 50 by '50 %') | 1 | fixed |
| BUG-37 | MEDIUM | code bug | recheck() of a float-list claim replays as unchecked | 1 | fixed |
| BUG-38 | MEDIUM | code bug | Source.meta can overwrite id, kind, sha256 and bytes in Source.info() | 4 | fixed |
| BUG-41 | MEDIUM | code bug | target.scene_value is 'match' when the claimed value is only part of the scene attribute | 4 | fixed |
| BUG-19 | LOW-MEDIUM | code bug | The encoding of the XML declaration is honoured for str input | 4 | fixed |
| BUG-23 | LOW-MEDIUM | code bug | Line hint: ties and lines that match nothing are reported as 'disambiguated_by line' | 3 | fixed |
| BUG-24 | LOW-MEDIUM | code bug | status no_text_layer is never produced; a quote with no source is labelled no_quote | 3 | fixed |
| BUG-28 | LOW-MEDIUM | code bug | Combining marks of Indic, Hebrew, Thai and Arabic split words | 4 | fixed |
| BUG-31 | LOW-MEDIUM | code bug | A claim whose source id names no source silently uses the first source and is reported as 'found' | 1 | fixed |
| BUG-33 | LOW-MEDIUM | code bug | LOD: only the first level is boxed | 1 | fixed |
| BUG-35 | LOW-MEDIUM | code bug | Space-grouped thousands are read only as exactly two groups with a plain space | 6 | fixed |
| BUG-39 | LOW-MEDIUM | code bug | canonical_json writes NaN/Infinity; claims_sha256 hashes raw Python values | 6 | fixed |
| BUG-18 | LOW | code bug | suggest_claims costs about 0.1 to 0.4 s per row | 1 | open 1/1 |
| BUG-20 | LOW | spec ambiguity | round_to_printed accepts a value MORE precise than its quote as an exact match | 4 | open 2/4 |
| BUG-21 | LOW | code bug | locus.attr is None when the quote starts at the attribute name | 2 | fixed |
| BUG-22 | LOW | code bug | The [USE=name] path segment is dead code | 1 | fixed |
| BUG-27 | LOW | spec ambiguity | Detached minus: -5 is verified by 'pages 3 - 5' | 1 | fixed |
| BUG-30 | LOW | code bug | Any bare 6-hex-digit word is read as a hex colour | 1 | fixed |
| BUG-32 | LOW | code bug | Path hint matches by endswith without a segment boundary | 1 | fixed |
| BUG-34 | LOW | code bug | rad2deg conversion fails for integer degrees from a rounded radian quote | 1 | fixed |
| BUG-36 | LOW | code bug | A list of more than 64 numbers never matches its verbatim quote | 9 | fixed |
| BUG-40 | LOW | code bug | CLI: input errors end in a traceback with exit code 1 (the code for 'some claims need a look') | 4 | fixed |
| BUG-42 | LOW | spec ambiguity | The summary does not count claims whose value the target scene does not hold | 1 | fixed |
| BUG-45 | HIGH | code bug | A vector is verified from consecutive numbers with unrelated words between them | 2 | open 2/2 |
| BUG-46 | LOW | code bug | A stray number in the quote blocks zero-fill | 1 | open 1/1 |
| BUG-47 | HIGH | code bug | A dotted version is read as a date, so any permutation verifies | 3 | fixed |
| BUG-48 | LOW | code bug | A version with a leading v reads as a mismatch | 1 | open 1/1 |
| BUG-49 | MEDIUM | code bug | A field naming a path below a DEF did not choose between repeated quotes | 5 | fixed |
| BUG-50 | MEDIUM | code bug | Coverage counts a claim only when its field is the inventory XPath | 1 | open 1/2 |

BUG-7 (`canonical()`/`sha256()` raised on a `Decimal` and could write `NaN` into a report) was found in the first build and fixed by the engine's own next revision; its regression tests stay.

## Questions the review left open

These are the places where the intent allows more than one reading. They are decisions for the owner, and none has a test marked as a defect unless it is listed above.

- **round_to_printed** (BUG-20): 'value rounds to the quote' versus 'quote rounds to the value'. v3: `0.0` supports 0.04. v5: a printed zero no longer does; `0.1` still supports 0.12 and 0.14 (documented).
- **Detached minus** (BUG-27): a typographic minus and a range dash look the same (`pages 3 - 5`). v5 rule: a digit just before the dash means a range; `temperature - 5` is still read as -5.
- **A shorter vector against a longer attribute** (BUG-10, last repro): `2 2` is accepted for `scale="2 2 2"`. Fine for prose, wrong for an attribute copied from a scene.
- **Recorded policy as a trust input** (BUG-2 / BUG-9): replaying under the recorded policy cannot detect an edit of that policy; the caller must pass the policy it trusts.
- **Dates**: the ISO year/day swap and set-membership reading were kept from GAIK; BUG-26 only stops reuse of one token.
- **Coverage** counts a fabricated quote (status `not_found`) as 'cited'; `verified_coverage` is the number to trust. Intended (GAIK parity), but easy to misread.
- **Booleans**: a Python `True` against the quote `TRUE` is `unchecked`, never `verified`; X3D's SFBool is TRUE/FALSE, so a writer's natural JSON `true` can never be verified.
- **suggest_claims** hard-codes `source='prompt'` and, because of broadcast, a lone `2` anywhere in the prompt supports a size of `2 2 2` (an upper bound, as documented).
- **unit_scale** (`<unit category='length' conversionFactor=...>`) is parsed but not applied to `TracePolicy.length_scale` automatically; the caller must copy it.
- **CLI** has no `--target`, so the scene-side check cannot be used from the command line.
- **Tokenisation of `1.2.3` / `v1.2.3`** and of `ISO dates in prose` follow the number-aware lexer; not tested as defects.

## Mistakes the reviewer made, found and fixed

Listed so a reader can tell a test mistake from an engine defect. Each was a wrong expectation in the suite, not a change to the engine.

- Round-trip property of the lexer was too strict (`50<Arabic letter>` splits when re-lexed alone): relaxed to compare the joined re-lexed tokens.
- `(3.14159265, '3.1416')` was wrongly expected to mismatch although round_to_printed documents it: row changed to `3.1417`.
- `x-rot-6` expected `mismatch`; the quote has no number, so `unchecked` is right. `x-rot-7` XPASSed and left the known-bug table. `1 234,50` moved to the BUG-35 test.
- Two entries of the MALFORMED list (an external-entity DOCTYPE and `<a:b xmlns:c='d'/>`) are well-formed: removed.
- The first BUG-8 'leak' test passed for the wrong reason (the quote was in a different Shape): replaced by `test_a_quote_inside_a_hostile_element_still_reports`.
- `pytest.xfail()` calls made tests unconditionally xfail; replaced by marks (`xfail(strict=False)`), so a fixed bug shows as XPASS.
- `5e-324` against `0` is `verified` by the absolute tolerance 1e-6, as documented: row removed from the extreme-number test.
- The XXE test looked for the secret marker in a report that echoes the writer's own quote; it now checks `status == not_found` for the marker quote and the marker's absence from a report that does not quote it.
- Timing ratio tests were flaky at millisecond scale: a 0.02 s floor, best of two for the small size, threshold 7 (linear is about 4 to 5, quadratic about 16).
- A memory test read `ru_maxrss` in a subprocess; Linux carries the parent's high-water mark across fork+exec, so it failed for the wrong reason in a big pytest process: replaced by `tracemalloc`.
- `1 2 3` against `1 2` as a target claim and a lone `2` from `1 2 4` in suggest_claims are allowed by the broadcast rule of the notes; the tests were adjusted (see the BUG-41 note and Spec ambiguities).

## Reproduce

```
python3 -I -m pytest tests/test_x3dtrace.py -q -p no:cacheprovider -rxX
X3DTRACE_PERF_LOG=/tmp/perf.json python3 -I -m pytest tests/test_x3dtrace.py -q -p no:cacheprovider   # also writes the timings
```

`tests/fixtures/make_trace_conformance.py` regenerates the conformance rows from a checkout of the GAIK toolkit (MIT; `NOTICE-x3dtrace.md`); the tests read only the JSON.
