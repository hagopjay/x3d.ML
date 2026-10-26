import sys; sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/tools")
from h import *
register()
body = '<Shape><Appearance><PhysicalMaterial/></Appearance><IndexedFaceSet coordIndex="0 1 2 -1" colorPerVertex="false"><Coordinate point="0 0 0 1 0 0 0 1 0"/><ColorRGBA color="0.5 0.5 0.5 0.5"/></IndexedFaceSet></Shape>'
reset(); path = write("rt0.x3d", wrap(body))
for g in range(4):
    imp(path)
    q = str(TMP / f"rt{g+1}.x3d"); exp(q, "X3D40")
    c = [e.attrib["color"] for e in ET.parse(q).getroot().iter("ColorRGBA")]
    print(f"generation {g+1}: ColorRGBA written = {c}")
    reset(); path = q
