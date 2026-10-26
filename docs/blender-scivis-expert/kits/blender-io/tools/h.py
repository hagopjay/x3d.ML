"""Shared harness: register the fork's source/ as an extension under bpy 5.2.3 and round-trip X3D text."""
import os, sys, tempfile, shutil, importlib, logging, io, contextlib
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

REPO = Path("/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/repo")
SCR = Path("/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io")
sys.path.append(str(SCR / "x3dpkg"))
import bpy

TMP = Path(tempfile.mkdtemp(prefix="x3dh_", dir=str(SCR)))

def register():
    pkg = TMP / "io_scene_x3d"
    if not pkg.exists():
        pkg.symlink_to(REPO / "source", target_is_directory=True)
    sys.path.insert(0, str(TMP))
    sys.path.insert(0, str(REPO / "tools"))
    sys.path.insert(0, str(REPO / "source"))
    mod = importlib.import_module("io_scene_x3d")
    try:
        mod.register()
    except Exception as e:
        print("register note:", e)
    return mod

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def write(name, text):
    p = TMP / name
    p.write_text(text, encoding="utf-8")
    return str(p)

def imp(path, **kw):
    return bpy.ops.import_scene.x3d(filepath=path, **kw)

def exp(path, version="X3D40", **kw):
    return bpy.ops.export_scene.x3d(filepath=path, x3d_version=version, use_selection=False, **kw)

def inventory(path):
    return Counter(e.tag for e in ET.parse(path).getroot().iter())

def wrap(body, version="4.0", head=""):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Immersive" version="{version}">
  <head>{head}</head>
  <Scene>
{body}
  </Scene>
</X3D>
'''
