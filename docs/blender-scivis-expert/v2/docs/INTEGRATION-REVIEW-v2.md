# Blender scientific visualization: an evidence-led integration

Private additive review · 17 November 2026

The project has a strong foundation: numerical models, declarative X3D scenes,
Blender authoring, independent renderers, a scene corpus and learning loops can
correct one another. The most useful next step is a shared contract for what
each result establishes. It should connect the existing tools and preserve their
different responsibilities.

This pass reads the three supplied files and the actual private branch
`claude/project-thread-0lc3kd` of `hagopjay/x3d.ml`, pinned at
`c1634f5c4f29c4220a092510807a430ce4cbfd2e`. All three attachments match their
branch counterparts byte for byte. The review preserves the original documents
and archive, adds structured inventories and corrections, and implements two
small integration adapters. It also executes new Blender 5.2.4 precision and
Blender 5.3.0 native-splat controls. No remote repository is changed.

## What the archive actually contains

The archived expert folder has **439 files totaling 4,583,862 bytes**: 217 Python
scripts, 126 X3D documents, 74 Markdown files, 13 JSON files, five shell scripts,
three PLY files and one patch. Its 27 dependency directories containing only
documentation are historical snapshots, not runnable source checkouts.

The raw workflow records 14 slice digests, the original 18 bridge proposals,
36 verifier responses and a critic. The critic contributes nine additional
bridges, B19–B27; its tenth suggested entry is a rule-hygiene note. The complete
catalog retains **27 bridge IDs and 221 verifier notes**, including contradictory
claims and the original source lines.

Source rescue has therefore partly happened already. B24 should recover the
missing replay material rather than recopy everything: there are no archived
PNG, EXR, `.blend`, SPZ, SOG, VDB or JSONL files in this folder. The 111-item
candidate Tier A manifest points to external scenes; it does not contain them.
Old PSNR, timing and corpus results remain historical observations unless their
specific inputs and output bytes can be recovered or regenerated.

See [the kit salvage review](../private/KIT-SALVAGE.md),
[full inventory](../private/kit-inventory.json) and
[raw-workflow summary](../private/raw-workflow-summary.json). All 217 archived
Python files parse; static execution leads identify paths, subprocesses and
dynamic imports worth reviewing. Parsing is not evidence that a script is safe,
portable or scientifically correct. Archived kits were not executed wholesale.

## The new work completed in this pass

| Work | Executed result | Exact boundary |
|---|---|---|
| Private archive recovery audit | Every file inventoried with SHA-256 and its Git blob checked | Source identity and availability, not a rerun of the old experiments |
| Research Loom inventory adapter | Existing packets, tools, exports and receipts become a queryable JSON-LD inventory | Checking current bindings does not upgrade old runs to reproduced experiments |
| Existing x3dprov integration | Three saved scientific scenes linked to their existing Blender render receipts and image bytes | Retrospective linkage, explicitly `render_reexecuted: false` |
| Provenance escape repair | Four failing string cases become passing cases after a one-line callback repair; five regression tests pass | Private x3dprov JSON insertion, without changing its content-hash protocol |
| Precision/origin fixture | Actual saved and reopened Blender 5.2.4 vertices measured against independent binary32 packing | Two synthetic metric-coordinate fixtures, restored in Python binary64 |
| Native Gaussian probe | Four SH3 splats imported on actual Blender 5.3.0 and passed through the pinned ecosystem fork | Attribute/data retention at this small fixture size; no renderer PSNR or scale result |
| Ontology and metadata shapes | Local vocabulary, JSON schema, SHACL shapes and query examples supplied | Metadata structure and declared relations, without automatic scientific truth inference |

The exact executed command results, source identities and remaining limitations
belong in the accompanying execution receipt. The prior Research Loom study
already supplies nine synthetic/analytic cases, 78 saved states, 63 scientific
witnesses and actual Blender/GLB transfer evidence. Reusing that evidence is a
concrete integration gain, but it does not close every acceptance criterion of
any original bridge.

## A taxonomy that makes the work reusable

Classify each item along several independent axes. A single project folder or
confidence grade cannot express these distinctions.

