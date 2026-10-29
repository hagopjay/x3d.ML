import numpy as np, json, ctypes, sys, time, gzip, io, brotli, lzma, zstandard
from skimage.metrics import structural_similarity as ssim
PLY='/mnt/project-files/polyxandria/landing-v2/gifts/synthsplat/splats.ply'
POSES='/mnt/project-files/polyxandria/landing-v2/gifts/synthsplat/poses.json'
raw=open(PLY,'rb').read(); hend=raw.index(b'end_header\n')+11
N=132923; D=np.frombuffer(raw,dtype='<f4',offset=hend).reshape(N,62).copy()
assert len(raw)==hend+N*248, (len(raw),hend)
print("PLY header bytes",hend,"N",N,"payload",N*248,flush=True)
pos=D[:,0:3].copy(); fdc=D[:,6:9].copy(); frest=D[:,9:54].reshape(N,3,15).copy()
logit=D[:,54].copy(); lsc=D[:,55:58].copy(); quat=D[:,58:62].copy()
def shfull(fdc,frest):
    sh=np.zeros((N,3,16),np.float32); sh[:,:,0]=fdc; sh[:,:,1:]=frest; return sh
lib=ctypes.CDLL('./librast.so')
fp=ctypes.POINTER(ctypes.c_float)
lib.render.argtypes=[ctypes.c_int]+[fp]*5+[ctypes.c_int]+[fp]*2+[ctypes.c_float]*4+[ctypes.c_int]*2+[fp,fp]
def P(a): a=np.ascontiguousarray(a,np.float32); return a, a.ctypes.data_as(fp)
P_=json.load(open(POSES))
fr=eval(P_['frames']) if isinstance(P_['frames'],str) else P_['frames']
# pick views
sel=[fr[i] for i in (0,36,72,100,140,170)]
g4=eval(P_['gift4']) if isinstance(P_['gift4'],str) else P_['gift4']
views=sel+[g4]
Wf,Hf=960,600; sc=0.5; W,H=int(Wf*sc),int(Hf*sc); K=P_['K']; fx,fy,cx,cy=K[0][0]*sc,K[1][1]*sc,K[0][2]*sc,K[1][2]*sc
bg=np.array([0.1153,0.1002,0.0873],np.float32)
def render(pos,lsc,quat,alin,sh,deg,view):
    w2c=np.array(view['w2c'],np.float32); c2w=np.array(view['c2w'],np.float32)
    cp=c2w[:3,3].copy()
    out=np.zeros((H,W,3),np.float32)
    keep=[]; 
    args=[]
    for a in (pos,lsc,quat,alin,sh):
        a2,p=P(a); keep.append(a2); args.append(p)
    w,wp=P(w2c[:3,:].reshape(-1)); c,cpp=P(cp); b,bp=P(bg)
    lib.render(len(pos),args[0],args[1],args[2],args[3],args[4],deg,wp,cpp,fx,fy,cx,cy,W,H,bp,out.ctypes.data_as(fp))
    return out
