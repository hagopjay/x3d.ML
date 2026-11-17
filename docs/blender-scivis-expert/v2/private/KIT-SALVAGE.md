# Private archive audit and recovery map

This audit inspected `hagopjay/x3d.ml`, branch
`claude/project-thread-0lc3kd`, at commit
`c1634f5c4f29c4220a092510807a430ce4cbfd2e`. The archived prefix is
`docs/blender-scivis-expert/`. All three supplied attachments are byte-identical
to the corresponding files at this revision. The knowledge files therefore
agree with the inspected branch; they are not three newer competing editions.

The result is a **usable prototype archive with incomplete experimental
payloads**. The archive saves enough code and small outputs to recover several
valuable tests, but it is not an installed toolchain or a replayable benchmark.
No archived Python or shell kit was imported or executed in this audit.

## What is actually preserved

`kit-inventory.json` inventories every tracked file with its relative path,
slice, bytes, SHA-256, Git blob identity, extension and a proposed salvage
action. It also records static Python dependencies, path literals and review
leads. The snapshot contains **439 files / 4,583,862 bytes**:

| Kind | Files | Interpretation |
|---|---:|---|
| Python | 217 | Experimental scripts, reference helpers, a patched add-on source copy and small probes |
| X3D | 126 | Bounded fixtures, exported snapshots, provenance examples and intentionally problematic scenes |
| Markdown | 74 | Knowledge, handoffs and mostly documentation-only dependency snapshots |
| JSON | 13 | The raw workflow, small result reports and external-corpus manifests |
| Shell | 5 | Environment-specific launchers; not a portable workflow |
| PLY | 3 | Two 2,000-splat synthetic inputs plus a four-splat SH3 probe |
| Patch | 1 | Existing scientific semantic-check proposal |

There are **no PNG, EXR, JPEG, `.blend`, SPZ, SOG, OpenVDB or JSONL files** in
this prefix. This is a statement about the archived folder, not every other
branch or project. In particular, the 111-entry candidate Tier A JSON contains
external absolute paths and metadata; it does not contain 111 scene bodies.

| Slice | Files | Most useful retained material |
|---|---:|---|
| `blender-io` | 44 | Twenty-six small fixtures and import/export probes |
| `splat-trailer` | 22 | Splat reference functions, deterministic generator, round-trip script, 2,000-splat report and three PLY inputs |
| `hall-build` | 60 | Color charts, transparency/light/order fixtures, animation freezer and render/compare recipes |
| `ontology` | 65 | Coordinate/unit/default/containment/contact/HAnim probes and selected X3D fixtures |
| `x3d-mcp-fork` | 31 | Guard pieces, scientific checks and the existing patch proposal |
| `x3d-ml` | 72 | Provenance source copies, round-trip/figure prototypes, selected results and ecosystem-watch recipe |
| `spine` | 35 | External-corpus manifests, survivor statistics, selected splat fixtures and worker/driver prototypes |
| `demos-heritage` | 43 | A complete prototype `patched_src` copy, color fixtures and integration scripts |
| `dspy-redteam` | 19 | Blender probes and sixteen exported-scene validation results |
| `agentics` | 13 | The separate source-loss audit / provenance prototype and retained snapshots |
| `compression` | 14 | Size/wall/slab experiments and reference fidelity scripts |
| Other kit slices | 16 | `b02`, `b17`, `langgraph-flywheel`, `lens-b05`, `rules-b03`, `vision` |
| Knowledge/workflow | 5 | Three knowledge documents, README and raw workflow |

The two large synthetic PLY files have literal binary-little-endian headers:
`synth_sh0_2000.ply` has 17 float32 fields per vertex (68 payload bytes), and
`synth_sh1_2000.ply` has 26 fields (104 bytes). The SH3 four-splat input has 62
float32 properties (248 bytes), including three normal placeholders. These
headers can be inspected now. The SH2/SH3 2,000-splat inputs and the rendered
SH0–SH3 comparison images are not present, although the historical report
contains rows for all four SH degrees.

## B24: what rescue already accomplished

The October rescue was real for source and small reports. Repeating a broad
"copy the scratch scripts" task would duplicate preserved work. `ref_render.py`,
`cmp_png.py`, `rt_test.py`, `rt_test_lib.py`, `fixture_gen_sh3.py`, the B09 patch,
guard pieces, chart2, alpha, plight, sort fixtures and color-test scripts are
already in Git. Their exact current archive identities are now inventoried.

Rescue is still incomplete for independent replay:

