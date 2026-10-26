import numpy as np, re, sys
ply='/mnt/project-files/polyxandria/landing-v2/gifts/synthsplat/splats.ply'
x3d=sys.argv[1]
with open(ply,'rb') as f:
    h=b''
    while not h.endswith(b'end_header\n'):
        h+=f.readline()
    names=[l.split()[-1] for l in h.decode().split('\n') if l.startswith('property')]
    n=int([l for l in h.decode().split('\n') if l.startswith('element vertex')][0].split()[-1])
    a=np.frombuffer(f.read(),dtype='<f4').reshape(n,len(names))
col={k:i for i,k in enumerate(names)}
s=open(x3d,encoding='utf8').read()
i=s.index('<GaussianSplats'); j=s.index('/>',i)
tag=s[i:j]
def vec(name,k):
    m=re.search(name+r'="([^"]*)"',tag)
    return np.array(m.group(1).split(),dtype=np.float64).reshape(-1,k)
pos=vec('positions',3); sc=vec('scales',3); ori=vec('orientations',4); op=vec('opacities',1)[:,0]
print('N',n,'x3d N',len(pos))
def md(a,b): return float(np.max(np.abs(a-b)))
P=a[:,[col['x'],col['y'],col['z']]].astype(np.float64)
print('pos max abs',md(P,pos))
S_=np.exp(a[:,[col['scale_0'],col['scale_1'],col['scale_2']]].astype(np.float64))
print('scale exp max abs',md(S_,sc),' rel',float(np.max(np.abs(S_-sc)/S_)))
q=a[:,[col['rot_0'],col['rot_1'],col['rot_2'],col['rot_3']]].astype(np.float64)
q=q/np.linalg.norm(q,axis=1,keepdims=True)
qx=q[:,[1,2,3,0]]
d=min(md(qx,ori),md(qx,-ori))
# sign-insensitive
dd=np.minimum(np.max(np.abs(qx-ori),axis=1),np.max(np.abs(qx+ori),axis=1))
print('quat xyzw max abs (sign-insens)',float(dd.max()))
O=1/(1+np.exp(-a[:,col['opacity']].astype(np.float64)))
print('opacity sigmoid max abs',md(O,op))
dc=a[:,[col['f_dc_0'],col['f_dc_1'],col['f_dc_2']]].astype(np.float64)
dc_x=vec('sphericalHarmonicsDegree0Coef0',3)
print('SH0 max abs',md(dc,dc_x))
if 'f_rest_0' in col:
    fr=a[:,[col[f'f_rest_{k}'] for k in range(45)]].astype(np.float64)  # R15,G15,B15
    R=fr[:,0:15];G=fr[:,15:30];B=fr[:,30:45]
    worst=0
    k=0
    for deg,cnt in ((1,3),(2,5),(3,7)):
        for c in range(cnt):
            xs=vec(f'sphericalHarmonicsDegree{deg}Coef{c}',3)
            ref=np.stack([R[:,k],G[:,k],B[:,k]],axis=1)
            e=md(ref,xs); worst=max(worst,e); k+=1
    print('SH1-3 channel-major mapping max abs',worst)
