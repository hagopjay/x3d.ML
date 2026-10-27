# Gobbler 3 Deep: every connected entity, with fidelity notes

Built 27 October 2026 on top of `GRAPH-v3.md` (the 26 October build, which stays as it was). Private. Scene `deep/build-private/gobbler3.x3d`, page `deep/build-private/gobbler3.html`, public candidate `deep/build-public-candidate/` (review only, nothing published).

## What changed
- **All entities.** The scene now draws 2476 entities, not 604: 642 core entities with full ribbons, 999 star-tier entities with 1 to 2 faint tethers each, and 835 untethered stars (seen by two or more runs but with no relation that survived voting; placed by class, Suspected). The remaining 1283 of the 3761 assembled entities were seen once; they are in the page's search list and `graph-v3.json` marked "in the data, not drawn".
- **New sources.** 79 new chunks: the 27 October memory state (index and spine plan), the 27 October Gobbler 3 note, and the docs of the three repos in scope (x3d_mcp, x3d-blender-io, x3d.ml) plus the poc README. 237 new extraction runs, same prompt, schema and 3-run vote.
- **Typing fix.** GitHub owner handles had been typed Org because they were a repo prefix; lowercase single-token handles are now Person, and the two he asked about carry licence facts read from their public pages on 27 October 2026 (provenance data): ahujasid, MIT, README says "Contributions are welcome!"; coderextreme, John Carlson, BSD 3-clause (Copyright 2015-6 John Carlson).
- **Page.** Open-source neighbours panel; "show more" in the entity list; undrawn entities searchable.

## Numbers and where they come from
| Claim | Number | Source |
|---|---|---|
| Extraction runs | 726 over 239 chunks (3 per chunk), plus stale runs of 2 documents whose text changed | `evidence/runs/` |
| Claims raised | 10572 | merge.py |
| Dropped, evidence sentence not verbatim in the chunk | 1980 (18.7 percent; was 14.9 percent before the repo docs, whose tables quote loosely) | merge.py |
| Kept | 8511 | merge.py |
| Entity resolution | first pass 594 of 962 pairs agreed; incremental pass 104 of 115 pairs agreed over 881 new candidates; canon chained | `evidence/resolve/`, `canon.json` |
| Doc evidence lines found verbatim in the corpus | 1800 of 1800 (first 60 normalised characters) | checked at build time |
| Provenance of entities | {'doc': 2232, 'data': 123, 'model_recall': 61, 'simulated': 60} | graph_deep.json |
| Provenance of relations | {'doc': 1850, 'simulated': 196, 'data': 144, 'model_recall': 222} | graph_deep.json |
| Grades of relations | {'Likely': 463, 'Suspected': 285, 'Confirmed': 1664} | graph_deep.json |
| Loops | 19: 9 mined from documents (Likely), 10 simulated community loops (Suspected) | compose.py |
| Public candidate | 288 of 2476 drawn entities | visibility runs, both must agree, plus deny list |
| Gemini spend, whole build | about $11.8 at assumed list prices (cap $15) | `evidence/spend.jsonl` |

## Checks
- Scene: fork validator x3d_mcp `main` 2b696f5, XSD valid, profile ok, 0 errors, 0 warnings, 4 infos, on both builds.
- Render: X_ITE 16.5.1 in headless Chromium with SwiftShader (rig binds each Viewpoint and sets its position, so it is a scripted-viewpoint rig). The deep scene runs at about 6 frames a second in software GL against about 10 for the 604-entity build; real GPU speed untested. Note: the default headless-shell browser of the sandbox crashes on this scene while the full Chromium build renders it; treat low-end machines and headsets as untested.
- Page: search, filters, entity card, fly-to-star, loop ride exercised headless, no page errors.

## Limits
- Position is a layout (Fruchterman-Reingold in a widened cone), not a measurement; untethered stars are placed by class and are decoration of position, not of fact.
- Star-tier tethers are each entity's best 1 to 2 relations; all relations remain in the data.
- Nodes keep extraction phrasing; some are fragments from tables or code listings in the repo docs.
- Public candidate: 288 entities swept for model and vendor names, project ids, costs, private links and paths. It still contains public bibliographic facts (for example Don Brutzman as an author) and the creator tag HagopJay in the scene header, as v2 does. Review before any release.
