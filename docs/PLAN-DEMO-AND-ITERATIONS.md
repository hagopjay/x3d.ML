# Plan: what to demo next, what to build next, and how much of it rests on blender_mcp

17 Oct 2026. Branch `feat/suite-physics-provenance`. Grades as in DESIGN.md (C confirmed by reading or running it today, L likely, S suspected). Read-only look at x3d.poc (94de74d), x3d_mcp (fa0b389, branch fix/physics-findings), x3d-blender-io (78212bc, feat/export-suite-conformance) and mcp-for-blender (7a0373e, upstream ahujasid, unforked). The live Blender window was not touched; `bpy_api_lookup` was read, not run.

## 1. How dependent are we on blender_mcp (mcp-for-blender)?

Almost not at all in the shipped path; it is a development and authoring channel.

| Edge | Depends on blender_mcp? | Evidence |
|---|---|---|
| x3d_mcp (validator, tools) to Blender | **No.** No `bpy` or Blender import anywhere in `src/`; the only mention is `docs/ecosystem-research.md` listing BlenderMCP as prior art | C (grep) |
| x3d-blender-io add-on (`source/`) | **No.** Needs `bpy` only; `blender_version_min = 4.2.0` | C |
| x3d-blender-io dev scripts | **No.** Corrected: the five files first listed here (`blender_mcp_client.py`, `drive1-3.py`, `gen_scene_via_mcp.py`) are untracked scratch scripts left in one local checkout during the live demo, not part of the repo (0 tracked files, 0 on origin/main). Nothing in the repo drives blender_mcp | C (git ls-files, git ls-tree origin/main) |
| Export suite (194 cases) and physics stress | **No.** Fresh headless `Blender -b` per case. The add-on itself refuses `-b` (B-24), another reason it cannot be a CI dependency | C |
| x3d.poc, x3d.ML | **No** (no source reference) | C |
| Physics stress, `mcp_overhead` suite | Measured it: 54 ms floor per `execute_blender_code` call from a 50 ms timer poll (B-20), superlinear receive loop (B-21) | C |

Risks if we lean on it harder: it is a third-party project we do not control (the add-on is "protocol 13", 6,441 lines, ships telemetry, consent and premium-hint modules); the installed copy in Blender 5.1 is byte-identical to the checkout (same sha1), so we are on its current main but pinned to nothing. Its own `tests/test_compat_matrix.py` guards server-versus-add-on compatibility across its history, not Blender-version compatibility.

## 2. How synchronised is it with the versioned Blender API and docs?

| Layer | Mechanism | Sync with Blender | Grade |
|---|---|---|---|
| blender_mcp `bpy_api_lookup`, `describe_node_type` | Runtime RNA introspection (`bl_rna`, `get_rna_type`) in the running Blender | **Exact to the running version**, by construction; it is not docs, so no prose, no deprecation notes | L (code read, not run) |
| blender_mcp `guides/*.md` (21 KB) | Hand-written prose with version notes (4.0 socket renames, 4.4 slotted actions, 5.0 `Action.fcurves` removal and `use_nodes` always on) | Static, covers up to 5.0; nothing for 5.1 to 5.3; no reference to docs.blender.org or the release notes | C (grep found none) |
| blender_mcp add-on `bl_info.blender` | `(3, 0, 0)` | Claims 3.0 and up; nothing here tests that | C |
| x3d-blender-io CI | headless matrix **4.5.14, 5.1.2, 5.2.2**; Python 3.11 and 3.13 | Declared minimum 4.2.0 is **not in the matrix**; 5.0 is not either; 5.3 (native splat API, alpha) is read by neither | C |
| Our runs (suite, physics) | Blender **5.1.0** locally (the one installed); DESIGN.md quotes a 5.2.2 bpy wheel | Different from CI's 5.1.2; chains record the version string but not the build hash | C |
| API surface the add-on touches | `ast` scan: at least 99 distinct `bpy.<a>.<b>` names in 21 files (data 42, types 16, app 12, context 12, ops 10); property-level uses (`node.inputs["Emission Color"]`, `rigid_body.restitution`) are invisible to that scan | No check that any of it exists in 4.2, 5.0 or 5.3 | C for the count |

