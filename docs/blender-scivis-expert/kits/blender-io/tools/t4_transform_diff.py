import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
import swatch_book, scene_fixture

def listing(path, tags):
    out = []
    for e in ET.parse(path).getroot().iter():
        if e.tag in tags:
            out.append((e.tag, e.attrib.get("DEF") or ("USE=" + e.attrib["USE"] if "USE" in e.attrib else "-")))
    return out

for name, build, kw in (("scene", lambda d: scene_fixture.build_scene_fixture(), dict(use_hierarchy=True, use_animation=True)),
                        ("swatch", lambda d: swatch_book.build_swatch_book(texture_dir=d), dict(use_normals=True))):
    reset(); d = str(TMP / name); os.makedirs(d, exist_ok=True); build(d)
    paths = []
    for g in range(2):
        p = f"{d}/{name}_{g}.x3d"; exp(p, "X3D40", **kw); paths.append(p); reset(); imp(p)
    print("==", name)
    for tag in ("Transform", "Shape", "IndexedFaceSet", "PhysicalMaterial", "UnlitMaterial", "Appearance"):
        a, b = listing(paths[0], {tag}), listing(paths[1], {tag})
        print(f" {tag}\n   gen0: {a}\n   gen1: {b}")
