# Scientific Visualization Integration v2

Private additive review of the Blender scientific-visualization knowledge base,
its 27 bridge proposals and the actual archived kits. Open
**[docs/Integration-Atlas.html](docs/Integration-Atlas.html)** directly in a browser.
It is self-contained, includes the full review and technical appendices, and
makes no network requests. External references open only when selected.

The original three documents, raw workflow and 439 archived files are unchanged.
The private patch adds this package under `docs/blender-scivis-expert/v2/`, plus
a one-line `src/x3dprov.py` repair and its five regression tests. No remote
commit, push, public publication or paid model experiment was performed.

## Read

- [Integration review](docs/INTEGRATION-REVIEW-v2.md): taxonomy, architecture,
  ontology hooks, measured findings and prioritized future work.
- [Bridge audit](private/BRIDGE-AUDIT.md), [full historical catalog](private/bridge-catalog.json)
  and [current-pass overlay](private/pass-updates.json).
- [Kit salvage](private/KIT-SALVAGE.md) and [439-file inventory](private/kit-inventory.json).
- [21 knowledge corrections](private/KB-v1.2-CORRECTIONS.md).
- [Actual native Blender 5.3 results](private/native53/NATIVE53-RESULTS.md).
- [Independent review and resolution](private/INDEPENDENT-REVIEW.md).

Historical claims retain their original grades and objections. New native-splat,
precision and provenance results have separate receipts and limited scope. A
passing probe that deliberately reproduces a transform loss is not a statement
that the transform preserves the scene.

## Use the adapters

The inventory adapter requires only Python 3.12+ and the standard library;
Python 3.13 was also tested. The provenance adapter needs `lxml` and the original
Research Loom distribution to recheck its external files.

```sh
python3 -m unittest discover -s integration/tests
python3 -O -m unittest discover -s integration/tests
python3 -m pip install lxml
python3 -m unittest discover -s adapters/tests
python3 -O -m unittest discover -s adapters/tests
```

To rebuild the delivered inventory against your current local files:

```sh
python3 integration/inventory.py import-research-loom \
  --study /path/to/x3d.STEM/studies/research-loom \
  --historical-notes inputs/FLYWHEEL-SYNERGY-v1.md \
  --private-workspace . \
  --output integration/examples/research-loom-inventory.jsonld \
  --bridge-map integration/examples/bridge_map.json

python3 integration/inventory.py verify integration/examples/research-loom-inventory.jsonld \
  --root stem_repo=/path/to/x3d.STEM \
  --root review_inputs=inputs \
  --root private_workspace=. \
  --output integration/examples/current-bindings.json
```

The `inputs` file is an exact copy of the original private source, included so
the example locator works without the temporary upload filename. Larger Research
Loom packets, renders and exports remain external; the inventory names and hashes
them instead of duplicating that project. Missing or changed files fail binding
verification. A previous inspection is not evidence about bytes edited later.

See [inventory usage](integration/README.md), [data model](integration/DATA-MODEL.md),
[one-oracle exercise](integration/ONE-ORACLE.md) and
[figure linkage](adapters/README.md). The adapters execute no old kit or model API.

## Reproduce the new Blender controls

The precision and native-splat folders contain their Python sources, tiny
fixtures, `.blend` files, field-level results and commands. Supply the named
Blender binary and, for the native fork round trip, the pinned add-on checkout.
The official Blender executables and downloaded archives are excluded from
this bundle. The existing native X_ITE browser limitation remains explicit;
the new splat test establishes structural/data behavior rather than pixels.

## Ontology and document tooling

```sh
python3 -m pip install -r requirements-review.txt
python3 ontology/check_graph.py
python3 docs/plot_precision.py
python3 docs/build_atlas.py
```

The semantic tooling validates local JSON-LD/SHACL metadata and a deliberately
malformed SHA control. It does not certify scientific truth or rights. The atlas
builder reads retained data; it does not run Blender or regenerate science.

The `private/build_*`, `write_corrections.py` and archive-audit scripts are
retained research/build notes. Some expect this review's original workspace
layout. They are separate from the portable adapters; inspect their inputs
before adaptation, as documented in the salvage review.

## Apply the private patch

Patch base: `hagopjay/x3d.ml@c1634f5c4f29c4220a092510807a430ce4cbfd2e`,
branch `claude/project-thread-0lc3kd`.

```sh
gzip -dk Blender-Scientific-Integration-v2.patch.gz
git apply --check Blender-Scientific-Integration-v2.patch
git apply Blender-Scientific-Integration-v2.patch
```

The targeted provenance-only patch is also supplied for separate review. It
reuses the archived literal-replacement repair, preserves the current protocol
and leaves the historical kits unchanged. Keep this material private. Generic
fixtures or code can be prepared as separate public-safe proposals later.
