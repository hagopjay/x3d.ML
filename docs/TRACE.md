# x3dtrace: a quote beside every value

`x3dprov` (docs/DESIGN.md) records what ran on a scene. It does not say where a number in the scene came from. `x3dtrace` closes that gap
one value at a time: whoever put a value into a scene (a model, a tool, a person) also copies the **exact quote** it read the value from,
and plain code, with no model call, answers three questions.

| Step | Question | How |
|---|---|---|
| FIND | Is the quote in the source? | an unbroken run of whole tokens; numbers keep sign, decimal point and exponent |
| COMPARE | Is the value in the quote? | numbers as numbers, vectors per component, colours, angles, units, words |
| LOCATE | Where is it? | character span, line and column, W3C selectors; for a scene also the node path, the DEF path and the world-space box |

The verdicts are `verified`, `check`, `reworded`, `unchecked`. The method, the four verdict names and the report field names come from
Umair Ali Khan's article "How I Added Traceability in Structured Data Extraction with AI" and his MIT toolkit GAIK; see
[NOTICE-x3dtrace.md](../NOTICE-x3dtrace.md) for the credit and for every place this code deliberately differs.

## Quick start

```
python3 src/x3dtrace.py inventory scene.x3d                      # every value-bearing attribute with its XPath
python3 src/x3dtrace.py check claims.json --source spec=spec.txt  # exit 1 if any value is check or unchecked
python3 src/x3dtrace.py suggest scene.x3d prompt.txt             # lexical first guess (an upper bound, not a model)
```

`claims.json` is a list of `{field, value, quote, source}`. `field` is an XPath 1.0 into the scene; write it the way `inventory` prints it,
for example `/X3D/Scene/Transform[@DEF='Pier3']/@rotation`. That form picks the node, and it is the only form `coverage` counts (BUG-50 in
[TRACE-REVIEW.md](TRACE-REVIEW.md)). `//*[@DEF='Pier3']/@rotation`, with or without a path below the DEF, also picks the node. `source` names
one of the `--source` files.

```python
import x3dprov as P, x3dprov_trace as T, x3dtrace as X

xml = P.add_step(scene, {"op": "generate", "input_sha256": "none"}, scene)
claims = [{"field": "/X3D/Scene/Transform[@DEF='Pier3']/@rotation", "value": "0 1 0 1.5708",
           "quote": "90 degrees about the vertical axis", "source": "spec"}]
xml, sidecar, report = T.trace_claims(xml, claims, {"spec": spec_text})
T.audit_trace(xml, {"spec": spec_text}, scene=True)     # {"ok": True, "status": "verified", ...}
```

`trace_claims` appends one `trace` step to the scene's own `<head><meta>` record. The step does not change the scene
(`input_sha256 == output_sha256`), and a `summary` step follows it so the trace has a successor in the hash chain.

## What COMPARE accepts

A conversion is accepted only when the quote itself carries the evidence, and the item records it in `derivation`.

| Quote says | Value is | `derivation` |
|---|---|---|
| `90 degrees` | `1.5708` (radians) | `deg2rad` |
| `3,5 m` or `3.5 m` | `3.5` | none: both notations are read, in prose sources only |
| `50 %` | `0.5` | `percent` |
| `#ff0000`, `rgb(255, 0, 0)`, `red`, `grey` | `1 0 0`, `0.5 0.5 0.5` | `hex`, `rgb255`, `colorname:red` |
| `2 ft` with a scene unit in metres | `0.6096` | `unit:ft` |
| `three` | `3` | `numword` |
| `radius 2` for a vector size | `2 2 2` | `broadcast` |
| `vertical axis, 90 degrees` | `0 1 0 1.5708` | `axis:vertical`, `deg2rad` |

Without that evidence the verdict is `check`: `1.5708` against a quote that says only `1.57` is `verified` (it is the rounded display), but
`1.5708` against `90` is `check` because nothing in the quote says degrees. A sign, a decimal point and an exponent are part of the number, so
`-1` does not match `1` and `1e-5` is one number. A vector is compared component by component in order, so `1 2 3` does not match `3 2 1`.
In a scene source identifiers (DEF names) are case-sensitive; in prose words are casefolded. A dotted version such as `16.7.0` is a version, not
a date: it is compared as text, so `7.16.0` is `check` (BUG-47, fixed). `11.04.2025` is still read as a date.

