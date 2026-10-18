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

## 7. Second pass: real cached model scenes (added 17 Oct 17:3x)

`stamp_gpu_phase.py` stamped **174 cached scenes** from the 11 Oct GPU phase (3 open models, one-shot and grounded repair, 1x L4) using only recorded facts (run id, hardware, tokens, latency, prompt hash, attempts, recorded verdict). **174 of 174 verify.** Only the final attempt's body is cached locally, so earlier attempts are summarised, not hashed.

| Model | mode | n | valid on 11 Oct | valid now (fork eb4b4b4) |
|---|---|---|---|---|
| qwen3-8b | oneshot | 30 | 3 | 2 |
| qwen3-8b | grounded | 25 | 12 | 3 |
| qwen2.5-coder-14b-awq | oneshot | 30 | 14 | 12 |
| qwen2.5-coder-14b-awq | grounded | 29 | 23 | 15 |
| gpt-oss-20b | oneshot | 30 | 13 | 10 |
| gpt-oss-20b | grounded | 30 | 26 | 12 |

**Validator drift, measured and attributed (C, corrected 17 Oct after the coordinator pointed to the recorded validators).** 37 scenes were valid on 11 Oct and are invalid now; 0 went the other way. The 11 Oct verdicts came from the deployed `x3d-mcp-svc` (XSD plus DEF/USE/ROUTE endpoints only, per `x3d-bench-next/open-models-fork/README.md`), not from a fork build. I re-ran all 174 original scenes on seven fork commits (`drift/runval.py`, verdicts in `drift/verdicts_by_fork_commit.json`):

| Fork commit | date | valid of 174 | agree with 11 Oct recorded verdict |
|---|---|---|---|
| 8c0a457 (the commit the GPU-phase score quotes) | 8 Oct | 55 | 138 |
| c9c9788 | 11 Oct | 55 | 138 |
| 688174f | 12 Oct | 54 | 137 |
| 76fc439, d61d4de | 13 Oct | 63 | 146 |
| eb4b4b4 (main) | 15 Oct | 54 | 137 |
| d5598c4 (spine branch) | 16 Oct | 54 | 137 |

Attribution of the 37 flips: **36 are already invalid on 8c0a457** (so not caused by later fork commits; the service was simply a weaker validator), **1 flips at 688174f** (`tuple-count`). By rule on 8c0a457: profile-component 20, route-invalid-from-field 14, containerfield-type-mismatch 7, route-type-mismatch 5, route-invalid-to-field 4, interpolator-key-length 2 (scenes can hit several). My per-model counts on 8c0a457 and c9c9788 (gpt-oss 10 and 13, coder 12 and 15, qwen3 2 and 3 for one-shot and grounded) match the earlier independent re-validation in `open-models-fork/README.md` exactly. Grounded counts differ from that run by one scene only at eb4b4b4 (gpt-oss grounded 13 to 12). The 13 to 63 jump at 76fc439 and back at eb4b4b4 is a rule that was relaxed then restored on the merge path; not investigated (S).

So my first-pass inference ("fork rules added since 11 Oct") was **wrong**, and this replaces it. The lesson stands in a corrected form: the service's *name* was recorded but not its build digest, and the service and the fork are different validators, which is exactly why every x3dprov validate step names `validator` and `validator_ref`. Caveat unchanged: grounded repair stopped when the weaker service was satisfied, so the grounded "valid now" drop (qwen3-8b 12 to 3) measures the validator, not the model.

## 8. Third pass: do the valid scenes draw? Real renders of all 174 (added 17 Oct 18:4x, method corrected 17 Oct 19:3x)

Question from the demo work: the 11 Oct service called 91 of the 174 scenes valid; does valid mean visible? I rendered every one of the 174 in **X_ITE 16.5.0** (the project's reference version, published as the page's own files; headless Chromium, software GL, offline, one fresh page per scene). Method (`demo/render/render_final3.py`, page `render3.html`): a watcher on X_ITE's end-of-frame event is registered **before** the scene loads, and the WebGL canvas is sampled inside that callback (the first 8 frames, then at most one every 150 ms, 20 samples); after 3.5 s a real screenshot of the canvas box is taken as an independent check. "Draws" = at least 0.5% of pixels differ from the background in any sampled frame or in the screenshot. Raw outcomes: `demo/data/renders3_x_ite_16.5.0.json`.

What X_ITE does (measured here): it does not fail on what it cannot read, it drops the node, prints a console warning and carries on. It renders on demand and every scene starts with blank frames. A scene with nothing drawable gets a median of 4 frames, the last at about 160 ms, and X_ITE then idles; a drawing scene keeps rendering until a median of 1.3 s (64 frames) and then idles unless it animates. Twelve blank scenes (HAnim and Geo scenes with running animations) kept rendering about 700 frames in a 12 s look with 90 samples each and stayed exactly blank (`demo/data/renders3_extended_x_ite_16.5.0.json`).

| Outcome | scenes | note |
|---|---|---|
| draws something | 115 | 36 of them printed dropped-node warnings: X_ITE drew the rest |
| only blank frames, X_ITE dropped nodes | 43 | 42 print "Unknown node type"; 37 of the 43 are Geospatial or HAnim nodes in an Immersive-profile scene with no `<component>` statement for them (X_ITE hints at "insufficient component or profile statements"); the rest are elements X3D does not have (USE as a node, InlineGeometry, BooleanSwitch) or a node in a container X_ITE rejects |
| only blank frames, nothing dropped | 4 | a malformed MFString, an array length, a bad ROUTE |
| does not parse | 12 | all 12 are not well-formed XML |

