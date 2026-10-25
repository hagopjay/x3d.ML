"""check_v4_perf.py: the one-loop performance gate for Tether Firehose 4 (WORKPLAN section 2: 01-loop and 30-firehose acceptance;
SPEC-v4 sections 7.1 and 13; ARCHITECTURE section 4, 01-loop).
Usage:
  python3 demo/tests/check_v4_perf.py [--csp viewer|eval|noeval|nowasm|noworker] [url]
    with demo/tests/v4fixture.py present and no url/PAGE: the fixture serves demo/build/v4 (or $BUILD_DIR) itself;
    otherwise:  PAGE=http://127.0.0.1:8765/index.html python3 demo/tests/check_v4_perf.py     (after python3 demo/serve.py --root build/v4 --port 8765)
  env CHROME=/opt/pw-browsers/chromium (the Python Playwright here has no bundled browser), PERF_P95_MS (default 20), PERF_SETTLE_MS (default 3000).
Measures at fx 0 (SwiftShader + navigator.webdriver put the page at fx 0; SPEC 7.4):
  frame p50 / p95 ms   rAF frame-to-frame times over 5 s with the replay running           p95 < 20 ms   (01-loop acceptance)
  rAF frames in 5 s    the loop is advancing                                                >= 60 (12 fps), and LOOP.frames grows
  setInterval( count   occurrences in the inline bundle + same-origin non-xite scripts     0             (ground truth 0 of ARCHITECTURE)
  #fh mutations        MutationObserver records under #fh over 5 s with LOOP.pause()       0             (30-firehose acceptance)
  data-fx              document.documentElement.dataset.fx === "0" under webdriver         (SPEC 13)
  page errors          pageerror + console.error minus X_ITE noise                          0
  info rows            LOOP.stats.frame (the page's own p95/mean), LOOP.stats.fps, LOOP.stats.panel over-budget counts, S.scenes delta, load average
Exit 0 all PASS, 1 any FAIL, 2 SKIP: the page has no window.LOOP after 15 s (01-loop not built yet, or the URL is not a v4 page).
No test hook is added to the page; the test only reads LOOP, S, document.scripts and installs its own MutationObserver.
"""
import asyncio, os, re, sys, json, time, glob
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
ARGS = sys.argv[1:]
CSP = ARGS[ARGS.index("--csp") + 1] if "--csp" in ARGS and ARGS.index("--csp") + 1 < len(ARGS) else "viewer"
URL = os.environ.get("PAGE") or next((a for i, a in enumerate(ARGS) if a.startswith("http") and not (i > 0 and ARGS[i - 1] == "--csp")), None)
P95_MS = float(os.environ.get("PERF_P95_MS", "20")); SETTLE_MS = int(os.environ.get("PERF_SETTLE_MS", "3000"))
NOISE = re.compile(r'font|fonts\.g|stylesheet|mikktspace|Content Security|Fetch API|Failed to load resource|net::ERR|XML Parser|wasm|Failed to fetch')
FLAGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--hide-scrollbars']
def chrome():
    exe = os.environ.get('CHROME')
    if exe: return exe
    c = sorted(glob.glob('/opt/pw-browsers/chromium*/chrome-linux/chrome')); return c[-1] if c else None
res = []
def ok(name, cond, detail=''):
    res.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name + ((' :: ' + str(detail)[:300]) if detail != '' else ''), flush=True)
def info(name, detail): print(f'info {name} :: {detail}', flush=True)
def pct(xs, q):
    if not xs: return float('nan')
    s = sorted(xs); return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]

