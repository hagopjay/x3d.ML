"""check_v4_raster.py — S7 first-light raster (26-raster) and S8 prompt × model matrix + error taxonomy flow (28-matrix-flow) acceptance.
Run: python3 demo/v4/build_v4.py demo/build/v4 && python3 demo/tests/check_v4_raster.py [--csp viewer|noeval|nowasm|noworker]   (V4_BUILD overrides the build dir)
Asserts (ARCHITECTURE §6 fixture; waits sized for a shared 4-core box under SwiftShader; one page, one X_ITE boot, the phone check resizes the same page):
  raster: 375 rows by default (174 replay + 201 live finals), 557 with every attempt, every default row paired (both passes), claim raster.flips computes
          {pairs: 557, flips: 0} === expected, raster.rows / raster.firstLight earned, sort and Show-all toggles, hover and click select a row, the live row:
          RASTER.measure(hero key) pins the hero to the top and resolves REPRODUCED | same answer, slower device | DIFFERS (SwiftShader: slower acceptable).
  matrix: 250 cells (50 × 5) in live17 with 201 filled after the full run, 17 cut cells, failed marks; MATRIX.compare('sp-09') loads a body on STAGE.show and
          draws ≥ 2 compare cards with a page hash; flow claims flow.profile_component / flow.xsd_gone / flow.xsd_stayed equal expected; FLOW.filter sets
          S.flags.filter and dims the matrix to the matching chains (63 for xsd → gone after repair 1); FLOW.clear resets; replay11 gives 50 × 6 cells.
  honesty: both headers carry three stamps and a grade, no .stamp-unknown, honesty labels name both patches; no page errors; no horizontal scroll at 390 px."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture
fx = Fixture()
HERO_KEY = "HERO.items[0].key"
async def main():
    bundle = open(os.path.join(fx.build_dir, "index.html"), encoding="utf-8").read()
    js = bundle[bundle.rfind("<script>"):]
    fx.ok("bundle carries 26-raster.js and 28-matrix-flow.js", "js/26-raster.js" in js and "js/28-matrix-flow.js" in js)
    fx.ok("bundle carries css/55-matrix.css", "css/55-matrix.css" in bundle)
    fx.ok("setInterval( count in the bundle is 0", js.count("setInterval(") == 0, js.count("setInterval("))
    fx.ok("no $digit replacement strings in the two modules (share sweep rule)", not re.search(r"\$[0-9]", open(os.path.join(fx.build_dir, "..", "..", "v4", "js", "26-raster.js")).read() + open(os.path.join(fx.build_dir, "..", "..", "v4", "js", "28-matrix-flow.js")).read()) if os.path.exists(os.path.join(fx.build_dir, "..", "..", "v4", "js", "26-raster.js")) else True)
    async with fx.browser() as b:
        pg = await fx.page(b)
        await fx.goto(pg)
        fx.ok("boot reaches BOOT.phase ready", await fx.wait(pg, 'BOOT.phase==="ready"', 170000), await pg.evaluate("[BOOT.phase,BOOT.ms,LOOP.frames]"))
        fx.ok("parts renders.series, renders.151, live.core, replay, live.bodies loaded", await fx.wait(pg, '["renders.series","renders.151","live.core","replay","live.bodies"].every(n=>DATA.loaded(n))', 90000), await pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state])))"))
        # ---- headers and honesty ----
        for sid in ("raster", "matrix"):
            st = await pg.evaluate(f"[...document.querySelectorAll('#{sid} .sh .stamps .stamp')].map(e=>e.dataset.k+'='+e.textContent)")
            fx.ok(f"#{sid} header has the three stamps and a grade", len(st) == 3 and await pg.evaluate(f"!!document.querySelector('#{sid} .sh .grade')"), st)
            fx.ok(f"#{sid} no .stamp-unknown", await pg.evaluate(f"document.querySelectorAll('#{sid} .stamp-unknown').length") == 0)
            hl = await fx.txt(pg, f"#{sid} > .hl")
            fx.ok(f"#{sid} honesty label names 16.5.1 / both passes or the recorded codes", ("16.5.1" in hl) or ("fork@eb4b4b4" in hl), hl[:120])
        fx.ok("raster renderer stamp is the two-pass vocabulary entry", await pg.evaluate("document.querySelector('#raster .stamp[data-k=renderer]').textContent") == "X_ITE 16.5.0 offline + 16.5.1 offline")
        # ---- raster rows ----
        fx.ok("raster: 375 rows by default", await fx.wait(pg, "__panels.raster.rows===375", 20000), await pg.evaluate("[__panels.raster.rows,__panels.raster.rowsAll,__panels.raster.builds]"))
        fx.ok("raster: 557 bodies carry both passes (rowsAll)", await pg.evaluate("__panels.raster.rowsAll") == 557, await pg.evaluate("__panels.raster.rowsAll"))
        fx.ok("raster: every default row is paired (16.5.0 above, 16.5.1 below)", await pg.evaluate("__panels.raster.paired") == 375, await pg.evaluate("__panels.raster.paired"))
        fx.ok("raster: 0 class flips between the patches on the 557 bodies", await pg.evaluate("__panels.raster.flips") == 0, await pg.evaluate("__panels.raster.flips"))
        fl = await pg.evaluate("(async()=>{const r=await CLAIMS.run('raster.flips');return [r.ok,JSON.stringify(r.value),JSON.stringify(r.expected)]})()")
        fx.ok("claim raster.flips compute()===expected ({pairs:557, flips:0})", fl[0] is True and fl[1] == '{"pairs":557,"flips":0}', fl)
        rr = await pg.evaluate("(async()=>{const r=await CLAIMS.run('raster.rows');return [r.ok,r.value,r.expected]})()")
        fx.ok("claim raster.rows compute()===expected (375)", rr[0] is True and rr[1] == 375, rr)
        fl2 = await pg.evaluate("(async()=>{const r=await CLAIMS.run('raster.firstLight');return [CLAIMS.status('raster.firstLight'),r.value]})()")
        fx.ok("claim raster.firstLight earned with a median first light under 1 s (16.5.0 offline)", fl2[0] == "earned" and fl2[1] is not None and 0 < fl2[1] < 1000, fl2)
        fx.ok("raster canvas drew dots (visible window)", await pg.evaluate("(()=>{document.getElementById('raster').scrollIntoView();__panels.raster.forceDraw=true;return true})()") and await fx.wait(pg, "__panels.raster.samples>200", 10000), await pg.evaluate("[__panels.raster.samples,__panels.raster.visible,__panels.raster.lastDraw]"))
        fx.ok("raster: sort by model reorders, sort by first light puts a lit row first", await pg.evaluate("(()=>{RASTER.setSort('model');const a=RASTER.rows()[0].key;RASTER.setSort('first');const b=RASTER.rows()[0];return a!==b.key&&b.fl0!=null&&__panels.raster.sort==='first'})()"))
        fx.ok("raster: Show all attempts → 557 rows, back → 375", await pg.evaluate("(()=>{RASTER.setAll(true);const a=__panels.raster.rows;RASTER.setAll(false);return a===557&&__panels.raster.rows===375})()"))
        fx.ok("raster: reconstructed sample times are monotonic and within [first, last]", await pg.evaluate("(()=>{const r=RASTER.rows().find(x=>x.a&&x.a.series.length===20);const t=RASTER.times(r.a);return t.every((v,i)=>i===0||v>=t[i-1])&&t[0]===r.a.first&&t[t.length-1]<=r.a.last})()"))
        sel = await pg.evaluate("(()=>{const r=RASTER.select(HERO.items[0].key);return r&&[r.key,__panels.raster.sel,document.querySelector('#raster .rs-card').hidden,document.querySelector('#raster .rs-card .rs-f[data-f=id]').textContent]})()")
        fx.ok("raster: selecting the hero row opens the card with its key", sel and sel[1] == sel[0] and sel[2] is False and sel[0] in sel[3], sel)
        fx.ok("raster: the card shows the measured JPEG thumbnail from live.jpg", await fx.wait(pg, "DATA.loaded('live.jpg')&&(RASTER.select(HERO.items[0].key),document.querySelector('#raster .rs-card .rs-th img'))", 60000), await pg.evaluate("document.querySelector('#raster .rs-card .rs-th').textContent.slice(0,80)"))
        box = await pg.evaluate("(()=>{const c=document.querySelector('#raster canvas.rs-cv');const b=c.getBoundingClientRect();return [b.left,b.top,b.width,b.height]})()")
        await pg.mouse.move(box[0] + box[2] * 0.5, box[1] + 30)
        fx.ok("raster: hover over the canvas names a row", await fx.wait(pg, "__panels.raster.hover!=null", 5000), await pg.evaluate("__panels.raster.hover"))
        # ---- live row ----
        fx.ok("boot's own hero measure landed (the raster adopts it as the first live row)", await fx.wait(pg, "BOOT.heroMeasure", 60000) and await fx.wait(pg, "__panels.raster.live&&__panels.raster.live.key===HERO.items[0].key", 10000), await pg.evaluate("__panels.raster.live&&[__panels.raster.live.key,__panels.raster.live.state,__panels.raster.live.note]"))
        live = await pg.evaluate("(async()=>{const R=await RASTER.measure(HERO.items[0].key);return R&&{nb:R.nb,frames:R.frames,err:R.err,noFrame:R.noFrame,kind:R.kind}})()")
        fx.ok("raster: RASTER.measure(hero) measured through STAGE.measure in this browser", live and not live.get("err") and (live.get("nb") or 0) >= 0.005, live)
        fx.ok("raster: live chip resolves", await fx.wait(pg, "__panels.raster.live&&__panels.raster.live.state==='done'", 20000), await pg.evaluate("__panels.raster.live&&__panels.raster.live.state"))
        chip = await pg.evaluate("[__panels.raster.live.chip,document.querySelector('#raster .rs-chip').textContent]")
        fx.ok("raster: chip is REPRODUCED or 'same answer, slower device' (SwiftShader) — the class agrees with the recorded 16.5.0 pass", chip[0] in ("REPRODUCED", "same answer, slower device") and chip[1] == chip[0], chip)
        fx.ok("raster: the live row is pinned at the top", await pg.evaluate("RASTER.rows()[0].key===HERO.items[0].key"), await pg.evaluate("RASTER.rows()[0].key"))
        note = await fx.txt(pg, "#raster .rs-livenote")
        fx.ok("raster: live note names the patch and the rig", "X_ITE 16.5.0 in this browser" in note and "viewAll(0)" in note and "not counted" in note, note[:160])
        fx.ok("raster: measure canvas never rigged", await pg.evaluate("__stage.measure.rigNodes") == 0)
        await pg.evaluate("document.getElementById('raster').scrollIntoView()"); await pg.wait_for_timeout(400); await fx.shot(pg, "v4_raster.png", full=False)
        # ---- matrix ----
        await pg.evaluate("SIM.seekTo(4610);document.getElementById('matrix').scrollIntoView();__panels.matrix.forceDraw=true;__panels.flow.forceDraw=true")
        fx.ok("matrix: 250 cells (50 × 5) in live17", await fx.wait(pg, "__panels.matrix.cells===250", 15000), await pg.evaluate("[__panels.matrix.cells,__panels.matrix.rows,__panels.matrix.cols]"))
        fx.ok("matrix: 201 cells filled after the full run, 17 cut chains hatched, failed marks drawn", await fx.wait(pg, "__panels.matrix.filled===201&&__panels.matrix.cut===17&&__panels.matrix.failed>=40", 10000), await pg.evaluate("[__panels.matrix.filled,__panels.matrix.cut,__panels.matrix.failed]"))
        fx.ok("matrix: cells fill in run order (seekTo(300) fills fewer)", await pg.evaluate("(()=>{SIM.seekTo(300);__panels.matrix.draw(performance.now());const n=__panels.matrix.filled;SIM.seekTo(4610);__panels.matrix.draw(performance.now());return n>0&&n<201&&__panels.matrix.filled===201})()"))
        cell = await pg.evaluate("(()=>{const c=MATRIX.cellAt(70,62);return c&&[c.p.id,c.lane&&c.lane.id]})()")   # (70, 62): first cell under the 58 px rotated-name header
        fx.ok("matrix: cellAt maps the first cell to obj-01 × the first lane", cell and cell[0] == "obj-01" and cell[1] == LM0(await pg.evaluate("LM.models[0].id")), cell)
        loads0 = await pg.evaluate("__stage.show.loads")
        cards = await pg.evaluate("(async()=>{const c=await MATRIX.compare('sp-09');return [c.length,document.querySelectorAll('#matrix .mx-cmp .mx-cc').length,document.querySelector('#matrix .mx-cmp .mx-cc .legend.m').textContent]})()")
        fx.ok("matrix: compare('sp-09') draws a card per lane with the page hash etched beneath", cards[0] >= 2 and cards[1] == cards[0] and "page hash" in cards[2] and "…" in cards[2], cards)
        fx.ok("matrix: compare loaded two bodies on the visible stage in turn", await pg.evaluate("__stage.show.loads") >= loads0 + 2, [loads0, await pg.evaluate("__stage.show.loads")])
        fx.ok("matrix: stage hash equals the second compared body's hash", await pg.evaluate("(()=>{const t=document.querySelectorAll('#matrix .mx-cmp .mx-cc .legend.m');const h=__stage.show.lastHash.slice(0,16);return [...t].some(e=>e.textContent.includes(h))})()"), await pg.evaluate("__stage.show.lastHash"))
        fx.ok("matrix: 'this browser' snapshots sit beside the measured frames", await fx.wait(pg, "document.querySelectorAll('#matrix .mx-live img').length>=1", 15000), await pg.evaluate("[...document.querySelectorAll('#matrix .mx-live .legend')].map(e=>e.textContent.slice(0,60))"))
        # ---- flow ----
        for cid, want in (("flow.profile_component", '{"n":54,"gone":54}'), ("flow.xsd_gone", '{"n":97,"gone":63}'), ("flow.xsd_stayed", '{"still":34,"gone2":13,"gaveUp":21}')):
            r = await pg.evaluate(f"(async()=>{{const r=await CLAIMS.run('{cid}');return [r.ok,JSON.stringify(r.value),JSON.stringify(r.expected)]}})()")
            fx.ok(f"claim {cid} compute()===expected (from STATS.sankey)", r[0] is True and r[1] == r[2], r)
        fx.ok("flow: computed from 201 chains, ribbons and 15 nodes", await fx.wait(pg, "__panels.flow.source==='computed'&&__panels.flow.ribbons>20&&__panels.flow.nodes===15&&__panels.flow.total===173", 10000), await pg.evaluate("[__panels.flow.source,__panels.flow.ribbons,__panels.flow.nodes,__panels.flow.total]"))
        f = await pg.evaluate("(()=>{const f=FLOW.filter('xsd','gone after repair 1');__panels.matrix.draw(performance.now());return [S.flags.filter&&S.flags.filter.code,S.flags.filter&&S.flags.filter.outcome,typeof S.flags.filter.test,__panels.matrix.filtered,document.querySelector('#matrix .fl-filter').hidden]})()")
        fx.ok("flow: FLOW.filter sets S.flags.filter {code, outcome, test} and the matrix keeps 63 chains lit", f[0] == "xsd" and f[1] == "gone after repair 1" and f[2] == "function" and f[3] == 63 and f[4] is False, f)
        fx.ok("flow: filter.test agrees with the taxonomy on every scene", await pg.evaluate("S.scenes.filter(s=>S.flags.filter.test(s)).length") == 63, await pg.evaluate("S.scenes.filter(s=>S.flags.filter.test(s)).length"))
        fx.ok("flow: FLOW.clear resets", await pg.evaluate("(()=>{FLOW.clear();__panels.matrix.draw(performance.now());return S.flags.filter===null&&__panels.matrix.filtered===0&&document.querySelector('#matrix .fl-filter').hidden})()"))
        fx.ok("matrix: field slot present for 56-field with a 2D fallback canvas", await pg.evaluate("MATRIX.fieldSlot()===document.getElementById('matrixField')&&!!document.querySelector('#matrixField canvas.fl-2d')&&MATRIX.fieldUniforms().u_thr===0.005"))
        fx.ok("matrix: category facet filters rows", await pg.evaluate("(()=>{MATRIX.facet('geospatial');__panels.matrix.draw(performance.now());const n=__panels.matrix.rows;MATRIX.facet('all');__panels.matrix.draw(performance.now());return n===5&&__panels.matrix.rows===50})()"))
        await pg.evaluate("document.getElementById('matrix').scrollIntoView()"); await pg.wait_for_timeout(400); await fx.shot(pg, "v4_matrix.png", full=False)
        fx.ok("matrix: replay11 → 50 × 6 cells (model · mode lanes)", await pg.evaluate("(()=>{MODES.set('replay11');SIM.seekTo(400);__panels.matrix.draw(performance.now());const c=__panels.matrix.cells,f=__panels.matrix.filled;MODES.set('live17');return c===300&&f===174})()"), await pg.evaluate("[__panels.matrix.cells,__panels.matrix.filled]"))
        # ---- phone width on the same page ----
        await pg.set_viewport_size({"width": 390, "height": 844})
        await pg.evaluate("dispatchEvent(new Event('resize'));__panels.raster.forceDraw=true;__panels.matrix.forceDraw=true;__panels.flow.forceDraw=true")
        await pg.wait_for_timeout(900)
        sw = await pg.evaluate("[document.documentElement.scrollWidth,document.documentElement.clientWidth,document.getElementById('raster').getBoundingClientRect().width,document.getElementById('matrix').getBoundingClientRect().width]")
        fx.ok("390 px: no horizontal page scroll with the raster and matrix sections", sw[0] <= sw[1] + 1 and sw[2] <= 390 and sw[3] <= 390, sw)
        fx.ok("390 px: raster is 200 px tall, matrix pages 10 rows (50 cells) with the pager shown", await pg.evaluate("document.querySelector('#raster .rs-wrap').getBoundingClientRect().height") <= 201 and await pg.evaluate("__panels.matrix.cells===50&&__panels.matrix.rows===10&&!document.querySelector('#matrix .mx-pager').hidden"), await pg.evaluate("[document.querySelector('#raster .rs-wrap').getBoundingClientRect().height,__panels.matrix.cells,__panels.matrix.rows]"))
        await fx.shot(pg, "v4_raster_phone.png", full=False)
        errs = fx.errors(pg)
        fx.ok("no page errors", not errs, errs[:5])
        fx.ok("no boot errors logged", await pg.evaluate("BOOT.log.length") == 0, await pg.evaluate("BOOT.log"))
    fx.summary()
def LM0(x): return x
Fixture.run(main)
