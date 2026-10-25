"""check_v4_bench.py — S10 The Bench (SPEC S10; WORKPLAN 34-bench acceptance).
Run: python3 demo/v4/build_v4.py demo/build/v4 --files-map && python3 demo/tests/check_v4_bench.py [--csp viewer]   (V4_BUILD=<dir> for a module build)
Viewer page: the bench auto-loads the hero's attempt 1 (sp-09 · gemini-3.8-flash, RECORDED 17 Oct) once live.bodies lands, validates it here through
VAL (js-port-of-8dd0d3e), the report shows the recorded first finding (roughness) and INVALID, the gutter marks the bad line, the named fix
drop-attribute is offered, APPLY ALL turns the verdict VALID in this browser; the commit slider has ten notches: recorded fork@eb4b4b4 and
fork@8dd0d3e verdicts for the recorded attempt, the js-port live verdict; an edited text leaves only the port's notch live (the recorded ones grey);
a broken tag reports NOT WELL-FORMED and never reaches STAGE.measure; DRAWS? measures a small box through STAGE.measure (nb > 0.01, MEASURED here);
STAMP THIS EDIT appends repair{human} + validate{js-port} (+ render when measured) through HASH, the chain verifies, the scene lands on the wall as
B-001 src bench, the aggregates are untouched (c.calls still 358); loadSelected takes the selected wall scene; a replay body shows the recorded notches;
the section fits 390 px without horizontal scroll; no page errors.
noeval page: the bench opens whatever VAL decides (full when wasm is still allowed, read-only with the reason when not); no page errors.
FAIL-SOFT (exit 2 unless JSVAL_OPTIONAL=1) when demo/jsval/x3dval.js is absent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
BOX = "<X3D profile='Interchange' version='4.0'>\\n  <Scene>\\n    <Viewpoint position='0 0 5'/>\\n    <Shape>\\n      <Appearance><Material diffuseColor='0.9 0.5 0.2'/></Appearance>\\n      <Box size='2.4 2.4 2.4'/>\\n    </Shape>\\n  </Scene>\\n</X3D>\\n"
async def main():
    if not os.path.isfile(os.path.join(REPO, "demo", "jsval", "x3dval.js")):
        fx.fail_soft("MISSING jsval", "demo/jsval/x3dval.js absent: the bench cannot validate here; everything below is skipped")
        fx.summary(); return
    src = open(os.path.join(REPO, "demo", "v4", "js", "34-bench.js"), encoding="utf-8").read()
    fx.ok("34-bench.js never says fork@ for its own work (only 'fork@' recorded refs) and labels js-port-of-8dd0d3e", "js-port-of-8dd0d3e" in src and "fork@eb4b4b4 recorded" in src and "setInterval" not in src and "innerHTML" in src and src.count("innerHTML") <= 2)
    async with fx.browser() as b:
        pg = await fx.page(b, fx=1)
        await fx.goto(pg)
        fx.ok("section #bench mounted with the closed-vocabulary stamps", await fx.wait(pg, "document.querySelector('#bench .sb #benchTa')&&/js-port-of-8dd0d3e here/.test(document.querySelector('#bench .sh').textContent)&&/RE-RUN HERE/.test(document.querySelector('#bench .sh').textContent)&&/X_ITE 16\\.5\\.0 in this browser/.test(document.querySelector('#bench .sh').textContent)", 60000), (await fx.txt(pg, "#bench .sh"))[:300])
        fx.ok("ten notches on the commit slider, select twin for phones", await pg.evaluate("document.querySelectorAll('#benchNotches .notch').length===10&&document.querySelectorAll('#benchSel option').length===10&&__bench.slider.notches.length===10"), await pg.evaluate("__bench.slider.notches"))
        fx.ok("hero attempt 1 auto-loaded once live.bodies landed", await fx.wait(pg, "__bench.loads>=1&&__bench.src&&__bench.src.kind==='live'", 180000), await pg.evaluate("__bench.src"))
        fx.ok("source line names the hero · gemini-3.8-flash · attempt 1 · RECORDED 17 Oct", await pg.evaluate("/hero sp-09 · gemini-3.8-flash · attempt 1 of 2 · RECORDED 17 Oct/.test(document.getElementById('benchSrc').textContent)"), await fx.txt(pg, "#benchSrc"))
        fx.ok("the editor holds the recorded body (LIVE[HERO.items[0].idx].B[0])", await pg.evaluate("BENCH.text()===LIVE[HERO.items[0].idx].B[0]&&BENCH.text().length>500"))
        # VAL comes up (the bench pulled VAL.need() when it mounted in view / loaded)
        fx.ok("VAL reaches 'full' here (worker + XSD 4.0 compile + self-test)", await fx.wait(pg, "VAL.mode==='full'", 150000), await pg.evaluate("[VAL.mode,VAL.reason,VAL.transport]"))
        fx.ok("bench status says the validator is ready, not read-only", await fx.wait(pg, "document.getElementById('benchStatus').dataset.mode==='full'&&__bench.readOnly===false&&!document.getElementById('benchTa').readOnly", 10000), await fx.txt(pg, "#benchStatus"))
        fx.ok("the hero attempt validated here: INVALID, the report names the recorded finding (roughness)", await fx.wait(pg, "__bench.last&&__bench.last.recorded!==true&&__bench.last.valid===false&&document.getElementById('benchRep').textContent.includes('roughness')&&document.getElementById('benchRep').textContent.includes('INVALID')", 30000), await pg.evaluate("[__bench.last&&__bench.last.valid, HERO.items[0].finding, (document.getElementById('benchRep').textContent||'').slice(0,200)]"))
        fx.ok("the report card carries the port's label and never fork@ for the live verdict", await pg.evaluate("(t=>t.includes('js-port-of-8dd0d3e')&&!t.includes('fork@'))(document.getElementById('benchRep').textContent)"))
        fx.ok("named fix offered: drop-attribute (roughness) with an APPLY button", await pg.evaluate("__bench.fixes.some(f=>f.kind==='drop-attribute'&&/roughness/.test(f.label))&&document.querySelectorAll('#benchRep .repApply').length>=1&&document.querySelectorAll('#benchFixes .benchFix').length>=1"), await pg.evaluate("__bench.fixes"))
        fx.ok("gutter marks the bad line (panel benchGutter drew marks)", await fx.wait(pg, "__panels.benchGutter&&__panels.benchGutter.marks>0", 10000), await pg.evaluate("__panels.benchGutter&&__panels.benchGutter.marks"))
        n0 = await pg.evaluate("__bench.last.xsd.errors.length")
        r = await pg.evaluate("(async()=>{const r=await BENCH.applyAll();return r&&{valid:r.valid,xe:r.xsd.errors.length,codes:codesOfRes(r),applied:__bench.applied.map(a=>a.kind)}})()")
        fx.ok(f"APPLY ALL: {n0} XSD line(s) → VALID in this browser (the fork's deterministic fix, applied as text)", r and r["valid"] is True and r["xe"] == 0 and "drop-attribute" in r["applied"], r)
        fx.ok("status pill VALID, the text is now 'edited in this browser', no roughness left", await pg.evaluate("document.getElementById('benchRep').textContent.includes('VALID')&&!document.getElementById('benchRep').textContent.includes('INVALID')&&/edited in this browser/.test(document.querySelector('#bench .benchEd .sub, #bench .benchEd header .sub')?.textContent||document.getElementById('bench').textContent)&&!/roughness=/.test(BENCH.text())"))
        fx.ok("gutter after the fix: the bad mark is gone (ok marks only)", await fx.wait(pg, "__panels.benchGutter.marks===0||!__bench.last.xsd.errors.length", 5000))
        # ---- the commit slider ----
        await pg.evaluate("BENCH.loadHero()")
        fx.ok("slider on the recorded attempt: eb4b4b4 and 8dd0d3e notches are recorded verdicts, the port notch live", await fx.wait(pg, "(v=>v.eb.state==='rec'&&v.eb.valid===false&&v.dd.state==='rec'&&v.dd.valid===false&&v.port.state==='live'&&v.port.valid===false)({eb:BENCH.verdictAt('eb4b4b4'),dd:BENCH.verdictAt('8dd0d3e'),port:BENCH.verdictAt('port')})", 30000), await pg.evaluate("JSON.stringify({eb:BENCH.verdictAt('eb4b4b4'),dd:BENCH.verdictAt('8dd0d3e'),port:BENCH.verdictAt('port'),svc:BENCH.verdictAt('svc')})"))
        await pg.evaluate("BENCH.setNotch(6)")
        fx.ok("notch 6 = fork@eb4b4b4 recorded · INVALID · xsd in #benchVerdict", await pg.evaluate("/fork@eb4b4b4 recorded · INVALID · xsd/.test(document.getElementById('benchVerdict').textContent)&&__bench.slider.active.id==='eb4b4b4'"), await fx.txt(pg, "#benchVerdict"))
        await pg.evaluate("BENCH.setNotch(9)")
        fx.ok("notch 9 = js-port-of-8dd0d3e here · INVALID", await pg.evaluate("/js-port-of-8dd0d3e here · INVALID/.test(document.getElementById('benchVerdict').textContent)"), await fx.txt(pg, "#benchVerdict"))
        fx.ok("an edited text: recorded notches grey ('not recorded for this text'), port still live", await pg.evaluate("(async()=>{await BENCH.set(BENCH.text().replace('roughness=', 'roughnessX='));const e=BENCH.verdictAt('eb4b4b4'),p=BENCH.verdictAt('port');return e.state==='grey'&&/not recorded/.test(e.why)&&p.state==='live'})()"), await pg.evaluate("JSON.stringify([BENCH.verdictAt('eb4b4b4'),BENCH.verdictAt('port')])"))
        # ---- malformed: NOT WELL-FORMED, never measured ----
        loads0 = await pg.evaluate("__stage.measure.loads")
        m = await pg.evaluate("(async()=>{const r=await BENCH.set(\"<X3D profile='Interchange' version='4.0'><Scene><Shape></Scene>\");return [r.valid,r.xsd.errors[0],document.getElementById('benchRep').textContent.includes('NOT WELL-FORMED'),__bench.fixes.length]})()")
        fx.ok("broken tag → NOT WELL-FORMED (XML parse error), no fixes offered", m[0] is False and str(m[1]).startswith("XML parse error") and m[2] is True and m[3] == 0, m)
        await pg.wait_for_timeout(600)
        fx.ok("a malformed body never reaches STAGE.measure (auto-measure gated)", await pg.evaluate("__stage.measure.loads") == loads0)
        # ---- DRAWS? ----
        fx.ok("STAGE.measure browser ready", await fx.wait(pg, "STAGE.measure.browser", 90000), await pg.evaluate("__stage.measure.err"))
        await pg.evaluate("document.getElementById('benchAuto').checked=false")
        r = await pg.evaluate("(async()=>{const v=await BENCH.set(`" + BOX + "`);const m=await BENCH.measure();return {valid:v.valid,nb:m&&m.nb,frames:m&&m.frames,kind:m&&m.kind,err:m&&m.err,noFrame:m&&m.noFrame,out:document.getElementById('benchDrawOut').textContent}})()")
        fx.ok("a small orange box: VALID here, measured nb > 0.01 through STAGE.measure, output says MEASURED here · X_ITE 16.5.0 in this browser", r["valid"] is True and r["nb"] is not None and r["nb"] > 0.01 and not r["err"] and "MEASURED here" in r["out"] and "X_ITE 16.5.0 in this browser" in r["out"], {k: r[k] for k in ("nb", "frames", "kind", "err", "noFrame")})
        fx.ok("__bench.measured carries the content hash of the measured text", await pg.evaluate("__bench.measured&&__bench.measured.hash===contentHash(BENCH.text())"))
        # ---- STAMP THIS EDIT ----
        calls0 = await pg.evaluate("(async()=>(await CLAIMS.run('c.calls')).value)()")
        nv0 = await pg.evaluate("S.viewer.length")
        sc = await pg.evaluate("(async()=>{const sc=await BENCH.stamp();if(!sc)return null;const st=readSteps(sc.xml).map(([n,c])=>JSON.parse(c));const v=verify(sc.xml);return {id:sc.id,src:sc.src,vref:sc.vref,verdict:sc.verdict,ok:v.ok,status:v.status,ops:st.map(s=>s.op),last:st.slice(-3),n:st.length,rec:document.getElementById('benchReceipt').textContent,note:document.getElementById('benchStampNote').textContent,sel:S.sel}})()")
        fx.ok("STAMP THIS EDIT → B-001 src bench on the wall, chain verifies", sc and sc["id"].startswith("B-") and sc["src"] == "bench" and sc["ok"] is True and sc["vref"] == "js-port-of-8dd0d3e" and sc["verdict"] == "valid", sc and {k: sc[k] for k in ("id", "src", "ok", "status", "verdict", "n", "sel")})
        fx.ok("steps end repair{human, viewer edit, report_shown} → validate{js-port-of-8dd0d3e, measured ms} → render{x_ite in this browser, measured}", sc and sc["ops"][-3:] == ["repair", "validate", "render"] and sc["last"][0]["kind"] == "human" and sc["last"][0]["agent"] == "viewer edit" and sc["last"][0]["report_shown"] is True and sc["last"][1]["validator_ref"] == "js-port-of-8dd0d3e" and sc["last"][1]["ms_src"] == "measured" and "in this browser" in sc["last"][2]["renderer"] and sc["last"][2]["nonblank_ratio"] > 0.01, sc and sc["last"])
        fx.ok("receipt shows the verified chain, the new rows, the honesty line", sc and "VERIFIED" in sc["rec"].upper() and "viewer edit" in sc["rec"] and "js-port-of-8dd0d3e" in sc["rec"] and "render measured here" in sc["rec"] and "excluded from every aggregate" in sc["note"], sc and sc["rec"][:200])
        fx.ok("the wall gained one viewer scene, selected; aggregates untouched (c.calls unchanged)", await pg.evaluate("S.viewer.length") == nv0 + 1 and await pg.evaluate("S.sel") == sc["id"] and await pg.evaluate("(async()=>(await CLAIMS.run('c.calls')).value)()") == calls0 == 358, [nv0, calls0])
        fx.ok("__bench.stamped lists it", await pg.evaluate("__bench.stamped.length>=1&&__bench.stamped[0]===S.sel"))
        # ---- loadSelected: the stamped scene itself (stripProv) ----
        ls = await pg.evaluate("(async()=>{const r=await BENCH.loadSelected();return [__bench.src&&__bench.src.label,BENCH.text().includes('<Box'),!/x3dml:prov|<prov/.test(BENCH.text()),r&&r.valid]})()")
        fx.ok("loadSelected takes the selected wall scene (prov stripped) and validates it", ls[0] and ls[0].startswith("B-") and ls[1] and ls[2] and ls[3] is True, ls)
        # ---- a replay body: recorded notches from the 11 Oct replay + drift ----
        rp = await pg.evaluate("(async()=>{const it=REAL.find(i=>i.f2&&i.f2[1]&&i.f2[1].length)||REAL[0];const r=await BENCH.load(it.b,'replay · '+it.k,{kind:'real',item:it});const v=id=>BENCH.verdictAt(id);return {k:it.k,f2:it.f2,port:r&&[r.valid,codesOfRes(r)],svc:v('svc').state,c8:v('8c0a457').state,eb:v('eb4b4b4'),dd:v('8dd0d3e'),p:v('port').state}})()")
        fx.ok("replay body: svc@11Oct, fork@8c0a457 … fork@eb4b4b4 and fork@8dd0d3e notches are recorded verdicts; the port's notch live", rp["svc"] == "rec" and rp["c8"] == "rec" and rp["eb"]["state"] == "rec" and rp["dd"]["state"] == "rec" and rp["p"] == "live", rp)
        fx.ok("replay body: the port agrees with the recorded fork@8dd0d3e verdict (valid flag + codes)", rp["port"][0] == rp["dd"]["valid"] and sorted(rp["port"][1]) == sorted(rp["dd"]["codes"]), {"port": rp["port"], "8dd0d3e": rp["dd"]})
        # ---- phone ----
        await pg.set_viewport_size({"width": 390, "height": 844})
        await pg.wait_for_timeout(700)
        fx.ok("phone 390 px: no horizontal scroll on the page or the bench grid", await pg.evaluate("document.documentElement.scrollWidth<=391&&document.getElementById('bench').scrollWidth<=391"), await pg.evaluate("[document.documentElement.scrollWidth,document.getElementById('bench').scrollWidth,document.querySelector('.benchGrid').scrollWidth]"))
        fx.ok("phone: the slider becomes the <select> (notches hidden)", await pg.evaluate("getComputedStyle(document.getElementById('benchSel')).display!=='none'&&getComputedStyle(document.getElementById('benchNotches')).display==='none'"))
        await pg.set_viewport_size({"width": 1500, "height": 1000})
        # gutter cost: the cached layer repaints only on a state change; 30 scrolled frames must stay under the 4 ms budget at p95
        gp = await pg.evaluate("(async()=>{await BENCH.loadHero();const ta=document.getElementById('benchTa'),p=__panels.benchGutter;for(let i=0;i<30;i++){ta.scrollTop=(i*37)%Math.max(1,ta.scrollHeight-ta.clientHeight);p.forceDraw=true;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}const t=p._t.slice(-30).sort((a,b)=>a-b);return {n:t.length,p95:t[Math.floor(t.length*.95)]||t[t.length-1],max:t[t.length-1],stat:LOOP.stats.panel.benchGutter,draws:p.draws,rateHz:p.rateHz}})()")
        fx.ok("benchGutter draw p95 under its 4 ms budget over 30 scrolled repaints, and the whole-session p95 (LOOP.stats, incl. the chunked layer repaints after load/APPLY) under 4 ms", gp["n"] >= 20 and gp["p95"] < 4 and gp["stat"]["p95"] < 4, gp)
        fx.ok("an unchanged bench state draws nothing (second draw of the same key costs < 0.5 ms)", await pg.evaluate("(async()=>{const p=__panels.benchGutter;p.forceDraw=true;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));p.forceDraw=true;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return LOOP.stats.panel.benchGutter.last<0.5})()"), await pg.evaluate("LOOP.stats.panel.benchGutter.last"))
        errs = fx.errors(pg)
        fx.ok("no page errors", not errs, errs[:5])
        fx.ok("no boot errors in #under (BOOT.log empty)", await pg.evaluate("BOOT.log.length") == 0, await pg.evaluate("BOOT.log"))
        await pg.context.close(); fx.stop()
        # ---- noeval: the bench opens whatever the policy allows ----
        ne = Fixture(csp="noeval", argv=[]); ne.res = fx.res
        pg2 = await ne.page(b); await ne.goto(pg2)
        fx.ok("[noeval] bench mounts", await ne.wait(pg2, "document.getElementById('benchTa')&&__bench.slider.notches.length===10", 60000))
        await pg2.evaluate("VAL.need()")
        fx.ok("[noeval] VAL settles (full when wasm stays allowed under this profile, none with a reason when not)", await ne.wait(pg2, "VAL.mode==='full'||VAL.mode==='none'", 150000), await pg2.evaluate("[VAL.mode,VAL.reason,ENV.wasmInstantiate,ENV.eval]"))
        mode = await pg2.evaluate("VAL.mode")
        if mode == "none":
            fx.ok("[noeval] read-only with the reason in the banner", await ne.wait(pg2, "__bench.readOnly===true&&document.getElementById('benchTa').readOnly&&/READ-ONLY/.test(document.getElementById('benchStatus').textContent)&&VAL.reason.length>0", 10000), await ne.txt(pg2, "#benchStatus"))
        else:
            fx.ok("[noeval] editable; the hero attempt validated here", await ne.wait(pg2, "__bench.readOnly===false&&__bench.last&&__bench.last.recorded!==true&&__bench.last.valid===false", 120000), await pg2.evaluate("[__bench.loads,__bench.last&&__bench.last.valid]"))
        e2 = ne.errors(pg2)
        fx.ok("[noeval] no page errors", not e2, e2[:5])
        await pg2.context.close(); ne.stop()
    fx.summary()
Fixture.run(main)
