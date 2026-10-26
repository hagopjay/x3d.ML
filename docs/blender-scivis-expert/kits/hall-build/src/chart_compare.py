import sys, json, numpy as np
from PIL import Image
S='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/hall-build/'
man=json.load(open(S+'chart2/chart2.x3d.json'))
def meas(png, sixteen):
    im=(np.asarray(Image.open(png).convert('RGB')) if not sixteen else np.asarray(Image.open(png))).astype(float)
    if sixteen and im.max()>255: im=im/257.0
    out=[]
    for p in man:
        cx=int((p['x']+1.0)*100); cy=int((2.0-p['y'])*100)
        out.append(im[cy-12:cy+12,cx-12:cx+12].reshape(-1,3).mean(0))
    return np.array(out)
X={'none':meas(S+'chart2/xite_tools_NONE/default.png',False),'neut':meas(S+'chart2/xite_tools_KHR_PBR_NEUTRAL/default.png',False)}
X1={'none':meas(S+'chart2/xite_tools1651_NONE/default.png',False),'neut':meas(S+'chart2/xite_tools1651_KHR_PBR_NEUTRAL/default.png',False)}
print('X_ITE 16.5.0 vs 16.5.1 max abs diff: none',np.abs(X['none']-X1['none']).max(),' neutral',np.abs(X['neut']-X1['neut']).max())
B={}
for br in ('br_main','br_5da2707'):
    for k in ('Standard','AgX_AgX__Medium_High_Contrast','Khronos_PBR_Neutral'):
        B[(br,k)]=meas(S+f'chart2/bl_{br}/{k}.png',True)
np.savez(S+'chart2/meas.npz', xn=X['none'], xt=X['neut'], **{f'{a}__{b}':v for (a,b),v in B.items()})
rows='ABCDEFGH'
def r(v): return v.round(0).astype(int).tolist()
def show(ri,cis,xk,bk,label):
    print(label)
    for ci in cis:
        i=ri*12+ci; p=man[i]
        print(f"  {rows[ri]}{ci:02d} in {[round(v,3) for v in p['rgb']]} tr={p['transparency']} | XITE {r(X[xk][i])} | BL main {r(B[('br_main',bk)][i])} | BL 5da {r(B[('br_5da2707',bk)][i])}")
for ri,lab in ((0,'A unlit grey'),(1,'B unlit colour'),(4,'E phong grey'),(5,'F phong colour'),(6,'G unlit texture'),(7,'H unlit transparency')):
    show(ri,[0,3,6,9,11] if ri not in (1,5,6) else [0,1,3,5],'none','Standard',lab+' | X_ITE NONE vs Blender Standard')
