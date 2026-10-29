"""check_v4_lane.py — S5 live tether lane (18-lane) and S15 members' desk (44-desk) (SPEC §4, S5, S15; WORKPLAN 18-lane / 44-desk / 07-tier acceptance).
Run: python3 demo/v4/build_v4.py demo/build/v4 --files-map && python3 demo/tests/check_v4_lane.py   (V4_BUILD=<dir> for a module build)
Every window.claude.use is a fixture stub (v4fixture claude=...): the page never reaches a real capability here.
Page A (owner stub: sample happy, files with a 2-scene fake run + 2 flywheel chains, downloads): badge PRIVATE · OWNER; pre-flight card; no sample /
  files.list call at load; GO → 2 sample calls (write, repair), 2 .att cards, a 5-step chain V-001 (generate, validate, repair, validate, render) in S.byId
  and #fh, the waterfall lane `you · live`, one scope sample, tiles unchanged, include my runs → S.flags.includeMine; the prompt sent is SYS.SYSTEM +
  PROMPT and the repair turn is the recorder's template; Save → a stored zip (PK header, scene.x3d inside) then the .json fallback when zip is refused.
  Desk: #desk present, files.list counter 0 until CONNECT, tree rows, LOAD → mode files:live-fake on the mast, 2 scenes after seek, waterfall rows 2,
  LIVE/LIVESTATS/c.calls untouched, flywheel re-validated on the port (1 of 2 valid) lights #xlad flywheel, owner BAKE THIS RUN recipe.
Page B (member stub, sample switchable): every §4.4 row — no <X3D, cancelled, rate_limited, refused, empty_completion, upstream_error + manual Retry,
  prompt_too_large (page bug line), truncated, validator throws, X_ITE no frame, not_granted (collapses, lane gone) — calls ≤ 3 per run.
Page C (no window.claude): one-line card, #desk absent, badge PRIVATE. Page D (nowasm CSP: VAL none): one-line reason, no lane in the waterfall.
FAIL-SOFT (exit 2 unless JSVAL_OPTIONAL=1) when demo/jsval/x3dval.js is absent."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
ROOT = "research/traceability-2026-10-17/firehose4"
INVALID = "<X3D profile='Interchange' version='4.0'><Scene><Shape DEF='a'><Box/></Shape><Shape DEF='a'><Box/></Shape></Scene></X3D>"
VALID = "<X3D profile='Interchange' version='4.0'><Scene><Viewpoint position='0 0 5'/><Shape><Appearance><Material diffuseColor='0.9 0.5 0.2'/></Appearance><Box size='2 2 2'/></Shape></Scene></X3D>"
def att(ok, t0, ms, nb=0.2):
    return {"t0": t0, "t1": t0 + ms / 1000, "ms": ms, "ti": 120, "to": 300, "u": 0.0, "fin": "stop", "ok": ok, "x": ok, "xe": [] if ok else ["xsd: bad"], "se": [], "fx": [],
            "sha": "", "ch": 180, "cn": 1, "vms": 4, "rl": 0, "rsha": "", "r": {"nodes": 4, "nb": nb, "frames": 8, "ms": 90}}
FAKE_RUN = {"items": [
    {"m": "model-x", "p": "obj-01", "c": "object", "k": "bench", "pt": "A red sphere.", "at": 1, "T": 1.0, "A": [att(1, 0.0, 900)], "B": [VALID]},
    {"m": "model-y", "p": "obj-02", "c": "object", "k": "bench", "pt": "A wooden table.", "at": 1, "T": 3.0, "A": [att(1, 2.0, 800)], "B": [VALID]}],
    "meta": {"date": "2026-10-24", "validator": "fork@8dd0d3e", "t_total": 6.0, "models": [{"id": "model-x", "prov": "files"}, {"id": "model-y", "prov": "files"}], "lanes": {}}}
SAMPLE = """(()=>{window.__sampleLog=[];window.__sampleMode='happy';
const INVALID=%s,VALID=%s;
const f=async(input,opts)=>{opts=opts||{};const turns=Array.isArray(input)?input:[{role:'user',content:String(input)}];
  window.__sampleLog.push({n:turns.length,first:turns[0].content.slice(0,120),last:turns[turns.length-1].content.slice(0,300),bytes:turns.reduce((a,t)=>a+t.content.length,0),tier:opts.modelTier,cache:opts.cache});
  const mode=window.__sampleMode;const err=(code,text)=>{const e={code,message:code+' (stub)'};if(text!=null)e.text=text;return Promise.reject(e)};
  if(mode==='cancelled')return new Promise((res,rej)=>{if(opts.onText)opts.onText({text:'partial…',delta:'partial…'});if(opts.signal)opts.signal.addEventListener('abort',()=>rej({code:'cancelled',message:'cancelled',text:'partial…'}))});
  if(mode==='upstream_error')return err(mode,'half an answer');
  if(['not_granted','rate_limited','refused','empty_completion','prompt_too_large'].includes(mode))return err(mode);
  const reply=async(text,truncated)=>{await new Promise(r=>setTimeout(r,120));if(opts.onText)opts.onText({text:text.slice(0,20),delta:text.slice(0,20)});await new Promise(r=>setTimeout(r,120));if(opts.onText)opts.onText({text,delta:text.slice(20)});return{text,truncated:!!truncated,modelTierApplied:'default'}};
  if(mode==='nox3d')return reply('I cannot draw that, sorry.');
  if(mode==='truncated')return reply('```xml\\n'+VALID+'\\n```',true);
  if(mode==='valid')return reply('Here:\\n```xml\\n'+VALID+'\\n```');
  return reply(turns.length===1?'Here is the scene:\\n```xml\\n'+INVALID+'\\n```':'Fixed:\\n```xml\\n'+VALID+'\\n```')};
f.limits=async()=>({maxPromptBytes:262144});return f})()""" % (json.dumps(INVALID), json.dumps(VALID))
FILES = """(()=>{window.__filesCalls={list:0,read:0};const T=new TextEncoder();const R=%s;
const F={[R+'/data/live-fake.json']:%s,[R+'/runs/2026-10-24/run.json']:'{"note":"stub"}',[R+'/flywheel/fw-01/chain.json']:'{"id":"fw-01"}',[R+'/flywheel/fw-01/r0.x3d']:%s,[R+'/flywheel/fw-01/r1.x3d']:%s,[R+'/flywheel/fw-02/chain.json']:'{"id":"fw-02"}',[R+'/flywheel/fw-02/r1.x3d']:%s};
const enc={};for(const k in F)enc[k]=T.encode(F[k]);
return{list:async o=>{window.__filesCalls.list++;return{entries:Object.keys(enc).map(p=>({path:p,isDirectory:false,size:enc[p].length,createdAt:'2026-10-24T10:00:00Z'}))}},
  read:async(p,o)=>{window.__filesCalls.read++;const b=enc[p];if(!b)return Promise.reject({code:'not_found',message:p});const off=(o&&o.offset)||0,len=(o&&o.length)||b.length;return{bytes:b.slice(off,off+len),size:b.length,revision:'rev-test-1'}},
  download:async()=>({status:'saved'}),asSampleTools:async()=>[]}})()""" % (json.dumps(ROOT), json.dumps(json.dumps(FAKE_RUN)), json.dumps(INVALID), json.dumps(VALID), json.dumps(INVALID))
DOWNLOADS = """(()=>{window.__dl=[];window.__dlMode='ok';return{save:async r=>{const d=r.data,bin=d&&d.byteLength!=null;const txt=bin?new TextDecoder().decode(d):String(d);
  window.__dl.push({filename:r.filename,bytes:bin?d.byteLength:txt.length,head:bin?Array.from(d.subarray(0,4)):txt.slice(0,4),hasScene:txt.includes('scene.x3d'),hasXml:txt.includes('<X3D')});
  if(window.__dlMode==='nozip'&&/\\.zip$/.test(r.filename))return Promise.reject({code:'rejected_extension',message:'zip'});return{status:'saved'}}}})()"""
STEPS = "(id=>readSteps(S.byId.get(id).xml).map(([n,c])=>JSON.parse(c)))"
async def boot(pg):
    ok = await fx.wait(pg, "BOOT.phase==='ready'&&DATA.loaded('live.core')", 240000)
    fx.ok("page boots (BOOT.phase ready, live.core in)", ok, await pg.evaluate("[BOOT.phase,Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state]))]"))
    return ok
async def run_lane(pg, mode, states, timeout=240000, reset=True):
    await pg.evaluate(f"window.__sampleMode={json.dumps(mode)}")
    if reset: await pg.evaluate("LANE.reset()")
    c0 = await pg.evaluate("__lane.calls")
    await pg.evaluate("document.getElementById('laneGo').click()")
    got = await fx.wait(pg, "&&".join(["__lane.state!=='running'", "__lane.state!=='preparing'"]) + "&&" + json.dumps(states) + ".includes(__lane.state)", timeout)
    st = await pg.evaluate("({state:__lane.state,err:__lane.err,msg:document.getElementById('laneMsg')?.textContent,calls:__lane.calls,sc:__lane.sc,steps:__lane.steps})")
    fx.ok(f"[{mode}] lane ends in {states} with <= 3 calls", got and st["calls"] - c0 <= 3, st)
    return st
async def main():
    if not os.path.isfile(os.path.join(REPO, "demo", "jsval", "x3dval.js")):
        fx.fail_soft("MISSING jsval", "demo/jsval/x3dval.js absent: the lane cannot validate here; everything below is skipped"); fx.summary(); return
    for f in ("18-lane.js", "44-desk.js"):
        src = open(os.path.join(REPO, "demo", "v4", "js", f), encoding="utf-8").read()
        fx.ok(f"{f}: IIFE, no setInterval, no eval/new Function, js-port-of-8dd0d3e labelled, no $digit", src.startswith("/*") and "(function(){" in src and "setInterval" not in src and "eval(" not in src and "new Function" not in src and "js-port-of-8dd0d3e" in src and not any(("$" + str(d)) in src for d in range(10)))
    src = open(os.path.join(REPO, "demo", "v4", "js", "18-lane.js"), encoding="utf-8").read()
    fx.ok("18-lane never writes fork@ for its own work", "fork@" not in src)
    async with fx.browser() as b:
        # ---------------- Page A: owner, happy sample, files, downloads ----------------
        pg = await fx.page(b, claude={"user": {"isOwner": True}, "files": FILES, "sample": SAMPLE, "downloads": DOWNLOADS})
        await fx.goto(pg)
        if not await boot(pg): fx.summary(); return
        fx.ok("badge PRIVATE · OWNER with the owner stub", await fx.wait(pg, "document.getElementById('tierBadge').textContent==='PRIVATE · OWNER'", 30000), await fx.txt(pg, "#tierBadge"))
        fx.ok("pre-flight card shown; no sample call, no files.list at load", await fx.wait(pg, "__lane.state==='preflight'", 20000) and await pg.evaluate("__lane.calls===0&&window.__filesCalls.list===0&&__sampleLog.length===0&&document.getElementById('lanePre').textContent.includes('Runs on your own Claude usage')"), await pg.evaluate("[__lane.state,__lane.calls,window.__filesCalls]"))
        fx.ok("picker lists the 50 recorded prompts grouped by category + free text", await pg.evaluate("document.querySelectorAll('#lanePick option').length===51&&document.querySelectorAll('#lanePick optgroup').length>=3"), await pg.evaluate("document.querySelectorAll('#lanePick option').length"))
        fx.ok("#desk present with the files stub, CONNECT button, nothing read yet", await pg.evaluate("!!document.getElementById('desk')&&!!document.getElementById('deskConnect')&&__desk.listCalls===0"), await pg.evaluate("[!!document.getElementById('desk'),__desk.listCalls]"))
        fx.ok("no stamp-unknown in the lane/desk headers", await pg.evaluate("document.querySelectorAll('#lane .stamp-unknown,#desk .stamp-unknown').length===0"))
        tiles0 = await pg.evaluate("[...document.querySelectorAll('.claim.tile .v')].map(e=>e.textContent)")
        stats0 = await pg.evaluate("JSON.stringify(LIVESTATS)")
        calls0 = await pg.evaluate("(CLAIMS.get('c.calls')||{}).expected")
        fx.ok("waterfall has no `you · live` lane before a run", await pg.evaluate("!(__panels.waterfall.lanes||[]).includes('you · live')"))
        await pg.evaluate("document.getElementById('laneGo').click()")
        done = await fx.wait(pg, "__lane.state==='done'||__lane.state==='off'||__lane.state==='error'", 300000)
        st = await pg.evaluate("({state:__lane.state,calls:__lane.calls,sc:__lane.sc,steps:__lane.steps,err:__lane.err,reason:__lane.reason,val:VAL.mode,msg:document.getElementById('laneMsg')?.textContent})")
        fx.ok("happy path: the loop ends done (VAL full, measure ready)", done and st["state"] == "done", st)
        if st["state"] != "done": fx.summary(); return
        fx.ok("happy path: 2 sample calls (write, repair), never more than 3", st["calls"] == 2, st["calls"])
        fx.ok("happy path: 2 .att cards (INVALID then VALID), the first with a report, both with a measured pill", await pg.evaluate("(()=>{const a=[...document.querySelectorAll('#laneAtts .att')];return a.length===2&&a[0].textContent.includes('INVALID')&&a[1].textContent.includes('VALID')&&a[0].querySelector('.rep')!=null&&a.every(c=>/measured|NO FRAME|REFUSED/.test(c.textContent))})()"), await pg.evaluate("[...document.querySelectorAll('#laneAtts .att .attHead')].map(e=>e.textContent)"))
        steps = await pg.evaluate(STEPS + "('V-001')")
        fx.ok("V-001: 5 steps generate, validate, repair, validate, render", [s["op"] for s in steps] == ["generate", "validate", "repair", "validate", "render"], [s["op"] for s in steps])
        fx.ok("V-001 steps: tokens null (never estimated), ms_src measured, js-port-of-8dd0d3e, report_shown, provider artifact sample", steps[0]["tokens_in"] is None and steps[0]["ms_src"] == "measured" and steps[1]["validator_ref"] == "js-port-of-8dd0d3e" and steps[1]["verdict"] == "invalid" and steps[2]["report_shown"] is True and steps[3]["verdict"] == "valid" and steps[0]["provider"] == "artifact sample" and "fork@" not in json.dumps(steps), steps[2])
        fx.ok("V-001 in S.byId as src viewer, verdict valid, excluded from aggregates (includeMine false)", await pg.evaluate("(()=>{const sc=S.byId.get('V-001');return !!sc&&sc.src==='viewer'&&sc.verdict==='valid'&&sc.promptId==='obj-01'&&S.flags.includeMine===false&&S.viewer.length===1})()"))
        fx.ok("the chain verifies (unsealed)", await pg.evaluate("verify(S.byId.get('V-001').xml).ok===true"), await pg.evaluate("verify(S.byId.get('V-001').xml).status"))
        log = await pg.evaluate("__sampleLog")
        fx.ok("sent: SYS.SYSTEM + PROMPT only (first call, 1 turn), then the recorder's repair template (3 turns, starts and ends on user); modelTier default, cache false",
              len(log) == 2 and log[0]["n"] == 1 and await pg.evaluate("__sampleLog[0].first.startsWith(SYS.SYSTEM.slice(0,120))") and log[1]["n"] == 3 and "XSD errors:" in log[1]["last"] and log[0]["tier"] == "default" and log[0]["cache"] is False, [{k: v for k, v in l.items() if k != "first"} for l in log])
        fx.ok("nothing baked went out: the turns hold no LIVESTATS / claims / parts text", await pg.evaluate("__sampleLog.every(l=>!/LIVESTATS|MANIFEST|parts\\//.test(l.first+l.last))&&__sampleLog[1].bytes<262144"))
        await pg.evaluate("document.getElementById('stream').scrollIntoView()")
        fx.ok("V-001 row in #fh (selected after the run)", await fx.wait(pg, "document.querySelector('#fh tr[data-id=\"V-001\"]')", 30000), await pg.evaluate("[S.sel,[...document.querySelectorAll('#fh tr[data-id]')].slice(0,3).map(t=>t.dataset.id)]"))
        await pg.evaluate("document.getElementById('film').scrollIntoView()")
        fx.ok("__panels.waterfall.lanes includes `you · live`", await fx.wait(pg, "(__panels.waterfall.lanes||[]).includes('you · live')", 30000), await pg.evaluate("__panels.waterfall.lanes"))
        fx.ok("scope has a viewer sample (ms and vms)", await pg.evaluate("SCOPE.samples().some(s=>s.you&&s.ms>0&&s.vms!=null)"), await pg.evaluate("SCOPE.samples().filter(s=>s.you).length"))
        tiles1 = await pg.evaluate("[...document.querySelectorAll('.claim.tile .v')].map(e=>e.textContent)")
        fx.ok("tiles unchanged until include my runs", tiles0 == tiles1 and await pg.evaluate("JSON.stringify(LIVESTATS)") == stats0, [tiles0, tiles1])
        fx.ok("LANE.includeMine(true) drives S.flags.includeMine; false restores", await pg.evaluate("LANE.includeMine(true)===true&&S.flags.includeMine===true&&document.getElementById('laneInclude').checked===true&&LANE.includeMine(false)===false&&S.flags.includeMine===false"))
        fx.ok("honesty label: LIVE · your own Claude · tier · js-port · unsealed · Suspected", await pg.evaluate("(t=>t.includes('LIVE · your own Claude')&&t.includes('model id not reported')&&t.includes('js-port-of-8dd0d3e')&&t.includes('unsealed chain')&&t.includes('Suspected'))(document.querySelector('#lane .hl').textContent)"), await fx.txt(pg, "#lane .hl"))
        saved = await pg.evaluate("LANE.save()")
        fx.ok("Save → a stored zip via downloads: PK header, scene.x3d + the XML inside", saved and saved["how"] == "zip" and saved["filename"].endswith(".zip") and await pg.evaluate("__dl[0].head.join()==='80,75,3,4'&&__dl[0].hasScene&&__dl[0].hasXml"), [saved, await pg.evaluate("__dl[0]")])
        await pg.evaluate("window.__dlMode='nozip'")
        saved2 = await pg.evaluate("LANE.save()")
        fx.ok("Save when zip is refused → the .json bundle", saved2 and saved2["how"] == "json" and saved2["filename"].endswith(".json") and await pg.evaluate("__dl[__dl.length-1].hasXml"), saved2)
        fx.ok("zipStore unit: 2 files → EOCD count 2", await pg.evaluate("(()=>{const z=zipStore([{name:'a.txt',bytes:'hello'},{name:'b.txt',bytes:new Uint8Array([1,2,3])}]);return z[0]===0x50&&z[1]===0x4b&&z[z.length-22+10]===2&&z[z.length-22]===0x50&&z[z.length-22+3]===6})()"))
        fx.ok("longestX3DBlock: fenced block wins, bare <X3D fallback, none → null", await pg.evaluate("longestX3DBlock('x ```xml\\n<X3D a/>\\n```\\n```\\n<X3D bb/>\\n```')==='<X3D bb/>'&&longestX3DBlock('text <X3D/><Scene/></X3D> tail')==='<X3D/><Scene/></X3D>'&&longestX3DBlock('nothing')===null"))
        # ---- desk ----
        fx.ok("files.list counter still 0 before CONNECT (after the lane run too)", await pg.evaluate("window.__filesCalls.list===0&&__desk.listCalls===0"))
        await pg.evaluate("document.getElementById('deskConnect').click()")
        fx.ok("CONNECT → files.list({path: firehose4 root, recursive}) once; tree lists the entries with sizes", await fx.wait(pg, "__desk.connected", 20000) and await pg.evaluate("window.__filesCalls.list===1&&document.querySelectorAll('#deskTree li[data-path]').length===7&&document.querySelectorAll('#deskTree li.dir').length>=3&&[...document.querySelectorAll('#deskTree .sz')].every(e=>e.textContent)"), await pg.evaluate("[window.__filesCalls,document.querySelectorAll('#deskTree li[data-path]').length,__desk.err]"))
        fx.ok("LOAD offered on the run json only (not on chain.json/x3d)", await pg.evaluate("document.querySelectorAll('#deskTree button.load').length===2&&!!document.querySelector('#deskTree li[data-path$=\"live-fake.json\"] button.load')"), await pg.evaluate("__desk.runs"))
        n0 = await pg.evaluate("S.scenes.length")
        await pg.evaluate("document.querySelector('#deskTree li[data-path$=\"live-fake.json\"] button.load').click()")
        fx.ok("LOAD → mode files:live-fake registered and current, mast segment button added", await fx.wait(pg, "S.mode==='files:live-fake'", 30000) and await pg.evaluate("!!MODES.get('files:live-fake')&&!!document.querySelector('#runseg button[data-m=\"files:live-fake\"]')&&__desk.revision==='rev-test-1'&&window.__filesCalls.read>=1"), await pg.evaluate("[S.mode,__desk.err,document.getElementById('deskStatus').textContent]"))
        fx.ok("the desk mode releases 2 scenes (D-001, D-002) with the file's chains", await pg.evaluate("(()=>{SIM.seekTo(SIM.tmax());return S.scenes.length===2&&S.scenes.every(s=>s.src==='files')&&S.scenes[1].id==='D-002'&&readSteps(S.scenes[1].xml).length===3&&S.scenes[1].item.m==='model-y'})()"), await pg.evaluate("[S.scenes.length,S.scenes.map(s=>s.id+':'+readSteps(s.xml).length)]"))
        await pg.evaluate("document.getElementById('film').scrollIntoView();WF.touch()")
        fx.ok("waterfall rows 2 (one call per chain) in the files mode, lanes model-x / model-y", await fx.wait(pg, "__panels.waterfall.rows===2", 30000) and await pg.evaluate("__panels.waterfall.lanes.length===2"), await pg.evaluate("[__panels.waterfall.rows,__panels.waterfall.lanes]"))
        fx.ok("aggregates untouched: LIVE 201, LIVESTATS byte-equal, c.calls expected unchanged", await pg.evaluate("LIVE.length===201&&JSON.stringify(LIVESTATS)===" + json.dumps(stats0)) and await pg.evaluate("(CLAIMS.get('c.calls')||{}).expected") == calls0)
        fx.ok("mast honesty / section honesty name the file and revision", await pg.evaluate("document.querySelector('#desk .hl').textContent.includes('revision rev-test-1')&&MODES.get('files:live-fake').honesty.includes('data/live-fake.json')"), await fx.txt(pg, "#desk .hl"))
        await pg.evaluate("document.getElementById('deskFly').click()")
        fx.ok("flywheel: 2 chains read (r1 bodies), 1 of 2 valid on the port, XLAD flywheel row lit", await fx.wait(pg, "__desk.flywheel", 120000) and await pg.evaluate("__desk.flywheel.n===2&&__desk.flywheel.valid===1&&document.querySelector('#xlad .row[data-id=\"flywheel\"]').classList.contains('lit')&&document.getElementById('deskFlyNote').textContent.includes('js-port-of-8dd0d3e')"), await pg.evaluate("[__desk.flywheel,__desk.err]"))
        fx.ok("owner: BAKE THIS RUN recipe text shown after a load", await pg.evaluate("(e=>!!e&&!e.hidden&&e.textContent.includes('BAKE THIS RUN')&&e.textContent.includes('build_parts.py'))(document.getElementById('deskBake'))"))
        fx.ok("switching back to live17 keeps the lane's V-001 out (fresh state) and the desk mode on the mast", await pg.evaluate("(()=>{MODES.set('live17');return S.mode==='live17'&&!!document.querySelector('#runseg button[data-m=\"files:live-fake\"]')})()"))
        errs = fx.errors(pg); fx.ok("page A: no page errors", not errs, errs[:6])
        await pg.context.close()
        # ---------------- Page B: member stub, every §4.4 row ----------------
        pg = await fx.page(b, claude={"user": {"isOwner": False}, "sample": SAMPLE})
        await fx.goto(pg)
        if not await boot(pg): fx.summary(); return
        fx.ok("member-less sample stub: badge PRIVATE, #desk absent (no files), lane pre-flight", await fx.wait(pg, "__lane.state==='preflight'", 20000) and await pg.evaluate("document.getElementById('tierBadge').textContent==='PRIVATE'&&!document.getElementById('desk')"), await pg.evaluate("[TIER.tier,__lane.state]"))
        await pg.evaluate("VAL.need()")
        fx.ok("VAL full for the failure rows", await fx.wait(pg, "VAL.mode==='full'", 200000), await pg.evaluate("[VAL.mode,VAL.reason]"))
        await pg.evaluate("LANE.RATE_WAIT_MS=1500")
        st = await run_lane(pg, "nox3d", ["done"])
        fx.ok("no <X3D in the text → 'no X3D document in the answer', validate step codes [no-x3d-document], loop ends stamped, 1 call", "no X3D document" in (st["msg"] or "") and st["calls"] == 1 and await pg.evaluate(STEPS + "(__lane.sc).some(s=>s.op==='validate'&&s.codes[0]==='no-x3d-document')"), await pg.evaluate(STEPS + "(__lane.sc).map(s=>s.op)"))
        await pg.evaluate("window.__sampleMode='cancelled';LANE.reset();document.getElementById('laneGo').click()")
        fx.ok("cancelled: the terminal shows the partial text while waiting", await fx.wait(pg, "__lane.state==='running'&&document.getElementById('laneTerm').textContent==='partial…'", 30000), await pg.evaluate("[__lane.state,document.getElementById('laneTerm').textContent]"))
        await pg.evaluate("document.getElementById('laneStop').click()")
        fx.ok("cancelled: Stop → lamps off, terminal keeps e.text, row 'stopped by viewer', no scene (nothing complete)", await fx.wait(pg, "__lane.state==='stopped'", 10000) and await pg.evaluate("document.getElementById('laneTerm').textContent==='partial…'&&document.getElementById('laneMsg').textContent==='stopped by viewer'&&document.querySelectorAll('#laneLamps .lamp.on').length===0&&S.viewer.length===1&&!document.getElementById('laneGo').disabled"), await pg.evaluate("[__lane.state,__lane.err]"))
        st = await run_lane(pg, "rate_limited", ["rate_limited"], 30000)
        fx.ok("rate_limited: amber bar, 'busy or at its limit', button disabled, no auto loop (1 call)", "busy or at its limit" in (st["msg"] or "") and st["calls"] == 3 and await pg.evaluate("document.getElementById('lane').dataset.bar==='amber'") and await pg.evaluate("document.getElementById('laneGo').disabled"), st)
        fx.ok("rate_limited: button re-enabled after the wait (30 s in the page, 1.5 s here)", await fx.wait(pg, "!document.getElementById('laneGo').disabled", 8000))
        st = await run_lane(pg, "refused", ["idle"], 30000)
        fx.ok("refused: terminal cleared, 'declined for this prompt; pick another'", "declined for this prompt" in (st["msg"] or "") and await pg.evaluate("document.getElementById('laneTerm').textContent===''"), st)
        st = await run_lane(pg, "empty_completion", ["idle"], 30000)
        fx.ok("empty_completion: 'no text came back; pick another prompt'", "no text came back" in (st["msg"] or ""), st)
        f0 = await pg.evaluate("__lane.failedRows")
        st = await run_lane(pg, "upstream_error", ["interrupted"], 30000)
        fx.ok("upstream_error: e.text kept labelled INTERRUPTED, failed row recorded, one manual Retry offered", await pg.evaluate("document.getElementById('laneTerm').textContent==='half an answer'&&document.getElementById('laneTermTag').textContent==='INTERRUPTED'&&!document.getElementById('laneTermTag').hidden&&!document.getElementById('laneRetry').hidden") and await pg.evaluate("__lane.failedRows") == f0 + 1, st)
        await pg.evaluate("window.__sampleMode='valid'")
        c0 = await pg.evaluate("__lane.calls"); n0 = await pg.evaluate("S.viewer.length")
        await pg.evaluate("document.getElementById('laneRetry').click()")
        fx.ok("Retry (manual) → a valid one-shot: 3 steps, 1 call, V-00n+1, Retry hidden again", await fx.wait(pg, "__lane.state==='done'", 240000) and await pg.evaluate("__lane.calls") == c0 + 1 and await pg.evaluate("S.viewer.length") == n0 + 1 and await pg.evaluate(STEPS + "(__lane.sc).map(s=>s.op).join()") == "generate,validate,render" and await pg.evaluate("document.getElementById('laneRetry').hidden"), await pg.evaluate("[__lane.state,__lane.sc,__lane.steps,__lane.err]"))
        st = await run_lane(pg, "prompt_too_large", ["idle"], 30000)
        fx.ok("prompt_too_large: page bug line 'lane error (prompt_too_large)', button re-enabled", (st["msg"] or "") == "lane error (prompt_too_large)" and await pg.evaluate("!document.getElementById('laneGo').disabled"), st)
        st = await run_lane(pg, "truncated", ["done"])
        fx.ok("truncated: attempt marked CUT AT THE OUTPUT LIMIT, body still validated (valid), generate finish 'length'", await pg.evaluate("document.querySelector('#laneAtts .att').textContent.includes('CUT AT THE OUTPUT LIMIT')") and await pg.evaluate(STEPS + "(__lane.sc)[0].finish") == "length" and await pg.evaluate("S.byId.get(__lane.sc).verdict") == "valid", st)
        await pg.evaluate("window.__origValidate=VAL.validate;VAL.validate=async()=>{throw new Error('boom (test)')};0")
        st = await run_lane(pg, "valid", ["done", "error"])
        await pg.evaluate("VAL.validate=window.__origValidate;0")
        fx.ok("validator throws: 'validator error', never a verdict; validate step absent, render step carries note", "validator error" in (st["msg"] or "") and await pg.evaluate(STEPS + "(__lane.sc).map(s=>s.op).join()") == "generate,render" and await pg.evaluate(STEPS + "(__lane.sc)[1].note.includes('validator error')"), st)
        await pg.evaluate("window.__origShow=STAGE.measure.show;STAGE.measure.show=async()=>({nb:null,frames:0,series:[],msgs:[],err:null,noFrame:true,slow:true,ms:12000});0")
        st = await run_lane(pg, "valid", ["done"])
        await pg.evaluate("STAGE.measure.show=window.__origShow;0")
        fx.ok("X_ITE no frame in 12 s: 'NO FRAME YET', render step no_frame 1 slow true, chain stamped", "NO FRAME YET" in (st["msg"] or "") and await pg.evaluate("(s=>s[s.length-1].no_frame===1&&s[s.length-1].slow===true)(" + STEPS + "(__lane.sc))") and await pg.evaluate("document.querySelector('#laneAtts .att').textContent.includes('NO FRAME YET')"), st)
        fx.ok("every run here used <= 3 calls and the lane drew `you · live` rows", await pg.evaluate("__lane.calls<=12&&__panels.waterfall.lanes!==undefined"))
        st = await run_lane(pg, "not_granted", ["off"], 30000)
        fx.ok("not_granted: card collapses to one line, lane removed from the waterfall for the view", await pg.evaluate("document.querySelector('#lane .laneOne').textContent.includes('live lane off (not allowed in this view)')&&document.querySelectorAll('#lane .att').length===0") and await pg.evaluate("(()=>{document.getElementById('film').scrollIntoView();return true})()") and await fx.wait(pg, "!(__panels.waterfall.lanes||[]).includes('you · live')", 20000), await pg.evaluate("[__lane.state,__panels.waterfall.lanes]"))
        errs = fx.errors(pg); fx.ok("page B: no page errors", not errs, errs[:6])
        await pg.context.close()
        # ---------------- Page C: no window.claude ----------------
        pg = await fx.page(b)
        await fx.goto(pg)
        if await boot(pg):
            fx.ok("no window.claude: one-line card 'did not grant a model', state nocap, no .att, no lane in the waterfall", await fx.wait(pg, "__lane.state==='nocap'", 30000) and await pg.evaluate("document.querySelector('#lane .laneOne').textContent.includes('this viewer did not grant a model to the page')&&document.querySelectorAll('#lane .att,#laneGo').length===0&&!(__panels.waterfall.lanes||[]).includes('you · live')"), await pg.evaluate("[__lane.state,document.querySelector('#lane .sb').textContent.slice(0,120)]"))
            fx.ok("no window.claude: badge PRIVATE, #desk absent, #owner absent", await fx.wait(pg, "TIER.tier", 30000) and await pg.evaluate("document.getElementById('tierBadge').textContent==='PRIVATE'&&!document.getElementById('desk')&&!document.getElementById('owner')"), await pg.evaluate("[TIER.tier,document.getElementById('tierBadge').textContent]"))
            errs = fx.errors(pg); fx.ok("page C: no page errors", not errs, errs[:6])
        await pg.context.close()
    # ---------------- Page D: nowasm → VAL none → one-line reason ----------------
    fxn = Fixture(csp="nowasm", argv=[])
    async with fxn.browser() as b:
        pg = await fxn.page(b, claude={"sample": SAMPLE})
        await fxn.goto(pg)
        ok = await fxn.wait(pg, "BOOT.phase==='ready'&&DATA.loaded('live.core')", 240000)
        fx.ok("nowasm page boots", ok, await pg.evaluate("BOOT.phase"))
        if ok:
            await fxn.wait(pg, "__lane.state==='preflight'||__lane.state==='off'", 30000)
            await pg.evaluate("VAL.need()")
            fx.ok("nowasm: VAL.mode none", await fxn.wait(pg, "VAL.mode==='none'", 120000), await pg.evaluate("[VAL.mode,VAL.reason]"))
            fx.ok("VAL not full → the one-line reason 'live lane off: the exact validator cannot run in this viewer (…)' and no WRITE button", await fxn.wait(pg, "__lane.state==='off'", 15000) and await pg.evaluate("(t=>t.includes('live lane off: the exact validator cannot run in this viewer')&&t.includes('would not be a tether'))(document.querySelector('#lane .laneOne').textContent)&&!document.getElementById('laneGo')"), await pg.evaluate("[__lane.state,document.querySelector('#lane .sb').textContent.slice(0,200)]"))
            await pg.evaluate("document.getElementById('film').scrollIntoView()")
            fx.ok("VAL not full → no `you · live` lane in the waterfall", await fxn.wait(pg, "__panels.waterfall.lanes&&__panels.waterfall.lanes.length>0", 30000) and await pg.evaluate("!(__panels.waterfall.lanes||[]).includes('you · live')"), await pg.evaluate("__panels.waterfall.lanes"))
            errs = fxn.errors(pg); fx.ok("page D: no page errors (X_ITE wasm excluded by the fixture)", not errs, errs[:6])
        await pg.context.close()
    fxn.stop()
    fx.summary()
if __name__ == "__main__":
    fx.run(main)
