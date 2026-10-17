"""Fallback: when X_ITE's own files do not load, the 3D tab says so and every other panel still works."""
import asyncio, re, os
from playwright.async_api import async_playwright
EXE=os.environ.get('CHROME')   # unset: Playwright's own Chromium
URL=os.environ.get('PAGE','http://127.0.0.1:8782/v2test.html')
res=[]
def ok(n,c,d=''):
    res.append(bool(c)); print(('PASS ' if c else 'FAIL ')+n+(' :: '+str(d)[:300] if d!='' else ''),flush=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=EXE,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox','--hide-scrollbars'])
        pg=await b.new_page(viewport={'width':1500,'height':1000}); errs=[]
        pg.on('pageerror',lambda e: errs.append(str(e)[:200]))
        await pg.route('**/xite/x_ite.min.js',lambda r: r.abort())
        await pg.goto(URL); await pg.wait_for_timeout(3000)
        await pg.click('#fh tr >> nth=2'); await pg.wait_for_timeout(300)
        await pg.click('#tabs button[data-t=v3d]'); await pg.wait_for_timeout(2500)
        msg=await pg.evaluate('document.getElementById("view3d").innerText')
        ok('3D tab names the missing X_ITE files',('published beside this page' in msg) and ('did not load' in msg),msg[:200].replace('\n',' | '))
        for t in ['chain','trace','verify','xml','prov','ol','otlp']:
            await pg.click(f'#tabs button[data-t={t}]'); await pg.wait_for_timeout(200)
            n=len(await pg.evaluate('document.getElementById("insBody").innerText')); ok(f'tab {t} still has content',n>80,n)
        await pg.click('#bTour'); await pg.wait_for_timeout(2500)
        tn=await pg.evaluate('document.getElementById("tn").innerText'); ok('tour still opens',bool(re.search(r'1\s*/\s*9',tn)) or bool(tn.strip()),tn[:80])
        k=await pg.evaluate('document.querySelectorAll("#fh tr").length'); ok('firehose still streams',k>=20,k)
        ok('no page errors',not errs,errs)
        await b.close()
    print('\nSUMMARY',sum(res),'pass',len(res)-sum(res),'fail')
    raise SystemExit(0 if all(res) else 1)
asyncio.run(main())