| Missing item or class | Consequence | Recovery action |
|---|---|---|
| `fx3`–`fx5` reference/X_ITE image sets, `pix_0.exr`, `pix_1.exr`, figure PNG/EXR and native `.blend` files | Historical PSNR, rendered-color and image-determinism claims cannot be remeasured from this prefix | Recover original bytes from their actual owner, or regenerate as a new run with new identities; do not relabel regeneration as the old run |
| `snapshot_v1.jsonl`, `layout_v1.json`, `nodebag_v1.npz`, corpus scene bodies and prompts JSONL | Corpus size/quality claims and the 111-item list are not an executable local benchmark | Materialize a licensed, hash-bound subset and an explicit membership manifest |
| Sphinx real PLY and `real_sphinx_mesh.json`, full ordering/slab result tables | Real-scene alpha clamp losses and view-dependent ordering comparisons remain historical claims | Recover the exact asset and receipt, including field semantics and camera poses |
| Full validator/add-on sources at the cited historical commits | `import` paths in old scripts point to absent implementations | Resolve exact repository + commit pairs; archived README copies are not installed dependencies |
| Original runtime/build packages and Python environments | A version string inside JSON is insufficient to recreate ABI and renderer behavior | Write a fresh environment manifest, then execute a new run against explicit binaries |

The updated B24 is therefore **inventory, recover missing payloads, and freeze a
new baseline before changing the importer**. The first two parts of that state
must be tracked independently: source archive complete for these 439 files;
render/corpus/toolchain payload recovery incomplete.

## What the raw 52-agent result establishes

The 651,632-byte JSON has 14 reader digests, a catalog of 18 bridges, 18 verified
bridge rows containing 36 verifier verdicts, and a critic with 11 missing-link
items, 19 overclaim items and ten suggested entries. Nine suggested entries are
the real B19–B27 bridges; the tenth is a rule-hygiene note.

The reported 52-agent arithmetic is consistent with 14 readers + one
synthesizer + 36 verifier reports + one critic. The JSON stores their texts; it
does not include provider execution receipts or proof that those reports were
independent executions. Its lower historical grades are 13 Likely, four
Suspected and one Confirmed. These remain **source-reported grades**, not fresh
confirmations made by this audit. In particular, a verifier's `ok: true` can
coexist with numerous problems and a downgrade.

The raw workflow is valuable as a research log and structured hypothesis bank.
It should not be used directly as a green capability registry. Preserve each
critic correction alongside the original pass criterion instead of extracting
only the synthesizer's headline numbers.

## Adopt, adapt, preserve, and retire

| Action | Exact entry points | Required next step and boundary |
|---|---|---|
| Reuse as fixture inputs | `kits/blender-io/fixtures/pointset_color.x3d`, `pointset_colorrgba.x3d`, `ils_color.x3d`, `lineset_color.x3d`, `unit_km.x3d`, `coordinatedouble.x3d` | Run against the exact current add-on and validators; compare values/topology/units, not object counts alone. Extend the current Research Loom mixed-geometry controls rather than making another scatter tool. |
| Recover the splat ladder | `kits/splat-trailer/work/rt_test.py`, `rt_test_lib.py`, `export_splats_ref.py`, `fixture_gen_sh3.py`, `ref_render.py`, `cmp_png.py` | Replace scratch paths with CLI inputs, pin add-on code, produce fresh SH0–SH3 inputs and actual alpha-space errors. Existing report is historical N=2,000; a different seed/count is a different fixture. |
| Merge guard and source audit deliberately | `kits/x3d-mcp-fork/work/guard.sh`, `bl_phase.py`, `gate.py` plus `kits/agentics/blender_lane_probe.py::loss_audit` | Source audit is a separate prototype. Export a declarative loss-rule table consumed by the existing guard/Playground owner; retain distinct warnings, refusals and errors. Audit before export so deleted features remain observable. |
| Rebase an existing proposal | `kits/x3d-mcp-fork/work/sci-semantic-checks.patch`, `sci_checks.py`, `run_probes_sci.py` | Compare rule IDs and present implementation before applying; restore explicit paired good/bad cases. Do not describe eleven emitted IDs as twelve independent tested rules. |
| Reuse look-test inputs and redesign runner | `kits/hall-build/chart2/chart2.x3d`, `alpha/`, `plight/`, `sorthaz/`, `src/chart_compare.py`, `src/measure_chart.py` | Freeze before-fix inputs first; record camera/light/color/view-transform/renderer settings per row class. Regenerate missing image pairs; do not carry old numeric thresholds as established current results. |
| Extend structural animation coverage | `kits/hall-build/src/freeze_x3d.py`, `kits/blender-io/fixtures/interp.x3d`, `kits/x3d-mcp-fork/work/anim_probe.py` | Add fixed-fraction value oracles and per-ROUTE endpoint correspondence. A higher ROUTE count does not establish retained animation. |
| Reuse ontology questions and fixtures | `kits/ontology/work/rig_from_uom.py`, `uom_containment.py`, `roundtrip_probe.py`, `unit_import_probe.py`, `defaults_probe2.x3d` | Resolve original ontology/XSLT/SHACL dependencies. Distinguish legal X3D containment from meaningful physical or anatomical modeling. |
| Extend the existing provenance owner | `src/x3dprov.py`; `kits/x3d-ml/t2_roundtrip.py`, `t4_render_stamp.py`, `t4b_repro.py`, `stage3_figure.py` | Keep the existing chain protocol; add explicit hash-method and asset bindings through an adapter/proposal. Reproduce escaped JSON behavior and figure bytes before adopting. |
| Preserve as historical result | Thirteen JSON documents listed in the inventory | Link each report to its archived bytes, declared pins and missing dependencies. A retained report is inspected evidence about an older execution, not a new run. |
| Preserve as design smoke test | `kits/langgraph-flywheel/t.py` | It increments an integer to three using MemorySaver. It provides no writer/export/validator/render integration and no process-kill recovery. Replace it with a thin adapter to the actual existing workflow; do not promote the counter to production orchestration evidence. |
| Keep prototype patch source for comparison | `kits/demos-heritage/patched_src/` | Diff selected behavior against the intended current add-on revision. Do not silently vendor this entire unpinned snapshot as a second maintained exporter. |
| Retire from operational paths | Hardcoded scratch environment paths, empty dependency shells, basename-only asset matching and unchecked narrative pass criteria | Keep their historical documentation; new runners need explicit roots, exact hashes, outputs and refusal semantics. |

