"""Colour chart X3D 4.0: 4 rows x 12 patches. Row A/B = UnlitMaterial (grey ramp, colours); row C/D = PhysicalMaterial (same colours) under one
DirectionalLight (direction 0 0 -1, intensity LI). Ortho view straight on, black Background, headlight off."""
import sys, json
LI = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
greys = [0.02, 0.05, 0.1, 0.18, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
cols = [(0.96, 0.845, 0.69), (213/255, 161/255, 103/255), (159/255, 147/255, 137/255), (0.45, 0.58, 0.90), (0.45337, 0.61859, 0.79866),
        (1.0, 0.45, 0.2), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0.5, 0.5, 0.5), (0.8, 0.8, 0.8), (0.2, 0.3, 0.4)]
rows = [("A", "unlit", [(g, g, g) for g in greys]), ("B", "unlit", cols), ("C", "phys", [(g, g, g) for g in greys]), ("D", "phys", cols)]
out = ["<?xml version='1.0' encoding='UTF-8'?>",
       "<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>",
       "<head><meta name='title' content='colour chart'/></head><Scene>",
       "<NavigationInfo headlight='false' type='\"NONE\"'/>", "<Background skyColor='0 0 0'/>",
       f"<DirectionalLight DEF='L' direction='0 0 -1' intensity='{LI}' color='1 1 1' global='true'/>",
       "<OrthoViewpoint DEF='V' position='6 -2 10' fieldOfView='-7 -3 7 3' description='chart'/>"]
manifest = []
for ri, (rn, kind, cs) in enumerate(rows):
    for ci, c in enumerate(cs):
        x = ci * 1.0 + 0.0 - 0.0; y = -ri * 1.0
        if kind == "unlit":
            mat = f"<UnlitMaterial emissiveColor='{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}'/>"
        else:
            mat = f"<PhysicalMaterial baseColor='{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}' metallic='0' roughness='1'/>"
        out.append(f"<Transform translation='{x} {y} 0'><Shape><Appearance>{mat}</Appearance><Rectangle2D size='0.9 0.9'/></Shape></Transform>")
        manifest.append({"row": rn, "kind": kind, "i": ci, "x": x, "y": y, "rgb": list(c)})
out += ["</Scene></X3D>"]
open(sys.argv[1], "w").write("\n".join(out) + "\n")
json.dump(manifest, open(sys.argv[1] + ".json", "w"))
print(len(manifest), "patches")
