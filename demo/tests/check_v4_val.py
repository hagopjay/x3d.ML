"""check_v4_val.py — M4 js-port wiring (ARCHITECTURE §4 / 05, SPEC §6; WORKPLAN 05-val acceptance).
Run: python3 demo/v4/build_v4.py demo/build/v4 --files-map && python3 demo/tests/check_v4_val.py [--csp viewer]   (V4_BUILD=<dir> for a module build)
Viewer CSP page: VAL.mode === 'full' through the own-file worker after the self-test; the schema parts xsd40/xsd41 loaded with hash ok; anim-01 attempt 1
(gemini-3.8-flash, RECORDED 17 Oct) → the report names `roughness`; the hero final body is valid; a malformed body is 'XML parse error'; memo hit;
parity: VAL.canary() validates every body with a recorded fork@8dd0d3e verdict (383 live attempts + 174 replay bodies + the ledger) in this browser and
agrees on the valid flag, the XSD flag, the XSD error count and the semantic error codes (0 flips, else FAIL listing ids), at least 50 from REAL and LIVE each;
per-body time after warm-up under 50 ms (median and p90); reportHtml/repairText label js-port-of-8dd0d3e and never fork@ for a port result; the mast chip.
nowasm page: VAL.mode === 'none' with a reason naming WebAssembly, the Bench (when built in) opens read-only, no page errors.
FAIL-SOFT (exit 2 unless JSVAL_OPTIONAL=1) when demo/jsval/x3dval.js is absent: prints MISSING jsval."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
PER_BODY_MS = float(os.environ.get("VAL_PER_BODY_MS", "50"))
async def main():
    if not os.path.isfile(os.path.join(REPO, "demo", "jsval", "x3dval.js")):
        fx.fail_soft("MISSING jsval", "demo/jsval/x3dval.js absent: the js-port cannot be wired; everything below is skipped")
        fx.summary(); return
    for rel in ("jsval/x3dval.js", "jsval/worker.js", "jsval/vendor/libxml2-wasm.bundle.mjs", "workers/val.worker.js", "jsval/data/uom-4.1.json", "jsval/data/schemas/xmldsig-core-schema.xsd"):
        fx.ok(f"build has {rel}", os.path.isfile(os.path.join(fx.build_dir, rel)))
    small = [f for f in os.listdir(os.path.join(fx.build_dir, "jsval", "data", "schemas")) if f.endswith(".xsd")]
    fx.ok("the five small XSDs are under jsval/data/schemas (the two big ones are parts xsd40/xsd41)", len(small) == 5 and "x3d-4.0.xsd" not in small, sorted(small))
    wsrc = open(os.path.join(fx.build_dir, "workers", "val.worker.js"), encoding="utf-8").read()
    fx.ok("val.worker.js is a classic worker: importScripts + no eval / new Function / fork@", "importScripts(" in wsrc and "eval(" not in wsrc and "new Function" not in wsrc and "fork@" not in wsrc)
    async with fx.browser() as b:
        pg = await fx.page(b)
        await fx.goto(pg)
        fx.ok("data parts live.bodies, replay, drift loaded", await fx.wait(pg, 'DATA.loaded("live.bodies")&&DATA.loaded("replay")&&DATA.loaded("drift")', 180000), await pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state])))"))
        fx.ok("VAL surface: label js-port-of-8dd0d3e, mode unloaded|full before need, ready/validate/validateMany/canary/compare/need present", await pg.evaluate("VAL.label==='js-port-of-8dd0d3e'&&['unloaded','full','none'].includes(VAL.mode)&&['validate','validateMany','canary','compare','need','init','on'].every(k=>typeof VAL[k]==='function')"), await pg.evaluate("[VAL.mode,VAL.reason,VAL.status.phase]"))
        await pg.evaluate("VAL.need()")
        got = await fx.wait(pg, "VAL.mode==='full'||VAL.mode==='none'", 150000)
        st = await pg.evaluate("JSON.stringify({mode:VAL.mode,reason:VAL.reason,st:VAL.status})")
        fx.ok("VAL.mode becomes 'full' after the self-test (worker boot + schema parts + XSD 4.0 compile, about 3 s in a worker)", got and await pg.evaluate("VAL.mode") == "full", st[:600])
        if await pg.evaluate("VAL.mode") != "full":
            fx.ok("VAL.reason names why", bool(await pg.evaluate("VAL.reason")), await pg.evaluate("VAL.reason"))
            errs = fx.errors(pg); fx.ok("no page errors", not errs, errs[:5]); fx.summary(); return
        fx.ok("transport is the own-file worker under the viewer CSP", await pg.evaluate("VAL.transport") == "worker", await pg.evaluate("[VAL.transport,VAL.status.notes]"))
        fx.ok("self-test passed on the known bodies", await pg.evaluate("VAL.status.selfTest&&VAL.status.selfTest.ok===true"), await pg.evaluate("JSON.stringify(VAL.status.selfTest)"))
        fx.ok("XSD 4.0 compiled (compileMs recorded by the port)", await pg.evaluate("!!(VAL.status.compileMs&&VAL.status.compileMs['4.0']>0)"), await pg.evaluate("JSON.stringify(VAL.status.compileMs)"))
        fx.ok("schema parts xsd40/xsd41 loaded with the manifest hash", await pg.evaluate("DATA.status.xsd40.state==='loaded'&&DATA.status.xsd41.state==='loaded'&&DATA.status.xsd40.sha===MANIFEST.parts.xsd40.sha256"), await pg.evaluate("[DATA.status.xsd40.state,DATA.status.xsd41.state]"))
        fx.ok("#under lists the xsd parts as loaded now that VAL asked", await pg.evaluate("[...document.querySelectorAll('#under table.parts tr[data-part^=xsd]')].every(tr=>tr.dataset.state==='loaded')"))
        fx.ok("mast chip #portChip reads js-port-of-8dd0d3e · ready", await fx.wait(pg, "document.getElementById('portChip').textContent.includes('ready')&&document.getElementById('portChip').dataset.mode==='full'", 5000), await fx.txt(pg, "#portChip"))
        # ---- anim-01 attempt 1 ----
        r = await pg.evaluate("(async()=>{const it=LIVE.find(i=>i.p==='anim-01'&&i.m==='gemini-3.8-flash');const r=await VAL.validate(it.B[0]);return {valid:r.valid,xe:r.xsd.errors,codes:codesOfRes(r),ms:r.ms,label:r.label,rep:reportHtml(r),txt:repairText(r),recOk:!!it.A[0].ok,recXe:it.A[0].xe}})()")
        fx.ok("anim-01 attempt 1 (gemini-3.8-flash): invalid, the report names roughness", r["valid"] is False and any("roughness" in e for e in r["xe"]) and "roughness" in r["rep"], {"xe": r["xe"][:2], "codes": r["codes"], "ms": r["ms"]})
        fx.ok("anim-01 attempt 1: the port's XSD lines equal the recorded fork@eb4b4b4 lines", r["xe"] == r["recXe"] and r["recOk"] is False, {"port": r["xe"], "recorded": r["recXe"]})
        fx.ok("reportHtml and repairText carry js-port-of-8dd0d3e and never fork@", "js-port-of-8dd0d3e" in r["rep"] and "fork@" not in r["rep"] and r["label"] == "js-port-of-8dd0d3e" and "roughness" in r["txt"] and "XSD errors:" in r["txt"], r["rep"][:160])
        fx.ok("reportHtml escapes data (no raw '<' from the finding text)", "&lt;" in r["rep"] or "<X3D" not in r["rep"])
        h = await pg.evaluate("(async()=>{const r=await VAL.validate(HERO.items[0].body);return [r.valid,codesOfRes(r),r.xsd.schema_version]})()")
        fx.ok("hero final body (recorded valid) validates VALID here against x3d-4.0.xsd", h[0] is True and h[2] == "4.0", h)
        m = await pg.evaluate("(async()=>{const r=await VAL.validate('<X3D profile=\\'Interchange\\' version=\\'4.0\\'><Scene><Shape></Scene>');return [r.valid,r.xsd.errors[0]]})()")
        fx.ok("malformed body → XML parse error, invalid", m[0] is False and str(m[1]).startswith("XML parse error"), m)
        memo = await pg.evaluate("(async()=>{const x=LIVE[0].B[0];const a=await VAL.validate(x),b=await VAL.validate(x);return [a===b,VAL.memo.size]})()")
        fx.ok("memo by sha: the same body returns the memoised result", memo[0] is True and memo[1] >= 3, memo)
        cmp_ = await pg.evaluate("(async()=>{const it=LIVE.find(i=>i.p==='anim-01'&&i.m==='gemini-3.8-flash');const r=await VAL.validate(it.B[0]);return [VAL.compare(r,false,['xsd']),VAL.compare(r,true,[]),VAL.compare(null,true,[])]})()")
        fx.ok("VAL.compare agrees|differs", cmp_ == ["agrees", "differs", "differs"], cmp_)
        # ---- parity with the recorded fork@8dd0d3e verdicts ----
        can = await pg.evaluate("(async()=>{const c=await VAL.canary();return {bodies:c.bodies,agree:c.agree,flips:c.flips.slice(0,12),nflips:c.flips.length,groups:c.groups,skipped:c.skipped,perBody:c.perBody,ms:c.ms,warnDiff:c.warnDiff,label:c.label,recorded:c.recorded}})()")
        nlive = len([k for k in can["skipped"] if k.startswith("live-")]) + can["groups"]["live"]
        fx.ok(f"canary covers every recorded body on the page: {can['groups']['live']} of the 383 live attempts (the rest have no body in part live.bodies: {len(can['skipped'])} skipped, none silently), all 174 replay bodies, the physics ledger", nlive == 383 and can["groups"]["replay"] == 174 and can["groups"]["ledger"] == 1 and can["groups"]["live"] >= 300 and can["bodies"] == can["groups"]["live"] + 174 + 1, {k: can[k] for k in ("bodies", "groups", "ms")} | {"skipped": len(can["skipped"]), "skipped_eg": can["skipped"][:3]})
        fx.ok("at least 50 recorded bodies from LIVE and from REAL were validated here", can["groups"]["live"] >= 50 and can["groups"]["replay"] >= 50)
        fx.ok(f"parity: {can['agree']} of {can['bodies']} bodies agree with fork@8dd0d3e (valid flag, XSD flag, XSD error count, semantic codes); 0 flips", can["nflips"] == 0 and can["agree"] >= 100, {"flips": can["flips"], "nflips": can["nflips"]} if can["nflips"] else f"agree {can['agree']} · warn-only differences {can['warnDiff']} · {can['ms']} ms for the whole set")
        pb = can["perBody"]
        fx.ok(f"per-body time after warm-up under {PER_BODY_MS:g} ms (median and p90)", pb["median"] is not None and pb["median"] < PER_BODY_MS and pb["p90"] < PER_BODY_MS, pb)
        fx.ok("the canary is labelled js-port-of-8dd0d3e vs fork@8dd0d3e recorded", can["label"] == "js-port-of-8dd0d3e" and can["recorded"] == "fork@8dd0d3e")
        fx.ok("c.canary claim (recorded canary) still computes to its expected value", (await pg.evaluate("(async()=>{const r=await CLAIMS.run('c.canary');return r.ok})()")) is True)
        # ---- the bench reads VAL when built in ----
        if await pg.evaluate("!!self.BENCH"):
            fx.ok("[bench] not read-only under the viewer CSP", await pg.evaluate("__bench.readOnly===false&&!document.getElementById('benchTa').readOnly"))
        errs = fx.errors(pg)
        fx.ok("no page errors", not errs, errs[:5])
        fx.ok("no boot errors in #under", await pg.evaluate("BOOT.log.length") == 0, await pg.evaluate("BOOT.log"))
        await pg.context.close(); fx.stop()
        # ---- nowasm: the port cannot run; mode none with a reason; the bench read-only ----
        nw = Fixture(csp="nowasm", argv=[]); nw.res = fx.res
        pg2 = await nw.page(b); await nw.goto(pg2)
        await pg2.evaluate("VAL.need()")
        fx.ok("[nowasm] VAL.mode === 'none'", await nw.wait(pg2, "VAL.mode==='none'", 60000), await pg2.evaluate("[VAL.mode,VAL.reason,ENV.wasmInstantiate]"))
        fx.ok("[nowasm] VAL.reason names WebAssembly / wasm", "wasm" in (await pg2.evaluate("VAL.reason")).lower() or "webassembly" in (await pg2.evaluate("VAL.reason")).lower(), await pg2.evaluate("VAL.reason"))
        fx.ok("[nowasm] VAL.validate rejects with 'VAL unavailable'", "VAL unavailable" in await pg2.evaluate("VAL.validate('<X3D/>').then(()=>'resolved',e=>String(e.message))"))
        fx.ok("[nowasm] xsd parts stay idle (never fetched when the port cannot run)", await pg2.evaluate("DATA.status.xsd40.state==='idle'&&DATA.status.xsd41.state==='idle'"), await pg2.evaluate("[DATA.status.xsd40.state,DATA.status.xsd41.state]"))
        fx.ok("[nowasm] #portChip says not available", await nw.wait(pg2, "document.getElementById('portChip').textContent.includes('not available')", 5000), await nw.txt(pg2, "#portChip"))
        if await pg2.evaluate("!!self.BENCH"):
            fx.ok("[nowasm] bench opens read-only with the reason", await nw.wait(pg2, "__bench.readOnly===true&&document.getElementById('benchTa').readOnly&&document.getElementById('benchStatus').textContent.includes('READ-ONLY')", 10000), await nw.txt(pg2, "#benchStatus"))
            fx.ok("[nowasm] bench still loads the hero attempt 1 and shows the recorded report", await nw.wait(pg2, "__bench.loads>=1&&__bench.last&&__bench.last.recorded===true", 60000), await pg2.evaluate("__bench.last&&[__bench.last.label,__bench.last.valid]"))
        e2 = nw.errors(pg2)
        fx.ok("[nowasm] no page errors (X_ITE's own wasm excluded by the fixture)", not e2, e2[:5])
        await pg2.context.close(); nw.stop()
    fx.summary()
Fixture.run(main)
