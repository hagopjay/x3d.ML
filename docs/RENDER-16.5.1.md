# Second render pass: X_ITE 16.5.1 against 16.5.0 (24 Oct 2026)

Question: everything the Tether Firehose pages say about "draws" versus "blank" was measured on X_ITE 16.5.0. Another thread reported that headless X_ITE 16.5.1 draws some scenes 16.5.0 leaves blank. Does the published headline move if the renderer is updated by one patch?

Answer, measured here: **no scene of the 557 changes class.** 383 of 383 live attempts and 174 of 174 replay scenes get the same draws / blank / unparsable answer on 16.5.1 as on 16.5.0, including the 7 valid-but-blank live scenes and the 17 valid-but-blank replay scenes. Grades: **Confirmed** = measured in this pass; **Likely** = read from the code or from other threads' notes, not measured here.

## Method (Confirmed)

Same rig, same settings, one variable changed (the X_ITE files served).

| | 16.5.0 pass (17 Oct 2026) | 16.5.1 pass (this one) |
|---|---|---|
| X_ITE | 16.5.0, the subset in `demo/build/xite` (105 files, 8.5 MB, `mkxite.py` over `npm i x_ite@16.5.0`), served by `demo/serve.py` on :8782 | 16.5.1 from `npm install x_ite@16.5.1` (registry, 24 Oct), the same `mkxite.py` subset (105 files, 8.48 MB, identical file list), served from the scratchpad by a copy of `serve.py` (same CSP, same routes) on :8783, `RENDER_URL` pointed at it as the README says for the 16.4.1 pass |
| Rig | `demo/render/render_final3.py` + `render/render3.html`: fresh page per scene, watcher on `browser.finishEvents()` registered before `replaceWorld`, canvas sampled inside the end-of-frame callback (first 8 frames, then one per 150 ms, `MAXS=20`), `SETTLE=3500` ms, then a real screenshot of the canvas box as the cross-check; `WORKERS=3` (one browser, three pages) | identical, byte for byte; `finishEvents` is a function on 16.5.1 too (`endEvents` is not), so the same branch runs |
| Viewpoint | the rig binds no Viewpoint; after `replaceWorld` it calls `getActiveLayer().viewAll(0)` | identical (see the note below) |
| Browser | Playwright Chromium with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist --no-sandbox --hide-scrollbars` | Chromium 141.0.7390.37 (Playwright build chromium-1194 at `/opt/pw-browsers`, passed through the rig's `CHROME` hook because Python Playwright 1.64.0 here has no browser of its own); UA `HeadlessChrome/141.0.0.0`; WebGL 2.0 (OpenGL ES 3.0 Chromium) on `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)`. The 17 Oct pass used the same flags; its exact Chromium build was not recorded in the files |
| Bodies | live: `runs/live-2026-10-17/x3d/<model>/<prompt>_a<n>.x3d` (383); replay: `/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11/results/x3d/<model>/<mode>/<prompt>.x3d` (174) | the same paths; the 174 mount files equal field `b` of `demo/data/replay.json` byte for byte (checked) |
| Class rule | the page's rule: `err` if X_ITE threw; else `draws` if max(in-callback best frame, screenshot) >= 0.5% of pixels differ from the background; else `blank` (`build_live.py`, `build_replay.py`, `live/analyze.py`) | the same rule applied to both files |
| Outputs | `demo/data/renders_live_x_ite_16.5.0.json`, `demo/data/renders3_x_ite_16.5.0.json` | `demo/data/renders_live_x_ite_16.5.1.json` (written through `live/merge_renders.py`, compact, like the 16.5.0 live file), `demo/data/renders3_x_ite_16.5.1.json` (the rig's own output, like the 16.5.0 replay file); same keys, same fields (`series`, `repMs`, `nodes`, `frames`, `first`, `last`, `nonblank`, `shot`, `jpg` 192x144 JPEG base64, `unknown`, `msgs`, `nmsg`, `ms`, `err`) |

Wall clock: live pass 19:50:32Z to 20:05:40Z, replay pass to 20:12:27Z; 21.9 minutes for both sets on 4 shared cores (load average 4 to 8 from another workflow). No scene hit the rig's 40 s per-scene limit; no harness errors.

## Per-set totals (Confirmed)

| set | scenes | X_ITE | draws | blank | unparsable (`err`) | same class as 16.5.0 |
|---|---:|---|---:|---:|---:|---:|
| live (17 Oct run, every attempt) | 383 | 16.5.0 | 292 | 71 | 20 | |
| | 383 | 16.5.1 | 292 | 71 | 20 | **383 of 383** |
| replay (11 Oct GPU phase) | 174 | 16.5.0 | 115 | 47 | 12 | |
| | 174 | 16.5.1 | 115 | 47 | 12 | **174 of 174** |

Not just the counts: the per-scene classes agree, and so do the finer facts. Scenes on which X_ITE printed "Unknown node type": 37 live and 69 replay on both patches, the same scenes with the same counts. Blank scenes with exactly 0 differing pixels: 64 live and 47 replay on both. The 20 + 12 unparsable files fail with the same message on both patches (`Couldn't parse X3D. No suitable file handler found for '<page url>'`; the strings differ only in the port, :8782 against :8783, which both build scripts collapse to a fixed text before it reaches the page).

