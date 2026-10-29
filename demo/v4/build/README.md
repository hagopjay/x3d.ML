# Tether Firehose 4: data build (`demo/v4/build/`)

The data layer of the v4 page (SPEC sections 7.4, 7.5 and 8). Six scripts, run in this order from the repo root, no network, no spend; each reads the recorded files and writes only under `demo/v4/`. Nothing under `demo/data/`, `demo/build/`, `demo/releases/`, `demo/jsval/`, `demo/live/` or `runs/` is modified. Every number the page displays as a headline is computed here from the files and carried as `expected`; the page's `compute()` must reproduce it or the claim chip goes red.

```
python3 -I demo/v4/build/build_events.py
python3 -I demo/v4/build/merge_renders.py
python3 -I demo/v4/build/hero.py
python3 -I demo/v4/build/claims.py --tree <x3d_mcp checkout at 8dd0d3e>      # or X3D_MCP_TREE=...
python3 -I demo/v4/build/build_parts.py [--run2 demo/data/live2.json]
python3 -I demo/v4/build/mirror_to_project.py
```

**build_events.py** (SPEC 8 step 1) reads `runs/live-2026-10-17/{events.jsonl, run.json, notes.json}`, `demo/live/ledger.jsonl` and `demo/data/live.json` and writes `demo/v4/data/events.json`: the 62 failed calls as `{m, p, k, t0, t1, kind}` on the run clock with `kind` in {429, 502, credit} computed from the error text (the text itself never leaves the script: it can carry a provider function id and an account string), the 17 cut chains with `reason` cap / time box from the lane stop reasons, the 46 ledger probe rows reduced to an HTTP code, the idle-collapse table (`[[gap start, gap end, seconds removed]]`, computed exactly as `demo/build_live.py` does: intervals `(t0, v1)` of the 358 attempts on the page, a stretch over 30 s with nothing in flight kept as 3 s) and the credit stop (first insufficient-credits row: run clock 1155.8 s, real 20:34:43Z, 11 calls refused). It asserts that its clock lands every one of the 358 attempts on the `A[].t0` live.json already shows, then reconciles the ledger the way `demo/live/reconcile.py` does: 464 ledger calls in the run window, 358 on the page, 106 not = 62 failed (events.jsonl) + 25 calls in the 17 cut chains + 19 retries the call layer made before logging one event (14 stream timeouts, 4 connection drops, 1 rate limit; glm 18, nemotron 1). Ledger USD 8.1079 vs page 7.5978; the difference is the cut gemini-3.1-pro chains (0.51 USD).

**merge_renders.py** (SPEC 8 step 2) reads the two offline X_ITE passes over the 383 live attempts (`renders_live_x_ite_16.5.0.json`, `renders_live_x_ite_16.5.1.json`) and the 16.5.1 pass over the 174 replay scenes (`renders3_x_ite_16.5.1.json`), keyed `<model slug>/<prompt>_a<k>.x3d` and `<model>/<mode>/<prompt>.x3d`. Writes `renders.series.json` (16.5.0 `series[20], first, last, frames, nonblank` per live attempt) and `renders.151.json` (`{nb, frames, first, last, err, series, unknown}` per live attempt and per replay scene; replay keys give the page `r.nb151`). No thumbnail bytes and no page URL leave these files (asserted). Cross-check printed: the draw / blank / unparsable class agrees with 16.5.0 on 383 of 383 live and 174 of 174 replay.

**hero.py** (SPEC S1 item 8, section 5 item 5) runs `hero_pick()` over `live.json`: final attempt valid on fork@eb4b4b4, `r.nb >= .05`, `r.nodes >= 20`, one per prompt (most nodes wins), cap 12, nb descending, the opening scene sp-09 moved first. Writes `hero.json` (`idx, m, p, c, k, pt, body, jpg, nb, nb151, frames, last, ok, u, calls, nodes, codes, finding, fix, rl, vms1, vmsN, key, text`) and `rigok.json`, the staging opt-outs computed statically from the XML of the 201 final bodies with lxml (`resolve_entities=False`, `no_network=True`): rigOk is false for any Geo\* node, HAnim\* node, ProximitySensor, `NavigationInfo type NONE`, `Viewpoint jump=false` or a body lxml cannot parse; bbox finiteness needs a renderer and stays null. Bodies are model output, so run it with `python3 -I`.

**claims.py** (SPEC 0 rule 1, 8 step 4) ports the v3 page's `LIVESTATS` and `REALSTATS` to Python line for line (JS median = sorted value at `n >> 1`, `Math.round` percentages) and computes every headline claim's `expected` with its rule in words and grade: `c.rates`, `c.seven` (ids printed), `c.ratio`, `c.calls`, `c.failed`, `c.cut`, `c.canary` (reads `drift/verdicts-8dd0d3e.json` and runs `drift/canary.py` against the given checkout; without a checkout `flips` is written as null, never guessed), `c.truncated`, `c.replay17`, `c.lockstep` (null until module 04 ships). Also the per-lane table, the Sankey of first-try codes and their fate after each repair, and the seven blank-valid scenes with both passes' numbers. Writes `stats.json`.

