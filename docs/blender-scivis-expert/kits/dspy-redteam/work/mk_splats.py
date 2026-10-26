import math, os
OUT="sp"
N=8
pos=[(math.cos(i*0.8),math.sin(i*0.8),i*0.2-0.7) for i in range(N)]
def j(vs): return " ".join(f"{x:.6g}" for v in vs for x in (v if isinstance(v,(tuple,list)) else (v,)))
scales=[(0.08,0.08,0.08)]*N
quat=[(0,0,0,1)]*N
op=[0.9]*N
C0=0.28209479177387814
rgb=[(0.9,0.2,0.2)]*N
sh0=[tuple((c-0.5)/C0 for c in r) for r in rgb]
def doc(name,positions=pos,scales=scales,quat=quat,op=op,sh0=sh0,extra="",comp='<component name="GaussianSplats" level="1"/>'):
    t=f'''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Immersive" version="4.1"><head>{comp}<meta name="title" content="{name}"/></head>
<Scene><NavigationInfo headlight="false"/><Viewpoint description="v" position="0 0 6"/>
<GaussianSplats positions="{j(positions)}" scales="{j(scales)}" orientations="{j(quat)}" opacities="{j(op)}" sphericalHarmonicsDegree0Coef0="{j(sh0)}" {extra}/></Scene></X3D>
'''
    open(f"{OUT}/{name}.x3d","w").write(t)
doc("g0_control")
doc("g1_opacity_logit", op=[2.2]*N)                                  # raw PLY logit instead of sigmoid
doc("g2_scale_log", scales=[(-2.5,-2.5,-2.5)]*N)                     # raw PLY log-scale
doc("g3_quat_wxyz", quat=[(1,0,0,0)]*N)                              # valid unit quat, but order swapped is identity vs 180deg about x ; use non-symmetric below
doc("g3b_quat_unnormalised", quat=[(0,0,0,5)]*N)
doc("g4_sh0_used_as_rgb", sh0=rgb)                                    # colour written as if it were already RGB, not DC coefficient
doc("g5_len_mismatch", scales=scales[:-3])
doc("g6_nan_pos", positions=pos[:-1]+[(float('nan'),0,0)])
doc("g7_float32_offset", positions=[(6378137.0+p[0]*0.01,p[1]*0.01,p[2]*0.01) for p in pos])  # real-world UTM-ish origin
doc("g8_no_component", comp="")
