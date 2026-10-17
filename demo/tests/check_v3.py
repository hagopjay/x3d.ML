import asyncio, json, sys, time, re, os
from playwright.async_api import async_playwright
EXE=os.environ.get('CHROME')   # unset: Playwright's own Chromium
os.makedirs('shots',exist_ok=True)
URL=os.environ.get('PAGE','http://127.0.0.1:8782/v3test.html')
NOISE=re.compile(r'font|fonts\.g|stylesheet|mikktspace|Content Security|Fetch API|Failed to load resource|net::ERR|XML Parser')
res=[]; 
def ok(name,cond,detail=''):
    res.append((name,bool(cond),str(detail)[:260])); print(('PASS ' if cond else 'FAIL ')+name+(' :: '+str(detail)[:260] if detail!='' else ''),flush=True)
async def txt(pg,sel): return await pg.evaluate('s=>document.querySelector(s)?.innerText||""',sel)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=EXE,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox','--hide-scrollbars'])
        pg=await b.new_page(viewport={'width':1500,'height':1000}); errs=[]
        pg.on('pageerror',lambda e: errs.append('PAGEERR '+str(e)[:300]))
        pg.on('console',lambda m: errs.append('console.error: '+m.text[:240]) if m.type=='error' and not NOISE.search(m.text) else None)
        await pg.goto(URL); await pg.wait_for_timeout(3500)
        ok('kpi tiles',await pg.evaluate('document.querySelectorAll(".kpi").length')==11,await pg.evaluate('document.querySelectorAll(".kpi").length'))
        n=await pg.evaluate('document.querySelectorAll("#fh tr").length'); ok('firehose rows >= 20',n>=20,n)
        wall=await pg.evaluate('(()=>{const c=document.getElementById("wall"),d=c.getContext("2d").getImageData(0,0,c.width,c.height).data;let nz=0;for(let i=3;i<d.length;i+=4)if(d[i]>0)nz++;return [c.width,c.height,nz]})()'); ok('integrity wall drawn',wall[2]>1000,wall)
        await pg.screenshot(path='shots/syn_overview.png',full_page=True)
        # inspect a scene in every tab
        await pg.click('#fh tr >> nth=3'); await pg.wait_for_timeout(300)
        sub=await txt(pg,'#insSub'); ok('inspector selected + VERIFIED',re.search(r'S-\d+',sub) and 'VERIFIED' in sub,sub)
        for t in ['chain','trace','verify','xml','prov','ol','otlp']:
            await pg.click(f'#tabs button[data-t={t}]'); await pg.wait_for_timeout(250)
            body=await txt(pg,'#insBody'); ok(f'tab {t} has content',len(body)>80,len(body))
        v=await txt(pg,'#insBody'); 
        await pg.click('#tabs button[data-t=otlp]'); o=await txt(pg,'#insBody'); ok('otlp has traceId + parentSpanId','traceId' in o and 'parentSpanId' in o)
        await pg.click('#tabs button[data-t=verify]'); vt=await txt(pg,'#insBody'); ok('verify table lists prev-hash checks','prev = SHA-256' in vt and 'content hash' in vt,vt[:120].replace('\n',' '))
        # the firehose picks drawable and nothing-drawable scenes at random, so select a drawable synthetic one by its data, not by row position
        sid=await pg.evaluate('(()=>{for(const tr of document.querySelectorAll("#fh tr")){const s=S.byId.get(tr.dataset.id);if(s&&s.src!=="real"&&s.drawKind==="draws")return s.id}return null})()')
        if sid: await pg.click(f'#fh tr[data-id="{sid}"]'); await pg.wait_for_timeout(300)
        await pg.click('#tabs button[data-t=v3d]')
        try: await pg.wait_for_function('(document.getElementById("v3msg")||{innerText:""}).innerText.includes("%")',timeout=30000)
        except Exception: pass
        m=await txt(pg,'#v3msg'); ok('3D tab: X_ITE loaded a synthetic scene',bool(sid) and ('X_ITE loaded' in m) and ('%' in m),(sid or 'no drawable synthetic row')+' :: '+m.replace('\n',' | ')); 
        await pg.screenshot(path='shots/syn_3d.png')
        # slow renderer: the first frame sample says "no frame", the second is the real one -> must wait, then show pixels, never claim "nothing drawable"
        pick='(()=>{const sc=S.scenes.slice().reverse().find(s=>s.drawKind==="draws");S.sel=sc.id;renderInspector(true);return sc.id})()'
        await pg.evaluate('(()=>{window.__real=window.sampleFrame;let n=0;window.sampleFrame=(fn,ms)=>{n++;if(n===1)return new Promise(r=>setTimeout(()=>r({err:"no frame"}),50));return window.__real(fn,ms)}})()')
        await pg.evaluate(pick); await pg.wait_for_timeout(6000)
        m=await txt(pg,'#v3msg'); hid=await pg.evaluate('document.getElementById("v3none").hidden'); ok('slow first frame: waits, shows pixels, no NOTHING TO DRAW overlay','pixels differing' in m and hid,m.replace('\n',' | '))
        # no frame at all on a drawable scene with no dropped-node messages: says NO FRAME YET, does not claim nothing drawable
        await pg.evaluate('window.sampleFrame=()=>new Promise(r=>setTimeout(()=>r({err:"no frame"}),50))')
        await pg.evaluate(pick); await pg.wait_for_timeout(2500)
        ov=await txt(pg,'#v3none'); ok('no frame on a drawable scene: NO FRAME YET, not NOTHING TO DRAW','NO FRAME YET' in ov and 'NOTHING TO DRAW' not in ov,ov[:140].replace('\n',' | '))
        await pg.evaluate('(()=>{window.sampleFrame=window.__real})()')   # a bare assignment would hand Playwright a function, which it calls
        await pg.click('#tabs button[data-t=chain]')
        # fault injection, unsigned
        for f in ['edit','del','flipmid','fliplast']:
            await pg.click(f'[data-f={f}]'); await pg.wait_for_timeout(300)
        await pg.wait_for_function('S.detected>=3',timeout=40000)   # the scrubber names the three detectable ones; no fixed sleep, so a loaded machine cannot flake this
        await pg.wait_for_timeout(500)
        kp=await pg.evaluate('[...document.querySelectorAll(".kpi")].map(k=>k.innerText.replace(/\\n/g," | "))')
        inj=[k for k in kp if k.startswith('INJECTED')]; ok('unsigned: 3 of 4 injections caught (last-verdict flip is the stated gap)','3' in (inj[0] if inj else '') and '/ 3' in (inj[0] if inj else ''),inj)
        # signing on, inject last-verdict flip on a sealed scene
        await pg.click('#bSeal'); await pg.wait_for_timeout(1500)
        r=await pg.evaluate('(()=>{const sc=S.scenes.slice().reverse().find(s=>s.sealed&&s.status==="verified"&&!s.injured);if(!sc)return null;inject("fliplast",sc);return sc.id})()'); ok('sealed scene found + injected',r,r)
        await pg.wait_for_timeout(8000)
        st=await pg.evaluate('(id=>{const s=S.byId.get(id);return s?s.status+"|det="+s.detected:"gone"})',r); ok('sealed last-verdict flip detected as seal-fail',st.startswith('seal-fail'),st)
        await pg.click('#bSeal')
        # validator ladder in synthetic
        await pg.click('#bUpgrade'); await pg.wait_for_timeout(200); await pg.click('#bRevalidate'); await pg.wait_for_timeout(500)
        al=await txt(pg,'#alerts'); ok('synthetic revalidate reports flips',re.search(r're-validated \d+ scenes on fork@8c0a457: \d+ flipped',al),al[:140].replace('\n',' | '))
        # ---- replay mode
        await pg.click('#seg button[data-m=real]'); await pg.wait_for_timeout(300)
        await pg.evaluate('(()=>{const r=document.getElementById("rate");r.value=60;r.dispatchEvent(new Event("input"))})()'); await pg.wait_for_timeout(5000)
        info=await pg.evaluate('({n:S.scenes.length,done:S.done,seq:S.seq,valid:S.scenes.filter(s=>s.verdict==="valid").length,draws:S.scenes.filter(s=>!s.blank).length,vref:[...new Set(S.scenes.map(s=>s.vref))]})'); ok('replay streamed 174 scenes',info['n']==174 and info['done'],info)
        ok('replay: all chains verify',await pg.evaluate('S.scenes.every(s=>verify(s.xml).ok)'))
        ok('replay: 91 valid on the 11 Oct service',info['valid']==91,info['valid'])
        await pg.screenshot(path='shots/real_overview.png',full_page=True)
        pv=await txt(pg,'#provenance'); mm=re.search(r'(\d+) draw; (\d+) drew only blank frames after X_ITE dropped what it could not read; (\d+) more drew only blank frames; (\d+) are unparseable',pv)
        ok('measured panel: render-pass counts are data-driven (sum to 174, some draw) and the cross-version sentence is present',mm and int(mm.group(1))>0 and sum(int(g) for g in mm.groups())==174 and 'the same draw, blank or unparseable answer for 174 of 174 scenes' in pv,(mm.group(0) if mm else pv[:300]))
        # restart replay to test the ladder from the start
        await pg.click('#bReset'); await pg.evaluate('(()=>{const r=document.getElementById("rate");r.value=60;r.dispatchEvent(new Event("input"))})()'); await pg.wait_for_timeout(5000)
        await pg.click('#bUpgrade'); await pg.click('#bRevalidate'); await pg.wait_for_timeout(400)
        al=await txt(pg,'#alerts'); ok('ladder step 1: 36 flip on fork 8c0a457',re.search(r'fork@8c0a457: 36 flipped',al),al[:200].replace('\n',' | '))
        await pg.click('#bUpgrade'); await pg.click('#bRevalidate'); await pg.wait_for_timeout(400)
        al=await txt(pg,'#alerts'); ok('ladder step 2: 1 more flips on fork eb4b4b4',re.search(r'fork@eb4b4b4: 1 flipped',al),al[:200].replace('\n',' | '))
        v=await pg.evaluate('S.scenes.filter(s=>s.verdict==="valid").length'); ok('54 valid on eb4b4b4 after the ladder',v==54,v)
        ok('valid-and-draws-nothing on fork eb4b4b4 is 0',await pg.evaluate('S.scenes.filter(s=>s.verdict==="valid"&&s.blank).length')==0)
        ok('chains still verify after revalidation',await pg.evaluate('S.scenes.every(s=>verify(s.xml).ok)'))
        # 3D on a real nothing-drawable scene and a real drawing scene
        await pg.evaluate('(()=>{const sc=S.scenes.find(s=>s.drawKind==="nothing drawable"&&s.item.k.includes("geo-03"));S.sel=sc.id;renderInspector(true)})()')
        await pg.click('#tabs button[data-t=v3d]'); await pg.wait_for_timeout(6500)
        m=await txt(pg,'#v3msg'); ov=await txt(pg,'#v3none'); ok('real geo scene: X_ITE says unknown node, only blank frames, overlay NOTHING TO DRAW','BLANK' in m and '0.0%' in m and 'Unknown node' in ov and 'NOTHING TO DRAW' in ov,(m+' || '+ov).replace('\n',' | '))
        await pg.screenshot(path='shots/real_3d_nodraw.png')
        await pg.evaluate('(()=>{const sc=S.scenes.find(s=>s.drawKind==="draws"&&s.item.k.includes("int-01"));S.sel=sc.id;renderInspector(true)})()'); await pg.wait_for_timeout(5000)
        m=await txt(pg,'#v3msg'); ok('real drawing scene: nonblank %','pixels differing' in m,m.replace('\n',' | '))
        await pg.screenshot(path='shots/real_3d_draws.png')
        # stale pixels: X_ITE keeps showing the previous scene's last frame while the next world is swapped in; the page must clear the view first
        await pg.evaluate('(()=>{const sc=S.scenes.find(s=>s.drawKind==="nothing drawable"&&s.item.k.includes("geo-03"));S.sel=sc.id;renderInspector(true)})()'); await pg.wait_for_timeout(6500)
        m=await txt(pg,'#v3msg'); ok('no stale pixels: a nothing-drawable scene right after a drawing one reads 0.0% BLANK','0.0%' in m and 'BLANK' in m,m.replace('\n',' | '))
        # a minimal static scene: the watcher is registered before the load, so it sees the frames whenever they come
        await pg.evaluate('''(()=>{const sc=S.scenes.find(s=>s.drawKind==="draws"),t=Object.assign({},sc,{id:"T-MIN",xml:"<X3D profile='Interchange' version='4.0'><Scene><Shape><Appearance><Material diffuseColor='1 0.4 0.1'/></Appearance><Box/></Shape></Scene></X3D>"});show3d(t)})()''')
        await pg.wait_for_timeout(6500)
        m=await txt(pg,'#v3msg'); mm=re.search(r'differing from background: ([\d.]+)%',m); ok('minimal static scene: watcher sees it draw (more than 1%)',bool(mm) and float(mm.group(1))>1.0 and 'no frame' not in m,m.replace('\n',' | '))
        # the live 3D view must reproduce the offline record (same renderer, same files): sample real scenes of each outcome
        sample=await pg.evaluate("""(()=>{const by=k=>S.scenes.filter(s=>s.drawKind===k);const pick=(k,n)=>{const a=by(k),st=Math.max(1,Math.floor(a.length/n));return a.filter((s,i)=>i%st===0).slice(0,n).map(s=>s.id)};return {"draws":pick("draws",4),"nothing drawable":pick("nothing drawable",3),"blank frame":pick("blank frame",3),"unparseable":pick("unparseable",2)}})()""")
        agree=0; total=0; bad=[]
        for kind,ids in sample.items():
            for sid in ids:
                await pg.evaluate('id=>{S.sel=id;renderInspector(true)}',sid); await pg.wait_for_timeout(6500)
                m=await txt(pg,'#v3msg'); ov=await txt(pg,'#v3none'); hid=await pg.evaluate('document.getElementById("v3none").hidden')
                live='nothing drawable' if (not hid and 'NOTHING TO DRAW' in ov) else 'unparseable' if (not hid and 'COULD NOT PARSE' in ov) else 'blank frame' if 'BLANK' in m else 'draws' if 'pixels differing' in m else 'other:'+m[:60]
                total+=1; agree+=(live==kind)
                if live!=kind: bad.append((sid,kind,live))
        ok('live 3D view agrees with the offline record on sampled real scenes (at most 1 miss)',total>=10 and agree>=total-1,f'{agree}/{total} agree; misses {bad}')
        await pg.click('#tabs button[data-t=chain]'); await pg.wait_for_timeout(300)
        c=await txt(pg,'#insBody'); ok('real chain tab shows prompt + X_ITE said + draw outcome','prompt' in c and 'X_ITE said' in c and 'draw outcome' in c,c[-260:].replace('\n',' | '))
        # share-safe
        await pg.click('#bSafe'); await pg.wait_for_timeout(500)
        fhtxt=await txt(pg,'#fh'); ok('share-safe hides model names in the firehose','qwen' not in fhtxt and 'gpt-oss' not in fhtxt,fhtxt[:80].replace('\n',' '))
        await pg.click('#tabs button[data-t=xml]'); x=await txt(pg,'#insBody'); ok('share-safe hides names/run ids/hardware in XML','qwen' not in x and 'g2-standard' not in x,x[:100])
        kp=await pg.evaluate('[...document.querySelectorAll(".kpi")].map(k=>k.innerText.replace(/\\n/g," | "))'); ok('share-safe hides cost KPI',any('hidden' in k for k in kp),[k for k in kp if 'COST' in k.upper() or 'SPEND' in k.upper()])
        await pg.click('#bSafe')
        # phone width
        pg2=await b.new_page(viewport={'width':390,'height':844}); e2=[]
        pg2.on('pageerror',lambda e: e2.append(str(e)[:200]))
        await pg2.goto(URL); await pg2.wait_for_timeout(2500)
        sw=await pg2.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]'); off=await pg2.evaluate('[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1&&!e.closest(".scroll")&&!e.closest("svg")).slice(0,6).map(e=>e.tagName+"."+e.className+" "+Math.round(e.getBoundingClientRect().right))'); ok('phone width: no horizontal page scroll',sw[0]<=sw[1]+1,[sw,off])
        await pg2.screenshot(path='shots/phone.png',full_page=False)
        errs=[e for e in errs if 'Failed to fetch' not in e]; ok('no page errors (X_ITE wasm fetch excluded)',not errs and not e2,(errs+e2)[:4])
        print('\nSUMMARY',sum(1 for r in res if r[1]),'pass',sum(1 for r in res if not r[1]),'fail')
        await b.close()
asyncio.run(main())