## Where a quote sits

Every item carries W3C Web Annotation selectors: a `TextQuoteSelector` (exact, prefix, suffix), a `TextPositionSelector` (start, end) and,
for a scene, an `XPathSelector`. A quote that occurs more than once (the usual case in a scene: the same `size="1 1 1"` appears on many
shapes) is resolved in this order: an explicit `prefix` and `suffix`, an explicit `path`, then the node named by the claim's `field`, then
`line`. `occurrences` says how many times it was found and `disambiguated_by` says which hint chose. The summary counts `ambiguous` items:
found more than once and nothing chose between them.

For a scene, `locus` holds the line and column, the node and its path, the DEF, the attribute and the world-space axis-aligned box
(`aabb_e6`, integer millionths of a scene unit; one box per USE instance; `aabb_owner` says which ancestor the box belongs to).

## The record

One `trace` step: `engine`, `sources` (id, kind, sha256, bytes, name), `claims_sha256`, `report_sha256`, `summary`, `policy`, and `items`.
Items are inline up to 64 KiB of canonical JSON, otherwise in a sidecar named by `report_sha256`. Everything that is hashed holds only text,
integers and booleans (no floats, no integers beyond 2**53), so a Python and a JavaScript implementation hash the same bytes; a float value
travels as its shortest text.

## Checking a trace later

`audit_trace(xml, source_texts)` runs `verify()` and then, for each trace step: the step did not change the scene; the items hash to
`report_sha256` and their claims to `claims_sha256`; every supplied source still hashes to its recorded sha256; no field is traced twice;
`scene=True` additionally requires each XPath `field` to resolve to exactly one node whose text equals the value; and the whole check is
**re-run** against the sources and compared item by item (verdict, status, span, derivation, locus, selectors). Because the verdicts are
recomputable, a flipped verdict is caught even in the last step of the chain, where `verify()` alone cannot see it (DESIGN.md section 3, limit 1).

## Views

`x3dprov_provo.py` maps a trace to PROV-O: each source is a `prov:Entity`, each quote a `prov:Quotation` (`prov:wasQuotedFrom`), its place a
`prov:Location` carrying `oa:start` and `oa:end`, each value an entity derived from its quote. `prov:hadPrimarySource` is not asserted: a verified
quote is the right words, not proof it is the right place. `x3dprov_openlineage.py` emits the `ColumnLineageDatasetFacet` (1-2-0) on the scene
dataset: output field = the scene field, input field = the source and the selector, `DIRECT` with subtype `IDENTITY` or `TRANSFORMATION`. Edges
are drawn only for `verified` and `reworded` values, so the lineage graph shows an evidence gap and never an unproven edge.

## Limits

* `verified` means the quote exists and holds the value. It does not mean the quote is the right place, or that the value is true (GopherCite's
  caveat: not all claims supported by evidence are true).
* A writer must copy the quote exactly. A paraphrase is `check`.
* The record is unsigned. A forger who rewrites the last steps of the chain consistently, including claims and report, produces a different but
  honest-looking trace. Only an external anchor (a signature, a commit, C2PA) binds a trace to a time and an author.
* Claims are about one scene version. A later `transform` step changes the hash, and the claims stay about the earlier version.
* Text has no box. Shapes built from Text, Extrusion or NURBS have no world box, and a shape under an unselected Switch child is not rendered, so it has none either.
* Scans and images have no text layer: nothing to FIND.
* A vector read from prose is matched on consecutive number tokens with any text between them, so `size 1 2 3` is `verified` by "1 apple, 2 pears
  and then 3 cows" (BUG-45, open). Treat a `verified` vector from prose as weaker evidence than one copied from a scene attribute.
* `coverage` and `verified_coverage` count a claim only when its `field` is the inventory XPath (BUG-50, open). `verified_coverage` is the number
  to read: a fabricated quote still counts as cited.
* A shorter vector (`2 2`) is accepted for a longer attribute (`2 2 2`), and `round_to_printed` accepts `0.12` for the quote `0.1`; the strict policy
  turns the second off (BUG-10, BUG-20, decisions).
* A quote inside an XML comment or a CDATA section counts as found when the scene is the source; the item's `locus.attr` is empty in that case.
* Eight review findings are open in all; each has a test that passes when it is fixed. See [TRACE-REVIEW.md](TRACE-REVIEW.md).
