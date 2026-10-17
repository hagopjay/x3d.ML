# x3d.ML

X3D traceability and observability for ML pipelines. Private, early.

Core idea: X3D is the 3D format an AI can be held accountable to. A hash-chained provenance record
(`x3dprov`) rides inside the scene's own `<head><meta>` lines, survives the Blender round trip, and is
checked by `verify()`. See `docs/DESIGN.md` for the record, the PROV / OpenLineage / C2PA comparison and
the measured results, and `docs/LOG.md` for the running log.