## Flip table (Confirmed)

| direction | live | replay |
|---|---|---|
| blank on 16.5.0, draws on 16.5.1 | none | none |
| draws on 16.5.0, blank on 16.5.1 | none | none |
| unparsable on one patch only | none | none |

The report that 16.5.1 draws scenes 16.5.0 leaves blank is **not reproduced** on these 557 scenes under this rig. What it most plausibly refers to (Likely, not measured here): the other thread's own rig (`fly.mjs`) screenshots from a scripted camera after binding a Viewpoint and setting its position, and it noted that without that step headless 16.5.1 showed only the Background; a scene that is blank *from its own camera* can draw from another one. This pass measures what a viewer opens on, with `viewAll(0)` as the only camera move, on both patches alike; it does not test other cameras.

Note on the Viewpoint-binding observation (Confirmed for this rig): with no script-bound Viewpoint, 16.5.1 drew 292 of the 383 live attempts and 115 of the 174 replay scenes here, the same ones as 16.5.0, so "draws only the Background until a script binds a Viewpoint" is not a property of 16.5.1 in general; it is Likely specific to that other setup.

## The 7 valid-but-blank live scenes (Confirmed: measured on both patches)

These are the 7 of 178 scenes valid at the end of the 17 Oct run that draw nothing (LIVE-RUN-FINDINGS.md, finding 6). Keys are the final attempt's render key. `nb` is the page's measure (max of the in-callback best frame and the screenshot), as a fraction of pixels differing from the background; blank is under 0.005.

| key | why it is blank (17 Oct reading) | nb 16.5.0 | nb 16.5.1 | frames 16.5.0 / 16.5.1 |
|---|---|---:|---:|---|
| `gemini-3.8-flash/int-05_a2.x3d` | proximity-lit, dark until the viewer walks up | 0 | 0 | 127 / 75 |
| `gpt-6.1-sol/int-05_a1.x3d` | proximity-lit, dark until the viewer walks up | 0.0045 | 0.0042 | 137 / 88 |
| `gemini-3.8-flash/geo-02_a2.x3d` | geospatial, content tiny from the default camera | 0.0018 | 0.0018 | 46 / 31 |
| `gemini-3.1-pro-preview/geo-02_a1.x3d` | geospatial, content tiny from the default camera | 0.0020 | 0.0015 | 181 / 97 |
| `gemini-3.8-flash/geo-03_a2.x3d` | geospatial, content tiny from the default camera | 0.0002 | 0.0002 | 58 / 23 |
| `gemini-3.1-pro-preview/geo-04_a2.x3d` | geospatial, content tiny from the default camera | 0.0047 | 0.0023 | 207 / 127 |
| `nvidia_nemotron-3-super-120b-a12b/hanim-01_a3.x3d` | H-Anim humanoid whose boxes hang off no joint | 0 | 0 | 4 / 4 |

