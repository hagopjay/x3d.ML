# Knowledge Base v1.1 addendum (24 Oct 2026, sits beside v1, which is unchanged)

**Scope set by HagopJay (24 Oct 18:28Z):** splats first; main output = round-trip fixtures; compatibility target = round-trip; Blender 5.2 LTS (with 5.3 noted); hands-on tests now; everything private; "best high visual fidelity" always.

## Upgrades from project memory (override v1 where they differ)
- **U1 (was Suspected, now Likely).** Blender 5.3 native splats: the ecosystem-watch thread read Blender git on 11 Oct: `PointCloud.type == 'GAUSSIAN_SPLAT'`, attributes scale (linear), rotation (w,x,y,z), `radiance:base` (SH DC + sigmoid opacity), `radiance:sh_i`; PLY/SPZ/glTF KHR/USD import, no export. 5.3 branch cut 9 Oct, release due 10 Nov 2026. This is more detailed than the trade-press report in v1 section 4.
- **U2.** x3d-blender-io 2.6.0 (PR #10) already has `source/splat_native.py`: exports native 5.3 splat PointClouds to X3D 4.1 and imports to them on 5.3+ (FLOAT_COLOR fallback on 5.1, splat mesh on 4.5). Open items there: add 5.3 to CI at release; check SH>=1 colour. This strengthens correction C1.
- **U3.** Extension id is now `x3d_blender_io` (no clash with upstream `web3d_x3d_vrml2_format`).

## Tooling check (Confirmed, this container)
- `pip` can fetch `bpy 5.2.3` (cp313 manylinux wheel, 403 MB); in a venv, `import bpy` reports **5.2.3 LTS**. So Blender 5.2 LTS hands-on tests can run here without a Blender install. Python 3.13.17.
- No GPU assumed; Cycles CPU only, so fidelity renders at high sample counts will be slow. Plan: Cycles CPU for hero stills, EEVEE not available headless without GL (Suspected; to test).
- Native splats need Blender 5.3 which is not on PyPI as a stable wheel; 5.2 route for splats = add-on/mesh fallback in splat_native.py. 5.3 daily builds are on blocked hosts, so they need the fetch-route (HagopJay downloads).

## First test plan (splat round trip, to be graded Confirmed when run)
1. Build a synthetic splat PLY (known N, SH0 and SH3 variants), compute exact expected size per KB v1 appendix arithmetic (68/104/164/248 B per splat).
2. PLY -> X3D 4.1 splats fixture via x3d-blender-io on bpy 5.2.3; validate with fork validator (name commit); view in X_ITE 16.5.1 (name patch).
3. X3D -> Blender -> PLY: measure position/scale/rotation/opacity/SH error (target < 1e-6 float32).
4. Colour check: Standard vs AgX render pair for the splat colour; high-sample Cycles stills for visual fidelity.
5. Record losses in an expected-loss table.
