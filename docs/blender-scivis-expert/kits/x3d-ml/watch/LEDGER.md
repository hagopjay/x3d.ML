# Blender-for-X3D ecosystem ledger

Append-only. Written by watch.py (deterministic probes) and by the daily routine's web pass (`note:` lines).

## 2026-10-11T17:52:40Z  (17 change(s))

- baseline `git:blender/blender:tags` = v5.1.2, v5.2.0, v5.2.1, v5.2.2
- baseline `git:blender/blender:heads` = blender-v5.0-release, blender-v5.1-release, blender-v5.2-release, blender-v5.3-release
- baseline `git:blender/blender:head` = 8cd8e62c5756
- baseline `git:KhronosGroup/glTF-Blender-IO:head` = ccc2cc6ea93f
- baseline `git:ahujasid/blender-mcp:head` = 7a0373ec9199
- baseline `git:create3000/x_ite:head` = b4e3be24cd89
- baseline `git:Kiri-Innovation/3dgs-render-blender-addon:head` = None
- baseline `git:FishWoWater/trellis_blender:head` = None
- baseline `git:Tencent-Hunyuan/Hunyuan3D-2:head` = None
- baseline `git:coderextreme/X3DJSONLD:head` = 402900d167f0
- baseline `git:Web3DConsortium/BlenderX3DSupport:head` = None
- baseline `pypi:bpy` = 5.2.2 (2026-09-15)
- baseline `pypi:x3d` = 4.0.65.7 (2026-10-01)
- baseline `pypi:mcp-for-blender` = 2.1.9 (2026-10-06)
- baseline `npm:x_ite` = 16.5.0 (2026-10-11)
- baseline `npm:@playcanvas/splat-transform` = 3.10.1 (2026-10-09)
- baseline `npm:@sparkjsdev/spark` = 2.3.1 (2026-10-01)

- 2026-10-11T17:53:16Z note: WEB baseline: io_scene_x3d (Web3D X3D/VRML2 format) latest 2.5.1 dated 2025-03-18 on extensions.blender.org; no 2026 release or commit found by search; projects.blender.org unreachable from container

- 2026-10-11T17:53:16Z note: WEB baseline: Blender 5.3 branch cut 2026-10-09 (git), release scheduled 2026-11-10 (cinevva, radiancefields); native GSplat import PLY+SPZ v4, glTF KHR_gaussian_splatting import (d73e281), USD UsdVolParticleField3DGaussianSplat import; no splat export

- 2026-10-11T17:53:16Z note: WEB baseline: Blender Lab official MCP server at projects.blender.org/lab/blender_mcp, v1.0.0 2026-04-27, v1.0.3 2026-09-11, needs Blender 5.1+, port 9876 (secondary: strayspark.studio, gamedev.net Lab Q1 report); not verified at source

- 2026-10-11T17:53:17Z note: WEB baseline: KHR_gaussian_splatting announced as release candidate 2026-02-03 (khronos.org); ratification not confirmed by search

- 2026-10-11T17:53:17Z note: WEB baseline: x3d-ecosystem list newest Blender thread found = Dec 2025 (Marchetti PhysicalMaterial via glTF->Castle); 2026 archives not indexed by search

- 2026-10-11T17:53:17Z note: WEB baseline: KIRI 3DGS Render 5.0 (Jun 2026: proxy-mesh deformation rigging, light bake, 4DGS sequence export); BlendSplat v0.6 (Jun 2026, Codeberg, GN asset library, Blender 5.1+)

- 2026-10-11T19:00:54Z note: x3d-blender-io PR #10 merged 2026-10-11 19:00Z: id x3d_blender_io 2.6.0 + Blender 5.3 native splat PointCloud <-> X3D 4.1 GaussianSplats

## 2026-10-12T13:52:28Z  (2 change(s))

- **commits** `git:blender/blender:head` 8cd8e62c5756 -> 4659decc99e1: 0 relevant
- **commits** `git:coderextreme/X3DJSONLD:head` 402900d167f0 -> d2525fe4bfcc: 0 relevant