**build_parts.py** (SPEC 7.4, 7.5, 8 step 5) packs each part as gzip (level 9, mtime 0) + base64 on one line into `demo/v4/parts/<name>.txt`, decodes each file back and compares sha256 before writing `parts/manifest.json` (`bytes_raw, bytes_gz, bytes_b64, sha256` of the decoded bytes, `rows, source, recorded, validator, xite, file` per part; `canary {bodies, flips, set}` from stats.json; `HAS_CYCLES` false; `HAS_RUN2` false unless `--run2 <live2.json>` is given, which packs the 24 Oct run as `parts/live2.txt` once `build_live.py` has written it; it was not run while that run records).

**mirror_to_project.py** (SPEC 8 step 7) copies JSON, JSONL and X3D only, with `cp`, into `/mnt/project-files/research/traceability-2026-10-17/firehose4/{data, data/v4, drift, runs/2026-10-17, runs/suite-physics-2026-10-17}`; anything else, and any file whose first bytes are PNG / JPEG / GIF / SVG, is refused (the shared folder C2PA-stamps images). The parts are not mirrored (derived). The mount is only written and stat-ed, never listed or grepped recursively. Last run: 414 files, 10,919,716 B, 0 refused. `--run runs/live-<date>` adds a finished run later.

## Outputs, measured 24 Oct 2026

| file | bytes | rows | notes |
|---|---:|---:|---|
| `demo/v4/data/events.json` | 14,018 | 62 failed + 17 cut + 46 probes | kinds 502: 28, 429: 23, credit: 11; cut: time box 14, cap 3; 4 idle gaps, 1109.3 s removed |
| `demo/v4/data/renders.series.json` | 72,407 | 383 | 16.5.0 |
| `demo/v4/data/renders.151.json` | 110,524 | 383 live + 174 replay | 16.5.1 |
| `demo/v4/data/hero.json` | 159,687 | 12 | sp-09, sp-04, sp-20, sp-19, asm-05, sp-10, asm-03, sp-15, asm-04, sp-16, sp-13, sp-05 |
| `demo/v4/data/rigok.json` | 31,857 | 201 | 157 pass the static rules; Geo 11, HAnim 17, ProximitySensor 5, not well-formed 11; own Viewpoint 188; Text 6 |
| `demo/v4/data/stats.json` | 11,156 | 10 claims | see table below |
| `demo/v4/parts/manifest.json` | 4,722 | 11 parts | canary 558 bodies, 0 flips |

| part | source | raw B | gz B | published B | sha256 | rows |
|---|---|---:|---:|---:|---|---:|
| `live.core` | live.json minus B[] and r.jpg | 336,481 | 66,429 | 88,572 | d287b58e | 201 |
| `live.bodies` | live.json B[] | 1,373,727 | 121,917 | 162,556 | 6499f2a9 | 358 |
| `live.jpg` | live.json A[].r.jpg | 885,665 | 370,091 | 493,456 | 7a05f8b6 | 286 |
| `replay` | replay.json | 826,599 | 183,532 | 244,712 | ebb06fe2 | 174 |
| `events` | events.json | 14,018 | 2,744 | 3,660 | 11937f73 | 125 |
| `renders.series` | renders.series.json | 72,407 | 14,139 | 18,852 | af2c7de5 | 383 |
| `renders.151` | renders.151.json | 110,524 | 19,540 | 26,056 | c9396fe2 | 557 |
| `drift` | drift/*.json | 171,838 | 5,627 | 7,504 | f4c03fed | 1,776 |
| `suite` | runs/suite-physics-2026-10-17/ | 21,301 | 5,179 | 6,908 | 4d0e4788 | 9 |
| `xsd40` | x3d-4.0.xsd | 1,333,390 | 102,500 | 136,668 | 0509fa5b | - |
| `xsd41` | x3d-4.1.xsd | 1,363,165 | 104,492 | 139,324 | 1a7935ca | - |
| total | 11 parts | 6,509,115 | 996,190 | 1,328,268 | | |

Claims (`stats.json`, grade C = Confirmed, S = Suspected): `c.rates` 20 → 98 · 57 → 100 · 77 → 100 (n 50 / 47 / 43, S: one run per prompt) · `c.seven` 7 of 178 (C) · `c.ratio` 1 ms vs 38,095 ms, ×38,095 (C) · `c.calls` 358 · `c.failed` 62 · `c.cut` 17 · `c.canary` 558 bodies, 0 flips (C, re-run at build) · `c.truncated` 49 · `c.replay17` 17 of 91 · `c.lockstep` null (module 04 not shipped).

Where these differ from the figures quoted in the SPEC prose, the files win: the SPEC's `×41,800` / `42 s` is `×38,095` / `38 s` here (JS median of `A[].ms` over the 358 calls); the sp-09 plaque reads 2 calls, 0.0388 USD, validator 5 ms then 6 ms, 1,454 report characters, XSD finding `roughness` with no named fix (an XSD-only report names none); the credit stop is 19:16 on the run clock (28:02 real); the reconciliation's 106 are 62 + 25 + 19, not 62 + 17 + 27.
