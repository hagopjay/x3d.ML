"""Colour chart v2, X3D 4.0, 8 rows x 12 patches (ortho, straight on, black Background, headlight off, one DirectionalLight 0 0 -1 intensity 1):
A unlit grey ramp   B unlit colours   C physical grey (lit)   D physical colours (lit)   E phong Material grey (lit)   F phong colours (lit)
G unlit emissiveTexture = solid-colour PNG of row B's colours   H unlit grey 1.0 with transparency 0.05..0.95 over black"""
import sys, json, os, struct, zlib
outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
greys = [0.02, 0.05, 0.1, 0.18, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
cols = [(0.96, 0.845, 0.69), (213/255, 161/255, 103/255), (159/255, 147/255, 137/255), (0.45, 0.58, 0.90), (0.45337, 0.61859, 0.79866),
        (1.0, 0.45, 0.2), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0.5, 0.5, 0.5), (0.8, 0.8, 0.8), (0.2, 0.3, 0.4)]
trans = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
def png(path, rgb8, n=8):
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb8) * n for _ in range(n))
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))
rows = [("A", "unlit", [(g, g, g) for g in greys]), ("B", "unlit", cols), ("C", "phys", [(g, g, g) for g in greys]), ("D", "phys", cols),
        ("E", "phong", [(g, g, g) for g in greys]), ("F", "phong", cols), ("G", "unlit_tex", cols), ("H", "unlit_tr", [(1, 1, 1)] * 12)]
out = ["<?xml version='1.0' encoding='UTF-8'?>",
       "<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>",
       "<head><meta name='title' content='colour chart v2'/></head><Scene>",
       "<NavigationInfo headlight='false' type='\"NONE\"'/>", "<Background skyColor='0 0 0'/>",
       "<DirectionalLight DEF='L' direction='0 0 -1' intensity='1' color='1 1 1' global='true'/>",
       "<OrthoViewpoint DEF='V' position='6 -3.5 10' fieldOfView='-7 -5.5 7 5.5' description='chart'/>"]
man = []
for ri, (rn, kind, cs) in enumerate(rows):
    for ci, c in enumerate(cs):
        x, y = float(ci), -float(ri); f = f"{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}"
        if kind == "unlit": mat = f"<UnlitMaterial emissiveColor='{f}'/>"
        elif kind == "phys": mat = f"<PhysicalMaterial baseColor='{f}' metallic='0' roughness='1'/>"
        elif kind == "phong": mat = f"<Material diffuseColor='{f}' specularColor='0 0 0' ambientIntensity='0' shininess='0.2'/>"
        elif kind == "unlit_tex":
            png(os.path.join(outdir, f"tex_{ci:02d}.png"), [round(v * 255) for v in c])
            mat = f"<UnlitMaterial><ImageTexture containerField='emissiveTexture' url='\"tex_{ci:02d}.png\"'/></UnlitMaterial>"
        elif kind == "unlit_tr": mat = f"<UnlitMaterial emissiveColor='1 1 1' transparency='{trans[ci]}'/>"
        out.append(f"<Transform translation='{x} {y} 0'><Shape><Appearance>{mat}</Appearance><Rectangle2D size='0.9 0.9'/></Shape></Transform>")
        man.append({"row": rn, "kind": kind, "i": ci, "x": x, "y": y, "rgb": list(c), "transparency": trans[ci] if kind == "unlit_tr" else 0})
out += ["</Scene></X3D>"]
open(os.path.join(outdir, "chart2.x3d"), "w").write("\n".join(out) + "\n"); json.dump(man, open(os.path.join(outdir, "chart2.x3d.json"), "w"))
print(len(man))
