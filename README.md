# x3d.ML

X3D traceability and observability for ML pipelines. Private, early.

Core idea: X3D is the 3D format an AI can be held accountable to. A hash-chained provenance record
(`x3dprov`) rides inside the scene's own `<head><meta>` lines, survives the Blender round trip, and is
checked by `verify()`. See `docs/DESIGN.md` for the record, the PROV / OpenLineage / C2PA comparison and
the measured results, and `docs/LOG.md` for the running log.

## Demo

`demo/` holds "Tether Firehose 2": a live page that streams AI-written scenes with their provenance chains, replays 174 real runs, re-validates them on three validators, renders each in X_ITE and tampers with them on cue. See `demo/README.md`. Headline (Confirmed for the sample, Suspected as a rate): of 91 scenes the 11 Oct service called valid, 17 draw nothing; of 54 valid on fork eb4b4b4, none.
