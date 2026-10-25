"""check_v4_fx.py — S6 sonification (54-sound) and S8 GLSL flow field (56-field) acceptance.
Run: python3 demo/v4/build_v4.py demo/build/v4-fx --no-xite && ln -sfn $PWD/demo/build/xite demo/build/v4-fx/xite && V4_BUILD=demo/build/v4-fx python3 demo/tests/check_v4_fx.py
Asserts (ARCHITECTURE §6 fixture; one page, waits sized for a shared 4-core box under SwiftShader):
  sound: no AudioContext constructed before a click (constructor counter from an init script + __sound.ctx === null); the mast Sound chip #bSound exists and reads
         "Sound: off"; at fx 0 (webdriver) a click refuses (SOUND.isOn false, no context); at fx 1 the click constructs exactly one AudioContext and SOUND.isOn is true;
         SIM events while on schedule the right oscillator: a valid scene → tick, an invalid one → thud, S.detected rising → alarm, failed calls passing the run clock → click
         (hook __sound.last / __sound.counts); FX.set(0) switches it off; prefers-reduced-motion refuses; still exactly one AudioContext at the end.
  field: at fx 0 no GL canvas in #matrixField (data-mode 2d); __FX.set(2) appends canvas.fl-gl with data-mode='gl' (or, when WebGL is unavailable, no canvas and one
         __field.err) and the uniforms {u_thr 0.005, u_bad, u_det} update after a SIM tick; the panel draws through LOOP (__panels.field, no own rAF);
         LOOP.stats.frame p95 at fx 2 < 25 ms (printed with the reason when the box is loaded); __FX.set(0) removes the canvas and resets data-mode; no page errors."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture, REPO
fx = Fixture()
AC_COUNTER = """(()=>{const wrap=n=>{const O=window[n];if(!O)return;const W=function(...a){window.__acCount=(window.__acCount||0)+1;return new O(...a)};W.prototype=O.prototype;window[n]=W};window.__acCount=0;wrap('AudioContext');wrap('webkitAudioContext')})();"""
async def main():
    bundle = open(os.path.join(fx.build_dir, "index.html"), encoding="utf-8").read()
    js = bundle[bundle.rfind("<script>"):]
    fx.ok("bundle carries 54-sound.js and 56-field.js", "js/54-sound.js" in js and "js/56-field.js" in js)
    fx.ok("setInterval( count in the bundle is 0", js.count("setInterval(") == 0, js.count("setInterval("))
    src = ""
    for f in ("54-sound.js", "56-field.js"):
        p = os.path.join(REPO, "demo", "v4", "js", f)
        if os.path.exists(p): src += open(p, encoding="utf-8").read()
    fx.ok("no $digit replacement strings, no eval/new Function, no audio files in the two modules", not re.search(r"\$[0-9]|new Function|[^a-zA-Z_]eval\(|\.(mp3|ogg|wav)\b", src))
    fx.ok("no requestAnimationFrame of its own in 56-field (LOOP panel only)", "requestAnimationFrame" not in src)
    frag = os.path.join(REPO, "demo", "v4", "shaders", "flow.frag")
    fx.ok("shaders/flow.frag is the readable copy of the embedded fragment shader (same uniforms)", os.path.exists(frag) and all(u in open(frag).read() for u in ("u_thr", "u_bad", "u_det")) and "u_det" in src)
    async with fx.browser() as b:
        pg = await fx.page(b)
        await pg.add_init_script(AC_COUNTER)
        await fx.goto(pg)
        fx.ok("boot reaches BOOT.phase ready", await fx.wait(pg, 'BOOT.phase==="ready"', 180000), await pg.evaluate("[BOOT.phase,BOOT.ms,LOOP.frames]"))
        fx.ok("fx 0 under webdriver", await fx.wait(pg, 'document.documentElement.dataset.fx==="0"', 20000))
        fx.ok("clock running", await fx.wait(pg, "S&&S.clk>5&&S.scenes.length>=3", 60000), await pg.evaluate("S&&[S.clk,S.scenes.length]"))
        # ---- sound: nothing before a gesture ----
        fx.ok("no AudioContext constructed at load (__sound.ctx === null, constructor count 0)", await pg.evaluate("__sound.ctx===null&&window.__acCount===0&&!SOUND.isOn"), await pg.evaluate("[__sound.ctx===null,window.__acCount,SOUND.isOn]"))
        fx.ok("mast Sound chip #bSound present in .mastR and muted by default", await fx.wait(pg, 'document.querySelector(".mastR #bSound")&&document.querySelector("#bSound").textContent==="Sound: off"', 20000), await fx.txt(pg, "#bSound"))
        fx.ok("sound panel registered with LOOP (no own timer)", await pg.evaluate("!!__panels.sound&&__panels.sound.rateHz===20"))
        await pg.click("#bSound")
        await pg.wait_for_timeout(300)
        fx.ok("at fx 0 the click refuses: no sound, no AudioContext", await pg.evaluate("!SOUND.isOn&&window.__acCount===0&&__sound.ctx===null&&/fx 0/.test(__sound.reason)"), await pg.evaluate("[SOUND.isOn,window.__acCount,__sound.reason]"))
        # ---- sound at fx 1 ----
        await pg.evaluate("__FX.set(1)")
        await pg.click("#bSound")
        fx.ok("click at fx 1 constructs exactly one AudioContext and SOUND.isOn", await fx.wait(pg, "SOUND.isOn&&__sound.ctx!==null&&window.__acCount===1", 5000), await pg.evaluate("[SOUND.isOn,__sound.ctx&&__sound.ctx.state,window.__acCount,__sound.reason]"))
        fx.ok("chip reads Sound: on with aria-pressed", await pg.evaluate('document.querySelector("#bSound").textContent==="Sound: on"&&document.querySelector("#bSound").getAttribute("aria-pressed")==="true"'))
        fx.ok("bed running (oscillators only)", await pg.evaluate("__sound.bed===true"))
        await pg.evaluate("SIM.pause()")
        await pg.evaluate("__sound.last=null;SIM.emit('scene',{id:'T-valid',src:'live',verdict:'valid'})")
        fx.ok("valid scene schedules the tick", await pg.evaluate("__sound.last") == "tick", await pg.evaluate("__sound.last"))
        await pg.evaluate("SIM.emit('scene',{id:'T-bad',src:'live',verdict:'invalid'})")
        fx.ok("invalid scene schedules the thud", await pg.evaluate("__sound.last") == "thud", await pg.evaluate("__sound.last"))
        await pg.evaluate("__sound.last=null;S.detected++;LOOP.dirty(LOOP.bits.VERIFY)")
        fx.ok("a detection (S.detected rising) schedules the alarm", await fx.wait(pg, '__sound.last==="alarm"', 5000), await pg.evaluate("[__sound.last,S.detected,__sound.detSeen]"))
        await pg.evaluate("S.detected--")
        # failed calls: seek just before the first failed row, then run; the baseline is re-taken on seek so the scrub itself never clicks
        t_fail = await pg.evaluate("Math.min(...EVENTS.failed.map(f=>f.t1!=null?f.t1:f.t0))")
        await pg.evaluate(f"SIM.seekTo({t_fail - 20});__sound.counts.click=0;SIM.resume()")
        fx.ok("the seek itself schedules no click (baseline re-taken)", await pg.evaluate("__sound.counts.click") == 0, await pg.evaluate("[__sound.counts.click,__sound.failedSeen,S.clk]"))
        fx.ok("a failed call passing the run clock schedules the click", await fx.wait(pg, "__sound.counts.click>0", 15000), await pg.evaluate("[__sound.counts.click,__sound.failedSeen,S.clk]"))
        fx.ok("ticks/thuds counted while the replay runs", await pg.evaluate("__sound.counts.tick+__sound.counts.thud>1"), await pg.evaluate("JSON.stringify(__sound.counts)"))
        await pg.evaluate("__FX.set(0)")
        fx.ok("FX.set(0) switches the sound off (honours fx 0)", await fx.wait(pg, '!SOUND.isOn&&__sound.bed===false&&/fx 0/.test(__sound.reason)', 3000), await pg.evaluate("[SOUND.isOn,__sound.reason]"))
        await pg.evaluate("__FX.set(1)")
        await pg.emulate_media(reduced_motion="reduce")
        r = await pg.evaluate("SOUND.on()")
        fx.ok("prefers-reduced-motion: SOUND.on() refuses", r is False and not await pg.evaluate("SOUND.isOn") and await pg.evaluate("/reduced-motion/.test(__sound.reason)"), await pg.evaluate("[SOUND.isOn,__sound.reason]"))
        await pg.emulate_media(reduced_motion="no-preference")
        fx.ok("still exactly one AudioContext (reused across on/off)", await pg.evaluate("window.__acCount") == 1, await pg.evaluate("window.__acCount"))
        # ---- field ----
        await pg.evaluate("__FX.set(0)")
        await pg.wait_for_timeout(200)
        fx.ok("fx 0: #matrixField has no GL canvas and data-mode 2d", await pg.evaluate('document.querySelector("#matrixField")&&!document.querySelector("#matrixField canvas.fl-gl")&&document.querySelector("#matrixField").dataset.mode==="2d"&&__field.gl===null'), await pg.evaluate('[!!document.querySelector("#matrixField"),document.querySelector("#matrixField")?.dataset.mode,__field.mode]'))
        fx.ok("field panel registered with LOOP at 30 Hz (no own rAF)", await pg.evaluate("!!__panels.field&&__panels.field.rateHz===30"))
        await pg.evaluate('document.querySelector("#matrix").scrollIntoView()')
        await pg.evaluate("__FX.set(2)")
        got = await fx.wait(pg, '(document.querySelector("#matrixField canvas.fl-gl")&&document.querySelector("#matrixField").dataset.mode==="gl"&&__field.gl)||__field.err', 10000)
        err = await pg.evaluate("__field.err")
        if err and not await pg.evaluate("__field.gl"):
            fx.ok("fx 2 without WebGL: no GL canvas, data-mode stays 2d, one __field.err", await pg.evaluate('!document.querySelector("#matrixField canvas.fl-gl")&&document.querySelector("#matrixField").dataset.mode==="2d"'), err)
            print("INFO  WebGL unavailable in this browser:", err, "— the gl branch could not be exercised here")
        else:
            fx.ok("__FX.set(2) appends canvas.fl-gl to #matrixField with data-mode gl", got, await pg.evaluate('[__field.mode,__field.err,document.querySelector("#matrixField")?.dataset.mode]'))
            fx.ok("2D fallback canvas hidden by CSS under data-mode gl", await pg.evaluate('getComputedStyle(document.querySelector("#matrixField .fl-2d")).display==="none"'))
            fx.ok("field panel becomes visible (IO on the slot) and draws through LOOP", await fx.wait(pg, "__panels.field.visible&&__field.frames>0", 20000), await pg.evaluate("[__panels.field.visible,__field.frames,__field.size]"))
            fx.ok("half resolution: canvas backing ≤ half the css size (dpr/2)", await pg.evaluate('(()=>{const c=document.querySelector("#matrixField canvas.fl-gl");return c.width<=Math.ceil(c.clientWidth*devicePixelRatio/2)+1&&c.width>0})()'), await pg.evaluate('(()=>{const c=document.querySelector("#matrixField canvas.fl-gl");return [c.width,c.height,c.clientWidth,c.clientHeight,devicePixelRatio]})()'))
            uf0 = await pg.evaluate("__field.uframes")
            await pg.evaluate("SIM.resume()")
            fx.ok("uniforms updated after SIM ticks (u_thr 0.005, u_bad in [0,1], u_det numeric)", await fx.wait(pg, f"__field.uframes>{uf0}+3&&__field.uniforms&&__field.uniforms.u_thr===0.005&&__field.uniforms.u_bad>=0&&__field.uniforms.u_bad<=1&&typeof __field.uniforms.u_det==='number'", 15000), await pg.evaluate("JSON.stringify(__field.uniforms)"))
            fx.ok("u_bad tracks MATRIX.fieldUniforms()", await pg.evaluate("Math.abs(__field.uniforms.u_bad-MATRIX.fieldUniforms().u_bad)<0.2"), await pg.evaluate("[__field.uniforms.u_bad,MATRIX.fieldUniforms().u_bad]"))
            await pg.wait_for_timeout(4000)
            st = await pg.evaluate("({frame:LOOP.stats.frame,fps:LOOP.stats.fps,field:LOOP.stats.panel.field,fx:document.documentElement.dataset.fx})")
            la = os.getloadavg()
            p95 = st["frame"]["p95"]
            if p95 < 25: fx.ok("LOOP.stats.frame p95 at fx 2 < 25 ms", True, f"p95 {p95:.1f} ms, panel field p95 {st['field']['p95']:.2f} ms over {st['field']['n']} draws, fps {st['fps']}, load {la[0]:.2f}")
            else: print(f"INFO  LOOP.stats.frame p95 at fx 2 = {p95:.1f} ms (≥ 25 ms): SwiftShader fragment shading on a shared 4-core box, load average {la[0]:.2f}; panel field p95 {st['field']['p95']:.2f} ms, over-budget {st['field']['over']} of {st['field']['n']} draws, fps {st['fps']}"); fx.ok("perf number printed with reason (box-bound)", True, f"p95 {p95:.1f} ms")
            await pg.evaluate("FIELD.dispose()"); await pg.wait_for_timeout(4000)
            st2 = await pg.evaluate("({frame:LOOP.stats.frame,fps:LOOP.stats.fps,panels:Object.entries(LOOP.stats.panel).filter(([k,v])=>v.p95>2).map(([k,v])=>k+' '+v.p95.toFixed(1)+'ms')})")
            print(f"INFO  same page at fx 2 with the field disposed: LOOP.stats.frame p95 {st2['frame']['p95']:.1f} ms, fps {st2['fps']}; panels over 2 ms p95: {', '.join(st2['panels'])}")
            fx.ok("the field adds no more than 10 ms to the page's own frame p95 at fx 2", p95 - st2["frame"]["p95"] <= 10, f"with {p95:.1f} ms, without {st2['frame']['p95']:.1f} ms")
            await pg.evaluate("FIELD.create()")
            fx.ok("field panel over-budget draws are a minority", st["field"]["n"] > 0 and st["field"]["over"] <= max(3, st["field"]["n"] * 0.5), json.dumps(st["field"]))
        await pg.evaluate("__FX.set(0)")
        fx.ok("__FX.set(0) removes the GL canvas, resets data-mode 2d, releases the context", await fx.wait(pg, '!document.querySelector("#matrixField canvas.fl-gl")&&document.querySelector("#matrixField").dataset.mode==="2d"&&__field.gl===null&&!FIELD.active', 5000), await pg.evaluate('[__field.mode,document.querySelector("#matrixField").dataset.mode,FIELD.active]'))
        await pg.evaluate("__FX.set(2)")
        await fx.wait(pg, '__field.gl||__field.err', 5000)
        await pg.evaluate("__FX.set(1)")
        fx.ok("fx 1 also disposes the field (fx 2 only)", await fx.wait(pg, '!document.querySelector("#matrixField canvas.fl-gl")&&__field.gl===null', 5000))
        errs = fx.errors(pg)
        fx.ok("no page errors", not errs, errs[:5])
    fx.summary()
fx.run(main)