async def measure(pg, errs):
    # 0. the loop must exist; otherwise this gate does not apply yet
    try: await pg.wait_for_function('typeof window.LOOP === "object" && window.LOOP', timeout=15000)
    except Exception:
        print('SKIP check_v4_perf: the page has no window.LOOP after 15 s (01-loop not built yet, or not a v4 page):', await pg.evaluate('location.href')); return 2
    # settle: the window opens after BOOT.phase === 'ready' and the boot hero measure (SwiftShader shader compiles are multi-second main-thread tasks), then SETTLE_MS more
    t0 = time.time()
    while time.time() - t0 < 180:
        try:
            if await pg.evaluate('!!(window.BOOT && BOOT.phase === "ready" && (BOOT.heroMeasure || (window.__stage && __stage.show && __stage.show.frozen) || performance.now() > 90000))'): break
        except Exception: pass
        await pg.wait_for_timeout(500)
    info('settle', f'BOOT.phase ready after {time.time() - t0:.1f} s wait, then {SETTLE_MS} ms')
    await pg.wait_for_timeout(SETTLE_MS)
    fx = await pg.evaluate('document.documentElement.dataset.fx')
    ok('data-fx is "0" under SwiftShader + webdriver', fx == '0', f'data-fx={fx!r}')
    # 1. setInterval( in the bundle (inline scripts) and same-origin non-xite external scripts; counted in Python so the probe text is never part of the page
    inline = await pg.evaluate('[...document.scripts].filter(s=>!s.src).map(s=>s.textContent).join("\\n")')
    ext = await pg.evaluate('''async () => { const out = {}; for (const s of document.scripts) { if (!s.src || s.src.includes('/xite/') || !s.src.startsWith(location.origin)) continue;
        try { out[s.src] = await (await fetch(s.src)).text(); } catch (e) { out[s.src] = ''; } } return out; }''')
    n_inline = inline.count('setInterval('); n_ext = {k.split('/')[-1]: v.count('setInterval(') for k, v in ext.items()}
    ok('setInterval( count in the bundle is 0', n_inline + sum(n_ext.values()) == 0, f'inline {n_inline} ({len(inline)//1024} KB of inline script); external {n_ext or "none"}')
    # 2. rAF frame times over 5 s with the replay running
    f0 = await pg.evaluate('LOOP.frames|0'); sc0 = await pg.evaluate('window.S && S.scenes ? S.scenes.length : null'); clk0 = await pg.evaluate('window.S ? S.clk : null')
    ts = await pg.evaluate('''() => new Promise(res => { const ts = []; const t0 = performance.now();
        function f(t) { ts.push(t); if (t - t0 < 5000) requestAnimationFrame(f); else res(ts); } requestAnimationFrame(f); })''')
    f1 = await pg.evaluate('LOOP.frames|0'); sc1 = await pg.evaluate('window.S && S.scenes ? S.scenes.length : null'); clk1 = await pg.evaluate('window.S ? S.clk : null')
    d = [b - a for a, b in zip(ts, ts[1:])]
    p50, p95, mx = pct(d, .5), pct(d, .95), max(d) if d else float('nan')
    ok(f'frame p95 < {P95_MS:g} ms at fx 0 over 5 s replay', p95 < P95_MS, f'p50 {p50:.1f} ms, p95 {p95:.1f} ms, max {mx:.1f} ms over {len(d)} intervals')
    ok('rAF advancing (>= 60 callbacks in 5 s) and LOOP.frames grows', len(ts) >= 60 and f1 > f0, f'{len(ts)} rAF callbacks; LOOP.frames {f0} -> {f1}')
    info('replay progress during the 5 s', f'S.scenes {sc0} -> {sc1}; S.clk {clk0} -> {clk1}')
    stats = await pg.evaluate('(() => { try { const s = LOOP.stats || {}; return {frame: s.frame || null, fps: s.fps ?? null, panels: Object.fromEntries(Object.entries(s.panel || {}).map(([k, v]) => [k, {p95: v.p95, n: v.n, over: v.over}]))}; } catch (e) { return {err: String(e)}; } })()')
    info('LOOP.stats (the page\'s own numbers)', json.dumps(stats)[:600])
    # 3. DOM mutations under #fh while paused
    mo = await pg.evaluate('''async () => { const fh = document.querySelector('#fh') || document.querySelector('#firehose table') || document.querySelector('section#firehose');
        if (!fh) return {missing: true};
        const before = window.S && S.scenes ? S.scenes.length : null; if (LOOP.pause) LOOP.pause();
        await new Promise(r => setTimeout(r, 250));
        let n = 0; const sample = []; const mo = new MutationObserver(rs => { n += rs.length; for (const r of rs) if (sample.length < 6) sample.push(r.type + ' ' + (r.target.nodeName || '#text') + (r.target.id ? '#' + r.target.id : '') + (r.attributeName ? ' @' + r.attributeName : '')); });
        mo.observe(fh, {childList: true, subtree: true, attributes: true, characterData: true});
        await new Promise(r => setTimeout(r, 5000)); mo.disconnect();
        const after = window.S && S.scenes ? S.scenes.length : null; const paused = LOOP.paused; if (LOOP.resume) LOOP.resume();
        return {n, sample, before, after, paused, sel: fh.id ? '#' + fh.id : fh.tagName, rows: fh.querySelectorAll('tr').length}; }''')
    if mo.get('missing'): ok('#fh present (firehose mounted)', False, 'no #fh, #firehose table or section#firehose in the DOM')
    else:
        ok('0 DOM mutations under #fh over 5 s while paused', mo['n'] == 0 and mo['before'] == mo['after'], f"{mo['n']} records on {mo['sel']} ({mo['rows']} rows); S.scenes {mo['before']} -> {mo['after']}; LOOP.paused={mo['paused']}; e.g. {mo['sample']}")
    ok('no page errors', not errs, errs[:3] or '0')
    return 0

