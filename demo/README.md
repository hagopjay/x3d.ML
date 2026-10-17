# Tether Firehose 2: the traceability demo

One page (HTML, about 0.9 MB) plus X_ITE 16.5.0 published beside it as its own files (105 files, 8.5 MB, see `mkxite.py`). It shows a production stream of AI-written X3D scenes, each carrying its own hash-chained provenance record (`x3dprov`, see `../docs/DESIGN.md`). Everything on it is computed live in the browser: SHA-256 (pure JS), chain verification, the optional seal, the tamper scrubber, PROV-JSON / OpenLineage / OTLP projections, and a real X_ITE render of the scene you select. Dark first, light theme, phone-width safe, a guided tour (9 steps, about 90 s) and a share-safe switch that hides model names, cost, hardware and run ids.

Two modes. **Synthetic** simulates the stream (rates, models and defect mix are modelled; the three open-model first-try rates are measured). **Replay** streams the 174 real scenes from the 11 Oct GPU phase (3 open models, one-shot and grounded repair, 1x L4), each re-stamped from recorded facts, re-validated on three validators (the 11 Oct service, fork 8c0a457, fork eb4b4b4) and rendered for real in X_ITE (headless, software GL, offline, one fresh page per scene, a frame watcher registered before the load plus a screenshot check).

## What the replay measured (Confirmed for this sample; Suspected as a rate, three small open models only)

| | scenes | draw nothing |
|---|---|---|
| valid on the 11 Oct service (XSD + DEF/USE/ROUTE only) | 91 | **17 (18.7%)** |
| valid on fork 8c0a457 | 55 | 0 |
| valid on fork eb4b4b4 | 54 | 0 |
| flipped valid to invalid on 8c0a457 | 36 | 17 |

115 of 174 scenes draw something (36 of them after X_ITE warned that it dropped part of the file), 43 draw only blank frames after X_ITE dropped what it could not read (42 print "Unknown node type", 37 are Geospatial or HAnim nodes with no `<component>` statement), 4 more draw only blank frames, 12 do not parse (all 12 are not well-formed XML). The converse does not hold: only 54 of the 115 scenes that draw pass the fork, because X_ITE draws the rest of a scene it cannot fully read. *Valid is not visible; a stricter validator closes that gap on this sample, and visible is still not valid.* X_ITE renders on demand and starts every scene with blank frames: a scene with nothing drawable gets about 4 of them and then X_ITE idles, so the pass registers a watcher on X_ITE's end-of-frame event before the load and does not wait for any frame. Checks on the measurement: sampled frames and a screenshot agree on 160 of 162 scenes that parse (the two misses are animations visible only part of the cycle); the same pass on X_ITE 16.4.1 gives the same answer for 174 of 174; 12 blank scenes that kept animating were watched for 12 s and stayed blank. My first pass sampled only after 700 ms and described the blank scenes as "no frame"; that was wrong and is corrected in `../docs/DESIGN.md` section 8 (the first-pass data is kept in `data/pass1/`).

## Layout

| path | what |
|---|---|
| `tether-firehose-v2.template.html` | the page (placeholders `/*__REAL__*/[]`, `/*__XCSS__*/""`); loads `xite/x_ite.min.js` |
| `build_v2.py` | bakes template + `data/replay.json` + `data/x_ite.css` into one file; `--share` bakes a source-level clean variant (open-8B/14B/20B, no cost, no hardware, no private link) |
| `build_replay.py` | rebuilds `data/replay.json` from a render file, `../drift/verdicts_by_fork_commit.json` and the cached GPU-phase run (`GPU_PHASE_DIR`) |
| `mkxite.py` | assembles the X_ITE subset that works as published files (components, fonts, wasm, licence); needs `npm i x_ite@16.5.0` |
| `render/render_final3.py`, `render/render3.html` | the headless render pass over all 174 scenes (frame watcher before the load, screenshot check; `ONLY`, `SETTLE`, `MAXS` env for a longer look at chosen scenes) |
| `render/render_final2.py`, `render/render.html` | the first pass (one sample after 700 ms), superseded, kept for the record |
| `serve.py` | local rig: one origin on :8782 with a viewer-like Content-Security-Policy (own files only, no CDN); serves the render pages too |
| `tests/check_v2.py`, `tests/check_tour.py`, `tests/check_fallback.py`, `tests/mktest.py` | headless regression (40 checks, 15 for the tour, 11 for the no-X_ITE fallback; the 40 and the tour run on both the private and the `--share` build); `PAGE` env selects the build under test |
| `leak_sweep.py` | source sweep for names, costs, hardware, ids, links, keys and image stamps; `--share` must exit 0 |
| `data/` | `replay.json`, `renders3_x_ite_16.5.0.json`, `renders3_x_ite_16.4.1.json`, `renders3_extended_x_ite_16.5.0.json` (12 scenes, 12 s look), `pass1/` (first method), X_ITE stylesheet (MIT, licence beside it) |
| `releases/` | every page as published, never overwritten (`SHA256SUMS`) |

## Rebuild and test

```
cd demo && npm i x_ite@16.5.0 playwright && pip install pillow lxml playwright
python3 mkxite.py node_modules/x_ite/dist build/xite                          # 105 files, 8.5 MB
python3 build_v2.py data/replay.json data/x_ite.css build/v2.html            # private build
python3 build_v2.py data/replay.json data/x_ite.css build/v2.share.html --share
LEAK_IDS='<project id>|<run-as name>|<project number>' python3 leak_sweep.py build/v2.share.html --share   # must print RESULT: clean (the ids stay out of the repo)
python3 tests/mktest.py build/v2.html build/v2test.html                       # adds the doctype the publish step adds
python3 serve.py &                                                            # :8782
CHROME=<path if Playwright has none> python3 tests/check_v2.py && python3 tests/check_tour.py && python3 tests/check_fallback.py
# render pass again (about 5 minutes; serve.py running):
#   python3 render/render_final3.py data/renders3_x_ite_16.5.0.json
#   python3 build_replay.py data/renders3_x_ite_16.5.0.json data/replay.json data/renders3_x_ite_16.4.1.json   # EXT=<extended file> adds the 12 s look
# (the 16.4.1 pass needs that version's own files served instead: RENDER_URL=http://127.0.0.1:<port>/render3.html)
```

Publish: the page as `index.html` plus the 105 files of `build/xite/` as published files, nothing else.

## What is not real

Signing is an HMAC stand-in for the planned Ed25519 seal. The two frontier model rows, all prices, tokens and latencies in Synthetic mode are illustrative. Hashes on the page use a text-normalised hash, not the repo's lxml C14N hash, so the two do not match byte for byte. A last unsigned step can be edited undetected (the stated gap; a sealed scene catches it). Scene thumbnails are 192x144 JPEGs from a software-GL render, not a GPU render. The live 3D tab uses the same frame watcher as the offline pass (it needs X_ITE 16.5.0's `finishEvents`, `endEvents` in 16.4.1), swaps in an empty world first so the previous scene's last frame cannot be sampled, and reads "no frame" as "nothing drawable" only when X_ITE printed dropped-node messages or the offline record says so; otherwise it waits up to 12 s and reports "NO FRAME YET", because a very slow renderer looks the same as an empty scene. Not tested here: the real artifact viewer (its policy is mimicked by `serve.py`); fonts in Text nodes need `eval` for X_ITE's woff2 decoder, so they may not draw there.
