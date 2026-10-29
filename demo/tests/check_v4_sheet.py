"""check_v4_sheet.py — wave 2 "sheet" group: S13 contact sheet (40-sheet.js), S14 export suite + physics ledger + ladder strip (42-suite.js),
S16 Ask the files + ASK box (48-ask.js), css/80-sheet.css. Three pages on one browser: a desktop page without window.claude (every panel, the
ASK box off), a short page with a sample stub (ASK box on, the stub records the prompt), a short page with sample null (one line, nothing else).
The lead's build does not copy demo/v4/data/staged.json yet: this test copies it into <build>/data/ when missing and opens the page with ?staged=1
(the page fetches it only under BUILD.staged or that query, so the fixture never sees a 404 in the lead's build).
Run: python3 demo/v4/build_v4.py demo/build/v4-sheet --modules=40-sheet,42-suite,48-ask,80-sheet --no-xite && V4_BUILD=demo/build/v4-sheet python3 demo/tests/check_v4_sheet.py"""
import os, re, sys, json, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
STAGED_SRC = os.path.join(REPO, "demo", "v4", "data", "staged.json")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PARTS_LOADED = 'Object.entries(DATA.status).filter(([k])=>!k.startsWith("xsd")).every(([,s])=>s.state==="loaded")'
SAMPLE_STUB = ("async (input, opts) => { window.__askInput = input; window.__askOpts = opts || null; "
               "if (opts && typeof opts.onText === 'function') opts.onText({text: 'stub answer', delta: 'stub answer'}); "
               "return {text: 'stub answer', truncated: false, modelTierApplied: 'default'}; }")