| Validator | valid | of those, draw nothing |
|---|---|---|
| 11 Oct service (XSD + DEF/USE/ROUTE only) | 91 | **17 (18.7%)** (7 geospatial, 9 HAnim, 1 interaction) |
| fork 8c0a457 | 55 | 0 |
| fork eb4b4b4 | 54 | 0 |

Of the 36 scenes that flip valid to invalid on 8c0a457, 17 draw nothing. The converse does not hold: only 54 of the 115 scenes that draw pass the fork, since X_ITE draws part of a scene it cannot fully read. Checks on the measurement itself: the sampled frames and the screenshot agree on 160 of the 162 scenes that parse (both misses are animated scenes visible only part of the cycle: the sampled frames reached about 21% and the screenshot caught them out of view, so they count as drawing); the same pass on **X_ITE 16.4.1 as own files** (`renders3_x_ite_16.4.1.json`, where the end-of-frame field is called `endEvents`) gives the same draw, blank or parse answer for 174 of 174 scenes. **Grade: C for this sample (three small open models, 174 scenes, two X_ITE versions, two measures); S as a rate.** What it supports: "valid is not visible" is a property of the weak validator here, and the stricter one removed it on this sample; "visible is not valid" stays. The stamped record can carry a `render` step with these fields (nodes, nonblank ratio, frames watched, unknown nodes, parser messages), and the demo does.

**Correction of my first pass** (`demo/render/render_final2.py`, outcomes kept in `demo/data/pass1/`): it sampled only frames arriving 700 ms or more after the load. The draw-or-nothing answer was the same for all but one scene (an animation that is visible only mid-cycle), but two things in my write-up were wrong. (1) I recorded 31 scenes as "no frame" and wrote that X_ITE never schedules a frame when nothing is drawable. It draws a few blank frames and then idles; the pass simply started looking after they had gone. (2) A sampler that waits a fixed time for the next frame depends on the machine: a static drawing scene keeps rendering for only about a second, so on a faster GPU the same pass could have called it "no frame" too. The new pass does not wait for any frame.

Renderer facts the demo had to respect. (1) X_ITE loaded from a CDN inside the artifact viewer loses lazy components, fonts and wasm at run time (found earlier in the Shroud thread), so the page ships X_ITE as its own published files (`demo/mkxite.py`, 105 files, 8.5 MB, MIT licence included). (2) While a new world is swapped in, X_ITE keeps showing the previous scene's last frame, so a sample taken then reports the old pixels (measured: a nothing-drawable scene after a drawing one read 8% and 21%); the page loads an empty world first and lets it clear. (3) The live 3D tab uses the same watcher as the offline pass and reads "no frame" as nothing drawable only when X_ITE printed dropped-node messages or the record says so; on a slow device it waits up to 12 s and says "NO FRAME YET".

The demo (`demo/`, page "Tether Firehose 2") replays this with live hashing, a validator ladder (service, then fork 8c0a457, then fork eb4b4b4, re-validating stored scenes "from the files alone" and flagging the stale verdicts), a tamper scrubber with signing on and off, a real X_ITE view of the selected scene beside its chain, and a share-safe switch; `demo/build_v2.py --share` produces a source-level clean variant. Not investigated: the 13 to 63 valid jump at fork 76fc439 and d61d4de (S).

## 9. Fourth pass: a recorded live run of real model calls (added 17 Oct 2026, 21:5x)

Method: five models (gemini-3.8-flash, gemini-3.1-pro-preview, gpt-6.1-sol; glm-5.3 and nemotron-3-super-120b-a12b on a free trial tier) were sent the same 50 prompts; every answer was validated in process on fork eb4b4b4; an invalid answer went back to the model with its own report, up to 3 attempts; every attempt was rendered offline in X_ITE 16.5.0 (the section 8 watcher). Data: `runs/live-2026-10-17/`, `demo/data/live.json`; tables in `LIVE-RUN-FINDINGS.md`; spend in `COST-LEDGER.md`. One run per prompt per model.

| Finding | Grade | Sample |
|---|---|---|
| With only the validator's report sent back, first-try valid 20, 57 and 77% becomes 98, 100 and 100% for the three paid models | Confirmed for the sample; Suspected as a rate | 50, 47 and 43 scenes, fork eb4b4b4 |
| 54 of the 119 first-try failures carried a profile-component error and it was gone after the next repair in 58 of 58 cases; XSD errors took more (76 gone, 55 still there) | Confirmed | 201 scenes |
| The median repair changes 7 tag lines (12% of the scene); 17 of 96 successful repairs rewrote more than half | Confirmed | 96 repairs |
| 7 of the 178 scenes valid at the end draw nothing: 2 proximity-lit, 4 geospatial, 1 H-Anim humanoid whose boxes hang off no joint (the loop converged on a scene that passes by saying less) | Confirmed for these scenes; the H-Anim pattern Suspected (one case) | X_ITE 16.5.0, each opened by hand |
| 10 of the 23 scenes that never became valid still draw something | Confirmed | X_ITE is more lenient than the validator |
| Validator median 1 ms, p90 5 ms, in process | Confirmed | 358 calls |
| Per valid scene (list-price estimate) gpt-6.1-sol 0.027, gemini-3.8-flash 0.033, gemini-3.1-pro-preview 0.103 USD | Likely | finished chains only |

What it changes in this document: section 5 (what a pipeline gains) now has a measured loop number, and section 3 (limits) a new honest one: the repair loop optimises for the checker, so a render check and an eyes-on pass stay in. Where tethering pays beyond X3D, and what to build next: `research/traceability-2026-10-17/WHERE-TETHERING-PAYS.md` (also a Claude Doc).
