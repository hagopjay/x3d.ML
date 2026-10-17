# Traceability workstream: running log (newest last)
Validator: x3d_mcp fork main eb4b4b4. Bridge: x3d-blender-io main 206f139, bpy 5.2.2. Spend: $0.

- 2026-10-17 16:50Z thread opened (HagopJay: traceability + observability as an X3D win in real-time ML ops).
- 16:5x Read plans/data-spine-2026-10-15/schema.sql: spine already has `lineage` (PROV-style), `generations`, `validations`, `renders`. Bridge already round-trips head meta and Metadata* nodes (extract.scene_head_meta, emit_x3d40.head_meta).
- 17:0x Wrote x3dprov.py (hash-chained head metas). cube sample: ingest, validate (invalid: profile-component), deterministic header autofix, validate (valid), Blender round trip, validate; verifies. Tamper tests as designed.
- 17:1x Ran on 5 more scenes incl. 16.8 MB and 62 MB earth-twin campus files: 6 of 6 verify, record survives Blender in 6 of 6. Last-step edit undetected (documented limit).
- 17:2x Probe: per-node MetadataSet survives Blender (gets containerField=metadata), WorldInfo dropped.
- 17:3x export_prov.py: PROV-JSON + OpenLineage projections of the cube record. DESIGN.md written.
- NEXT (default, $0): stamp cached spine scenes (ask before reading the bucket), then fork tools provenance_stamp/verify and a bridge regression test as draft PRs. Open question for him: where should the library live.
- 17:3x (second pass, after "pls proceed") stamp_gpu_phase.py: 174 cached GPU-phase scenes (qwen3-8b, qwen2.5-coder-14b-awq, gpt-oss-20b; oneshot + grounded; run 11 Oct, vLLM on 1x L4) stamped from results/*.jsonl with real generate steps (run_id, hardware, tokens, latency, prompt sha, attempts) + the recorded historical verdict + a fresh verdict from fork eb4b4b4. All 174 verify. Scenes that are not well-formed XML (models do emit them) fall back to a text hash (x3dprov.content_hash).
- RESULT (C, corrected): the 11 Oct verdicts came from the deployed x3d-mcp-svc (weaker than the fork), not a fork build. Re-ran all 174 scenes on fork 8c0a457, c9c9788, 688174f, 76fc439, d61d4de, eb4b4b4, d5598c4 (drift/): 36 of 37 flips are already invalid on 8c0a457, 1 flips at 688174f (tuple-count). Counts match open-models-fork/README.md exactly. My earlier "fork rules added since" inference was wrong; fixed in DESIGN.md section 7 and the PR.
