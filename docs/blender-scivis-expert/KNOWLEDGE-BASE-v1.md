# Blender Scientific Visualization Expert: Knowledge Base v1

Built 24 Oct 2026 from six source documents (a six-tab research doc dated 15-18 Oct 2026, written by a prior Claude session; "the Survey"). Version everything: corrections go in v1.1 beside this file, never over it.

**Grading.** The Survey tags claims [V] (read in primary docs), [R] (secondary/trade press), [I] (inference). This project grades Confirmed / Likely / Suspected. Mapping used here: Survey [V] = **Likely** (primary docs read by someone else, not reproduced by us); [R] and [I] = **Suspected**. **Confirmed** is reserved for things we reproduced with a named validator and X_ITE patch. Nothing below is Confirmed yet.

**Freshness.** Version facts are as of 18 Oct 2026 and go stale in weeks. Re-check list is in section 9.

---

## 1. Thesis (the one-page version)

Capture, prediction and generation got cheap and photoreal; **trust** (editing, lighting, measurement, validation, provenance) is the scarce part. Blender adds controlled lighting/compositing/rendering; X3D adds a validated, annotated, web-native container. In the Survey's words, X3D's lane has a validator between model and scene; Blender's MCP lane does not. That is exactly the project's tether: *X3D is the 3D format an AI can be held accountable to.*

Eleven Survey insights, compressed:
1. Bottleneck moved from making 3D to trusting it (86% of zero-shot Llama 3 X3D failed schema validation, only 34% rendered, 2024 ACM Web3D paper; Likely).
2. Blender is a pipeline (loader add-on, Geometry Nodes attributes, Cycles/EEVEE, compositor, Python), not a program.
3. Version pinning is the hidden cost: Blender 5.2 LTS (14 Jul 2026) satisfies every add-on minimum checked; 5.3 is alpha.
4. Blender visualizes, it does not analyze. Compute contacts/PAE/stats upstream, import as attributes or geometry.
5. Numbers narrow at the Blender border: 32-bit floats vs 64-bit Python, roughly 6 vs 15 orders of magnitude (Suspected, one forum thread). Center and scale before import.
6. Splats are a viewing representation; meshes measure and simulate.
7. AlphaFold changed access, not outcomes.
8. Licenses split the same way everywhere (Inria splat trainer, SHARP weights, AlphaFold 3 weights).
9. Declarative beats imperative for AI authoring.
10. Interchange is the quiet disruption (glTF, OpenUSD, 3D Tiles, X_ITE all moved on splats within months).
11. The skill is judgment: knowing when a model is wrong.

## 2. Blender engine facts that matter for science (Likely unless noted)

| Area | Fact | Why it matters for X3D sync |
|---|---|---|
| Cycles | Path tracer; GPU via CUDA/OptiX/HIP/oneAPI/Metal; spills to system RAM when VRAM fills | "Blender owns the look": final renders come from here |
| EEVEE Next | Real-time, screen-space RT; 5.3 makes Vulkan default (Suspected until 5.3 notes read) | Fast previews to compare against X_ITE |
| Volumes | OpenVDB; Principled Volume reads grids named density/color/temperature; sparse renders dense; 5.0 added volume-grid GN nodes | Maps to X3D Volume Rendering component; grid naming is the join key |
| Geometry Nodes | Attributes, fields, instances, simulation/repeat zones; 5.2 changed Python API for modifier properties | Per-point attributes (pLDDT, charge, velocity) are the data carrier; X3D has no equivalent, needs Metadata nodes or Color/ColorRGBA |
| Passes/AOVs | Depth/Position/Normal/Vector/Index, shader AOVs, Cryptomatte; save as OpenEXR | Turns a render into a measurement; X3D side has no analog, keep in sidecar |
| Cameras | Perspective, ortho, equirect, fisheye (final render only), OSL custom cameras (OptiX only) | X3D Viewpoint/OrthoViewpoint map; panoramic does not |
| Colour mgmt | **Standard** view transform when colour encodes a value; AgX tone-maps; tag data images Non-Color | Biggest hidden error class. X_ITE renders unmanaged sRGB-ish, so Standard is the fair comparison |
| Python | `bpy` on PyPI, headless, `--cycles-device`, extensions via blender_manifest.toml | Our x3d-blender-io CI already uses the bpy wheel |
| Interchange | Built in: glTF, USD, Alembic, OBJ, PLY, STL, FBX. X3D only via extension (Survey says X3D 3.3) | See correction C1 below |

