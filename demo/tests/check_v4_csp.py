"""check_v4_csp.py — the page boots and stays honest under every CSP profile the real viewer might turn out to have (ARCHITECTURE §6/§8).
Run: python3 demo/tests/check_v4_csp.py                 # noeval, nowasm, noworker in turn (one page at a time)
     python3 demo/tests/check_v4_csp.py --csp noworker  # one profile
Asserts per profile: Step 0 reports exactly what the profile allows; parts load with hash ok; the clock runs; the stage is up; HASH falls back to the main
thread under noworker (and still verifies); no page errors; the Step 0 table in #under names the blocked capability."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture
argv = sys.argv[1:]
profiles = [argv[argv.index("--csp") + 1]] if "--csp" in argv else ["noeval", "nowasm", "noworker"]
rep = Fixture(csp=profiles[0], argv=[])
async def main():
    async with rep.browser() as b:
        for prof in profiles:
            fx = Fixture(csp=prof, argv=[]); fx.res = rep.res
            pg = await fx.page(b); await fx.goto(pg)
            want = {"eval": prof not in ("noeval", "nowasm"), "wasm": prof != "nowasm", "worker": prof != "noworker"}   # nowasm has neither eval token (see v4fixture)
            fx.ok(f"[{prof}] boot reaches BOOT.phase ready", await fx.wait(pg, 'BOOT.phase==="ready"', 180000), await pg.evaluate("[BOOT.phase,BOOT.ms,LOOP.frames]"))
            fx.ok(f"[{prof}] loop advancing (rAF held by SwiftShader shader compiles for up to minutes on a loaded box)", await fx.wait(pg, "LOOP.frames>10", 120000), await pg.evaluate("LOOP.frames"))
            fx.ok(f"[{prof}] data parts load with hash ok", await fx.wait(pg, 'Object.entries(DATA.status).filter(([k])=>!k.startsWith("xsd")).every(([,s])=>s.state==="loaded")', 180000), await pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state+(v.state==='loading'?' '+(v.phase||'')+' '+v.got+'/'+v.bytes:'')])))"))
            fx.ok(f"[{prof}] Step 0 done", await fx.wait(pg, "ENV.done===true", 20000), await pg.evaluate("ENV.short()"))
            # workers may answer late under SwiftShader: give the late-promotion path its 12 s
            if want["worker"]: await fx.wait(pg, "ENV.worker===true", 14000)
            env = await pg.evaluate("({eval:ENV.eval,wasm:ENV.wasmInstantiate,worker:ENV.worker,blob:ENV.workerBlob,notes:ENV.notes})")
            fx.ok(f"[{prof}] Step 0: eval {want['eval']}, wasm {want['wasm']}, worker {want['worker']}", env["eval"] is want["eval"] and env["wasm"] is want["wasm"] and env["worker"] is want["worker"], env)
            rows = await pg.evaluate("[...document.querySelectorAll('#env tr[data-k]')].map(tr=>tr.dataset.k+': '+tr.children[1].textContent)")
            blocked = {"noeval": "eval: blocked", "nowasm": "wasm: ", "noworker": "worker (own file): blocked"}[prof] if prof in ("noeval", "nowasm", "noworker") else "eval: allowed"
            fx.ok(f"[{prof}] #env names the blocked capability", any(r.startswith(blocked) for r in rows) and (prof != "nowasm" or any(r.startswith("wasm: ") and "blocked" in r for r in rows)), rows[:4])
            fx.ok(f"[{prof}] clock runs at x30", await fx.wait(pg, "S&&S.clk>5&&S.scenes.length>=1", 30000), await pg.evaluate("S&&[S.clk,S.scenes.length]"))
            hm = await pg.evaluate("(async()=>{const xs=LIVE.slice(0,10).map(i=>i.B[0]);const h=await HASH.hashMany(xs);return [HASH.mode,h.filter((v,i)=>v===contentHash(xs[i])).length]})()")
            fx.ok(f"[{prof}] HASH.mode {'main' if prof == 'noworker' else 'worker'} and hashes agree", hm[0] == ("main" if prof == "noworker" else "worker") and hm[1] == 10, hm)
            bt = await pg.evaluate("(async()=>{const xs=S.scenes.slice(0,5);const r=await HASH.batch(xs.map(s=>s.id),xs.map(s=>s.xml));return r.filter(x=>x.ok).length===xs.length&&xs.length>0})()")
            fx.ok(f"[{prof}] HASH.batch verifies chains", bt)
            fx.ok(f"[{prof}] stage up (X_ITE from own files, wasm-free)", await fx.wait(pg, "__stage.show.ready", 40000), await pg.evaluate("JSON.stringify(__stage.show)"))
            if prof == "noeval":
                fx.ok("[noeval] text probe reports fonts do not draw (or is still pending)", await pg.evaluate("ENV.textDraws!==true"), await pg.evaluate("ENV.textDraws"))
            errs = fx.errors(pg)
            fx.ok(f"[{prof}] no page errors", not errs, errs[:4])
            await pg.context.close(); fx.stop()
    rep.summary()
Fixture.run(main)