## Portability findings from static inspection

All 217 Python files parse under the audit interpreter; this is syntax
inspection, not a compatibility or execution claim. Forty-five distinct
absolute path literals point principally to October scratch and
`/mnt/project-files` layouts. Many scripts create files, reset Blender state,
parse CLI arguments or dynamically load dependencies at module scope.
Importing them as orchestration nodes can therefore execute a whole experiment
or fail before a node has been called.

The scanner labels candidate operations with their line numbers and whether
they occur syntactically outside a function. This includes code inside
`if __name__ == '__main__'` and other conditional blocks, so that flag is a
review lead rather than proof of import-time execution. The scan found 11
process-launch call sites, ten dynamic-code/import call sites and two direct
network candidates. These are expected ingredients in experimental scripts;
they explain why adaptation must precede execution. Examples include `eval`
of data fields in `kits/compression/splatfid/{abl,fid}.py`, module-level
`exec_module` in Blender probes, CLI parsing in guard phases, `ffmpeg`
subprocesses in `never_black.py`, a `curl` fetch in `fetch_hanim.py`, and
networked texture loading in the archived importer.

There are **27 documentation-only dependency directories** resembling add-on,
validator or renderer checkouts. They contain README/contribution/release-note
files without executable source. Their names are historical context, not a
dependency lock. The one complete `patched_src` prototype is a separate case.

## A concrete provenance defect worth carrying forward

`src/x3dprov.py` is byte-identical to `kits/x3d-ml/x3dprov.py`, SHA-256
`74746444c0093a72636686fa325da5950802d860861e61a859ed1c0ba78cedae`.
The alternative `kits/x3d-ml/xprov/x3dprov.py` has SHA-256
`922d45c1ede366b634247d26c1a4de23c007460b83e09603cd9f3583936de661`.
Besides documentation, the second copy contains a meaningful callback change:

```python
# src: replacement text interprets regex backslash escapes
re.sub(r"</head>", metas + "</head>", xml, count=1)

# archived variant: callback inserts JSON-bearing metadata literally
re.sub(r"</head>", lambda match: metas + "</head>", xml, count=1)
```

`x3dprov-escape-microreproducer.json` records a fresh standard-library
reproduction of that replacement-expression behavior, without importing the
old module. A valid JSON detail containing a newline and a Windows path is
corrupted by the replacement-string operation; the callback preserves its JSON
semantics. This supports a small regression test and private fix proposal to
the existing provenance owner. It does not establish that every x3dprov path
has been tested. The useful correction was already latent in the archive.

Keep four identities distinct when integrating figure chains: original file
bytes, parsed/canonical X3D content, scientific arrays, and decoded pixels.
They intentionally answer different questions. The existing v0.1 source removes
comments/provenance/whitespace-only text before C14N, with a textual fallback
for malformed XML. It has no explicit `hash_method` field or external
`assets[]` binding. An adapter should declare these conventions and derive from
the existing record rather than treating all SHA-256 values as interchangeable.

## Practical next sequence

1. Adopt the hash inventory and mark the missing payload classes explicitly.
   Preserve the three original knowledge documents and the raw workflow.
2. Reuse Research Loom's current mixed geometry, source/hash binding and
   measured Blender/GLB readback as a small working core. They advance parts of
   B04/B10/B11/B12/B26/B27; they do not validate the old entire corpus or splat
   color/oracle ladder.
3. Add the escaped-metadata regression, point/line retention fixture, current
   large-coordinate probe and a fresh SH0–SH3 ladder with field-level losses.
4. Resolve exact upstream sources and recover missing renderer image pairs;
   only then establish cross-engine pixel tolerances and a before/after ledger.
5. Attach a thin checkpointed workflow to the existing scorekeeper/provenance
   owner. Preserve capability facets and refusals instead of reducing all
   checks to one "confirmed" badge.

The durable product of this pass is an archive map and an adoption route. It
does not execute networked historical kits, spend on models, contact other
owners, mutate public repositories or replace the existing evidence protocol.
