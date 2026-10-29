# Live run 2 findings (24 Oct 2026)

Second recorded tether run, free lanes only, no spend. Validator: fork `8dd0d3e` (hagopjay/x3d_mcp main, XSD plus the 14 semantic checks). Render: X_ITE 16.5.0, SwiftShader, viewAll rig, frame watcher registered before the load (`demo/render/render_final3.py`). Data: `runs/live-2026-10-24/`, `demo/data/live2.json`, `demo/data/renders_live2_x_ite_16.5.0.json`, `demo/data/renders_live2_extended_x_ite_16.5.0.json`. Every number below is for this sample under this rig; grades follow the project rule (Confirmed, Likely, Suspected).

## What was run

- 50 prompts, 4 lanes (two Nemotron sizes, one MiniMax, one GLM), 2 arms, 2 samples: 600 chains planned, 150 min wall, cap 1 USD (unused: 0 USD).
- Arm A: model repair with the validator report (as on 17 Oct). Arm B: the fork's deterministic autofix runs first on an invalid first attempt, then the model repairs what is left.
- 273 chains finished inside the wall (621 model calls, 93 autofix steps, 2 failed calls, 7 chains cut by the wall). The MiniMax and GLM lanes were slow (median call 146 s and 285 s) and only their arm A segment got through, so the arm comparison is Confirmed on the two Nemotron lanes only and Likely as a general statement.

## Findings

1. **Autofix-first lifts the weaker lane most (Confirmed, this sample).** Nemotron 3.5 super VL: valid at the end 42% (A) to 64% (B); by attempt 2, 25% to 48%. Nemotron 3 ultra: 76% (A) to 81% (B). The autofix step alone finishes the job rarely (6 of 46 and 1 of 47 chains valid right after it) but it removes every profile-component error (129 of 129 gone at the next step), so the model's repair call spends its tokens on the XSD errors instead.
2. **XSD errors are the sticky class (Confirmed).** Across all repair steps the XSD code went away 110 times and stayed 289 times; every other code is cleared more often than it stays.
3. **The dark seven again (Confirmed for six, Likely for one).** 163 bodies are valid on the fork; 7 of them draw nothing in X_ITE under the viewAll rig: hanim-02 twice, hanim-05 twice, geo-04 twice, obj-05 once (0.05% of pixels). The 17 Oct run had 7 of 178. An extended pass (12 s settle, 90 samples) confirms six at 0 pixels; one geo-04 body lit 11.6% of the pixels in a single frame callback and 0 on the screenshot, so it flickers rather than draws (Likely blank). The two hanim-05 bodies end their first 4 frames and idle, the signature of nothing drawable; the hanim-02 and geo-04 bodies keep rendering 700 frames of nothing.
4. **Invalid is not the same as invisible either.** 42 of the 109 chains that never became valid still draw something; 83 of the 714 bodies could not be parsed by X_ITE at all (unparseable XML from truncated outputs).
5. **Output limits bite the free lanes.** 172 calls were cut at the 8,000 output-token limit; MiniMax was cut on 64 of 88 calls and ended with 1 valid chain of 31.
6. **Category order holds.** Assembly and animation prompts are easiest (51% and 38% valid first try), hanim and geospatial hardest (0% first try, under 50% at the end), the same order as 17 Oct.

## Tables (demo/live/analyze.py over live2.json)

272 chains from 621 model calls, 6 lane(s) (4 models, arms A,B, samples 2), 9301 s run clock (0 s idle collapsed), validator fork@8dd0d3e, failed call rows 2 (1 shown as steps), 93 autofix steps, 7 cut chains kept, 1 chains with no verdict at all

