"""Headless regression for the Live run 17 Oct mode of Tether Firehose 3: the recorded run streams, the waterfall and the Tether tab are drawn from the embedded data,
every chain verifies and names each attempt, the share-safe switch hides model names and costs, and the page stays inside a phone viewport.
PAGE=<url> selects the build under test (the private build by default); SHARE=1 marks the --share build (no vendor names may exist in the DOM at all)."""
import asyncio, os, re
from playwright.async_api import async_playwright
EXE = os.environ.get('CHROME')   # unset: Playwright's own Chromium
os.makedirs('shots', exist_ok=True)
URL = os.environ.get('PAGE', 'http://127.0.0.1:8782/v3test.html')
SHARE = os.environ.get('SHARE') == '1'
NOISE = re.compile(r'font|fonts\.g|stylesheet|mikktspace|Content Security|Fetch API|Failed to load resource|net::ERR|XML Parser')
NAMES = re.compile(r'gemini|gpt-6|\bglm\b|nemotron|zhipu|nvidia|openai|aiplatform', re.I)
res = []
def ok(name, cond, detail=''):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name + (' :: ' + str(detail)[:300] if detail != '' else ''), flush=True)
async def txt(pg, sel): return await pg.evaluate('s=>document.querySelector(s)?.innerText||""', sel)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--hide-scrollbars'])
        pg = await b.new_page(viewport={'width': 1500, 'height': 1000}); errs = []
        pg.on('pageerror', lambda e: errs.append('PAGEERR ' + str(e)[:300]))
        pg.on('console', lambda m: errs.append('console.error: ' + m.text[:240]) if m.type == 'error' and not NOISE.search(m.text) else None)
        await pg.goto(URL); await pg.wait_for_timeout(3000)
        ok('live data is embedded', await pg.evaluate('LIVE.length>=40 && LM.models.length>=3 && !!LIVESTATS'), await pg.evaluate('[LIVE.length,LM.models.length]'))
        ok('waterfall card takes no room outside the live mode', await pg.evaluate('document.getElementById("wfCard").getBoundingClientRect().height')==0, await pg.evaluate('document.getElementById("wfCard").getBoundingClientRect().height'))
        await pg.click('#seg button[data-m=live]'); await pg.wait_for_timeout(400)
        ok('live mode selected, mode tag names the run', await pg.evaluate('S.mode')=='live' and 'RECORDED LIVE RUN' in await txt(pg, '#modeTag'), await txt(pg, '#modeTag'))
        ok('waterfall card visible only in live mode', not await pg.evaluate('document.getElementById("wfCard").hidden'))
        ok('validator ladder is off in live mode', await pg.evaluate('document.getElementById("bUpgrade").disabled && document.getElementById("bRevalidate").disabled'))
        ok('speed control relabelled', (await txt(pg, '#rateL')).strip() == 'speed' and (await txt(pg, '#rateV')).startswith('×'), await txt(pg, '#rateV'))
        await pg.screenshot(path='shots/live_start.png', full_page=True)
        await pg.evaluate('(()=>{const r=document.getElementById("rate");r.value=60;r.dispatchEvent(new Event("input"))})()')
        await pg.wait_for_timeout(9000)
        mid = await pg.evaluate('({n:S.scenes.length,clk:S.clk,sp:document.querySelectorAll("#svgWF rect.sp").length,fl:document.querySelectorAll("#svgWF rect.sp[fill=\\"var(--acc)\\"]").length})')
        ok('mid-run: scenes released follow the clock, some calls in flight', mid['n'] > 0 and mid['sp'] > mid['n'] and mid['fl'] >= 0, mid)
        await pg.screenshot(path='shots/live_mid.png', full_page=True)
        await pg.wait_for_function('S.done', timeout=240000); await pg.wait_for_timeout(700)
        st = await pg.evaluate('({n:S.scenes.length,N:LIVE.length,wf:WF.total,calls:LIVESTATS.calls,rects:document.querySelectorAll("#svgWF rect.sp").length,lanes:WF.lanes.length,models:LM.models.length,stat:document.getElementById("wfStat").innerText})')
        ok('every recorded scene was released', st['n'] == st['N'], st)
        ok('waterfall draws one bar per recorded call', st['rects'] == st['wf'] == st['calls'], st)
        ok('waterfall run strip counts every call', re.search(r'calls done\s*%d of %d' % (st['calls'], st['calls']), st['stat'].replace('\n', ' ')), st['stat'][:160].replace('\n', ' '))
        ok('one lane per model', st['lanes'] == st['models'] >= 3)
        ok('every live chain verifies', await pg.evaluate('S.scenes.every(s=>verify(s.xml).ok)'))
        bad = await pg.evaluate('''(()=>{const bad=[];S.scenes.forEach(s=>{const ops=readSteps(s.xml).map(([n,c])=>JSON.parse(c).op).join(","),A=s.item.A.length,exp=["generate","validate"];for(let k=1;k<A;k++)exp.push("repair","validate");exp.push("render");if(ops!==exp.join(","))bad.push([s.id,ops])});return bad.slice(0,4)})()''')
        ok('chain steps follow the recorded loop: generate, validate, (repair, validate)*, render', not bad, bad)
        lk = await pg.evaluate('''(()=>{let n=0;const bad=[];S.scenes.filter(s=>s.item.A.length>1).forEach(s=>{const st=readSteps(s.xml).map(([i,c])=>JSON.parse(c));for(let k=1;k<s.item.A.length;k++){const rep=st[2*k];if(rep.op!=="repair"||rep.input_sha256!==contentHash(s.item.B[k-1])||rep.output_sha256!==contentHash(s.item.B[k]))bad.push(s.id+":"+k);n++}});return {n,bad:bad.slice(0,4)}})()''')
        ok('every repair step names the previous attempt body by hash and its own output', lk['n'] > 0 and not lk['bad'], lk)
        ok('model panel rows agree with the data', await pg.evaluate('LIVESTATS.per.every(p=>S.mod[p.id].n===p.n&&S.mod[p.id].valid===p.valid&&S.mod[p.id].first===p.first)'))
        ok('latency plot has one dot per call', await pg.evaluate('document.querySelectorAll("#svgDrift circle").length')==st['calls'] and (await txt(pg, '#driftH')).lower() == 'call latency', await txt(pg, '#driftH'))
        pv = await txt(pg, '#provenance')
        ok('panel numbers come from the data', await pg.evaluate('(t=>t.includes(LIVESTATS.n+" scenes from "+LIVESTATS.calls+" real API calls")&&t.includes("valid on the fork at the first try: "+LIVESTATS.first+" of "+LIVESTATS.n)&&t.includes("Of the "+LIVESTATS.valid+" that are valid on the fork, "+LIVESTATS.validNoDraw+" draw nothing")||t.includes("Of the "+LIVESTATS.valid+" that are valid on the fork, 0 draw nothing"))', pv), pv[:200].replace('\n', ' '))
        ok('wall shows every scene', await pg.evaluate('document.getElementById("wallSub").innerText.startsWith(LIVE.length+" stored")'), await txt(pg, '#wallSub'))
        # the Tether tab of a repaired scene
        sid = await pg.evaluate('S.scenes.find(s=>s.item.A.length>1&&s.verdict==="valid")?.id')
        ok('a repaired valid scene exists', bool(sid), sid)
        if sid:
            await pg.evaluate('id=>{S.sel=id;renderInspector(true)}', sid); await pg.click('#tabs button[data-t=tether]'); await pg.wait_for_timeout(500)
            info = await pg.evaluate('({att:document.querySelectorAll("#insBody .att").length,A:S.byId.get(S.sel).item.A.length,df:document.querySelectorAll("#insBody .df").length,add:document.querySelectorAll("#insBody .df .a").length,del:document.querySelectorAll("#insBody .df .d").length,arrows:document.querySelectorAll("#insBody .arrow").length,html:document.getElementById("insBody").innerText})')
            ok('Tether tab: one block per attempt, a diff for every repair', info['att'] == info['A'] and info['df'] == info['A'] - 1 and info['arrows'] == info['A'] - 1, {k: v for k, v in info.items() if k != 'html'})
            ok('Tether tab: the diff has added and removed lines, a header names the counts', info['add'] + info['del'] > 0 and re.search(r'Δ against attempt 1: \+\d+ −\d+ tag lines', info['html']), info['html'][:200].replace('\n', ' | '))
            ok('Tether tab: shows the validator report that was sent back', ('INVALID' in info['html']) and ('VALID' in info['html']) and re.search(r'the model is sent its own report: \d+ error', info['html']), '')
            await pg.screenshot(path='shots/live_tether.png')
            await pg.click('#tabs button[data-t=chain]'); c = await txt(pg, '#insBody')
            ok('Chain tab shows the prompt, calls, tokens, draw outcome', 'prompt' in c and 'calls' in c and 'draw outcome' in c, c[-240:].replace('\n', ' | '))
        # clicking a finished bar opens its scene on the Tether tab
        await pg.evaluate('''(()=>{const r=document.querySelector("#svgWF rect.sp");r.dispatchEvent(new MouseEvent("click",{bubbles:true}))})()''')
        await pg.wait_for_timeout(300)
        ok('clicking a waterfall bar selects that scene on the Tether tab', await pg.evaluate('tab')=='tether' and bool(await pg.evaluate('S.sel')), await pg.evaluate('[tab,S.sel]'))
        # tamper evidence works on live scenes
        t0 = await pg.evaluate('S.detected')
        await pg.evaluate('(()=>{const sc=S.scenes.find(s=>s.status==="verified"&&!s.injured&&s.nsteps>=3);inject("edit",sc)})()')
        await pg.wait_for_function('S.detected>%d' % t0, timeout=60000)
        ok('an edit to a live scene is detected by the scrubber', True)
        # Ask the files: every number is parsed out of the scenes' own heads and reconciles with the recorded run
        await pg.evaluate('document.getElementById("askCard").scrollIntoView()'); await pg.wait_for_timeout(700)
        ask = await pg.evaluate('({nm:LM.models.length,rows:[...document.querySelectorAll("#askBody tr")].map(r=>r.innerText.replace(/\\t/g," | ")),note:document.getElementById("askNote").innerText,find:[...document.querySelectorAll("#askFind tr")].map(r=>r.innerText.replace(/\\t/g," | ")),sub:document.getElementById("askSub").innerText})')
        ok('Ask the files: one row per model plus a total', len(ask['rows']) == ask['nm'] + 1 and ask['rows'][-1].startswith('all'), ask['rows'][-1] if ask['rows'] else '')
        ok('Ask the files: reconciles with the recorded run to the token', 'Reconciles with the recorded run' in ask['note'] and 'Does not reconcile' not in ask['note'], ask['note'][-150:])
        ok('Ask the files: the findings table lists what the validator found first', len(ask['find']) >= 3 and all(re.search(r'\d', r) for r in ask['find']), ask['find'][:3])
        await pg.screenshot(path='shots/live_ask.png')
        # real X_ITE on the recorded scenes, and agreement with the offline record
        kinds = await pg.evaluate('({draws:S.scenes.filter(s=>s.drawKind==="draws").length,nothing:S.scenes.filter(s=>s.drawKind==="nothing drawable").length,blank:S.scenes.filter(s=>s.drawKind==="blank frame").length,unp:S.scenes.filter(s=>s.drawKind==="unparseable").length})')
        ok('most recorded scenes draw (the render pass worked)', kinds['draws'] > 0.3 * st['N'], kinds)
        sample = await pg.evaluate("""(()=>{const by=k=>S.scenes.filter(s=>s.drawKind===k);const pick=(k,n)=>{const a=by(k),st=Math.max(1,Math.floor(a.length/n));return a.filter((s,i)=>i%st===0).slice(0,n).map(s=>s.id)};return {"draws":pick("draws",5),"nothing drawable":pick("nothing drawable",3),"blank frame":pick("blank frame",2),"unparseable":pick("unparseable",2)}})()""")
        agree = total = 0; badl = []
        for kind, ids in sample.items():
            for sid2 in ids:
                await pg.evaluate('id=>{S.sel=id;renderInspector(true)}', sid2)
                await pg.click('#tabs button[data-t=v3d]'); await pg.wait_for_timeout(6500)
                m = await txt(pg, '#v3msg'); ov = await txt(pg, '#v3none'); hid = await pg.evaluate('document.getElementById("v3none").hidden')
                live = 'nothing drawable' if (not hid and 'NOTHING TO DRAW' in ov) else 'unparseable' if (not hid and 'COULD NOT PARSE' in ov) else 'blank frame' if 'BLANK' in m else 'draws' if 'pixels differing' in m else 'other:' + m[:60]
                total += 1; agree += (live == kind)
                if live != kind: badl.append((sid2, kind, live, ov[:120].replace('\n', ' ')))
        ok('live 3D view agrees with the offline record on sampled recorded scenes (at most 1 miss)', total >= 6 and agree >= total - 1, f'{agree}/{total}; misses {badl}')
        await pg.screenshot(path='shots/live_3d.png')
        await pg.click('#tabs button[data-t=chain]')
        # share-safe switch hides model names and costs everywhere on the page
        await pg.click('#bSafe'); await pg.wait_for_timeout(900)
        parts = await pg.evaluate('({fh:document.getElementById("fh").innerText,wf:document.getElementById("svgWF").innerHTML+document.getElementById("wfStat").innerText,mod:document.getElementById("svgModels").innerHTML,lat:document.getElementById("svgDrift").innerHTML,pv:document.getElementById("provenance").innerText,kp:document.getElementById("kpis").innerText,ask:document.getElementById("askCard").innerText})')
        for k, v in parts.items(): ok(f'share-safe: no vendor or model names in {k}', not NAMES.search(v), NAMES.search(v).group(0) if NAMES.search(v) else '')
        ok('share-safe: spend is hidden in the run strip and KPIs', 'hidden' in parts['wf'] and 'hidden' in parts['kp'], '')
        ok('share-safe: Ask the files shows no price', '$' not in parts['ask'] and 'hidden' in parts['ask'], re.findall(r'.{20}\$.{10}', parts['ask'])[:2])
        sid3 = await pg.evaluate('S.scenes.find(s=>s.item.A.length>1)?.id')
        await pg.evaluate('id=>{S.sel=id;renderInspector(true)}', sid3)
        for t in ['tether', 'chain', 'xml', 'prov', 'otlp']:
            await pg.click(f'#tabs button[data-t={t}]'); body = await pg.evaluate('document.getElementById("insBody").innerHTML')
            ok(f'share-safe: no vendor or model names or prices in the {t} tab', not NAMES.search(body) and not re.search(r'"cost[a-z_]*":\s*[0-9.]+', body), NAMES.search(body).group(0) if NAMES.search(body) else '')
        await pg.click('#bSafe')
        if SHARE:
            whole = await pg.evaluate('document.documentElement.outerHTML')
            ok('share build: no vendor or model names anywhere in the page', not NAMES.search(whole), NAMES.search(whole).group(0) if NAMES.search(whole) else '')
        # phone width
        pg2 = await b.new_page(viewport={'width': 390, 'height': 844}); e2 = []
        pg2.on('pageerror', lambda e: e2.append(str(e)[:200]))
        await pg2.goto(URL); await pg2.wait_for_timeout(2500)
        await pg2.click('#seg button[data-m=live]'); await pg2.evaluate('(()=>{const r=document.getElementById("rate");r.value=60;r.dispatchEvent(new Event("input"))})()'); await pg2.wait_for_timeout(8000)
        sw = await pg2.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]')
        off = await pg2.evaluate('[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1&&!e.closest(".scroll,.sc,.tabs,pre,.under,table,#wfScroll,#tour")).slice(0,4).map(e=>e.tagName+"#"+e.id+"."+e.className)')
        ok('phone width: no horizontal page scroll in live mode', sw[0] <= sw[1] + 1 and not off, (sw, off))
        await pg2.screenshot(path='shots/live_phone.png', full_page=False)
        errs = [e for e in errs if 'Failed to fetch' not in e]
        ok('no page errors (X_ITE wasm fetch excluded)', not errs and not e2, (errs + e2)[:4])
        print('\nSUMMARY', sum(res), 'pass', len(res) - sum(res), 'fail')
        await b.close()
    raise SystemExit(0 if all(res) else 1)
asyncio.run(main())
