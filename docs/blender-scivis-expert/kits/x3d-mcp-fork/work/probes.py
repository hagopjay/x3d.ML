"""Baseline probes: scenes that are valid-but-wrong for science visualisation.
Run each through the fork at the checked-out commit (xsd + semantic_diagnostics).
Usage: python -I probes.py <x3d_mcp_src_dir>   (prints one JSON line per probe)"""
import sys, json, math, random
SRC = sys.argv[1]
sys.path.insert(0, SRC)
from validation.validate import validate_xml
import re
try:
    from validation.semantic import semantic_diagnostics
except ImportError:  # branches older than 7cc4f59 only have the markdown report
    from validation.semantic import validate_semantic
    class _D:
        def __init__(s, level, check): s.level, s.check = level, check
    def semantic_diagnostics(text):
        out, lvl = [], None
        for line in validate_semantic(text).splitlines():
            if line.startswith("## "): lvl = {"Errors":"error","Warnings":"warning","Info":"info"}.get(line[3:].strip())
            m = re.match(r"- \*\*\[([a-z0-9-]+)\]\*\*", line)
            if m and lvl: out.append(_D(lvl, m.group(1)))
        return out

def wrap(body, version="4.1", profile="Immersive", head=""):
    comp = '<component name="GaussianSplats" level="1"/>' if "GaussianSplats" in body else ""
    comp += '<component name="VolumeRendering" level="2"/>' if "VolumeData" in body else ""
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<X3D profile="{profile}" version="{version}">\n'
            f'<head>{comp}{head}</head>\n<Scene>\n<Viewpoint position="0 0 6" description="v"/>\n{body}\n</Scene>\n</X3D>\n')

def fmt(v, nd=3): return " ".join(f"{x:.{nd}f}" for x in v)

def splats(n=200, sh0=None, scale=0.05, opac=None, seed=1, extra=""):
    r = random.Random(seed)
    pos = [(r.uniform(-1,1), r.uniform(-1,1), r.uniform(-1,1)) for _ in range(n)]
    sc = [(scale,)*3 for _ in range(n)]
    q = [(0,0,0,1) for _ in range(n)]
    op = opac if opac is not None else [r.uniform(0.3,0.95) for _ in range(n)]
    if sh0 is None:  # realistic: rgb in 0..1 -> SH DC
        C0 = 0.28209479177387814
        sh0 = [tuple((r.random()-0.5)/C0 for _ in range(3)) for _ in range(n)]
    f = lambda rows: " ".join(f"{x:.5f}" for row in rows for x in row)
    return (f'<GaussianSplats positions="{f(pos)}" scales="{f(sc)}" orientations="{f(q)}" '
            f'opacities="{" ".join(f"{o:.4f}" for o in op)}" sphericalHarmonicsDegree0Coef0="{f(sh0)}" {extra}/>')

P = {}
mat = '<Shape><Appearance><Material diffuseColor="{c}"/></Appearance><Box/></Shape>'
P["P01_material_color_out_of_range"] = wrap(mat.format(c="1.5 -0.2 0.3"))
P["P02_color_node_out_of_range"] = wrap('<Shape><IndexedFaceSet coordIndex="0 1 2 -1" colorPerVertex="true"><Coordinate point="0 0 0 1 0 0 0 1 0"/><Color color="300 0 0 0 -4 0 0 0 9"/></IndexedFaceSet></Shape>')
# 1 cm grid at UTM-like offset, 3 decimals written
pts=[]; idx=[]
N=20
for j in range(N):
    for i in range(N):
        pts.append((500000.0+0.01*i, 4100000.0+0.01*j, 100.0))
for j in range(N-1):
    for i in range(N-1):
        a=j*N+i; idx += [a,a+1,a+N+1,a+N,-1]