| lane | chains | calls | valid first try | repaired | valid at end | valid+blank | draw | tokens in | tokens out | est. spend | median call | median first token |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| glm-5.3 A | 11 | 25 | 2 (18%) | 4/9 | 6 (55%) | 0 | 8 | 17,621 | 146,190 | $0.00 | 284.8 s | 208.8 s |
| nemotron-3-ultra-550b-a55b A | 68 | 133 | 22 (32%) | 30/46 | 52 (76%) | 2 | 58 | 188,864 | 411,221 | $0.00 | 35.6 s | 23.2 s |
| nemotron-3-ultra-550b-a55b B | 64 | 127 | 18 (28%) | 34/46 | 52 (81%) | 2 | 56 | 262,422 | 426,168 | $0.00 | 38.0 s | 25.3 s |
| nemotron-3.5-super-vl-120b-a12b A | 48 | 126 | 4 (8%) | 16/44 | 20 (42%) | 0 | 36 | 137,678 | 587,957 | $0.00 | 43.4 s | 26.2 s |
| nemotron-3.5-super-vl-120b-a12b B | 50 | 122 | 3 (6%) | 29/47 | 32 (64%) | 3 | 36 | 138,055 | 632,503 | $0.00 | 47.4 s | 33.0 s |
| minimax-m3.1-flash A | 31 | 88 | 0 (0%) | 1/31 | 1 (3%) | 0 | 4 | 79,900 | 611,615 | $0.00 | 146.1 s | 64.8 s |

valid within 1, 2, 3 model attempts (arm B: the autofix step counts with attempt 1); list-price estimate per valid scene; calls cut off at the output-token limit
| lane | chains | valid at attempt 1 | by attempt 2 | by attempt 3 | est. $ per valid scene | calls cut at limit |
|---|---:|---:|---:|---:|---:|---:|
| glm-5.3 A | 11 | 2 (18%) | 5 (45%) | 6 (55%) | - | 10 |
| nemotron-3-ultra-550b-a55b A | 68 | 22 (32%) | 47 (69%) | 52 (76%) | - | 15 |
| nemotron-3-ultra-550b-a55b B | 64 | 24 (38%) | 41 (64%) | 52 (81%) | - | 14 |
| nemotron-3.5-super-vl-120b-a12b A | 48 | 4 (8%) | 12 (25%) | 20 (42%) | - | 29 |
| nemotron-3.5-super-vl-120b-a12b B | 50 | 4 (8%) | 24 (48%) | 32 (64%) | - | 40 |
| minimax-m3.1-flash A | 31 | 0 (0%) | 1 (3%) | 1 (3%) | - | 64 |

autofix step (arm B): chains that were invalid at attempt 1 and went through the fork's deterministic repair before any model repair
| lane | autofix steps | valid right after autofix | model repaired the rest | median ms | median changes | change kinds | with unfixable | fixer errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nemotron-3-ultra-550b-a55b B | 46 | 6 (13%) | 28/40 | 1 ms | 1 | component 27, containerField 3 | 11 | 7 |
| nemotron-3.5-super-vl-120b-a12b B | 47 | 1 (2%) | 28/46 | 1 ms | 1 | component 33, containerField 4 | 8 | 18 |

by prompt category (all lanes)
| category | chains | valid first try | valid at end |
|---|---:|---:|---:|
| hanim | 20 | 0 (0%) | 9 (45%) |
| geospatial | 19 | 0 (0%) | 9 (47%) |
| object | 40 | 4 (10%) | 26 (65%) |
| showpiece | 108 | 13 (12%) | 58 (54%) |
| interaction | 24 | 4 (17%) | 12 (50%) |
| animation | 26 | 10 (38%) | 20 (77%) |
| assembly | 35 | 18 (51%) | 29 (83%) |

first-try failure codes (chains carrying the code, all lanes)
| code | chains | by model |
|---|---:|---:|
| xsd | 194 | nemotron-3.5-super-vl-120b-a12b 83, nemotron-3-ultra-550b-a55b 72, minimax-m3.1-flash 31, glm-5.3 8 |
| profile-component | 112 | nemotron-3-ultra-550b-a55b 54, nemotron-3.5-super-vl-120b-a12b 48, minimax-m3.1-flash 6, glm-5.3 4 |
| containerfield-type-mismatch | 12 | nemotron-3.5-super-vl-120b-a12b 7, nemotron-3-ultra-550b-a55b 5 |
| containerfield-unknown | 7 | nemotron-3-ultra-550b-a55b 3, minimax-m3.1-flash 2, nemotron-3.5-super-vl-120b-a12b 2 |
| route-invalid-from-field | 7 | nemotron-3.5-super-vl-120b-a12b 4, nemotron-3-ultra-550b-a55b 2, glm-5.3 1 |
| duplicate-def | 5 | nemotron-3.5-super-vl-120b-a12b 4, nemotron-3-ultra-550b-a55b 1 |
| tuple-count | 4 | nemotron-3.5-super-vl-120b-a12b 2, nemotron-3-ultra-550b-a55b 2 |
| route-type-mismatch | 4 | nemotron-3-ultra-550b-a55b 3, nemotron-3.5-super-vl-120b-a12b 1 |
| route-invalid-to-field | 2 | nemotron-3.5-super-vl-120b-a12b 1, nemotron-3-ultra-550b-a55b 1 |
| route-missing-from-node | 2 | minimax-m3.1-flash 1, nemotron-3.5-super-vl-120b-a12b 1 |
| interpolator-key-length | 1 | nemotron-3-ultra-550b-a55b 1 |
| use-before-def | 1 | nemotron-3-ultra-550b-a55b 1 |

