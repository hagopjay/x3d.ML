# Gobbler 3: the knowledge graph, with its fidelity notes

Built 26 October 2026. Private. The scene is `build-private/gobbler3.x3d`; the page is `build-private/gobbler3.html` (needs the X_ITE vendor files, see README). `build-public-candidate/` is the filtered build for HagopJay to review; nothing has been published anywhere.

## What it is
A graph of PolyXandria and the X3D community that grows out of the gobbler's neck. 604 entities, 1179 relations, 15 flywheel loops drawn as wheels. The virtuous circle and the knowledge graph are the same structure here: loops are first-class (steps, centre node, `feeds` and `step_of` edges), and findings, rules, experiments and metrics are reserved places in the layout, so the flywheel is visible and not crowded out by hub tools.

## Where every number comes from
| Claim | Number | Source (Confirmed unless marked) |
|---|---|---|
| Corpus | 105 memory files plus docs, 163 chunks, SHA-256 list in `evidence/corpus-sha256.txt` | build log |
| Extraction | 489 runs (3 per chunk), temperature 0.55, strict closed schema of 19 classes and 35 predicates | `evidence/runs/` |
| Claims raised | 7078 | `evidence/merged.json` |
| Dropped because the evidence sentence was not verbatim in the chunk | 1055 (14.9 percent) | merge.py verbatim filter |
| Dropped for a predicate outside the schema | 44 | merge.py |
| Kept after filtering | 5949 | merge.py |
| Entity resolution | 3,303 raw names to 2,666 entities; 962 candidate pairs, 594 agreed by both runs, 363 merged groups | `evidence/resolve/`, `canon.json` |
| Data layers | spine 98 nodes and 120 edges from the BigQuery spine tables; ecosystem watch 25 nodes and 24 edges | provenance `data`, `layers.py` |
| Evidence lines in the drawn graph found verbatim in the source corpus | 695 of 695 (first 60 normalised characters) | checked at build time |
| Provenance of drawn entities | {'doc': 426, 'data': 112, 'model_recall': 6, 'simulated': 60} | `graph.json` |
| Provenance of drawn relations | {'doc': 717, 'simulated': 197, 'data': 144, 'model_recall': 121} | `graph.json` |
| Grades of drawn relations | {'Likely': 228, 'Suspected': 216, 'Confirmed': 735} | `graph.json` |

Grade rules (compose.py): a document relation seen by 2 or more of 3 runs is Likely, or Confirmed when the extractor also marked it as measured; relations seen once are dropped. A recalled relation needs all 3 runs for Likely, 2 for Suspected. Data-layer rows are Confirmed. Simulated hypotheses are always Suspected.

## The loops
- The flywheel: doc, Likely, votes 3, 5 steps
- Validator repair loop: doc, Likely, votes 2, 3 steps
- Five-step loop: doc, Likely, votes 3, 5 steps
- THE TETHER: doc, Likely, votes 3, 5 steps
- Discovery loop programme: doc, Likely, votes 3, 4 steps
- AI Code Generation & Validation: simulated, Suspected, votes 2, 5 steps
- Blender to Web Pipeline: simulated, Suspected, votes 2, 5 steps
- Standards Interoperability: simulated, Suspected, votes 2, 5 steps
- Ontology and Semantic Web: simulated, Suspected, votes 2, 5 steps
- Gaussian Splatting Integration: simulated, Suspected, votes 2, 5 steps
- Automated Benchmarking & Testing: simulated, Suspected, votes 2, 5 steps
- Archive Mirroring and Distribution: simulated, Suspected, votes 1, 5 steps
- Ecosystem Tooling and Linting: simulated, Suspected, votes 1, 5 steps
- Community Loop: simulated, Suspected, votes 1, 5 steps
- DSPy Loop: simulated, Suspected, votes 1, 5 steps

The 5 document loops were mined from the corpus and each appeared in at least 2 extraction runs of at least 2 chunks; their wording is quoted. The 10 simulated loops come from two independent runs asked for community flywheels; 6 themes appeared in both runs (votes 2), 4 in one (votes 1). They are tagged simulated and drawn dimmer; they are hypotheses, not findings. Simulated relations drawn: 91 (the loop edges of the 10 simulated loops plus the hypothesis edges). For the hypotheses, 3 runs proposed 75 missing links; pairs proposed by 2 or more runs are kept at weight 2, singles (capped at 45) at weight 1; all Suspected.

## Public candidate
121 of 604 entities are marked public (both visibility runs had to agree, plus a deny list for model and vendor names, spend, cloud resources, private links and unpublished work). Metric document names and private paths are dropped from the public JSON. One of fourteen visibility batches failed JSON parsing and defaulted to private, which is the safe direction. Swept for model and vendor names, project ids, dollar amounts, private links and paths: clean. It still names two public GitHub accounts of community maintainers (coderextreme, ahujasid) because they appear as maintainers of public repos; review before any release.

## Checks
- Scene: fork validator x3d_mcp `main` 2b696f5 on both builds: XSD valid, profile ok, 0 errors, 0 warnings, 4 infos. Scriptless X3D 4.0, 205 nodes, 76 ROUTEs, 6 shaders (receipts beside each build).
- Render: X_ITE 16.5.1, headless Chromium with SwiftShader software GL; the test rig binds each Viewpoint and then sets its position, so it is a scripted-viewpoint rig, not viewAll. All six views drawn with no console errors beyond one 404 for an optional asset. About 9 to 11 frames a second in software GL; a real GPU is faster. Not tested in a headset (Likely fine: scale is in metres, the head is about 7.5 m tall).
- Page: search, filters, entity card, fly-to-star and loop ride exercised headless with no page errors.

## Limits
- Position in 3D is a layout (Fruchterman-Reingold in a cone out of the neck), not a measurement.
- Only 604 of 2,734 assembled entities are drawn; selection is by degree and mentions with reserved room for findings, rules, experiments and decisions. Everything is in `graph.json` and `merged.json`.
- Model prices in `spend.jsonl` are assumed list prices (about $9.4 of the $15 cap).
- The Gemini model names, entity-extraction prompts and costs are in the private evidence only; the public candidate carries none.
- Node notes come from extraction and can carry memory-file phrasing (for example an instruction to add a repo); they are quoted from the sources, not cleaned.