- 2026-10-12T13:53:16Z note: WEB: SplatGen (Shehab Mekky) preview for Blender 5.3 alpha trains Gaussian splats inside Blender (V2 trainer on Brush) and saves them as native GAUSSIAN_SPLAT point clouds; x3d-blender-io 2.6.0 can export those to X3D 4.1, so a full in-Blender capture-to-X3D path exists. https://radiancefields.com/splatgen-trains-and-relights-gaussian-splats-inside-the-blender-5-3-alpha

## 2026-10-25T02:56:52Z  (11 change(s))

- **new refs** `git:blender/blender:tags`: v4.5.15, v5.2.3
- **commits** `git:blender/blender:head` 4659decc99e1 -> 25b478f6f0cc: 45 relevant
  - 2026-10-24 `bd8c79cd0` Fix: unescaped bone & shape key names in FBX/USD imported animation paths
  - 2026-10-24 `32f5c9c48` GSplat: Minor bugfixes
  - 2026-10-22 `94363991e` glTF: Refactor: filtering nodes
  - 2026-10-22 `bfd982cce` Anim: add Python API to create NLA sound strips
  - 2026-10-22 `fa392fded` glTF: Fix py args property changes when saving export options
  - 2026-10-22 `b6cf4a455` Fix #163936: glTF: Fix instance collection with collection(s) inside
  - 2026-10-20 `70007afa1` Fix: PLY: Import failing for empty binary elements with unknown types
  - 2026-10-20 `29a0bcfd9` Fix: PLY: Import dropping empty rows of skipped ASCII elements
  - 2026-10-20 `f89d087cd` Fix: PLY: Don't assume index 0 for missing ASCII face and tristrips index
  - 2026-10-20 `f84b5d621` Fix: PLY: Import wrong edges for vertex indices above 2^24
- **commits** `git:KhronosGroup/glTF-Blender-IO:head` ccc2cc6ea93f -> e03d6603c44a: 0 relevant
- **commits** `git:ahujasid/blender-mcp:head` 7a0373ec9199 -> febcd90ece59: 9 relevant
  - 2026-10-24 `febcd90ec` hygiene: version bump
  - 2026-10-24 `d461a2bf1` feat(meshy): pose_mode for A-pose and T-pose characters (#408)
  - 2026-10-24 `322a16271` fix: get addon protocol number in telemetry
  - 2026-10-20 `5a3618fcc` fix: link url to Premium was missing
  - 2026-10-20 `98b991c8d` docs: Windows install without ExecutionPolicy bypass, add winget path (#401)
  - 2026-10-20 `e38102574` hygiene: version bump
  - 2026-10-20 `7944ab50f` feat: run Meshy through Premium (#402)
  - 2026-10-18 `25e1fe008` hygiene: version bump
  - 2026-10-18 `15b43b169` feat: add Meshy with users' API keys (#398)
- **commits** `git:create3000/x_ite:head` b4e3be24cd89 -> 1e2d03c9b8e2: 2 relevant
  - 2026-10-21 `5f282709c` Build version 16.6.0
  - 2026-10-13 `c38f310fe` Build version 16.5.1
- **commits** `git:coderextreme/X3DJSONLD:head` d2525fe4bfcc -> f8eb4fe7c8c8: 0 relevant
- **version** `pypi:bpy`: 5.2.2 -> 5.2.3 (2026-10-22)
- **version** `pypi:mcp-for-blender`: 2.1.9 -> 2.2.4 (2026-10-24)
- **version** `npm:x_ite`: 16.5.0 -> 16.6.0 (2026-10-21)
- **version** `npm:@playcanvas/splat-transform`: 3.10.1 -> 3.10.3 (2026-10-21)
- **version** `npm:@sparkjsdev/spark`: 2.3.1 -> 2.4.0 (2026-10-20)