| Axis | Useful classes | Example |
|---|---|---|
| Scientific object | Samples, scalar/vector/tensor fields, surfaces, volumes, graphs, trajectories | A covariance matrix and its point observations |
| Representation | Raw arrays, scientific projection, scene graph, authoring scene, radiance model, raster figure | A VTP point array versus a colored sphere glyph |
| Activity | Compute, encode, transform, import, export, validate, render, inspect, compare, learn | Blender save/reopen readback |
| Acceptance facet | Legality, loadability, visibility, completeness, quantities, appearance, dynamics, provenance, resources, rights | An XSD pass establishes legality under one schema |
| Evidence mode | Reported, inspected, executed, independently reproduced | A retained old JSON result remains reported evidence unless the appropriate operation is rerun |
| Outcome | Pass, fail, partial, unknown, with a stated comparison | A successful export that omits points is a completed operation with a retention failure |
| Operational readiness | Archived, recoverable, adaptable, replayable, gated, integrated | A script with absent absolute-path inputs is adaptable rather than replayable |
| Ownership | Existing core, consumer adapter, fixture, integration proposal | Extend x3dprov; avoid a second provenance protocol |

The important architectural shift is to separate an evidence record from the
activity it describes. Reading a Cycles receipt today creates a new inspection
record; it does not mean Cycles ran today. A version announcement can be checked
against primary documentation without an X_ITE renderer. An actual vertex
comparison can establish geometry retention while appearance remains untested.

## Scientific quantities must survive the display mapping

The reusable scientific record is a quantity with an identity, association,
components, units, coordinate frame, missingness and uncertainty assumptions.
Color is a declared mapping from that record into a visual channel. Preserve
both sides of the mapping.

Research Loom illustrates the distinction well. Its membrane display exaggerates
height while the exported VTP retains unexaggerated displacement and velocity.
Its ellipsoid is a fitted Gaussian contour, not a generic confidence region for
the mean. Its steady ABC flow gives trajectories with periodic seam clipping;
a line drawn directly across the box would invent a path segment.

This pattern transfers to molecular confidence, medical-style volume phantoms,
geoscience, mechanical simulation and game debugging. A pLDDT color requires
proof that the source field actually means pLDDT; an arbitrary experimental PDB
B-factor does not acquire that meaning from a palette. A volume needs spacing,
orientation and transfer-function records. A gameplay trace needs its time step,
force convention and distinction between physical state and presentation effects.

Blender may compute scientific results through Python or Geometry Nodes. The
principle is reproducible numerical authority, not a ban on analysis inside an
authoring application. Likewise, a mesh is not automatically a measurement and
a splat is not automatically useless for measurement: suitability follows from
the acquisition, calibration, reconstruction, uncertainty and intended task.

## Two precision lessons with actual Blender data

The old phrase “six versus fifteen orders of magnitude” confuses significant
precision with exponent range. Precision must be budgeted at the coordinate
magnitude used by the actual storage and transform path.

| Synthetic metric frame | Direct global maximum coordinate error | Local storage with binary64 origin restoration |
|---|---:|---:|
| ECEF-like | 0.2345000003 m | 0.000001890585 m |
| UTM-like | 0.1543210996 m | 0.000001890643 m |

The probe uses actual Blender **5.2.4 LTS**, build `cd5dc428cce1`, saves and
reopens the `.blend`, reads `MeshVertex.co`, and compares against an independent
`struct` binary32 reference. Deliberate vertex changes are detected. The source
coordinates and reversible origin survive as retained source data.

The origin is added back outside Blender in Python binary64. Moving the object
back to a very large Blender world translation can reintroduce precision loss.
Centering preserves physical units; rescaling changes the mapping and needs its
own explicit conversion. The example does not promise micrometre accuracy for
arbitrary scenes or GPUs, and coordinate magnitude does not identify a CRS.
Use X3D's existing Geospatial/GeoCoordinate/GeoOrigin direction where applicable.

## Native splats: the former future task is now a measured route

Blender 5.3 was released on 10 November 2026. Its primary release notes document
native splat imports, attributes and rendering, alongside color and transform
limitations. The new control goes further than those release facts: it runs an
official **Blender 5.3.0**, build `02f0899d78e3`, whose downloaded archive matches
the vendor SHA-256. It imports four deliberately asymmetric SH3 PLY splats.

The measured route distinguishes raw DC radiance from RGB, sigmoid opacity from
logits, exponential scale from log scale, normalized quaternion ordering,
all 15 higher-order RGB coefficient slots, positions/object transforms and the
absence of a per-asset training-color-space flag. The ecosystem fork's native
X3D 4.1 export/import is checked as a separate route. Blender's own lack of native
splat export is not a statement about that fork's exporter.