All 7 stay blank on 16.5.1, with no dropped-node messages on either patch (`unknown` 0, `msgs` empty): X_ITE reads these files whole and the result is still under 0.5% of pixels. The two exact zeros (one proximity-lit scene, the humanoid) are exact zeros on both patches. The five with a trace of pixels (0.0002 to 0.0047) keep the same order of magnitude on 16.5.1; the one that moved most, `geo-04_a2` 0.0047 to 0.0023, is an animated scene sampled at a different phase, and a 16.5.0 re-run on this machine gives 0.0015 (control below), so the move is run-to-run variance, not the patch. `geo-04_a2` and `int-05_a1` on 17 Oct were the two closest to the line (0.0047 and 0.0045 against 0.005), so the 17 Oct claim "7 valid scenes draw nothing" rests on a margin of 0.0003 to 0.0005 for those two; three measurements each (17 Oct 16.5.0, today's 16.5.0 control, today's 16.5.1) all fall under the line, `int-05_a1` at 0.0045, 0.0042, 0.0042 and `geo-04_a2` at 0.0047, 0.0015, 0.0023. The margin is small for `int-05_a1` on any renderer; a page that wants a safer statement can say "under 0.5%" rather than "nothing". Likely, from reading the scenes rather than from new measurement: the geospatial four would draw from a closer camera, and the two proximity-lit ones once a ProximitySensor fires; neither happens on a fresh load on either patch. The humanoid draws nothing from any camera on either patch (Confirmed: 4 blank frames then idle, on both).

## The 17 valid-but-blank replay scenes (Confirmed: measured on both patches)

These are the 17 of the 91 scenes the 11 Oct service called valid (`x` and `s` set in `replay.json`) that draw nothing (DESIGN.md section 8). All 17 are exactly 0 on both patches, and X_ITE prints the same dropped-node messages on both.

| key | nb 16.5.0 | nb 16.5.1 | unknown nodes (same on both) | what X_ITE dropped (16.5.1 messages) |
|---|---:|---:|---:|---|
| `gpt-oss-20b/grounded/geo-03.x3d` | 0 | 0 | 3 | GeoLocation, GeoViewpoint, GeoElevationGrid (also an ImageTexture URL it could not fetch) |
| `qwen2.5-coder-14b-awq/grounded/geo-01.x3d` | 0 | 0 | 2 | GeoLocation, GeoViewpoint |
| `qwen2.5-coder-14b-awq/grounded/geo-04.x3d` | 0 | 0 | 2 | GeoLocation, GeoPositionInterpolator |
| `qwen2.5-coder-14b-awq/oneshot/geo-01.x3d` | 0 | 0 | 2 | GeoLocation, GeoViewpoint |
| `qwen2.5-coder-14b-awq/oneshot/geo-04.x3d` | 0 | 0 | 3 | GeoLocation, GeoPositionInterpolator |
| `qwen3-8b/grounded/geo-03.x3d` | 0 | 0 | 3 | GeoLocation, GeoViewpoint, GeoElevationGrid |
| `qwen3-8b/oneshot/geo-04.x3d` | 0 | 0 | 3 | GeoLocation, GeoViewpoint, GeoPositionInterpolator |
| `gpt-oss-20b/grounded/hanim-01.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `gpt-oss-20b/grounded/hanim-02.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `gpt-oss-20b/grounded/hanim-03.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `gpt-oss-20b/grounded/hanim-04.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `gpt-oss-20b/oneshot/hanim-04.x3d` | 0 | 0 | 3 | HAnimJoint, HAnimHumanoid |
| `qwen2.5-coder-14b-awq/grounded/hanim-01.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `qwen2.5-coder-14b-awq/grounded/hanim-04.x3d` | 0 | 0 | 2 | HAnimHumanoid |
| `qwen3-8b/grounded/hanim-02.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `qwen3-8b/grounded/hanim-05.x3d` | 0 | 0 | 1 | HAnimHumanoid |
| `qwen3-8b/grounded/int-04.x3d` | 0 | 0 | 0 | nothing dropped (one unknown field `set_emissiveColor` on Shape); blank for another reason |

16 of the 17 are Geospatial or H-Anim nodes used without a `<component>` statement in an Immersive profile; X_ITE 16.5.1 drops them exactly as 16.5.0 does, and the rest of each scene has nothing visible. The 17th (`qwen3-8b/grounded/int-04.x3d`) parses whole on both patches and still draws nothing. Nothing in the 16.5.0 to 16.5.1 change touches component loading for these node types (Confirmed by outcome: identical messages and counts; Likely as to the cause, the changelog was not read).