## 3. Domain tooling map (Tier A = current on 5.x, B = verify first, C = legacy; the Survey's own ranking, Suspected)

- **Structural biology**: Molecular Nodes 520.2.0 (18 Sep 2026, needs 5.2 LTS+; MDAnalysis + biotite; AlphaFold DB fetch, pLDDT colouring, IMDv3 live MD streaming; sphere style = point cloud so one material). Tier A. ProteinBlender, Beautiful Atoms: Tier B.
- **Microscopy / medical**: Microscopy Nodes (5.2 LTS+, visualization only), Bioxel Nodes 2.0 (DICOM/NIfTI/Nrrd/HDF5, 5.0+). Tier A.
- **Simulation / CFD / climate**: SciBlend 1.3.0 (19 Jul 2026, 5.1+, Python 3.13; reads vtk/vtu/NetCDF/shapefile/**X3D**; colormap shaders, compositor legends). Tier A. OpenFOAM importer tested only on 3.4.1: Tier C. EPCC headless HPC workflow (500 frames = 3,200 CPU hours on ARCHER2).
- **Cell biology**: CellBlender/MCell 4.2.0. **Research rendering**: Mitsuba add-on. **Maths**: Sverchok, Math Art, LaTeX Text Generator, Math Anim.
- **Geospatial**: BlenderGIS (compat unverified). **Astronomy**: AstroBlend, FRELLED (old).
- **Synthetic data**: BlenderProc, Blenderless.

Unverified in the Survey and still open: BioBlender, ePMV, Atomic Blender, Beautiful Atoms/BlenderGIS/NeuroMorphoVis/blendvis/blender-plots/Animation Nodes compatibility; MN atom-count limit; MN contact detection (only distance annotations found).

## 4. Gaussian splatting (the part most tied to Splat Park)

- Splat = position(3) + scale(3) + rotation quaternion(4) + opacity(1) + SH colour. At SH degree 3: 59 numbers, 248 bytes in PLY (Likely, from the paper). Table: SH0 68 B, SH1 104 B, SH2 164 B, SH3 248 B per splat; 10M splats at SH3 = 2.48 GB.
- Formats: PLY (lossless), SPZ (~10x, MIT, Niantic, v4 ZSTD), SOG (15-20x, PlayCanvas, WebP images), `.splat/.ksplat`, glTF `KHR_gaussian_splatting` (ratified 3 Sep 2026, **[R] only**: Survey never opened khronos.org), OpenUSD 26.03 `UsdVolParticleField3DGaussianSplat` (Likely), Cesium 3D Tiles LOD.
- Blender: today KIRI 3DGS Render 5.1.0 / BlendSplat add-ons on 5.1-5.2. **5.3 alpha (Suspected, PR 163102 via trade press)**: PointCloud type "3D Gaussian Splats"; attributes `position`, `scale`, `rotation` (quaternion), `radiance:base` (4-part: opacity + base colour), `radiance:sh_N`; PLY auto-detect, SPZ v4 import with axis conversion; **no export**; emissive shading in Workbench/EEVEE/Cycles; Diffuse swap = crude relighting; known: sRGB assumption, Apply Transform ignores scale/rotation/SH.
- X_ITE 16.6.0 (MIT) reads splat PLY, SPZ, SOG (Likely; "runtime feature, not core node"). Open question: does it follow the glTF extension.
- Axis: PLY splats typically Z-forward, -Y-up; check on import.
- Licensing traps: Inria reference trainer non-commercial; gsplat Apache-2.0; LichtFeld Studio GPL-3.0; Postshot free non-commercial tier; Apple SHARP weights non-commercial; World Labs Marble output needs eligible plan. Not legal advice. Scanning places/people raises privacy/likeness rights (not researched; relevant to Shroud Street View and Enrie plates rules).
- Open problems: relighting, editing, measurement, file size.

## 5. AlphaFold / molecular (Likely/Suspected as tagged in source)

- AFDB: 214M predictions, CC BY 4.0. AF2 params CC BY 4.0. AF3 code Apache-2.0 reported, weights academic-only, Server non-commercial with changing daily limits (10/20/30 reported at different times).
- Evidence: AF2 models screen like apo structures (EF1% 13.16 vs apo 11.56 vs holo 24.81; refined 19.25). Co-folding models memorize ligand poses (Runs N' Poses); physics docking beats co-folding on novel ligands; ipTM is not affinity. Phase I 80-90% vs Phase II ~40%; no AI-discovered drug approved as of Jul 2026; Isomorphic had dosed no patient on 8 Oct 2026.
- Visualization rules: pLDDT lives in the B-factor column (0-100; >90 high, <50 low); PAE is a residue-pair matrix in JSON; a PAE plot can mislead (default ChimeraX domain colouring hid a wrong packing). Molecular Nodes reads structure only; **PAE and AF3 summary scores need a script (Suspected)**. Interactions come from PLIP/ProLIF upstream and are drawn as curves.
- **X3D has no concept of atoms, bonds or interactions** (Likely). ChimeraX saves .x3d as static meshes. No AlphaFold-specific X3D tooling found.

## 6. AI and agents: the lane comparison (the core of our tether argument)

| | Blender lane | X3D lane |
|---|---|---|
| Interface | Blender Lab MCP 1.0.3 (11 Sep 2026, 5.1+, port 9876 reported) plus community servers; run arbitrary Python | x3d_mcp: 4 levels (type-safe construction, JSON Schema, XML Schema 4.0/4.1, semantic checks) |
| Guard | None; Blender Lab itself warns of file deletion/exfiltration | Validator between model and scene |
| Failure mode | Valid-looking but wrong colours/scale; code execution | Schema-valid but not true (units, mapping) |
| Benchmarks | None found for Blender agents | SciVisAgentBench covers ParaView/napari/VMD; ParaView-MCP 50.7% (Claude Sonnet 4.6) |

Policy: Blender Foundation says no generative AI in or planned for Blender (1 May 2026, [R]); Anthropic became a Blender Development Fund patron April 2026 [R]. Keep that disclosure beside any assistant-related claim.

## 7. Safe-use checklist for agent-written Blender scripts (adopted as standing practice)

Work on a copy; save every generated script; review before run (especially file/network); sandbox; pin Blender + add-on versions; **validate the exported X3D after every agent script** (our addition: this closes the Blender lane's missing guard).

## 8. How the expert feeds all further R&D (operating model)

**Role.** A standing reviewer and spec-writer, not a builder. For any thread that touches Blender, scientific data, splats or molecular scenes it supplies: (a) the right tool for the data type, (b) the traps (colour management, precision, versions, licences), (c) a test list with pass criteria, (d) the claim grading.

**Feed routes into existing work**

| Project thread / repo | What the expert supplies | Concrete first deliverable |
|---|---|---|
| x3d-blender-io (PRs #21/#22 merged; bidirectional sync) | A science-data round-trip suite: Colour/ColorRGBA, Normal, UnlitMaterial (known importer losses in the 15 Oct memo), volume/point/splat nodes, Metadata nodes for units/provenance, 32-bit precision offset test | Fixture list + expected-loss table, graded |
| Splat Park / X3D 4.1 GaussianSplats fixture (splats-fixture-x3d41.x3d) | Mapping table: Blender 5.3 `radiance:*` attributes <-> X3D splat fields <-> glTF KHR <-> SPZ/SOG; axis and SH-degree rules | Mapping v1 plus a PLY->X3D->Blender->PLY fidelity measurement |
| x3d_mcp fork / Accountability Playground (ontology methods and skills) | Scientific-visualization failure taxonomy as validator-style rules (valid-but-wrong: missing units metadata, colour map without legend, pLDDT out of 0-100, unnormalised coordinates) | Candidate semantic checks, drafted for the Playground thread to adopt, not built here |
| Compact encodings | SPZ/SOG/PLY size arithmetic and SH-degree trade-offs | Shared size table (section 4) |
| Flywheel / University scale (hub) | A/B experiments the Survey says nobody has run: agent builds same scene via Blender MCP vs x3d_mcp; measure defect rate with and without validator report | Experiment spec, which also fills the "no Blender agent benchmark" gap |
| Blenderization / Shroud / Giza / Burruss | Colour-management and render-setting checklist; Standard vs AgX pairs | Add to every look A/B |

**Rules for the expert's own outputs.** Name the validator (fork 688174f / d5598c4 / main eb4b4b4; upstream 74da0ec) and the exact X_ITE patch (16.5.0 blank, 16.5.1 draws, Survey cites 16.6.0) and Blender build for every number; Confirmed only after we reproduce; no vendor names or private links on public pages; nothing to outside repos or Web3D Consortium until "send"; no OpenAI credit probes; no new billable GCP resources without a per-step yes; no commits with AI trailers to the public x3d_mcp fork.

## 9. Corrections and gaps found while reading (so v1.1 can fix them)

- **C1. The Survey understates our toolchain.** It says Blender's X3D extension is X3D 3.3 with no PBR export. Our x3d-blender-io already exports X3D 4.0 PhysicalMaterial/UnlitMaterial, animation, HAnim, Inline, fold-morph shape keys (PR #22) and has a 4.1 splats fixture. Treat the Survey's X3D-in-Blender claims as describing the upstream extension only (Likely).
- **C2.** Survey Tab 1 sections 10-11 still describe X3D as static meshes; Tab 5 corrects this (X_ITE has volume, particles, splats, WebXR).
- **C3.** Survey says SciBlend reads X3D; unverified how (version, profile). Test against our validator.
- **C4.** Version register not independently re-verified. Re-check list: Blender 5.2/5.3, Molecular Nodes 520.x, SciBlend 1.3.0, Bioxel 2.0, Microscopy Nodes, Blender Lab MCP 1.0.3, KIRI 3DGS Render 5.1.0, LichtFeld 0.5.4, X_ITE 16.6.0, Khronos ratification, OpenUSD 26.03. Our network allow-list blocks several of these hosts (web3d.org, huggingface.co); use the fetch-route for blocked ones.
- **C5.** Trade-press-only [V] tags in Tab 2 may be over-graded; the handoff itself says to downgrade. We downgrade to Suspected.
- **C6.** Survey admits no hands-on tests were run. All its checklists are therefore our opportunity to produce first Confirmed results.

## 10. Master hands-on test list (candidates for Confirmed results; each needs validator + X_ITE + Blender build named)

1. Round-trip a science fixture (points + Color, volume grid, Metadata units) Blender -> X3D -> Blender; report losses.
2. Standard vs AgX render of a heat-map; compare to X_ITE render.
3. 32-bit precision: geospatial-scale coordinates through export/import with and without offset.
4. PLY splat -> X3D (X_ITE 16.5.1/16.6.0) vs Blender 5.3 daily import; file size at SH0-3.
5. AlphaFold model: pLDDT B-factor -> Color in X3D; verify bands (50/90) survive.
6. Agent A/B: same scene via Blender MCP vs x3d_mcp, validator on/off.
7. glTF export to second runtime as cross-check.
8. Largest structure load: memory and viewport (Molecular Nodes).

## 11. Source document map

Tab 1 Scientific Visualization in Blender (sec 1-22, App A-F); Tab 2 Gaussian splatting masterclass (sec 1-16, App A-E); Tab 3 Handoff; Tab 4 AlphaFold and drug discovery (sec 1-13); Tab 5 Visualization disruption (sec 1-7, App A-F); Tab 6 Final insights (11 insights, App A-H). Raw extracts are kept in the session scratchpad only; the six docx originals are the record.