The transform control reproduces an important limitation: applying object
rotation/scale changes the represented world covariance when the splat's
attributes are not transformed consistently. Preserved positions alone would
miss this. A Gaussian is its center, covariance, opacity and directional
radiance—not simply a point with a radius.

This closes a useful part of B13. It does not establish B01's SH0–SH3 ladder at
large sizes, multi-pose image fidelity, SPZ conversion quality, general transform
correctness or a supported CI matrix. Those remain separate experiments.

The storage arithmetic also needs a precise layout. SH3 has 59 meaningful model
scalars, or 236 bytes at float32. The common reference PLY adds three normal
fields, producing 62 float32 values and 248 payload bytes per splat. Header,
endianness and declared property types matter. Neither a PLY extension nor a
ZSTD container by itself guarantees lossless scientific quantities.

## Preserve existing provenance and repair its actual boundary

The private `src/x3dprov.py` hashes scene content after removing provenance,
comments and whitespace-only text, then applies XML canonicalization. Its
malformed-XML fallback uses a different text normalization. Research Loom uses
exact file-byte hashes and canonical JSON hashes for different purposes.
These identifiers must keep their method names; an apparently matching
64-character string is not a universal content identity.

Two integration problems were reproduced:

1. In `_inject_meta`, `re.sub` treated serialized JSON as a replacement template.
   Escaped newlines, Windows paths and replacement-like strings could be decoded
   or rejected. An archived `xprov` copy already contained the correct callback
   pattern. The proposed core patch adopts that one-line repair, with regression
   tests. The original archive stays unchanged.
2. A caller could append to a stale stamped scene and use the previous recorded
   output as the default input identity, making the extended chain verify.
   The new figure adapter first refuses stale or broken input. This is an explicit
   caller precondition; it does not silently change the old protocol's repair
   semantics for every other consumer.

The figure adapter records `link_existing_render`, not `render`. It binds each
source packet, selected frame, X3D export, renderer receipt and image to the
existing chain. It checks live producer files and decoded geometry. It preserves
both the original packet-frame hash and the export-normalized frame hash:
normalizing integer/float values or adding defaults can change canonical JSON
identity without changing the represented geometry.

A hash chain helps reveal accidental gaps. It is not an authenticated publisher
signature or proof that the recorded science is true. Keeping original evidence,
live bindings and clearly scoped observations is essential even after a chain
verifies.

## Ontology hooks with clear implementation boundaries

The supplied JSON-LD inventory uses a local `urn:x3d-scivis:inventory:` vocabulary.
It aligns artifacts, datasets and claims with PROV entities, validation and
transformation runs with activities, and bridge categories with SKOS concepts.
PROV usage/derivation relations are kept distinct: an evidence file is not an
activity merely because it mentions a tool.

| Concept | Existing hook | Required local detail |
|---|---|---|
| Artifact / dataset | `prov:Entity` | Locator, byte length, hash method, SHA-256, confidentiality |
| Validation / transformation | `prov:Activity` | Input/output identities, exact tool build, scope, time, outcome |
| Derivation | `prov:wasDerivedFrom` | Which representation changed and which quantities were retained |
| Scientific observation | SOSA alignment hook | Observed property, procedure, feature of interest and result; do not label every render an observation |
| Quantity | QUDT alignment hook | Unit URI where known, numeric value, association and uncertainty |
| Bridge / category | `skos:Concept` | Stable B-ID, broader/narrower concepts and related work package |
| Loss | Local comparison record | Field, coordinate convention, expected projection, tolerance and observed difference |
| Claim | Local scoped assertion | Subject, facet, evidence mode, outcome, supporting artifacts and freshness |

The JSON schema and Python checks enforce the inventory contract. The Turtle
hooks, SHACL shapes and SPARQL example make external graph integration concrete.
SHACL checks metadata structure; live byte checks and facet-support queries remain
separate. Neither stage infers physical truth. Rights are source assertions and
policy inputs, not legal conclusions inferred from a filename or short regex.

