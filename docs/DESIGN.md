# X3D traceability: what a provenance record should hold, and what a pipeline gains

17 Oct 2026. Thread "Traceability" (HagopJay's insight: traceability and observability are a major win for X3D in real-time ML operation pipelines). $0 spent. Private. Grades: **C** Confirmed (ran it, numbers below), **L** Likely (reasoned from what I know of the standard or read the code), **S** Suspected (unverified).
Validator behind every validation number: x3d_mcp fork main **eb4b4b4**. Blender: bpy 5.2.2 wheel, x3d-blender-io main **206f139**. Hash: SHA-256. Code: `x3dprov.py`, `demo.py`, `export_prov.py` beside this file; evidence in `runs/`.

## 1. Why X3D is a good carrier (and what is already in the file format)

| Fact | Grade | Source |
|---|---|---|
| X3D XML has `<head><meta name content/></head>` for free-form named strings, any number, any name | C | spec shape; validator accepts `x3dprov.*` names (verdict unchanged) |
| Metadata nodes (`MetadataSet`/`MetadataString`/`MetadataDouble`...) attach to any node via `containerField="metadata"` | C | validator flags a MetadataSet on a Shape WITHOUT `containerField="metadata"` (code `containerfield-unknown`); the bridge exporter writes it |
| Blender import then export **keeps every head meta** (custom names too) in order and appends its own generator | C | 6 scenes, 5 KB to 62 MB, record survived 6 of 6 (`runs/*/result.json`, `blender_kept_meta_steps`); code: `extract.scene_head_meta`, `emit_x3d40.head_meta` |
| Blender round trip **keeps per-node MetadataSet/MetadataString** on a Shape, adds `containerField="metadata"` | C | probe in this thread (cube, bpy 5.2.2) |
| Blender round trip **drops `WorldInfo`** | C | same probe: WorldInfo in, absent out (matches the known loss in earth-twin notes) |
| So: scene-level provenance goes in **head meta**, node-level in **Metadata\* nodes**; never in WorldInfo | C | consequence of the three rows above |

This is the traceability argument in one line: glTF `extras`, USD customData and PLY comments exist, but X3D is the one where a **validator that names the exact fix** and a **browser that shows the result** and **Blender round trip that keeps the record** are all already in our loop.

## 2. The record (x3dprov 0.1, implemented)

One `x3dprov.version` meta and one `x3dprov.step.N` meta per step. Content is compact canonical JSON (sorted keys). Every step:

| Field | Meaning | Spine column it mirrors |
|---|---|---|
| `op` | ingest / generate / validate / repair / render / transform / judge | `lineage.relation`, `generations.condition` |
| `input_sha256`, `output_sha256` | hash of the scene CONTENT (comments and whitespace dropped, all `x3dprov.*` metas removed, C14N) before and after | `scenes.scene_id` (same idea; spine hashes whitespace-normalised XML, so ids differ unless we align, see section 6) |
| `prev` | sha256 of the previous step's JSON text (`0`x64 for the first) | new: this is the chain |
| `agent`, `agent_ref` | tool and commit, or model id | `lineage.agent`, `generations.model_id` |
| generate: `model`, `provider`, `prompt_sha256`, `prompt_id`, `temperature`, `seed`, `exemplar_ids`, `tokens_in/out`, `cost_usd_est` | the model call | `generations.*` |
| validate: `validator`, `validator_ref`, `xsd`, `xsd_valid`, `semantic_error_codes`, `verdict` | which validator at which commit said what | `validations.*` |
| repair: `kind` (model / deterministic), `report_shown`, `fixes`, `round` | what was shown and what was changed | `generations.condition`, `lineage.detail` |
| render: `renderer`, `nonblank_ratio`, `load_ok` | "valid is not the same as visible" | `renders.*` |
| transform: `tool`, `agent_ref`, `detail` | Blender round trip etc. | `lineage.relation=converted_from` |

Verification (`verify()`), four verdicts: **verified** (chain intact and last output hash equals file content), **stale** (content changed after the last recorded step = an untracked edit), **broken-chain** (a step was removed or edited), **no-record**.

### Measured (C, fork eb4b4b4, bpy 5.2.2)

| Check | Result |
|---|---|
| Full pipeline ingest, validate, deterministic repair, validate, Blender round trip, validate: record verifies | 6 of 6 scenes |
| Largest scenes through the pipeline | 16.8 MB (campus-local) and 62.0 MB (campus-local.blender) verified, 41 s and 48 s end to end |
| Edit a coordinate after the last step | `stale` on 6 of 6 |
| Delete step 2 | `broken-chain` on 6 of 6 |
| Flip a verdict in an interior step | `broken-chain` on 6 of 6 |
| Flip the verdict in the **last** step | **still `verified`** on 6 of 6: see limits |
| Overhead | about 611 bytes per step, 3,670 bytes for 6 steps, independent of scene size (6.7% on a 58 KB scene, 25% on 18 KB, 170% on the 3.4 KB cube; negligible above 1 MB) |

## 3. Limits stated plainly (C unless marked)

1. **Unsigned = tamper evidence for accidents and pipeline gaps, not proof against an adversary.** The last step has no successor, so its content (even its verdict) can be changed undetected; anyone can also rewrite the whole chain consistently. Fix is 0.2: sign the head hash (Ed25519 or COSE, C2PA-shaped), key held by the pipeline. Nothing in 0.1 should be sold as "tamper-proof".
2. **Hash binds content, not bytes.** Whitespace and comment changes verify; that is deliberate (Blender rewrites the whole file) but means a comment cannot carry meaning. Hash is over canonical XML; classic VRML and JSON encodings are not covered yet.
3. **Blender rewrites geometry text**, so every round trip must be a recorded `transform` step; an unrecorded one shows as `stale`. That is the feature.
4. **Public pages**: records name models and validators. Project rule is no vendor or model names on public pages; plan a `public` profile that replaces `model` with a family class and drops `cost_usd_est`, `prompt_sha256` kept. (S: not built.)
5. **Model steps are not in the demo**: the demo uses real tool steps only (autofix, validator, Blender). The generate/judge fields are the spine's `generations` columns; filling them from cached spine rows is the next step (the E1 scene bodies are in GCS/BigQuery, not in the shared folder). No model provenance was invented.

## 4. Comparison with PROV, OpenLineage, C2PA

| | W3C PROV (PROV-O / PROV-JSON) | OpenLineage | C2PA | x3dprov 0.1 |
|---|---|---|---|---|
| Unit | Entity, Activity, Agent; wasGeneratedBy, used, wasDerivedFrom, wasAssociatedWith | Run, Job, Dataset in/out, extensible facets | Manifest: claim, assertions, signature, hard-binding hash | Chain of steps with content hashes |
| Where it lives | anywhere (a graph elsewhere) | an event stream to a lineage server | embedded in the asset (JUMBF) or sidecar/remote manifest | **inside the scene file** |
| Travels with the file | no | no | yes for supported formats | **yes, and through Blender** (C) |
| Tamper evidence | none by itself | none | **yes: signed, X.509 trust** | hash chain only; signature is 0.2 |
| Fits ML ops tooling | research / archives | **yes** (Airflow, Spark, dbt integrations exist) L | content authenticity, press, camera | the join key between all three |
| X3D support | none | none | no registered X3D binding that I know of (S); our SVG/PNG/JPEG stamping layer shows XML-ish assets can carry it | native |
| Grade | L | L | L (spec read from memory, not re-fetched today) | C |

Conclusion (L): do not compete; **x3dprov is the in-file source of truth and the three are views.** `export_prov.py` already projects a record into PROV-JSON (entities by content hash, activities per step, agents with commit, wasDerivedFrom between differing hashes) and OpenLineage RunEvents (one per step, step JSON as a custom facet, dataset name = content hash). Run on the 6-step cube: 6 events, `runs/cube/prov.json`, `runs/cube/openlineage.json`. Not yet validated against the OpenLineage JSON schema (S) and PROV-JSON is a hand projection (S: not run through a PROV validator). C2PA 0.2: a claim whose hard binding is the content hash and whose assertion is the step list.

## 5. What a real-time ML pipeline gains (and what is measured)

| Gain | Why | Grade |
|---|---|---|
| **Untracked-edit alarm** in the artifact itself | stale / broken-chain verdicts above; no log server needed | C |
| **Validator-version drift detection** | every verdict names `validator_ref`; when the fork moves, `SELECT` scenes whose last verdict used an older ref and re-validate only those | L (needs the spine) |
| **Join key across systems**: content hash is in the file, in BigQuery (`scenes.scene_id`), in OpenLineage datasets, in a C2PA claim | one scene, four systems, no mapping table | L |
| **Per-scene cost and failure attribution** | model, tokens, cost, repair rounds on the scene that was produced; answers "which exemplar set made this" from the file | L (fields exist in spine; not yet written into files) |
| **Licence and training gate that travels** | spine has `usable_for_training`; a copied file that lost its row still carries its chain | L |
| **Observability at the edge**: a viewer or CI step can verify on load | `verify()` is stdlib + lxml, 40 lines of logic | C |
| **The "report shown" signal** | the tether result (7 to 10 of 10 repairs pass when the validator report is shown) becomes visible per scene as `report_shown` | L |

## 6. Next steps (default, no spend)

1. Fill generate/repair steps from cached spine rows: align the hash with `scenes.scene_id` (spine uses whitespace-normalised XML sha256; x3dprov uses C14N minus metas; pick one, my vote: spine's, with the prov metas stripped first), then stamp a sample of cached E1 scenes (needs the scene bodies pulled from GCS: **a read, no cost, but I will ask before touching the bucket**).
2. Add `provenance_stamp` / `provenance_verify` as tools in the fork x3d_mcp so the model loop calls them (draft PR to hagopjay/x3d_mcp, nothing upstream).
3. Add a bridge regression test (head meta and per-node MetadataSet survive round trip, WorldInfo documented as lost) to x3d-blender-io (draft PR).
4. 0.2: Ed25519 signature over the head hash, `public` redaction profile, C2PA claim projection.
5. Wait for Dr. Polys's view on whether the Consortium wants a registered `x3dprov.*` meta namespace (his call, nothing sent).
