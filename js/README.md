# js/: x3dtrace in the browser

`x3dtrace.js` is a dependency-free port (ES2018, no DOM, about 680 lines) of the engine's core: FIND, COMPARE and the choice of one occurrence by prefix,
suffix and line. A page can use it to check a claim without a server. It is a port, not the engine: the check that matters for a record is the Python one.

```
node js/test_vectors.js js/vectors.json /tmp/disagreements.json    # exits 0; prints one line per family
python3 -I -B js/make_vectors.py src/ <dir with the corpus checkouts> tests/fixtures/trace_conformance.json out.json   # regenerates the full vector file
```

`vectors.json` holds 968 rows produced by running the Python engine (sha256 prefix in the file): all 135 GAIK-derived rows, 152 prose rows, 398 rows from real
scenes of the corpus and every fourth of 1,066 mutated rows. The port agrees with the engine on all 968 (the full set of 1,767 also agrees; the full file is
2.5 MB and is regenerated, not stored). Beyond the vectors: `fuzz_make.py` writes 30,000 random rows against the live engine (seeds 21 to 25 gave 0 disagreements other
than the field-locator class), and `diff_internals.py` checks the helpers (`\w`, `\d`, `\s`, case folding, digits, entities, rounding, the lexer) on every code point.

Not ported, and what happens instead:

| Left out | What the port does |
|---|---|
| Choosing between repeated quotes by the claim's `field` or node path (needs the scene index) | takes the first occurrence after the prefix, suffix and line hints; `findAll()` returns every span so a page can choose; 0 of the 1,767 vectors, about 1.1% of the fuzz rows |
| HTML5-only named entities (`&Acy;`) | decodes numeric entities and the 252 HTML 4 names; Python knows 2,231 |
| Code points that Python's Unicode 15.1 leaves unassigned | differ only there |
| Dates, boxes, XPath selection | dates are ported; boxes and XPath are not |

Both implementations share the open weaknesses in `docs/TRACE-REVIEW.md` (BUG-45: a vector is verified from numbers scattered through prose).
