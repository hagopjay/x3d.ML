# x3d.ML

X3D traceability and observability for ML pipelines. Private, early.

Core idea: X3D is the 3D format an AI can be held accountable to. A hash-chained provenance record
(`x3dprov`) rides inside the scene's own `<head><meta>` lines, survives the Blender round trip, and is
checked by `verify()`. See `docs/DESIGN.md` for the record, the PROV / OpenLineage / C2PA comparison and
the measured results, and `docs/LOG.md` for the running log.

## Demo

`demo/` holds "Tether Firehose 2" and "Tether Firehose 3" (v3 adds a recorded live run of 358 real model calls on five models, 17 Oct 2026; see `docs/LIVE-RUN-FINDINGS.md` and `docs/COST-LEDGER.md`): a live page that streams AI-written scenes with their provenance chains, replays 174 real runs, re-validates them on three validators, renders each in X_ITE and tampers with them on cue. See `demo/README.md`. Headline (Confirmed for the sample, Suspected as a rate): of 91 scenes the 11 Oct service called valid, 17 draw nothing; of 54 valid on fork eb4b4b4, none.

## Test runs as evidence

`src/ingest_runs.py` turns an X3D export-suite run and the physics-stress metrics into `x3dprov` chains, and `audit()` checks a chain against the files it came from. Plan and caveats: `docs/INTEGRATION-SUITE-PHYSICS.md`; a run over the local data: `runs/suite-physics-2026-10-17/`; tests: `tests/` (needs lxml).

## Standards views

`src/x3dprov_provo.py` maps a chain to W3C PROV-O (Turtle, JSON-LD) with OWL-Time and back, losslessly; `src/x3dprov_openlineage.py` emits OpenLineage RunEvents for a lineage server. Shapes and schemas in `schemas/`; results in `docs/DESIGN.md` section 10. Tests need lxml, rdflib, pyshacl, jsonschema (`pip install lxml rdflib pyshacl jsonschema rfc3339-validator rfc3987 pytest`).
