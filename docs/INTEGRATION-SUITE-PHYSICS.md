# Plan: test runs as provenance evidence (export suite + physics stress)

17 Oct 2026. Branch `feat/suite-physics-provenance`. Grades as in DESIGN.md (C confirmed, L likely, S suspected). Code: `src/ingest_runs.py` (library + CLI), `src/demo_runs.py` (run over the local data), `tests/test_ingest_runs.py`. Evidence: `runs/suite-physics-2026-10-17/`. Run with a python that has lxml (x3d_mcp's venv): `python -m pytest tests -q`, `python src/demo_runs.py <work-dir> <outdir> <stamped-dir> --blender-io <repo>`.

## What a test run should look like

A run is a scene's history, so it gets the same record: one `x3dprov` chain, step JSON in head metas, checked by the unchanged `verify()`. Two data sources, two carriers.

| | export suite (194 cases, Blender 5.1.0) | physics stress (3 agents, JSONL) |
|---|---|---|
| Carrier | the exported scene itself, one chain per profile file (`x3d_suite_main.x3d`, `_crease`, `_x41`) | a ledger scene with no geometry (`<WorldInfo>` only); the chain is the content |
| Step 1 `ingest` | file bytes sha256, size, exporter (`X3D Blender I/O v2.6.1`), Blender, export options and seconds, manifest sha256, repo sha + dirty flag at ingest | sha256 + size of every metrics, findings and report file; machine and tool versions from the `env` suite (Blender, x3d_mcp sha, bridge sha, python) |
| Middle | `validate`: `validate_x3d_export.py` 2.0.0, its sha256, verdict, counts per tier, every case id with its verdict, messages of failed cases | one `measure` step per (agent, suite): record count, sha256 of the canonical records, and every (case, metric, params) group as its median over repeats; one `judge` step per findings file (id, severity, component, hash of the text) |
| Last step | `summary` (redundant roll-up so the `validate` step, which holds the verdicts, has a successor) | `summary` (same idea) |

Two checks, kept apart on purpose. `verify()` says the chain and the carrier are intact. `audit()` rebuilds the expected steps from the source files and compares: it names the suite, case and metric that differ. A metric edited in the JSONL leaves the chain intact (the chain cannot see files it does not carry); a metric edited inside the record breaks it (`broken-chain`).

## Where the data and DESIGN.md meet badly (noted, not bent)

1. DESIGN section 2 names `validate` fields `xsd`, `xsd_valid`, `semantic_error_codes`. The suite validator is a conformance checker (exporter output against a manifest), not an XSD or semantic validator, so those fields are left out rather than invented. `verdict` keeps its vocabulary: `valid` iff no CORE case FAIL or ERROR; WARN, MISSING and NEW are informational and counted.
2. `op` has no value for a measurement. `measure` and `summary` are added as free-text values; `verify()` never reads `op`. Open question whether DESIGN.md should list them.
3. A ledger scene has no content that changes, so every step has `input_sha256 == output_sha256`. The hash binds the empty carrier, not the metrics; the metrics are bound by `prev` only.
4. The repo sha is read at ingest, not at run time (the runs predate it). Each record says so (`predates_run`). The physics `env` suite is the only run-time source and is used as such; its x3d_mcp sha is eb4b4b4, the fork commit DESIGN.md quotes, while the current x3d_mcp checkout is cf84f64.
5. DESIGN quotes Blender 5.2.2 for the round trip; these runs use 5.1.0. Both are recorded per run.

## Not in this change

No Ed25519 sealing, no XSD/semantic validation of the exported scenes (x3d_mcp), no push. Checked once by hand, not in the tests: the ledger carrier is XSD-valid with no semantic errors on x3d_mcp fa0b389 (the first draft was not: `WorldInfo` is outside profile Core, so the carrier is `Interchange`), and `export_prov.py` projects the 29-step ledger unchanged.
