# Live run of 17 Oct 2026: findings

Private. Validator behind every number: x3d_mcp fork main eb4b4b4 (XSD plus semantic checks, in process). Renderer: X_ITE 16.5.0, headless, software GL, one offline pass over every attempt. Run record: `runs/live-2026-10-17/` (events.jsonl, x3d/, run.json, notes.json). Page data: `demo/data/live.json`. Grades follow `research/bug-reporting-protocol/PROTOCOL.md`. Spend and reconciliation: `docs/COST-LEDGER.md`.

## What was run

- 50 prompts (the 30 of the 11 Oct benchmark and 20 showpiece scenes) sent to 5 models in the same order: three paid (gemini-3.8-flash, gemini-3.1-pro-preview, gpt-6.1-sol) and two on a free trial tier (glm-5.3, nemotron-3-super-120b-a12b).
- Loop: validate on the fork; if invalid, send the model its own report and ask again, up to 3 attempts. One run per prompt per model.
- 201 finished scenes from 358 calls are on the page. 17 unfinished chains (3 stopped by the spend cap, 14 by the free lanes' time box) and 62 failed call rows (rate limits, gateway errors, retried) are in the ledger only.

## Findings

1. **Confirmed for this sample.** The loop closes the gap using only the validator's report. First-try valid to valid at the end: 20% to 98%, 57% to 100% and 77% to 100% for the three paid models (50, 47 and 43 scenes). On the 43 prompts every paid model finished: 19%, 58% and 77% to 100% each.
2. **Confirmed for this sample.** The two free-tier models did not close the gap inside their time box: glm 32% to 64% (25 scenes) and nemotron 11% to 64% (36 scenes). Coverage is partial and they are rate-limited (glm: 287 s median call, 28 of its 53 calls cut at the output limit), so they are not comparable with the paid lanes.
3. **Confirmed.** Most first-try failures are small and mechanical. 54 of the 119 scenes that failed first carried a profile-component error and it was gone after the next repair in 58 of 58 cases; XSD errors (97 scenes) took more: 76 gone, 55 still there after one repair. A deterministic fix for that class would touch 45% of the first-try failures (Likely; scenes that carry other errors as well still need a model call; not built yet).
4. **Confirmed.** Repairs are small. The median repair changes 7 tag lines (12% of the first attempt's tags); 17 of the 96 repairs that ended valid rewrote more than half of the scene.
5. **Likely** (list-price estimates, finished chains only). Per valid scene: gpt-6.1-sol 0.027 USD, gemini-3.8-flash 0.033, gemini-3.1-pro-preview 0.103. The best first-try model was also the cheapest per valid scene; the dearest was not the best.
6. **Confirmed for these scenes.** Valid is still not visible. 7 of the 178 scenes valid at the end draw nothing in X_ITE (under 0.5% of pixels differ from the background). Each was opened and read by hand: 2 proximity-lit scenes that stay dark until the viewer walks up (int-05, two models), 4 geospatial scenes whose content is tiny from the default camera (geo-02 twice, geo-03, geo-04), and 1 H-Anim humanoid whose boxes hang off no joint (nemotron, hanim-01: the loop converged on a scene that passes by saying less; a single case, Suspected as a pattern). The other way round, 10 of the 23 scenes that never became valid still draw something: X_ITE is more lenient than the validator.
7. **Confirmed.** The validator is not the bottleneck: median 1 ms, 90th percentile 5 ms over 358 in-process validations, against model calls of 25 to 287 s median.
8. **Suspected as rates.** One run per prompt: sampling noise is not measured, so the percentages describe these scenes, not the models.

## Tables

Output of `python3 demo/live/analyze.py demo/data/live.json --md`.

201 scenes from 358 calls, 5 models, 4610 s run clock (1109 s idle collapsed), validator fork@eb4b4b4, failed call rows 62

| model | scenes | calls | valid first try | repaired | valid at end | valid+blank | draw | tokens in | tokens out | est. spend | median call |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash | 50 | 92 | 10 (20%) | 39/40 | 49 (98%) | 3 | 46 | 134,197 | 399,826 | $1.60 | 24.5 s |
| gemini-3.1-pro-preview | 47 | 72 | 27 (57%) | 20/20 | 47 (100%) | 2 | 45 | 59,015 | 393,881 | $4.84 | 35.2 s |
| gpt-6.1-sol | 43 | 53 | 33 (77%) | 10/10 | 43 (100%) | 1 | 42 | 37,467 | 107,829 | $1.15 | 46.7 s |
| glm-5.3 | 25 | 53 | 8 (32%) | 8/17 | 16 (64%) | 0 | 18 | 27,938 | 317,787 | $0.00 | 287.2 s |
| nemotron-3-super-120b-a12b | 36 | 88 | 4 (11%) | 19/32 | 23 (64%) | 1 | 30 | 111,524 | 268,564 | $0.00 | 53.3 s |

valid within 1, 2, 3 attempts; list-price estimate per valid scene; calls cut off at the output-token limit
| model | scenes | valid at attempt 1 | by attempt 2 | by attempt 3 | est. $ per valid scene | calls cut at limit |
|---|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash | 50 | 10 (20%) | 48 (96%) | 49 (98%) | $0.033 | 4 |
| gemini-3.1-pro-preview | 47 | 27 (57%) | 42 (89%) | 47 (100%) | $0.103 | 8 |
| gpt-6.1-sol | 43 | 33 (77%) | 43 (100%) | 43 (100%) | $0.027 | 0 |
| glm-5.3 | 25 | 8 (32%) | 14 (56%) | 16 (64%) | - | 28 |
| nemotron-3-super-120b-a12b | 36 | 4 (11%) | 16 (44%) | 23 (64%) | - | 9 |

the 43 prompts every paid model finished
| model | scenes | valid first try | valid at end |
|---|---:|---:|---:|
| gemini-3.8-flash | 43 | 8 (19%) | 43 (100%) |
| gemini-3.1-pro-preview | 43 | 25 (58%) | 43 (100%) |
| gpt-6.1-sol | 43 | 33 (77%) | 43 (100%) |

by prompt category (all models)
| category | scenes | valid first try | valid at end |
|---|---:|---:|---:|
| object | 25 | 4 (16%) | 20 (80%) |
| hanim | 18 | 5 (28%) | 16 (89%) |
| showpiece | 78 | 29 (37%) | 66 (85%) |
| assembly | 25 | 11 (44%) | 22 (88%) |
| geospatial | 11 | 5 (45%) | 10 (91%) |
| interaction | 19 | 11 (58%) | 19 (100%) |
| animation | 25 | 17 (68%) | 25 (100%) |

first-try failure codes (scenes carrying the code, all models)
| code | scenes | by model |
|---|---:|---:|
| xsd | 97 | gemini-3.8-flash 36, nemotron-3-super-120b-a12b 30, glm-5.3 17, gemini-3.1-pro-preview 11, gpt-6.1-sol 3 |
| profile-component | 54 | nemotron-3-super-120b-a12b 23, gemini-3.1-pro-preview 10, gemini-3.8-flash 9, gpt-6.1-sol 8, glm-5.3 4 |
| containerfield-type-mismatch | 5 | nemotron-3-super-120b-a12b 3, gemini-3.8-flash 1, gpt-6.1-sol 1 |
| containerfield-unknown | 4 | nemotron-3-super-120b-a12b 2, gemini-3.8-flash 1, glm-5.3 1 |
| duplicate-def | 3 | nemotron-3-super-120b-a12b 3 |
| interpolator-key-length | 2 | nemotron-3-super-120b-a12b 1, gemini-3.8-flash 1 |
| tuple-count | 2 | nemotron-3-super-120b-a12b 2 |
| route-invalid-to-field | 2 | nemotron-3-super-120b-a12b 2 |
| route-invalid-from-field | 2 | nemotron-3-super-120b-a12b 2 |
| use-undefined-def | 1 | nemotron-3-super-120b-a12b 1 |
| route-type-mismatch | 1 | gemini-3.1-pro-preview 1 |

attempt 2 outcome per code that attempt 1 had: gone / still there
| code | gone | still there |
|---|---:|---:|
| xsd | 76 | 55 |
| profile-component | 58 | 0 |
| containerfield-type-mismatch | 6 | 1 |
| containerfield-unknown | 5 | 1 |
| duplicate-def | 3 | 2 |
| route-invalid-to-field | 3 | 1 |
| interpolator-key-length | 3 | 0 |
| tuple-count | 3 | 0 |
| route-invalid-from-field | 2 | 1 |
| use-undefined-def | 1 | 0 |

repairs that ended valid: 96; changed tag lines (added + removed) median 7, p90 79; share of the first attempt's tags: median 12%, p90 226%; rewrote more than half: 17

attempts per scene: {1: 82, 2: 81, 3: 38}
never valid after 3 attempts: 23 ['nemotron-3-super-120b-a12b/asm-01', 'nemotron-3-super-120b-a12b/asm-03', 'nemotron-3-super-120b-a12b/obj-02', 'nemotron-3-super-120b-a12b/obj-04', 'glm-5.3/obj-03', 'nemotron-3-super-120b-a12b/sp-03', 'nemotron-3-super-120b-a12b/sp-04', 'nemotron-3-super-120b-a12b/obj-05', 'gemini-3.8-flash/geo-05', 'nemotron-3-super-120b-a12b/sp-05', 'nemotron-3-super-120b-a12b/sp-06', 'nemotron-3-super-120b-a12b/sp-09', 'nemotron-3-super-120b-a12b/sp-07', 'glm-5.3/sp-06', 'glm-5.3/obj-05', 'glm-5.3/sp-02', 'glm-5.3/sp-04', 'glm-5.3/sp-05', 'glm-5.3/sp-03', 'glm-5.3/asm-01']

mean call: first 4364 out tokens, 72.4 s, $0.0263; repair 3889 out tokens, 89.5 s, $0.0147

valid on the fork but nothing (or almost nothing) drawn in X_ITE
| model | prompt | attempts | pixels differing | frames | X_ITE said |
|---|---:|---:|---:|---:|---:|
| gemini-3.8-flash | int-05 | 2 | 0 | 127 |  |
| gemini-3.8-flash | geo-03 | 2 | 0.0002 | 58 |  |
| gemini-3.8-flash | geo-02 | 2 | 0.0018 | 46 |  |
| gpt-6.1-sol | int-05 | 1 | 0.0045 | 137 |  |
| gemini-3.1-pro-preview | geo-02 | 1 | 0.002 | 181 |  |
| gemini-3.1-pro-preview | geo-04 | 2 | 0.0047 | 207 |  |
| nemotron-3-super-120b-a12b | hanim-01 | 3 | 0 | 4 |  |

invalid on the fork but X_ITE draws something: 10 of 23
first attempt valid but blank: 2 of 82

estimated spend of the scenes on the page: $7.60

## Reproduce

```
python3 demo/build_live.py runs/live-2026-10-17 demo/data/renders_live_x_ite_16.5.0.json demo/data/live.json
python3 demo/live/analyze.py demo/data/live.json --md
python3 demo/live/reconcile.py demo/data/live.json --md
```
