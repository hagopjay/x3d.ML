"""PROTOTYPE Blender-script guardrail: run an agent's bpy script, export X3D with the x3d-blender-io
add-on, gate the export with the x3d_mcp fork validator (XSD + semantic) plus the prototype sci checks,
write a ledger row, exit non-zero on any error. Scratch only; nothing here is pushed.

    BLENDER_USER_RESOURCES=<dir> python -I blender_guard.py --src <x3d_mcp>/src --addon <x3d-blender-io>/source \
        --script agent.py --out OUT --x3d-version X3D41
"""
import argparse, hashlib, importlib, json, os, runpy, subprocess, sys, tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True); ap.add_argument("--addon", required=True)
ap.add_argument("--script", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--x3d-version", default="X3D41")
ap.add_argument("--data-colour", action="store_true", help="scene colours encode values: require Standard view transform")
a = ap.parse_args()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy

os.makedirs(a.out, exist_ok=True)
tmp = tempfile.mkdtemp()
pkg = Path(tmp) / "io_scene_x3d"
pkg.symlink_to(Path(a.addon), target_is_directory=True)
sys.path.insert(0, tmp)
mod = importlib.import_module("io_scene_x3d")
mod.register()

bpy.ops.wm.read_factory_settings(use_empty=True)
pre = {"blender": bpy.app.version_string,
       "view_transform_before_script": bpy.context.scene.view_settings.view_transform,
       "units_before": [bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length]}
runpy.run_path(a.script, run_name="__agent__")
sc = bpy.context.scene
post = {"view_transform": sc.view_settings.view_transform, "look": sc.view_settings.look,
        "unit_system": sc.unit_settings.system, "scale_length": sc.unit_settings.scale_length,
        "objects": len(bpy.data.objects)}
guard = []   # Blender-side findings, before any export
if a.data_colour and post["view_transform"] != "Standard":
    guard.append(["error", "view-transform", f"colour encodes a value but view transform is {post['view_transform']}; use Standard"])
for im in bpy.data.images:
    if im.colorspace_settings.name == "sRGB" and any(k in im.name.lower() for k in ("normal", "rough", "metal", "height", "depth", "mask", "ao")):
        guard.append(["warning", "image-colourspace", f"image {im.name!r} looks like data but is tagged sRGB; tag Non-Color"])

out_x3d = os.path.join(a.out, "export.x3d")
r = bpy.ops.export_scene.x3d(filepath=out_x3d, x3d_version=a.x3d_version, use_selection=False,
                             meta_title="agent-script export", meta_creator="blender_guard prototype")
manifest = Path(a.addon, "blender_manifest.toml").read_text()
addon_v = next((l.split("=")[1].strip().strip('"') for l in manifest.splitlines() if l.startswith("version")), "?")
Path(a.out, "bl_phase.json").write_text(json.dumps({"export_result": sorted(r), "blender": pre["blender"], "addon": addon_v,
    "x3d_version": a.x3d_version, "scene": post, "guard": guard}, indent=1))
print("bl_phase done", sorted(r))