next step's outcome per code the previous step had (a model repair or the autofix step): gone / still there
| code | gone | still there |
|---|---:|---:|
| xsd | 110 | 289 |
| profile-component | 129 | 0 |
| containerfield-type-mismatch | 16 | 2 |
| containerfield-unknown | 13 | 4 |
| route-invalid-from-field | 6 | 4 |
| duplicate-def | 6 | 3 |
| tuple-count | 4 | 5 |
| route-type-mismatch | 6 | 3 |
| route-invalid-to-field | 2 | 2 |
| use-before-def | 2 | 1 |

repairs that ended valid: 114; changed tag lines (added + removed) median 25, p90 117; share of the first attempt's tags: median 82%, p90 122%; rewrote more than half: 69

model calls per chain: {1: 59, 2: 77, 3: 136}
not valid at the end: 109 ['nemotron-3.5-super-vl-120b-a12b/A/obj-01', 'minimax-m3.1-flash/A/obj-01', 'minimax-m3.1-flash/A/sp-01', 'nemotron-3-ultra-550b-a55b/A/sp-02', 'nemotron-3.5-super-vl-120b-a12b/A/obj-03', 'nemotron-3.5-super-vl-120b-a12b/A/sp-02', 'nemotron-3-ultra-550b-a55b/B/sp-03', 'nemotron-3-ultra-550b-a55b/B/obj-05', 'minimax-m3.1-flash/A/obj-02', 'nemotron-3-ultra-550b-a55b/A/sp-03', 'minimax-m3.1-flash/A/sp-02', 'nemotron-3.5-super-vl-120b-a12b/A/sp-03', 'nemotron-3.5-super-vl-120b-a12b/A/obj-04', 'nemotron-3-ultra-550b-a55b/A/sp-04', 'nemotron-3.5-super-vl-120b-a12b/B/sp-03', 'glm-5.3/A/obj-01', 'nemotron-3.5-super-vl-120b-a12b/B/obj-05', 'minimax-m3.1-flash/A/obj-03', 'nemotron-3.5-super-vl-120b-a12b/A/obj-05', 'minimax-m3.1-flash/A/obj-04']

mean call: first 4832 out tokens, 75.8 s, $0.0000; repair 4302 out tokens, 65.6 s, $0.0000

failed calls shown as steps, by status: 502: 1

valid on the fork but nothing (or almost nothing) drawn in X_ITE
| lane | prompt | steps | pixels differing | frames | X_ITE said |
|---|---:|---:|---:|---:|---:|
| nemotron-3-ultra-550b-a55b A | obj-05 | 2 | 0.0005 | 57 |  |
| nemotron-3-ultra-550b-a55b B | hanim-02 | 4 | 0 | 200 |  |
| nemotron-3-ultra-550b-a55b A | hanim-05 | 3 | 0 | 4 |  |
| nemotron-3.5-super-vl-120b-a12b B | hanim-02 | 3 | 0 | 202 |  |
| nemotron-3-ultra-550b-a55b B | geo-04 | 4 | 0 | 161 |  |
| nemotron-3.5-super-vl-120b-a12b B | hanim-05 | 4 | 0 | 4 |  |
| nemotron-3.5-super-vl-120b-a12b B | geo-04 | 3 | 0 | 194 |  |

invalid on the fork but X_ITE draws something: 42 of 109
first attempt valid but blank: 0 of 49

estimated spend of the chains on the page: $0.00