For a future domain record, require at least: quantity ID, name, association,
components, units, coordinate-frame ID, missingness, numeric range, uncertainty
description, display transfer function and a comparison profile. A profile should
state its equivalence relation. Quaternion comparison must allow `q` and `−q`;
Gaussian comparison should include covariance under a basis change; SH comparisons
need the declared coefficient basis and rotation convention.

## Fit the pieces into the existing projects

| Project | Reuse now | Keep under its existing ownership |
|---|---|---|
| Private x3d.ml expert archive | Hashed kit catalog, additive corrections, bridge taxonomy, evidence adapter and figure links | Private corpus/benchmark records and the x3dprov source repair |
| x3d.STEM / Research Loom | Numerical packets, scientific witnesses, VTP/VTI fields, coordinate maps and actual readback controls | Scientific model implementations and publication eligibility |
| x3d.mathslab | Lesson kernels, prediction questions, independent references and displayed-coordinate captions | Teaching sequence and learner-facing explanations |
| x3d-blender-io | Known-answer fixtures and expected-loss tables; native 5.3 capability probe | Importer/exporter repairs and compatibility CI |
| x3d_mcp / Playground | Minimal counterexamples, typed scientific rule proposals and explicit resource refusals | Schema/semantic verdicts, repair rungs and the main scorekeeper |
| x3d.demo | A small versioned discovery card after a destination is verified | Gallery naming, versioning and publication |
| x3d.docs | Coordinate, color, evidence and hash-method drills using public-safe fixtures | Reusable technical explanations and claim grading |
| x3d.flywheel / agent work | Evidence vector, stable adapters, improvement hypotheses and failure families | Orchestration, model experiments and any later corpus write-back |

The local MathLab checkout already connects 18 lessons, including SVD, aliasing,
heat diffusion and refraction. This is a useful source of small known-answer
fixtures and explanations, rather than a reason to copy every kernel into STEM.
The Flywheel/PolyXandria names in the historical archive are integration targets;
this review does not assert their remote pipelines are currently deployed.

Public handoff patches should contain only synthetic fixtures, generic adapters
and necessary documentation after review. Private survey prose, corpus IDs,
raw workflow outputs, internal storage maps and asset rights notes stay in the
private package. Nothing is pushed or sent by this pass.

## Consolidate 27 bridges into eight work packages

| Package | Bridges | Shared product |
|---|---|---|
| WP0 Recovery and baseline | B24 | Recoverable inputs, exact build register, before-fix results |
| WP1 Representations and budgets | B01, B02, B03, B08, B16, B25 | One splat/codec/partition/scale ladder with per-field errors |
| WP2 Exchange retention | B04, B06, B07, B11, B26, B27 | Expected-loss ledger and consumer-specific comparison profiles |
| WP3 Scientific semantics | B09, B10, B19–B23 | Known-answer domain fixtures, quantity records and semantic rules |
| WP4 Provenance and rights | B12, B17 | Existing provenance extended with explicit asset/method references |
| WP5 Guarded execution | B05, B14 | Source-loss audit adapter, pure commands and durable checkpoints |
| WP6 Evaluation | B15, B18 | Typed oracle outcomes and controlled held-out experiments |
| WP7 Capability watch | B13 | Dated software capabilities backed by executable probes |

The machine-readable catalog retains every original bridge, old acceptance
criterion, verifier objection, proposed owner and corrected dependency. It is
an implementation backlog, not a claim that 27 integrations now work.

## Sequence the remaining work by what it resolves

**First: freeze reusable baselines.** Preserve the current stock/fork point-line
fixture, native 5.3 splat probe, precision control and the original broken
provenance behavior. Recover the absent images and corpus files by exact identity
where available; regeneration creates a new run. Reconcile B09's 11-versus-12 rule
list before treating it as a standard gate.

**Next: close one ordinary exchange loop.** B27's points, ColorRGBA and lines,
B26's GLB cross-check and B04's value/default tests share most of their machinery.
Use the existing Research Loom readback fixture and preserve scientific arrays
in sidecars/VTP. Fix omissions in the owning exporter, then compare the same
before/after values. Keep native pixels, geometry and source data as separate
acceptance criteria.

**Then: the splat ladder.** Reuse the recovered synthetic generators, but name
fixture cardinality, float layout and exact values. Measure opacity in both
alpha and logit spaces where clamps matter. Test SH0–SH3, asymmetric covariances,
multiple camera poses and declared transforms. Parser limits, XSD limits and
renderer ordering are different failure modes. A resource refusal should remain
distinguishable from an invalid scene. Increasing parser allowances alone is
not a complete large-file strategy.