async def own_browser():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome(), args=FLAGS)
        ctx = await b.new_context(viewport={'width': 1500, 'height': 1000}, locale='en-US'); pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append('PAGEERR ' + str(e)[:300]))
        pg.on('console', lambda m: errs.append('console.error: ' + m.text[:240]) if m.type == 'error' and not NOISE.search(m.text) else None)
        await pg.goto(URL, wait_until='load'); code = await measure(pg, errs); await b.close(); return code

async def with_fixture():
    from v4fixture import Fixture
    fx = Fixture(build_dir=os.environ.get('BUILD_DIR') or os.environ.get('V4_BUILD') or os.path.join(REPO, 'demo', 'build', 'v4'), csp=CSP)
    async with fx.browser() as b:
        pg = await fx.page(b, width=1500, height=1000); await fx.goto(pg)
        code = await measure(pg, [])          # the fixture collects errors itself; measure() sees none through this list
        try: errs = fx.errors(pg); ok('no page errors (fixture)', not errs, errs[:3] or '0')
        except Exception as e: info('fixture errors()', e)
        return code

def main():
    try: la = os.getloadavg(); info('box', f'load average {la[0]:.2f} {la[1]:.2f} {la[2]:.2f} on {os.cpu_count()} cores; thresholds p95 < {P95_MS:g} ms (PERF_P95_MS)')
    except Exception: pass
    use_fixture = URL is None and os.path.isfile(os.path.join(HERE, 'v4fixture.py'))
    if URL is None and not use_fixture:
        print('SKIP check_v4_perf: give a URL (PAGE=http://127.0.0.1:<port>/index.html after `python3 demo/serve.py --root build/v4 --port <port>`) or add demo/tests/v4fixture.py'); sys.exit(2)
    info('target', f"{'v4fixture ' + CSP if use_fixture else URL}")
    code = asyncio.run(with_fixture() if use_fixture else own_browser())
    if code == 2: sys.exit(2)
    n_fail = sum(1 for _, c in res if not c)
    print(f'SUMMARY check_v4_perf: {len(res) - n_fail} pass, {n_fail} fail'); sys.exit(1 if n_fail else 0)
if __name__ == '__main__': main()