async def main():
    t0 = time.time()
    dst = os.path.join(fx.build_dir, "data", "staged.json")
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(STAGED_SRC, dst); print("note: copied demo/v4/data/staged.json into the build's data/ (the lead's build does not bake it yet)")
    staged = json.load(open(STAGED_SRC, encoding="utf-8"))
    bundle = open(os.path.join(fx.build_dir, "index.html"), encoding="utf-8").read()
    for m in ("40-sheet.js", "42-suite.js", "48-ask.js", "80-sheet.css"):
        fx.ok(f"bundle carries {m}", m.split(".")[0] in bundle, m)
    js = bundle[bundle.rfind("<script>"):]
    stripped = re.sub(r"(^|[\s;{}(,=])//[^\n]*", r"\1", re.sub(r"/\*.*?\*/", lambda m: "" if "@env-probe" not in m.group(0) else "/*@env-probe*/", js, flags=re.S))   # the build's own grep: comments out, env-probe lines allowed
    probe_free = "\n".join(l for l in stripped.split("\n") if "/*@env-probe*/" not in l)
    fx.ok("no eval / new Function (outside the env-probe lines) and no setInterval in the bundle", not re.search(r"new\s+Function\b|(?<![A-Za-z0-9_.$])eval\(", probe_free) and js.count("setInterval(") == 0)
    fx.ok("no $digit replacement strings in my modules", not any(re.search(r"\$[0-9]", open(os.path.join(REPO, "demo", "v4", "js", f), encoding="utf-8").read()) for f in ("40-sheet.js", "42-suite.js", "48-ask.js")))
    async with fx.browser() as b:
        # ================= page 1: desktop, no window.claude =================
        pg = await fx.page(b, query="?staged=1")
        await fx.goto(pg)
        fx.ok("boot reaches ready", await fx.wait(pg, 'BOOT.phase==="ready"', 180000), await pg.evaluate("[BOOT.phase,BOOT.ms]"))
        fx.ok("LOOP running", await fx.wait(pg, "LOOP.frames>10", 120000))
        fx.ok("parts loaded (non-xsd)", await fx.wait(pg, PARTS_LOADED, 150000), await pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state])))"))
        # ---- S13 contact sheet ----
        fx.ok("#sheet mounted with no unknown stamp", await pg.evaluate('document.querySelector("#sheet .sb .sheetGrid")!==null&&document.querySelectorAll("#sheet .sh .stamp-unknown").length===0'))
        fx.ok("532 tiles: 358 live attempt bodies + 174 replay bodies", await fx.wait(pg, 'document.querySelectorAll("#sheetLive .th").length===358&&document.querySelectorAll("#sheetReplay .th").length===174', 30000),
              await pg.evaluate('[document.querySelectorAll("#sheetLive .th").length,document.querySelectorAll("#sheetReplay .th").length]'))
        fx.ok("two pass pills on every tile (16.5.0 and 16.5.1)", await pg.evaluate('document.querySelectorAll("#sheet .sheetGrid .th .pass.p0").length===532&&document.querySelectorAll("#sheet .sheetGrid .th .pass.p1").length===532'))
        fx.ok("pass pills classed agree | differ | na, most agree", await pg.evaluate('(()=>{const a=document.querySelectorAll("#sheet .pass.p1.agree").length,d=document.querySelectorAll("#sheet .pass.p1.differ").length,n=document.querySelectorAll("#sheet .pass.p1.na").length;return a+d+n===532&&a>400})()'),
              await pg.evaluate('[document.querySelectorAll("#sheet .pass.p1.agree").length,document.querySelectorAll("#sheet .pass.p1.differ").length,document.querySelectorAll("#sheet .pass.p1.na").length]'))
        fx.ok("tiles carry data-key = ledgerKey(item) for live bodies", await pg.evaluate('(()=>{const it=LIVE[0];const k=SHEET.ledgerKey(it);return !!document.querySelector(`#sheetLive .th[data-key="${k}"]`)})()'))
        fx.ok("VALID, NOT VISIBLE strip: 24 tiles (7 live finals + 17 replay) matching c.seven + c.replay17", await fx.wait(pg, 'document.querySelectorAll("#vnv .th").length===24', 30000),
              await pg.evaluate('[document.querySelectorAll("#vnv .th").length,CLAIMS.get("c.seven").value,CLAIMS.get("c.replay17").value]'))
        fx.ok("VNV strip carries both claim chips and a why line per tile", await pg.evaluate('document.querySelectorAll("#vnv .claim[data-claim=\'c.seven\'], #vnv .claim[data-claim=\'c.replay17\']").length===2&&document.querySelectorAll("#vnv .th .why").length===24'))
        fx.ok("sheet claims all computed, none bad", await fx.wait(pg, 'CLAIMS.list().filter(c=>c.id.startsWith("sheet.")).every(c=>c.value!==undefined&&c.status!=="bad")', 20000),
              await pg.evaluate('JSON.stringify(CLAIMS.list().filter(c=>c.id.startsWith("sheet.")).map(c=>[c.id,c.status,c.value]))'))
        fx.ok("sheet.live earned against MANIFEST rows (358) and sheet.replay 174", await pg.evaluate('CLAIMS.get("sheet.live").value===358&&CLAIMS.get("sheet.live").status==="earned"&&CLAIMS.get("sheet.replay").value===174'))
        fx.ok("thumbnails: 286 live jpgs set on visible or all tiles after live.jpg", await pg.evaluate('CLAIMS.get("sheet.jpg").value===286'), await pg.evaluate('CLAIMS.get("sheet.jpg").value'))
        # staged manifest
        fx.ok("staged manifest loaded from data/staged.json (?staged=1)", await fx.wait(pg, 'SHEET.stagedSource==="file"&&STAGEDM', 20000), await pg.evaluate("SHEET.stagedSource"))
        want = await pg.evaluate('[...new Set([...Object.keys(STAGEDM.turntables||{}),...Object.keys(STAGEDM.stills||{})])].filter(k=>SHEET.tiles.has(k)).length')
        fx.ok("one STAGED slot per matched manifest key (keys are ledgerKey(item))", await fx.wait(pg, f'document.querySelectorAll("#sheet .sheetGrid .th .stg").length==={want}', 10000) and want >= 20,
              (want, await pg.evaluate('document.querySelectorAll("#sheet .sheetGrid .th .stg").length')))
        fx.ok("ledger key in the manifest is not a sheet tile (S14 owns it)", await pg.evaluate('!SHEET.tiles.has("suite-physics-2026-10-17/physics-stress.ledger.x3d")'))
        st = await pg.evaluate('(async()=>{const r=await fetch("data/staged.json");if(!r.ok)return null;const j=await r.json();let urls=0,blank=0;for(const e of Object.values(j.stills||{}))for(const c of ["vp","staged"]){const x=e[c];if(!x)continue;if(x.url)urls++;if(x.blank)blank++}return {urls,blank,tt:Object.values(j.turntables||{}).filter(t=>t.url).length}})()')
        if st and st["urls"]:
            await pg.wait_for_function('document.querySelectorAll("#sheet .sheetGrid .stg.has").length>0', timeout=30000)
            lit = await pg.evaluate('(()=>{const s=[...document.querySelectorAll("#sheet .sheetGrid .stg")];return {n:s.length,has:s.filter(e=>e.classList.contains("has")).length,imgs:s.filter(e=>e.querySelector("img[src*=\'/_blob/\']")).length,staged:s.filter(e=>e.textContent.includes("STAGED")).length}})()')
            fx.ok("urls filled (assets uploaded): slots with a non-blank still read STAGED and light up, blank ones keep their label", lit["n"] > 0 and lit["has"] > 0 and lit["has"] <= st["urls"] and lit["staged"] >= lit["has"], {**lit, **st})
        else:
            fx.ok("urls null in this build: slots read STAGED · no url, none lit", await pg.evaluate('(()=>{const s=[...document.querySelectorAll("#sheet .sheetGrid .stg")];return s.length>0&&s.every(e=>!e.classList.contains("has"))&&s.some(e=>e.textContent.includes("STAGED"))})()'))
        n_blank = sum(1 for o in staged["stills"].values() for v in o.values() if v.get("blank") is True)
        fx.ok(f"blank stills read from the manifest flag, not a list: {n_blank}", await pg.evaluate('CLAIMS.get("sheet.blankStaged").value') == n_blank and await pg.evaluate('SHEET.blankRule') == "manifest", await pg.evaluate('[CLAIMS.get("sheet.blankStaged").value,SHEET.blankRule]'))
        blanks = await pg.evaluate('(()=>{const out=[];Object.entries(STAGEDM.stills).forEach(([k,o])=>Object.entries(o).forEach(([cam,v])=>{if(v.blank===true&&SHEET.tiles.has(k)){const lb=SHEET.lightbox(k);const pane=lb.querySelector(`.lbPane.staged[data-cam="${cam}"]`);out.push(!!pane&&pane.classList.contains("noblender")&&pane.textContent.includes("did not render in Blender")&&!pane.querySelector("img")&&!!lb.querySelector(".lbPane.measured"));SHEET.closeLightbox()}}));return out})()')
        fx.ok("every blank still on a tile reads did not render in Blender beside the measured frame, never as a render", len(blanks) == n_blank - 2 and all(blanks), blanks)
        fx.ok("lightbox for geo-04: the vp still reads did not render in Blender, the other cam reads STAGED", await pg.evaluate('(()=>{const lb=SHEET.lightbox("gpt-oss-20b/grounded/geo-04.x3d");const t=lb.textContent;const ok=!lb.hidden&&t.includes("did not render in Blender")&&lb.querySelectorAll(".lbPane.staged.noblender").length===1&&lb.querySelectorAll(".lbPane.staged").length===2&&lb.querySelector(".lbPane.staged:not(.noblender)").textContent.includes("STAGED")&&lb.querySelector(".lbPane.measured")!==null;SHEET.closeLightbox();return ok})()'))
        fx.ok("no Cycles wipe when BUILD.HAS_CYCLES is false", await pg.evaluate('BUILD.HAS_CYCLES?true:document.querySelectorAll("#sheet .cycles, #lightbox .cycles").length===0'))
        # lightbox: measured frame with hash
        k0 = await pg.evaluate('(()=>{const it=LIVE.find(i=>i.A[i.A.length-1].ok&&i.A[i.A.length-1].r&&i.A[i.A.length-1].r.jpg);return SHEET.ledgerKey(it)})()')
        lbx = await pg.evaluate('k=>{const lb=SHEET.lightbox(k);const t=SHEET.tiles.get(k);const h=contentHash(t.body());const r={shown:!lb.hidden,measured:!!lb.querySelector(".lbPane.measured img"),cap:lb.querySelector(".lbPane.measured figcaption").textContent,foot:lb.querySelector(".lbFoot").textContent,hash:h};SHEET.closeLightbox();r.closed=lb.hidden;return r}', k0)
        fx.ok("lightbox opens the measured frame with both passes and the content hash, closes", lbx["shown"] and lbx["measured"] and "MEASURED" in lbx["cap"] and "16.5.1" in lbx["cap"] and lbx["hash"] in lbx["foot"] and lbx["closed"], {k: str(v)[:80] for k, v in lbx.items()})
        # hover → STAGE.show
        fx.ok("show stage ready", await fx.wait(pg, "__stage.show.ready", 60000), await pg.evaluate("JSON.stringify(__stage.show)"))
        hv = await pg.evaluate('async k=>{const t=SHEET.tiles.get(k);const r=await SHEET.hoverLoad(k);return {ok:r&&r.ok,err:r&&r.err,hash:__stage.show.lastHash===contentHash(t.body()),msg:document.getElementById("stageMsg")?.textContent||""}}', k0)
        fx.ok("hover loads the body on the show stage through STAGE.show.load and labels the stage line", hv.get("hash") and (hv.get("ok") or hv.get("ok") is None) and "contact sheet" in hv.get("msg", "") and "MEASURED" in hv.get("msg", ""), {k: str(v)[:100] for k, v in hv.items()})
        # lit tiles follow the run clock
        fx.ok("clock running, scenes arriving", await fx.wait(pg, "S&&S.scenes.length>=3", 30000), await pg.evaluate("S&&[S.mode,S.clk,S.scenes.length]"))
        lit = await pg.evaluate('(()=>{SHEET.refresh();const byItem=new Set(S.scenes.map(s=>s.item));const expect=174+LIVE.filter(i=>byItem.has(i)).reduce((n,i)=>n+i.A.length,0);return [__panels.sheet.lit,expect,document.querySelectorAll("#sheetLive .th.ahead").length]})()')
        fx.ok("lit tiles = replay (recorded) + live attempts of scenes on the clock; the rest dim as ahead", lit[0] == lit[1] and lit[2] == 358 - (lit[0] - 174), lit)
        fx.ok("chain pill on a lit tile names its chain", await fx.wait(pg, '[...document.querySelectorAll("#sheetLive .th:not(.ahead) .cp")].some(e=>/^(✓|…) /.test(e.textContent))', 15000))
        flt = await pg.evaluate('(()=>{SHEET.filter("blank");const b=__panels.sheet.shown;const want=SHEET.list.filter(t=>t.kind!=="draws"&&t.kind!=="unknown").length;SHEET.filter("valid");const v=__panels.sheet.shown;SHEET.filter("all");return [b,want,v,__panels.sheet.shown]})()')
        fx.ok("filters: blank shows only the blank tiles, valid fewer than all, all restores 532", flt[0] == flt[1] and 0 < flt[0] < 532 and 0 < flt[2] < 532 and flt[3] == 532, flt)
        fx.ok("selecting a tile selects its scene", await pg.evaluate('(()=>{const sc=S.scenes[0];const k=SHEET.ledgerKey(sc.item);SHEET.select(k,true);return S.sel===sc.id})()'))
        # ---- S14 suite + ledger + ladder ----
        fx.ok("#suite mounted, no unknown stamp", await pg.evaluate('document.querySelector("#suite #ledger")!==null&&document.querySelectorAll("#suite .sh .stamp-unknown").length===0'))
        fx.ok("ledger loaded and verified with the page hash", await fx.wait(pg, '__ledger.status==="verified"', 60000), await pg.evaluate("JSON.stringify({s:__ledger.status,p:__ledger.problems,e:__ledger.err})"))
        fx.ok("29 steps in the ribbon, all lit", await fx.wait(pg, 'document.querySelectorAll("#ledger .step").length===29&&document.querySelectorAll("#ledger .step.lit").length===29', 15000), await pg.evaluate('[document.querySelectorAll("#ledger .step").length,document.querySelectorAll("#ledger .step.lit").length]'))
        hs = await pg.evaluate("[__ledger.pageHash,__ledger.repoHash,__ledger.bytes,document.getElementById('ledgerDetail').textContent]")
        fx.ok("page hash and repo C14N hash differ, both quoted in the verdict line", HEX64.match(hs[0] or "") and HEX64.match(hs[1] or "") and hs[0] != hs[1] and hs[0][:16] in hs[3] and hs[1][:16] in hs[3] and "byte equality not claimed" in hs[3], [hs[0][:12], hs[1][:12], hs[2]])
        fx.ok("ledger bytes as served = 219,412 (DOCTYPE stripped) and ledger.repoBytes quoted 219,515", hs[2] == 219412 and await pg.evaluate('CLAIMS.get("ledger.repoBytes").value===219515'), hs[2])
        fx.ok("ledger claims earned against result.json (steps 29, groups, records, findings 43)", await fx.wait(pg, '["ledger.steps","ledger.groups","ledger.records","ledger.findings"].every(id=>CLAIMS.get(id).status==="earned")', 20000),
              await pg.evaluate('JSON.stringify(["ledger.steps","ledger.groups","ledger.records","ledger.findings"].map(id=>[id,CLAIMS.get(id).status,CLAIMS.get(id).value,CLAIMS.get(id).expected]))'))
        tm = await pg.evaluate('(()=>{const r=LEDGER.tamper("metric");return {status:r.status,p:r.problems[0]||"",bad:document.querySelectorAll("#ledger .step.bad").length,lit:document.querySelectorAll("#ledger .step.lit").length,v:document.getElementById("ledgerVerdict").dataset.status}})()')
        fx.ok("TRY IT metric: chain broken, first problem at step 8, ribbon turns red from 8", tm["status"] == "broken" and "step 8" in tm["p"] and tm["v"] == "broken" and tm["bad"] == 22 and tm["lit"] == 7, tm)
        fx.ok("RESET restores verified", await pg.evaluate('LEDGER.reset().status==="verified"&&document.querySelectorAll("#ledger .step.bad").length===0'))
        tl = await pg.evaluate('(()=>{const r=LEDGER.tamper("last");const d=document.getElementById("ledgerDetail").textContent;LEDGER.reset();return {status:r.status,gap:d.includes("the gap"),audit:d.includes("evidence-mismatch")}})()')
        fx.ok("TRY IT last step: still verified (the gap), the detail names it and the recorded audit", tl["status"] == "verified" and tl["gap"] and tl["audit"], tl)
        fx.ok("ledger slot: both Cycles stills read did not render in Blender", await fx.wait(pg, '[...document.querySelectorAll("#ledgerStaged .stg")].length===2&&[...document.querySelectorAll("#ledgerStaged .stg")].every(e=>e.textContent.includes("did not render in Blender")&&e.classList.contains("noblender"))', 15000),
              await pg.evaluate('[...document.querySelectorAll("#ledgerStaged .stg")].map(e=>e.textContent)'))
        fx.ok("suite part landed: 15 chain pills, all verified recorded, newest 3 re-verified in-page", await fx.wait(pg, 'document.querySelectorAll("#suite .chainpill").length===15', 20000) and await pg.evaluate('[...document.querySelectorAll("#suite .chainpill")].every(e=>e.dataset.status==="verified")&&[...document.querySelectorAll("#suite .chainpill")].filter(e=>e.textContent.includes("in-page ✓")).length===3'),
              await pg.evaluate('[...document.querySelectorAll("#suite .chainpill")].map(e=>e.textContent).slice(-3)'))
        fx.ok("suite.inpage: 3 of 3 chains, every step hash reproduced with the canonical serialiser", await fx.wait(pg, 'CLAIMS.get("suite.inpage").value&&CLAIMS.get("suite.inpage").value.ok===3', 20000), await pg.evaluate('JSON.stringify(CLAIMS.get("suite.inpage").value)'))
        fx.ok("suite.corefail 4 → 1 → 0 → 4 → 0 and suite.chains 15 of 15", await pg.evaluate('JSON.stringify(CLAIMS.get("suite.corefail").value)==="[4,1,0,4,0]"&&CLAIMS.get("suite.chains").value.verified===15&&CLAIMS.get("suite.chains").value.n===15'), await pg.evaluate('JSON.stringify([CLAIMS.get("suite.corefail").value,CLAIMS.get("suite.chains").value])'))
        fx.ok("tier bar: 5 tiers of the merged run", await pg.evaluate('document.querySelectorAll("#tierBar .tier").length===5'))
        await pg.evaluate("__panels.suiteChart.forceDraw=true;__panels.metric.forceDraw=true")
        fx.ok("step chart drawn (5 runs) and metric explorer drawn (rigid_scale step_ms vs n_bodies)", await fx.wait(pg, "__panels.suiteChart.samples===5&&__panels.metric.samples>0", 10000), await pg.evaluate("[__panels.suiteChart.samples,__panels.metric.samples,document.getElementById('mxSuite').value,document.getElementById('mxMetric').value]"))
        fx.ok("metric explorer: suites and metrics selectable, x3d_fidelity rmse quoted", await pg.evaluate('document.getElementById("mxSuite").options.length>=10&&document.getElementById("mxMetric").options.length>=1&&document.querySelectorAll("#mxFidelity .chip").length===9'))
        fx.ok("tamper table quoted from result.json with two TRY IT buttons and the audit quote", await pg.evaluate('document.querySelectorAll("#tamperBody tr").length>=6&&document.querySelectorAll("#tamperBody .tryit").length===2&&document.getElementById("auditQuote").textContent.includes("evidence-mismatch")'))
        fx.ok("ladder strip: 9 rows from LADDER_ROWS, no external links in this build", await pg.evaluate('document.querySelectorAll("#xlad .row.xrow").length===9&&document.querySelectorAll("#xlad a[href^=http]").length===0&&document.querySelectorAll("#xlad .xrow .claim").length===9'))
        fx.ok("XLAD.light lights the flywheel row", await pg.evaluate('XLAD.light("flywheel","test")&&document.querySelector("#xlad .row[data-id=flywheel]").classList.contains("lit")'))
        # ---- S16 Ask the files, no window.claude ----
        fx.ok("Ask the files drawer mounted first in the deck", await fx.wait(pg, 'document.querySelector("#deck .sb > details:first-child")?.id==="askDrawer"', 20000))
        fx.ok("tier resolved public without window.claude → ASK off", await fx.wait(pg, 'TIER.tier&&ASK.mode==="off"', 60000), await pg.evaluate("[TIER.tier,ASK.mode]"))
        off = await pg.evaluate('(()=>{const b=document.getElementById("askBox");return {n:b.childElementCount,t:b.textContent,q:!!document.getElementById("askQ")}})()')
        fx.ok("ASK box off: one line 'not available in this view' and nothing else", off["n"] == 1 and "not available in this view" in off["t"] and not off["q"], off)
        fx.ok("per-model table from the parsed chains", await fx.wait(pg, 'document.querySelectorAll("#askBody tr").length>=1', 30000), await pg.evaluate('[...document.querySelectorAll("#askBody tr")].map(r=>r.children[0].textContent)'))
        fx.ok("reconciliation chips earned: on page 358 vs ledger 464, 106 = 62 + 25 + 19", await fx.wait(pg, '["ask.ledgerCalls","ask.onPage","ask.notOnPage","ask.failedCalls","ask.cutCalls","ask.retries","ask.probes","ask.pageTokens"].every(id=>CLAIMS.get(id).status==="earned")&&CLAIMS.get("ask.onPage").value===358&&CLAIMS.get("ask.ledgerCalls").value===464', 20000),
              await pg.evaluate('JSON.stringify(["ask.ledgerCalls","ask.onPage","ask.notOnPage","ask.failedCalls","ask.cutCalls","ask.retries","ask.probes"].map(id=>[id,CLAIMS.get(id).status,CLAIMS.get(id).value]))'))
        q = await pg.evaluate('(()=>{const r=ASK.query({op:"validate",verdict:"invalid",limit:5});return {total:r.total,n:r.rows.length,bytes:JSON.stringify(r).length,ops:[...new Set(r.rows.map(x=>x.op))]}})()')
        fx.ok("query_steps filter runs over the parsed rows (no code from the model), ≤ 32 KB", q["n"] <= 5 and q["total"] >= q["n"] and q["bytes"] <= 32768 and q["ops"] in ([], ["validate"]), q)
        ctx = await pg.evaluate('(()=>{const c=ASK.context();return {bytes:JSON.stringify(c).length,keys:Object.keys(c),claims:Object.keys(c.claims||{}).length}})()')
        fx.ok("context carries claims, livestats, reconcile, ask tables, selected scene; ≤ 32 KB", ctx["bytes"] <= 32768 and all(k in ctx["keys"] for k in ("claims", "livestats", "reconcile", "ask_the_files", "selected_scene")) and ctx["claims"] > 20, ctx)
        srch = await pg.evaluate('(()=>{const i=document.getElementById("askSearch");i.value="validate";i.dispatchEvent(new Event("input",{bubbles:true}));return [document.querySelectorAll("#askHits .hit").length,document.getElementById("askHitN").textContent]})()')
        fx.ok("search box lists step rows", srch[0] >= 1, srch)
        # ---- health ----
        fx.ok("one rAF loop: panels sheet, suiteChart, metric, ledgerRibbon, ask registered", await pg.evaluate('["sheet","suiteChart","metric","ledgerRibbon","ask"].every(n=>!!__panels[n])'))
        fx.ok("sheet panel p95 under 20 ms", await pg.evaluate("LOOP.stats.panel.sheet.p95<20"), await pg.evaluate("JSON.stringify(LOOP.stats.panel.sheet)"))
        await fx.shot(pg, "v4_sheet.png", full=True)
        errs = fx.errors(pg)
        fx.ok("page 1: no page errors", not errs, errs[:5])
        fx.ok("no boot errors", await pg.evaluate("BOOT.log.length") == 0, await pg.evaluate("BOOT.log"))
        await pg.context.close()
        # ================= page 2: sample stub → ASK on =================
        pg2 = await fx.page(b, claude={"sample": SAMPLE_STUB, "user": {"isOwner": False}})
        await fx.goto(pg2)
        fx.ok("page 2: ASK on once the tier resolves (sample is a function)", await fx.wait(pg2, 'ASK.mode==="on"&&document.getElementById("askQ")', 90000), await pg2.evaluate("[TIER.tier,ASK.mode,window.__claudeCalls]"))
        await fx.wait(pg2, "S&&S.scenes.length>=1", 30000)
        res = await pg2.evaluate('async()=>{document.getElementById("askQ").value="how many calls failed?";document.getElementById("askGo").click();for(let i=0;i<40&&!(ASK.lastAnswer||ASK.lastError);i++)await new Promise(r=>setTimeout(r,250));const inp=window.__askInput||"";const ctx=inp.includes("CONTEXT")?inp.slice(inp.indexOf("{"),inp.lastIndexOf("}")+1):"";return {a:document.getElementById("askA").textContent,err:ASK.lastError,hasQ:inp.includes("QUESTION:\\nhow many calls failed?"),hasCtx:inp.includes("CONTEXT (JSON"),ctxBytes:JSON.stringify(ASK.lastContext||{}).length,calls:window.__claudeCalls.sample,tools:(window.__askOpts&&window.__askOpts.tools||[]).map(t=>t.name),cache:window.__askOpts&&window.__askOpts.cache,signal:!!(window.__askOpts&&window.__askOpts.signal),status:document.getElementById("askStatus").textContent}}')
        fx.ok("ASK → sample called once with instructions + context + question; answer rendered via textContent", res["a"] == "stub answer" and res["hasQ"] and res["hasCtx"] and res["calls"] >= 1 and not res["err"], {k: str(v)[:80] for k, v in res.items()})
        fx.ok("context ≤ 32 KB, cache false, abort signal passed, query_steps tool offered", res["ctxBytes"] <= 32768 and res["cache"] is False and res["signal"] and "query_steps" in res["tools"], [res["ctxBytes"], res["cache"], res["tools"]])
        tool = await pg2.evaluate('(()=>{const t=window.__askOpts.tools.find(t=>t.name==="query_steps");const r=t.execute({filter:{op:"generate",limit:3}});return {n:r.rows.length,bytes:JSON.stringify(r).length,ops:[...new Set(r.rows.map(x=>x.op))]}})()')
        fx.ok("tool execute answers from stored rows under 32 KB", tool["n"] <= 3 and tool["bytes"] <= 32768 and tool["ops"] in ([], ["generate"]), tool)
        fx.ok("nothing left the page: no fetch to any model endpoint", await pg2.evaluate('!performance.getEntriesByType("resource").some(e=>/openai|anthropic|api\\./.test(e.name))'))
        e2 = fx.errors(pg2)
        fx.ok("page 2: no page errors", not e2, e2[:5])
        await pg2.context.close()
        # ================= page 3: sample null → one line =================
        pg3 = await fx.page(b, claude={"sample": None, "user": {"isOwner": False}})
        await fx.goto(pg3)
        fx.ok("page 3: tier resolved with sample null → ASK off", await fx.wait(pg3, 'TIER.tier&&ASK.mode==="off"&&document.getElementById("askBox")', 90000), await pg3.evaluate("[TIER.tier,ASK.mode,window.__claudeCalls]"))
        off3 = await pg3.evaluate('(()=>{const b=document.getElementById("askBox");return {n:b.childElementCount,t:b.textContent,q:!!document.getElementById("askQ"),calls:window.__claudeCalls.sample}})()')
        fx.ok("sample null: exactly one line containing 'not available in this view', no textarea, claude.use('sample') was asked", off3["n"] == 1 and "not available in this view" in off3["t"] and not off3["q"] and off3["calls"] >= 1, off3)
        e3 = fx.errors(pg3)
        fx.ok("page 3: no page errors", not e3, e3[:5])
        await pg3.context.close()
    print(f"elapsed {time.time()-t0:.0f} s")
    fx.summary()
Fixture.run(main)
