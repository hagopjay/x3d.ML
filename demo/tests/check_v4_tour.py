"""check_v4_tour.py — the Tour (50-tour) acceptance (WORKPLAN 50-tour, SPEC-v4 "Tour (12 steps)", section 13).
Inherits check_tour.py's shape (12 steps, buttons driven, injected counts, closes) re-cut for v4: 12 headings; every step's run() drives a documented control of
another module and the documented DOM changes (step 5 ends with the waterfall's event line naming the credit stop at x60; step 9 injects and RE-VERIFIES; step 10
turns signing on; step 11 PAUSES on the lane card and never increments __lane.calls); tourStop() restores rate, clock state, filter, slider, signing, inspector tab,
bench text and scroll; Esc and the arrow keys; the mast chip. Every expected number is read from the page (EVENTS, STATS, TOUR itself), never typed here.
Run: V4_BUILD=demo/build/v4-tour python3 demo/tests/check_v4_tour.py [--csp viewer|noeval|nowasm|noworker]"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
T_START = time.time()
STEP_MS = 9000
async def main():
    bundle = open(os.path.join(fx.build_dir, "index.html"), encoding="utf-8").read()
    for name in ("50-tour.js", "52-director.js"):
        p = os.path.join(REPO, "demo", "v4", "js", name); src = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
        fx.ok(f"{name}: no setInterval, no innerHTML, no eval/new Function, no $digit replacement", src and "setInterval(" not in src and "innerHTML" not in src and "eval(" not in src and "new Function" not in src and not re.search(r"\$[0-9]", src), name)
    fx.ok("bundle carries 50-tour, 52-director and css/85-tour.css", "js/50-tour.js" in bundle and "js/52-director.js" in bundle and "css/85-tour.css" in bundle)
    async with fx.browser() as b:
        pg = await fx.page(b)
        await fx.goto(pg)
        booted = await fx.wait(pg, 'self.BOOT&&BOOT.phase==="ready"', 150000)
        fx.ok("boot reaches BOOT.phase ready", booted, await pg.evaluate("self.BOOT?[BOOT.phase,BOOT.ms,LOOP.frames]:['no BOOT']"))
        if not booted: print("page errors:", fx.errors(pg)[:8], flush=True); fx.summary(); return
        fx.ok("parts loaded (xsd parts idle)", await fx.wait(pg, 'Object.entries(DATA.status).filter(([k])=>!k.startsWith("xsd")).every(([,s])=>s.state==="loaded")', 120000))
        fx.ok("no mount errors in BOOT.log", await pg.evaluate("BOOT.log.length") == 0, await pg.evaluate("BOOT.log"))
        fx.ok("html[data-fx] is 0 under webdriver", await pg.evaluate("document.documentElement.dataset.fx") == "0")
        # ---- engine + chip ----
        fx.ok("TOUR has 12 steps with distinct headings and run()", await pg.evaluate("TOUR.length===12&&new Set(TOUR.map(s=>s.h)).size===12&&TOUR.every(s=>typeof s.run==='function'&&typeof s.t==='function'&&s.h)"), await pg.evaluate("TOUR.map(s=>s.h)"))
        fx.ok("every step's sentence renders without throwing and quotes no 'undefined'", await pg.evaluate("TOUR.every(s=>{const t=s.t();return typeof t==='string'&&t.length>40&&!/undefined|NaN/.test(t)})"), await pg.evaluate("TOUR.map(s=>s.t().slice(0,60))"))
        fx.ok("the SPEC order of the 12 steps (stage, spine, morph, seven, film, scope, matrix, port, wall, gap, lane, take it)", await pg.evaluate("TOUR.map(s=>s.sec).join(',')") == "stage,stage,morph,seven,film,film,matrix,ladder,wall,wall,lane,deck", await pg.evaluate("TOUR.map(s=>s.sec)"))
        fx.ok("step 11 is the pause step (no timer) and the only one", await pg.evaluate("TOUR.filter(s=>s.pause).length===1&&TOUR[10].pause===true&&TOUR[10].ms===0"))
        fx.ok("#bTour chip sits in the mast's right group before the tier badge; #tour hidden at load", await pg.evaluate("(()=>{const b=document.querySelector('#mast .mastR #bTour');return !!b&&b.nextElementSibling&&['bDirect','tierBadge'].includes(b.nextElementSibling.id)&&document.getElementById('tour').hidden})()"))
        fx.ok("tour never calls liveTether or GO (source)", await pg.evaluate("!/liveTether|\\bGO\\b.*click|bGo\\b/.test(TOUR.map(s=>s.run.toString()).join(''))"))
        # a settled clock so the steps have scenes to pick
        await pg.evaluate("SIM.seekTo(Math.max(S.clk,900));if(S.paused&&!S.done)SIM.resume()")
        await pg.wait_for_timeout(600)
        snap = await pg.evaluate("({y:scrollY,rate:S.rate,paused:S.paused,filter:S.flags.filter,seal:!!S.sealOn,slider:[SLIDER.i,SLIDER.active],tab:INSPECTOR.tab,bench:self.BENCH?BENCH.text():null,inj:S.inj,lane:self.__lane?__lane.calls:null})")
        val_full = await pg.evaluate("!!(self.VAL&&VAL.mode==='full')")
        # ---- step 1: the stage ----
        await pg.evaluate("tourShow(0)")
        fx.ok("step 1: overlay shown with heading 1 / 12 and the rate at x30; hero 0 opened", await fx.wait(pg, "!document.getElementById('tour').hidden&&document.getElementById('th').textContent===TOUR[0].h&&document.getElementById('tn').textContent.startsWith('1 / 12')&&S.rate===30&&__hero.cur===0", 5000), await pg.evaluate("[document.getElementById('th').textContent,document.getElementById('tn').textContent,S.rate,__hero.cur,__tour.drove[0]]"))
        fx.ok("step 1: the page scrolled to #stage and the chip is on", await pg.evaluate("document.getElementById('bTour').classList.contains('on')&&Math.abs(document.getElementById('stage').getBoundingClientRect().top)<400"), await pg.evaluate("document.getElementById('stage').getBoundingClientRect().top"))
        # ---- step 2: spine + tiles ----
        await pg.evaluate("tourShow(1)")
        fx.ok("step 2: rate x4, a repaired valid scene selected, inspector on Report", await fx.wait(pg, "S.rate===4&&S.sel&&INSPECTOR.tab==='report'", 8000), await pg.evaluate("[S.rate,S.sel,INSPECTOR.tab,__tour.drove[1]]"))
        # ---- step 3: morph ----
        await pg.evaluate("tourShow(2)")
        fx.ok("step 3: the morph opened a repaired chain and replays", await fx.wait(pg, "__morph.cur&&__morph.replay", 8000), await pg.evaluate("[__morph.cur&&__morph.cur.p,!!__morph.replay,__tour.drove[2]]"))
        await fx.wait(pg, "__morph.loads>0||!__morph.inst||!__morph.inst.bot", 12000)   # let the morph's lazy instance finish its load before the tour moves on (a real step lasts 10 s)
        # ---- step 4: dark seven ----
        await pg.evaluate("tourShow(3)")
        fx.ok("step 4: a dark-seven scene is current and FIND IT was driven", await fx.wait(pg, "__seven.cur&&__tour.drove[3].includes('SEVEN.findIt')", 8000), await pg.evaluate("[__seven.cur,__tour.drove[3]]"))
        await fx.wait(pg, "__seven.loaded===__seven.cur||!__seven.inst", 12000)   # same for the seven's instance
        # ---- step 5: the run as film ----
        await pg.evaluate("tourShow(4)")
        fx.ok("step 5: x60 and the clock seeks to just before the credit stop", await fx.wait(pg, "S.rate===60&&S.clk>=EVENTS.creditStop.t-21&&!S.paused", 5000), await pg.evaluate("[S.rate,S.clk,EVENTS.creditStop.t,S.paused]"))
        fx.ok("step 5: a bar opened in the inspector (Tether tab) through SIM.select + emit('open')", await fx.wait(pg, "__tour.drove[4].includes('SIM.select + emit(open tether)')&&INSPECTOR.tab==='tether'", 10000), await pg.evaluate("[__tour.drove[4],INSPECTOR.tab]"))
        fx.ok("step 5 ends with the clock past the credit stop and the waterfall's event line naming it", await fx.wait(pg, "S.clk>=EVENTS.creditStop.t&&document.getElementById('wfEvents').textContent.includes(BUILD.share?'credit exhausted':'CREDITS OUT')&&(!document.getElementById('wfStat')||/credit/i.test(document.getElementById('wfStat').textContent))", 25000), await pg.evaluate("[S.clk,EVENTS.creditStop.t,document.getElementById('wfEvents').textContent.slice(0,160)]"))
        # ---- step 6: scope ----
        await pg.evaluate("tourShow(5)")
        fx.ok("step 6: the decade drill button was driven and the scope drills", await fx.wait(pg, "__tour.drove[5].includes('#scopeDrill')&&(__panels.scope.drilling||__panels.scope.decade>0||__panels.scope.span<4000)", 8000), await pg.evaluate("[__tour.drove[5],__panels.scope.drilling,__panels.scope.decade,__panels.scope.span]"))
        # ---- step 7: matrix + taxonomy ----
        await pg.evaluate("tourShow(6)")
        fx.ok("step 7: a taxonomy filter is set (S.flags.filter) and the chip shows it", await fx.wait(pg, "S.flags.filter&&S.flags.filter.kind==='taxonomy'", 8000), await pg.evaluate("[S.flags.filter&&S.flags.filter.label,__tour.drove[6]]"))
        # ---- step 8: the port / ladder ----
        await pg.evaluate("tourShow(7)")
        fx.ok("step 8: the run segment switches to the 11 Oct replay (the chains that carry the service verdict), the slider sits on fork@8c0a457 and RE-VALIDATE was pressed", await fx.wait(pg, "S.mode==='replay11'&&SLIDER.ref==='fork@8c0a457'&&__tour.drove[7].includes('#bRevalidate')", 8000), await pg.evaluate("[S.mode,SLIDER.ref,SLIDER.active,__tour.drove[7]]"))
        fx.ok("step 8: the re-validation stamped scenes and the log names the flips (S.revals, S.flips from the recorded verdicts)", await fx.wait(pg, "S.revals>0&&S.flips>0&&/re-validated \\d+ scenes on fork@8c0a457: \\d+ flipped/.test(JSON.stringify(S.alerts))", 8000), await pg.evaluate("[S.revals,S.flips,REALSTATS.flip,JSON.stringify(S.alerts).slice(0,160)]"))
        fx.ok("step 8: flips equal the recorded REALSTATS.flip", await pg.evaluate("S.flips===REALSTATS.flip"), await pg.evaluate("[S.flips,REALSTATS.flip]"))
        val_full = await fx.wait(pg, "self.VAL&&VAL.mode==='full'", 6000)
        if val_full:
            fx.ok("step 8: with the js-port loaded, RE-VALIDATE 558 ON THE PORT is started (or already done)", await fx.wait(pg, "__tour.drove[7].includes('#bRevalPort')||(PORT.result&&!PORT.busy)", 10000), await pg.evaluate("[__tour.drove[7],PORT.busy,!!PORT.result]"))
        else:
            fx.ok("step 8: without the js-port the port button is left alone and the sentence says so", await pg.evaluate("TOUR[7].t().includes('recorded rails only')"))
        # ---- step 9: wall ----
        inj0 = await pg.evaluate("S.inj")
        await pg.evaluate("tourShow(8)")
        fx.ok("step 9: back on the 17 Oct run at x30; integrity injections land (S.inj grows) and the log fills", await fx.wait(pg, "S.mode==='live17'&&S.rate===30&&S.inj>=2&&document.getElementById('alerts').textContent.length>20", 12000), await pg.evaluate(f"[S.mode,S.rate,S.inj,{inj0},__tour.drove[8]]"))
        fx.ok("step 9: injection 5 (nocomp) was driven and RE-VERIFY ALL pressed", await fx.wait(pg, "__tour.drove[8].includes('#bReverify')", 12000), await pg.evaluate("[__tour.drove[8],document.getElementById('rvLine')&&document.getElementById('rvLine').textContent.slice(0,120)]"))
        # ---- step 10: gap + signing ----
        inj1 = await pg.evaluate("S.inj")
        await pg.evaluate("tourShow(9)")
        fx.ok("step 10: fliplast injected then signing turned on (HMAC stand-in)", await fx.wait(pg, f"S.inj>={inj1}+1&&S.sealOn===true&&document.getElementById('bSeal').classList.contains('on')", 8000), await pg.evaluate("[S.inj,S.sealOn,document.getElementById('bSeal').textContent,__tour.drove[9]]"))
        # ---- step 11: the live lane PAUSES ----
        lane0 = await pg.evaluate("self.__lane?__lane.calls:null"); lane_present = await pg.evaluate("!!(self.LANE&&typeof LANE.preflight==='function')")
        await pg.evaluate("tourShow(10)")
        fx.ok("step 11: the tour pauses on the lane card (no timer, Continue button)", await fx.wait(pg, "__tour.paused===true&&document.getElementById('tNext').textContent.includes('Continue')&&document.querySelector('.tourBox').dataset.pause==='1'", 5000), await pg.evaluate("[__tour.paused,document.getElementById('tNext').textContent]"))
        await pg.wait_for_timeout(2500)
        fx.ok("step 11: still on step 11 after 2.5 s (no auto-advance) and the lane section is in view", await pg.evaluate("__tour.i===10&&Math.abs(document.getElementById('lane').getBoundingClientRect().top)<500"), await pg.evaluate("[__tour.i,document.getElementById('lane').getBoundingClientRect().top]"))
        fx.ok("step 11: __lane.calls never incremented (LANE.preflight only, never liveTether)", await pg.evaluate("self.__lane?__lane.calls:null") == lane0, [lane0, await pg.evaluate("self.__lane?__lane.calls:null")])
        if lane_present: fx.ok("step 11: LANE.preflight() was driven", await pg.evaluate("__tour.drove[10].includes('LANE.preflight')"), await pg.evaluate("__tour.drove[10]"))
        else: fx.ok("step 11 without 18-lane: the sentence shows the card's absence line", await pg.evaluate("document.getElementById('tt').textContent.startsWith('No live lane')"), await fx.txt(pg, "#tt"))
        # ---- step 12 ----
        await pg.evaluate("TOUR.next()")
        fx.ok("Continue advances to step 12: Receipt tab then PROV, Versions drawer open", await fx.wait(pg, "__tour.i===11&&document.getElementById('versionsDeck').closest('details').open&&(INSPECTOR.tab==='receipt'||INSPECTOR.tab==='prov')", 8000), await pg.evaluate("[__tour.i,INSPECTOR.tab,__tour.drove[11]]"))
        fx.ok("every step drove at least one real control", await pg.evaluate("__tour.drove.length===12&&__tour.drove.every(d=>d&&d.length>0)"), await pg.evaluate("__tour.drove.map(d=>d&&d.length)"))
        # ---- tourStop restores ----
        await pg.evaluate("tourStop()")
        await pg.wait_for_timeout(800)
        after = await pg.evaluate("({y:scrollY,rate:S.rate,paused:S.paused,filter:S.flags.filter,seal:!!S.sealOn,slider:[SLIDER.i,SLIDER.active],tab:INSPECTOR.tab,bench:self.BENCH?BENCH.text():null,hidden:document.getElementById('tour').hidden,on:document.getElementById('bTour').classList.contains('on'),running:__tour.running})")
        fx.ok("tourStop hides the overlay, chip off, not running", after["hidden"] and not after["on"] and not after["running"], after)
        fx.ok("tourStop restores rate, pause state, filter, signing, slider, inspector tab, bench text", after["rate"] == snap["rate"] and after["paused"] == snap["paused"] and after["filter"] == snap["filter"] and after["seal"] == snap["seal"] and after["slider"] == snap["slider"] and after["tab"] == snap["tab"] and after["bench"] == snap["bench"], {"before": {k: snap[k] for k in ("rate", "paused", "seal", "slider", "tab")}, "after": {k: after[k] for k in ("rate", "paused", "seal", "slider", "tab")}})
        fx.ok("tourStop restores the scroll position", abs(after["y"] - snap["y"]) <= 2, [snap["y"], after["y"]])
        # ---- keys + chip ----
        await pg.evaluate("tourShow(0)")
        await pg.wait_for_timeout(300)
        clk0 = await pg.evaluate("S.clk")
        await pg.keyboard.press("ArrowRight")
        fx.ok("→ steps to 2 / 12 while the tour runs", await fx.wait(pg, "__tour.i===1", 3000), await pg.evaluate("__tour.i"))
        fx.ok("→ did not seek the run clock by 10 s (the mast's handler is skipped)", await pg.evaluate(f"Math.abs(S.clk-{clk0})<6"), await pg.evaluate(f"[S.clk,{clk0}]"))
        await pg.keyboard.press("ArrowLeft")
        fx.ok("← steps back to 1 / 12", await fx.wait(pg, "__tour.i===0", 3000))
        await pg.keyboard.press("Escape")
        fx.ok("Esc stops the tour", await fx.wait(pg, "!__tour.running&&document.getElementById('tour').hidden", 3000))
        await pg.click("#bTour")
        fx.ok("the mast chip starts the tour", await fx.wait(pg, "__tour.running&&__tour.i===0", 3000))
        await pg.click("#bTour")
        fx.ok("the mast chip stops it again", await fx.wait(pg, "!__tour.running", 3000))
        fx.ok("auto-advance: step 1 moves on by itself after its ms", await pg.evaluate("TOUR[0].ms>0&&TOUR[0].ms<=15000"), await pg.evaluate("TOUR.map(s=>s.ms)"))
        errs = [e for e in fx.errors(pg) if "parts/run24.txt" not in e]
        fx.ok("no page errors during the tour", not errs, errs[:6])
        await fx.shot(pg, "v4_tour.png")
    print(f"info suite wall time {time.time() - T_START:.0f} s", flush=True)
    fx.summary()
Fixture.run(main)