## Checks on the measurement (Confirmed)

- The in-callback best frame and the screenshot agree on draw/blank for 348 of 363 live scenes that parse on 16.5.1 (347 of 363 on 16.5.0) and 161 of 162 replay scenes (160 of 162 on 16.5.0). Every disagreement is a scene the sampled frames caught drawing and the 3.5 s screenshot caught out of view or dark (animations, a proximity-lit room, a fading spotlight); the page's max rule counts them as drawing on both patches, so none is a flip.
- Among scenes that draw on both, the median differing fraction is the same (live 0.259 on both; replay 0.2511 against 0.2552). Four scenes moved by more than 0.15 (`gemini-3.8-flash/sp-13_a2` 0.69 to 0.91, `nvidia_nemotron-3-super-120b-a12b/sp-19_a1` 0.67 to 0.39, `gpt-oss-20b/grounded/anim-02` 0.07 to 0.37, `qwen2.5-coder-14b-awq/oneshot/hanim-02` 0.49 to 0.23): all four are animated, and the best-of-20 sample lands on a different phase. Likely a sampling effect, not a renderer change; not separated here.
- Timing differs and is not a version property: median time per scene 6.5 s here against 5.0 s on 17 Oct (live) and 6.6 s against 4.6 s (replay); median frames per drawing scene 51 against 64 (live) and 31.5 against 62 (replay). This machine ran at load 4 to 8 with 3 pages in one browser and another workflow on the same 4 cores. Blank scenes still get their few frames and then idle (median 3 frames, live), as on 17 Oct.
- Control on this machine (Confirmed): the 7 live and 17 replay valid-but-blank scenes were re-rendered on the 16.5.0 subset (`demo/build/xite` through `demo/serve.py` on :8782) with the same rig in the same hour (20:12Z to 20:13Z): 24 of 24 blank, the 17 replay scenes exactly 0 with the same unknown-node counts, and the 7 live scenes at 0, 0.0018, 0.0013, 0.0002, 0.0015, 0.0042, 0 (`int-05_a2`, `geo-02_a2`, `geo-02_a1`, `geo-03_a2`, `geo-04_a2`, `int-05_a1`, `hanim-01_a3`). So the differences between the two full passes on `geo-04_a2` (0.0047 on 17 Oct, 0.0023 on 16.5.1, 0.0015 on 16.5.0 today) and `geo-02_a1` (0.0020, 0.0015, 0.0013) are run-to-run variance of animated scenes, not the patch.

## What this does and does not support

- Confirmed for this sample: the Tether Firehose headlines ("7 of 178 valid live scenes draw nothing", "17 of 91 service-valid replay scenes draw nothing", "115 of 174 draw") hold on X_ITE 16.5.1 as published; nothing on the pages needs re-measuring for this patch.
- Not measured: other cameras (a bound Viewpoint from script, a closer camera on the geospatial scenes), GPU rendering, X_ITE versions beyond 16.5.1, fonts in Text nodes under the real artifact viewer's policy (as before).
- The 16.5.1 files are not wired into the pages: `build_replay.py` takes a cross-version file as its optional third argument (it names the fields `nb164` / `err164` after the 16.4.1 pass), and `build_live.py` takes one render file; neither was re-run, and `demo/build/xite` stays at 16.5.0.

## Reproduce

```
S=<scratch>; mkdir -p $S/xite1651 && cd $S/xite1651 && npm install x_ite@16.5.1
cd demo && python3 mkxite.py $S/xite1651/node_modules/x_ite/dist $S/xite1651/build/xite      # 105 files
# serve $S/xite1651/build on :8783 with serve.py's CSP and the /render3.html route (a copy of serve.py with the directory and port changed)
CHROME=/opt/pw-browsers/chromium RENDER_URL=http://127.0.0.1:8783/render3.html RENDER_DIR=../runs/live-2026-10-17/x3d RENDER_GLOB='*/*.x3d' python3 render/render_final3.py $S/live.json
python3 live/merge_renders.py data/renders_live_x_ite_16.5.1.json $S/live.json
CHROME=/opt/pw-browsers/chromium RENDER_URL=http://127.0.0.1:8783/render3.html python3 render/render_final3.py data/renders3_x_ite_16.5.1.json
```