**Extend to scientific domains with independent answers.** B19 should begin
with an analytic anisotropic-spacing volume phantom. B20 should preserve atom
and residue identities in a tiny molecular fixture before adding large structures.
B22 should compare keyed values at fixed fractions and individual ROUTE endpoints,
rather than counting tags. B23 should check joint hierarchy, centers and weight
normalization. B21 can extend the new origin fixture into a declared CRS path.

**Orchestrate after interfaces stabilize.** B14 needs import-safe local commands
and a durable checkpoint test that survives a process kill. Wrapping an old
script that runs remote commands at import is not a neutral node. The inventory
adapter is deliberately read-only and does not become a new workflow engine.
Any future post-export validator also remains distinct from the process boundary
that limits a Blender script's filesystem or network effects.

**Evaluate models last.** B18 needs an actual feasible prompt selector, held-out
split, fixed budget and paired protocol. The old “115 feasible prompts” is not
present as a reproducible selector. Report legality, visible output and fidelity
with their own denominators; first-try-valid rates are not scientific-fidelity
rates. B15 should use a vector of independent oracle findings, including unknown
or failed execution states, rather than hide disagreement in one average.

## Working heuristics

1. Select a representation for a question; do not infer its scientific authority
   from its file extension or visual polish.
2. Preserve the smallest input that can refute a claimed property. Four distinct
   splats can expose ordering mistakes; they cannot establish million-splat scale.
3. Compare actual output data. Retained metadata can describe geometry that was
   silently omitted or changed.
4. Record expected projections as well as losses. A glyph mesh is a deliberate
   representation change; losing the observation coordinates is a different event.
5. Freeze a before-fix case before changing a converter. Regression evidence
   requires the same contract on both sides.
6. Upgrade only the claim that was tested. A native import, a source inspection
   and a multi-pose renderer comparison have different coverage.
7. Keep known failure results. An Apply Transform counterexample is valuable
   evidence and a regression target, even though the probe itself passes.
8. A derived figure should retain its numerical source, display mapping, selected
   state and renderer record. Its beauty does not substitute for any of them.
9. Promote a new rule after a minimal reproducer and a held-out check; matching
   the mutants used to write a rule is coverage, not generalization.
10. Prefer one owned implementation with many adapters. A shared identity and
    loss vocabulary will compound more effectively than parallel scorekeepers.

The long-term payoff is an expanding collection of small, inspectable scientific
cases. Each new domain supplies a useful figure and a new way to detect a wrong
one. Each repaired bridge increases how many tools can carry the same question
without losing its meaning.

## Reading and execution map

- [Knowledge corrections](../private/KB-v1.2-CORRECTIONS.md): 21 scoped corrections,
  primary URLs, precision receipt and reference PLY arithmetic.
- [Executed results](EXECUTED-RESULTS.md): test counts, metadata checks, live
  bindings and limits, with separate records for actual Blender runs.
- [Bridge audit](../private/BRIDGE-AUDIT.md) and [catalog](../private/bridge-catalog.json):
  complete historical proposals and corrected work packages.
- [Kit salvage review](../private/KIT-SALVAGE.md): what is actually preserved,
  which dependencies are absent and how to adapt each slice.
- [Current evidence map](../private/current-evidence-map.md): scoped reuse of
  existing Research Loom results.
- [Inventory adapter](../integration/README.md): JSON-LD contract, root mappings,
  live bindings, support queries and meaningful negative controls.
- [Provenance adapter](../adapters/README.md): existing protocol, retrospective
  figure linkage and the private source repair.
- `private/native53/`: actual native probe, data and reproducible command.
- `private/probes/`: actual precision/origin fixture and saved Blender data.
- [Ontology hooks](../ontology/hooks.ttl), [metadata shapes](../ontology/shapes.ttl)
  and [query](../ontology/queries.rq).

Primary standards context: [PROV-O](https://www.w3.org/TR/prov-o/),
[Blender 5.3 rendering notes](https://developer.blender.org/docs/release_notes/5.3/rendering/),
[X3D shader attributes](https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/shaders.html),
[Web3D molecular examples](https://www.web3d.org/x3d/content/examples/Basic/ChemistryMarkupLanguage/).
