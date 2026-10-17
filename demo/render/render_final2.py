"""Final offline render pass v2 (3-frame sampling: 700 ms, +500, +500; best frame wins; frames>1 means the scene animates). Previous: render_final.py.
Final offline render pass for the Tether Firehose v2 replay: ALL 174 cached GPU-phase scenes, one FRESH page per scene,
3 s frame fallback, X_ITE parser messages captured. X_ITE 16.5.0 published as own files, headless (SwiftShader), viewer-like CSP rig (serve.py).
A scene that X_ITE accepts but that leaves nothing drawable never schedules a frame (X_ITE renders on demand): recorded as nf=1, nonblank 0.
Usage: python3 render_final2.py data/renders_x_ite_16.5.0.json   (serve.py running, build/xite from mkxite.py)
Output renders_final2.json {key: {nodes, nonblank, nf, err, msgs[], unknown, jpg(b64), ms}}"""
import asyncio, base64, glob, io, json, os, re, sys, time
from playwright.async_api import async_playwright
from PIL import Image
EXE=os.environ.get('CHROME')   # unset: Playwright's own Chromium
G=os.environ.get('GPU_PHASE_DIR','/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11')+'/results/x3d'
URL=os.environ.get('RENDER_URL','http://127.0.0.1:8782/render.html')   # serve.py serves it
OUT=sys.argv[1] if len(sys.argv)>1 else 'renders_final2.json'
LIMIT=int(os.environ.get('LIMIT','0'))   # smoke test: render only the first N scenes
files=sorted(glob.glob(G+'/*/*/*.x3d'))[:LIMIT or None]
HOOK='''window.run2=async(x)=>{const B=document.querySelector('x3d-canvas').browser,out={},sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const grab=ms=>new Promise(res=>{window.__want={resolve:res,fn:pixels};setTimeout(()=>res({noframe:true}),ms)});
 try{const sc=await B.createX3DFromString(x);await B.replaceWorld(sc);out.nodes=B.currentScene.rootNodes.length;
   try{B.getActiveLayer().viewAll(0)}catch(e){}
   const shots=[];await sleep(700);const s=await grab(3000);
   if(!s.noframe){shots.push(s);for(const d of [500,500]){await sleep(d);const t=await grab(600);if(t.noframe)break;shots.push(t)}}
   if(!shots.length){out.nf=1;out.nonblank=0}else{const best=shots.reduce((a,b)=>b.nonblank>a.nonblank?b:a);out.nonblank=best.nonblank;out.png=best.url;out.frames=shots.length;out.series=shots.map(q=>q.nonblank)}
 }catch(e){out.err=String(e).slice(0,240)}return out}'''
NOISE=re.compile(r'font|x_ite\.css|mikktspace|logo\.svg|Content Security|Fetch API|PAGEERR Event')
async def worker(b,q,out):
    while True:
        try: f=q.get_nowait()
        except asyncio.QueueEmpty: break
        key='/'.join(f.split('/')[-3:]); x=open(f,encoding='utf-8',errors='replace').read(); msgs=[]; t=time.time()
        pg=await b.new_page(viewport={'width':400,'height':300})
        pg.on('console',lambda m: msgs.append(m.type+': '+m.text[:200].replace('\n',' ')) if m.type in ('error','warning') else None)
        r={}
        try:
            await pg.goto(URL); await pg.wait_for_function('document.querySelector("x3d-canvas").browser!==undefined',timeout=20000)
            await pg.evaluate('initCss()'); await pg.evaluate(HOOK); msgs.clear()
            r=await asyncio.wait_for(pg.evaluate('x=>run2(x)',x),timeout=40)
        except Exception as e: r={'err':'harness: '+type(e).__name__}
        png=r.pop('png',None)
        if png:
            im=Image.open(io.BytesIO(base64.b64decode(png.split(',')[1]))).convert('RGB').resize((192,144)); buf=io.BytesIO(); im.save(buf,'JPEG',quality=72); r['jpg']=base64.b64encode(buf.getvalue()).decode()
        keep=[m for m in msgs if not NOISE.search(m)]
        r['unknown']=sum(1 for m in keep if 'Unknown node type' in m)
        r['msgs']=[m[:170] for m in keep][:4]; r['nmsg']=len(keep); r['ms']=int((time.time()-t)*1000); out[key]=r
        print(len(out),key,r.get('nodes'),r.get('nonblank'),r.get('nf'),(r.get('err') or '')[:50],flush=True)
        await pg.close()
async def main():
    out={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=EXE,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox','--hide-scrollbars'])
        q=asyncio.Queue(); [q.put_nowait(f) for f in files]
        await asyncio.gather(*[worker(b,q,out) for _ in range(3)]); await b.close()
    json.dump(out,open(OUT,'w')); print('done',len(out))
asyncio.run(main())