Honest summary: the live-introspection tool is synchronised by construction, the prose and our own support claims are not, and nothing yet joins the two. Our evidence for "works on version X" is only the CI matrix, and our own demo data comes from a version outside it.

## 3. What to demo next (audience as before: technical peers, Dr. Polys)

One story, three beats, every number clickable down to its chain.
1. **One scene through the whole stack, no MCP**: Blender (headless) to x3d-blender-io 4.0 export with `use_animation` to x3d_mcp validate (now with RigidBodyPhysics checks) to X_ITE render, stamped as it goes. x3d.poc's new "Physics and fidelity" page already shows the Z13 ball; add its chain next to it and a "tamper this value" button (reuse the Tether Firehose in-browser SHA-256 and `verify`).
2. **The suite as a regression you can audit**: the 5 runs already ingested show the CORE failures going 4, 1, 0 as exporter fixes landed (51, 51b, 51c); show that run by run with the case ids that flipped.
3. **The honest gap page**: physics definitions lost 100 percent both directions (X-01, X-04), validator blind spots 23 of 40 (X-09), with the loss split as measured, not as a promise.

## 4. Iterations (smallest first; each has a check that fails if it is not true)

| # | Build | Repo | Done when | Needs |
|---|---|---|---|---|
| I1 | Record at run time, not ingest: Blender build hash, repo sha and dirty flag, validator sha written into the suite manifest | x3d-blender-io (suite runner) | `predates_run` is gone from new chains | none |
| I2 | `pipeline` script: author, export, validate (x3d_mcp), render (X_ITE), stamp, in one headless command | x3d.ML | one command gives a chain that `verify()`s and `audit()`s, on Blender 5.1 and 5.2 | I1 |
| I3 | API-surface check: for every `bpy` name (and each `rigid_body`, node-socket name the suite relies on) ask `bl_rna` in each Blender version; chain gets `api_surface_sha256` and the missing names | x3d.ML tool, run in x3d-blender-io CI | a report per version; 4.2 and 5.0 either pass or have named failures | none |
| I4 | Widen the matrix to 4.2 (declared minimum), 4.5, 5.0, 5.1, 5.2; ingest each run into its own ledger | x3d-blender-io CI | `blender_version_min` is either proven or raised | I3 |
| I5 | Add XSD and semantic validation of the exported suite scenes (x3d_mcp) and an X_ITE nonblank step to the suite chains | x3d.ML | each chain gains `validate` (fork) and `render` steps | I2 |
| I6 | x3d.poc evidence page with in-browser verify, plus the `public` redaction profile (DESIGN limit 4) | x3d.poc, x3d.ML | page verifies the ledger offline and tampering turns it red; no tool or model names in the public build | I1 |
| I7 | Physics round trip as a regression: definition loss (now 100 percent) and baked-motion survival tracked per exporter commit | x3d-blender-io, x3d.ML | metrics ingested per commit; a drop in loss fails the check | I2 |
| I8 | Ed25519 sealing of the head hash (DESIGN 0.2); key stays with the user | x3d.ML | last-step edit detected without sources | his decision |

## 5. Decisions for the user

1. **blender_mcp's role.** Recommendation: keep it as an optional authoring front-end (agents driving a live Blender), record it as a `transform`-class step with the add-on protocol version when used, and keep it out of CI and out of the shipped add-on. The alternative is to drop it from the stack; nothing breaks today either way.
2. **Pin or fork.** Pin to a sha in a small `requirements`-style note; fork only if we need the 54 ms poll fixed (B-20).
3. **Supported Blender range.** Raise the declared minimum to the lowest version I4 proves, or add 4.2 to CI.
4. **Local versus CI Blender.** Align the version used for evidence runs with CI (5.1.0 versus 5.1.2 and 5.2.2).

Not verified here: that the 99-name scan misses nothing at property level (it cannot see it), that `bpy_api_lookup` behaves on 5.1 (not run), and what 5.3 changes (alpha, not installed).
