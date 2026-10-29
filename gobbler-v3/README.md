# Gobbler 3

A knowledge graph of PolyXandria and the X3D community, growing out of the gobbler's neck as a scriptless X3D 4.0 scene, with the flywheel loops drawn as wheels. Read `GRAPH-v3.md` first: it says where every number comes from.

- `build-private/` the full build (604 entities, 1,179 relations, 15 loops): `gobbler3.x3d`, `gobbler3.html`, `graph-v3.json`, `graph-v3.jsonld`, validator receipt.
- `build-public-candidate/` the filtered build (121 entities) for review. Nothing here has been published.
- `shots/` the six viewpoints (Wide, Colossus, Eye, Inside, Flywheel, Crown), headless render, 1600x900.
- `evidence/` raw extraction runs, community runs, entity-resolution runs, merged claims, canon map, spend ledger, corpus SHA-256 list.
- `kg/` the pipeline: `extract.py`, `community.py`, `merge.py`, `resolve.py`, `layers.py`, `enrich.py`, `hypo2.py`, `loops2.py`, `loops3.py`, `compose.py`, `layout.py`.
- `tools/` `build_gobbler_v3.py` (graph to X3D, validates with the fork validator), `build_page.py` (page, JSON, JSON-LD, public filter), `shoot.mjs`, `pagetest.mjs`.

Rebuild (from a scratch copy that holds `corpus/`, `data/` and the Gemini client credentials of the session):

    python3 -I kg/extract.py; python3 -I kg/community.py; python3 -I kg/merge.py; python3 -I kg/resolve.py; python3 -I kg/merge.py
    DUMP=1 python3 -I kg/compose.py; python3 -I kg/enrich.py; python3 -I kg/hypo2.py; python3 -I kg/loops2.py; python3 -I kg/loops3.py; cp extra_new.json extra.json
    NMAX=640 EMAX=2000 python3 -I kg/compose.py graph.json
    python3 -I tools/build_gobbler_v3.py --graph graph.json --out out
    python3 -I tools/build_page.py --graph graph.json --scene out/gobbler3.x3d --out page   # add --public for the filtered build
    # the page needs vendor/x_ite (x_ite.min.js, x_ite.css, assets/) next to it; copy from the x3d.poc site

Rules kept: v1 and v2 of the gobbler are untouched; nothing sent outside; the public candidate carries no model or vendor names, project ids, costs or private links.

## Deep build (27 October 2026)
`deep/` holds Gobbler 3 Deep: every connected entity drawn (2,476 stars, 3,759 entities searchable), 19 loops, new sources (docs of the three repos), typing fix for GitHub handles, open-source neighbours panel. Read `deep/GRAPH-v3-deep.md`. Build with `ALL=1 NMAX=650 EMAX=1900 python3 -I kg/compose.py graph.json` (after `INCR=1 PYTHONHASHSEED=0 python3 -I kg/resolve.py` for new corpus, `kg/vis2.py` for visibility of new entities). The 26 October build above is untouched.