P["P03_float32_utm_offset_1cm_grid"] = wrap(f'<Shape><IndexedFaceSet coordIndex="{" ".join(map(str,idx))}"><Coordinate point="{fmt([c for p in pts for c in p])}"/></IndexedFaceSet></Shape>')
P["P03b_same_grid_centred"] = wrap(f'<Shape><IndexedFaceSet coordIndex="{" ".join(map(str,idx))}"><Coordinate point="{fmt([c for p in [(0.01*(k%N),0.01*(k//N),0) for k in range(N*N)] for c in p])}"/></IndexedFaceSet></Shape>')
r=random.Random(3)
P["P04_splat_sh0_is_rgb_0to1"] = wrap(splats(sh0=[tuple(r.random() for _ in range(3)) for _ in range(200)]))
P["P04b_splat_sh0_correct"] = wrap(splats())
P["P05_splat_scales_100x_extent"] = wrap(splats(scale=100.0))
P["P06_splat_all_opacity_0.002"] = wrap(splats(opac=[0.002]*200))
P["P07_splat_positions_nan"] = wrap(splats().replace(splats().split('positions="')[1].split()[0], "nan", 1))
P["P08_plddt_01_scale_metadata"] = wrap('<Shape metadata="x"><Appearance><Material/></Appearance><PointSet><Coordinate point="0 0 0 1 0 0 2 0 0"/><Color color="0 0.33 0.84 1 0.86 0.07 1 0.49 0.27"/></PointSet></Shape>'.replace(' metadata="x"','')
    + '<MetadataSet name="pLDDT" reference="AF-P12345-F1"><MetadataFloat name="plddt" value="0.93 0.55 0.31"/></MetadataSet>')
P["P09_plddt_value_120"] = wrap('<MetadataSet name="pLDDT"><MetadataFloat name="plddt" value="120 55 -3"/></MetadataSet>')
P["P10_unit_conversion_zero"] = wrap('<Shape><Appearance><Material/></Appearance><Box/></Shape>', head='<unit category="length" name="angstrom" conversionFactor="0"/>')
P["P10b_unit_category_bad"] = wrap('<Shape><Appearance><Material/></Appearance><Box/></Shape>', head='<unit category="distance" name="metre" conversionFactor="1"/>')
P["P11_no_meta_no_title"] = wrap('<Shape><Appearance><Material/></Appearance><Box/></Shape>')
P["P12_color_count_lt_coords"] = wrap('<Shape><IndexedFaceSet coordIndex="0 1 2 3 -1" colorPerVertex="true"><Coordinate point="0 0 0 1 0 0 1 1 0 0 1 0"/><Color color="1 0 0 0 1 0"/></IndexedFaceSet></Shape>')
P["P13_normal_not_unit"] = wrap('<Shape><IndexedFaceSet coordIndex="0 1 2 -1"><Coordinate point="0 0 0 1 0 0 0 1 0"/><Normal vector="0 0 5 0 0 5 0 0 5"/></IndexedFaceSet></Shape>')
P["P14_volumedata_no_voxels_no_style"] = wrap('<VolumeData dimensions="0 0 0"/>')
P["P15_pointset_color_count_mismatch"] = wrap('<Shape><PointSet><Coordinate point="0 0 0 1 0 0 2 0 0 3 0 0"/><Color color="1 0 0 0 1 0"/></PointSet></Shape>')
P["P16_transparency_out_of_range"] = wrap('<Shape><Appearance><Material transparency="1.7" emissiveColor="40 40 40"/></Appearance><Box/></Shape>')
P["P17_splat_colorspace_bad_enum"] = wrap(splats(extra='colorSpace="ACEScg"'))
P["P18_splat_colorspace_linear_with_srgb_dc"] = wrap(splats(extra='colorSpace="LIN_REC709_DISPLAY"'))
P["P19_viewpoint_outside_far_plane"] = wrap('<NavigationInfo visibilityLimit="5"/><Transform translation="0 0 -200"><Shape><Appearance><Material/></Appearance><Sphere/></Shape></Transform>')
P["P20_hdr_emissive_1000"] = wrap('<Shape><Appearance><PhysicalMaterial emissiveColor="1000 800 600"/></Appearance><Sphere/></Shape>')

def rep(name, text):
    out = {"probe": name, "bytes": len(text)}
    try:
        v = validate_xml(text)
        out["xsd_valid"] = v["valid"]
        if not v["valid"]: out["xsd_err"] = v["errors"][:2]
    except Exception as e:
        out["xsd_crash"] = repr(e)[:160]
    try:
        d = semantic_diagnostics(text)
        out["sem"] = sorted({f"{x.level}:{x.check}" for x in d})
    except Exception as e:
        out["sem_crash"] = repr(e)[:160]
    return out

if __name__ == "__main__":
    import os
    outdir = sys.argv[2] if len(sys.argv) > 2 else None
    for k, t in P.items():
        if outdir:
            open(os.path.join(outdir, k + ".x3d"), "w").write(t)
        print(json.dumps(rep(k, t)))