def sig(x): return 1/(1+np.exp(-x))
# ---- codecs ----
def spz_encode(pos,fdc,frest,logit,lsc,quat,shdeg,fracbits=12,rotbits=10):
    n=len(pos)
    fx_=np.clip(np.round(pos*(1<<fracbits)),-(1<<23),(1<<23)-1).astype(np.int32)
    u=(fx_&0xFFFFFF).astype(np.uint32)
    posb=np.stack([u&255,(u>>8)&255,(u>>16)&255],-1).astype(np.uint8).reshape(n,9) if False else None
    posb=np.zeros((n,3,3),np.uint8)
    for k in range(3):
        uu=(fx_[:,k]&0xFFFFFF).astype(np.uint32); posb[:,k,0]=uu&255; posb[:,k,1]=(uu>>8)&255; posb[:,k,2]=(uu>>16)&255
    a=np.clip(np.round(sig(logit)*255),0,255).astype(np.uint8)
    col=np.clip(np.round(fdc*(0.15*255)+0.5*255),0,255).astype(np.uint8)
    sc=np.clip(np.round((lsc+10)*16),0,255).astype(np.uint8)
    q=quat/np.linalg.norm(quat,axis=1,keepdims=True)  # w,x,y,z
    # smallest three, order as (x,y,z,w) like spz
    qs=np.stack([q[:,1],q[:,2],q[:,3],q[:,0]],1)
    idx=np.argmax(np.abs(qs),1); sgn=np.sign(qs[np.arange(n),idx]); sgn[sgn==0]=1; qs=qs*sgn[:,None]
    mask=np.ones((n,4),bool); mask[np.arange(n),idx]=False
    others=qs[mask].reshape(n,3)
    m=(1<<(rotbits-1))-1; neg=others<0
    mag=np.clip(np.round(np.abs(others)/ (2**-0.5) * m),0,m).astype(np.uint32)
    word=(idx.astype(np.uint32))<<30
    for k in range(3):
        word|= ((neg[:,k].astype(np.uint32)<<(rotbits-1))|mag[:,k]) << (rotbits*(2-k)) if rotbits==10 else 0
    rotb=np.stack([word&255,(word>>8)&255,(word>>16)&255,(word>>24)&255],1).astype(np.uint8)
    parts=[posb.reshape(-1),a,col.reshape(-1),sc.reshape(-1),rotb.reshape(-1)]
    ncoef=[0,3,8,15][shdeg]
    shq=None
    if ncoef:
        sh=frest[:,:,:ncoef]  # n,3,ncoef
        b=np.zeros((n,ncoef,3),np.uint8)
        for j in range(ncoef):
            bits=5 if j<3 else 4; bucket=1<<(8-bits)
            qv=np.round(sh[:,:,j]*128+128).astype(np.int32)
            qv=(qv+bucket//2)//bucket*bucket
            b[:,j,:]=np.clip(qv,0,255).astype(np.uint8)
        parts.append(b.reshape(-1))
    header=np.frombuffer(b'NGSP'+np.array([3,n,shdeg,fracbits,0,0],dtype='<u4').tobytes()[:0],dtype=np.uint8)
    hdr=(np.array([0x5053474e,3,n],'<u4').tobytes()+bytes([shdeg,fracbits,0,0]))
    assert len(hdr)==16
    stream=hdr+b''.join(p.tobytes() for p in parts)
    return stream,dict(fx=fx_,a=a,col=col,sc=sc,word=word,idx=idx,shq=shq,ncoef=ncoef,fracbits=fracbits,n=n,shdeg=shdeg,parts=parts)
def spz_decode(stream,n,shdeg,fracbits=12,rotbits=10):
    off=16
    pb=np.frombuffer(stream,np.uint8,count=n*9,offset=off).reshape(n,3,3); off+=n*9
    uu=pb[:,:,0].astype(np.int32)|(pb[:,:,1].astype(np.int32)<<8)|(pb[:,:,2].astype(np.int32)<<16)
    uu=np.where(uu&0x800000,uu-(1<<24),uu); pos=(uu/(1<<fracbits)).astype(np.float32)
    a=np.frombuffer(stream,np.uint8,count=n,offset=off).astype(np.float32)/255; off+=n
    col=np.frombuffer(stream,np.uint8,count=n*3,offset=off).reshape(n,3).astype(np.float32); off+=n*3
    fdc=((col/255-0.5)/0.15).astype(np.float32)
    sc=np.frombuffer(stream,np.uint8,count=n*3,offset=off).reshape(n,3).astype(np.float32); off+=n*3
    lsc=sc/16-10
    rb=np.frombuffer(stream,np.uint8,count=n*4,offset=off).reshape(n,4).astype(np.uint32); off+=n*4
    word=rb[:,0]|(rb[:,1]<<8)|(rb[:,2]<<16)|(rb[:,3]<<24)
    idx=(word>>30).astype(np.int64); m=(1<<(rotbits-1))-1
    vals=np.zeros((n,3),np.float32)
    for k in range(3):
        f=(word>>(rotbits*(2-k)))&((1<<rotbits)-1); neg=(f>>(rotbits-1))&1; mag=(f&m).astype(np.float32)
        v=mag/m*(2**-0.5); vals[:,k]=np.where(neg==1,-v,v)
    large=np.sqrt(np.maximum(0,1-(vals**2).sum(1)))
    qs=np.zeros((n,4),np.float32); mask=np.ones((n,4),bool); mask[np.arange(n),idx]=False
    qs[mask]=vals.reshape(-1); qs[np.arange(n),idx]=large
    quat=np.stack([qs[:,3],qs[:,0],qs[:,1],qs[:,2]],1)
    ncoef=[0,3,8,15][shdeg]; frest=np.zeros((n,3,15),np.float32)
    if ncoef:
        b=np.frombuffer(stream,np.uint8,count=n*ncoef*3,offset=off).reshape(n,ncoef,3).astype(np.float32)
        for j in range(ncoef): frest[:,:,j]=(b[:,j,:]-128)/128
    return pos,fdc,frest,lsc,quat,a
def metrics(ref,img):
    mse=((ref-img)**2).mean(); psnr=10*np.log10(1/mse) if mse>0 else 99.0
    s=ssim(ref,img,channel_axis=2,data_range=1.0)
    return psnr,s
refs=[]
shF=shfull(fdc,frest); alin=sig(logit)
t=time.time()
for v in views: refs.append(render(pos,lsc,quat,alin,shF,3,v))
print("render ref x",len(views),"in %.1fs"%(time.time()-t),flush=True)
from PIL import Image
Image.fromarray((np.concatenate(refs[:3],1)*255).astype(np.uint8)).save('ref_views.png')
Image.fromarray((np.concatenate(refs[3:6],1)*255).astype(np.uint8)).save('ref_views2.png')
Image.fromarray((refs[-1]*255).astype(np.uint8)).save('ref_gift4.png')
rows=[]
def evalvar(name,pos_,fdc_,frest_,alin_,lsc_,quat_,deg,size=None):
    shv=shfull(fdc_,frest_)
    ps=[];ss=[]
    for r,v in zip(refs,views):
        im=render(pos_,lsc_,quat_,alin_,shv,deg,v); p,s=metrics(r,im); ps.append(p); ss.append(s)
    row=dict(name=name,psnr_mean=float(np.mean(ps)),psnr_min=float(np.min(ps)),ssim_mean=float(np.mean(ss)),ssim_min=float(np.min(ss)))
    if size: row.update(size)
    rows.append(row); print(json.dumps(row),flush=True)
def sizes(stream):
    d=dict(raw=len(stream),gzip9=len(gzip.compress(stream,9,mtime=0)))
    d['brotli11']=len(brotli.compress(stream,quality=11,lgwin=24))
    return d

stream,_=spz_encode(pos,fdc,frest,logit,lsc,quat,3)
d=spz_decode(stream,N,3)
dpos,dfdc,dfrest,dlsc,dquat,dalpha=d
# normalise reference quats for fair comparison (renderer normalises anyway)
evalvar("ablate: position only (fracbits 12)",dpos,fdc,frest,alin,lsc,quat,3)
evalvar("ablate: alpha 8-bit only",pos,fdc,frest,dalpha,lsc,quat,3)
evalvar("ablate: DC colour 8-bit only",pos,dfdc,frest,alin,lsc,quat,3)
evalvar("ablate: log-scale 8-bit only",pos,fdc,frest,alin,dlsc,quat,3)
evalvar("ablate: rotation 10-bit only",pos,fdc,frest,alin,lsc,dquat,3)
evalvar("ablate: SH rest 5/4-bit only",pos,fdc,dfrest,alin,lsc,quat,3)
# SH-rest 8-bit (no bucket drop) 
fr8=np.clip(np.round(frest*128+128),0,255); fr8=((fr8-128)/128).astype(np.float32)
evalvar("ablate: SH rest 8-bit (no bit drop)",pos,fdc,fr8,alin,lsc,quat,3)
json.dump(rows,open('abl_rows.json','w'),indent=1)
