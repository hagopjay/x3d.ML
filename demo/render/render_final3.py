"""Render pass v3 for the Tether Firehose v2 replay: ALL 174 cached GPU-phase scenes, one FRESH page per scene, X_ITE 16.5.0 published as own files,
headless (SwiftShader), viewer-like CSP rig (serve.py).
What changed from render_final2.py: that pass sampled only frames arriving 700 ms or more after the load, so a scene whose frames had already come and gone
(X_ITE renders on demand) could read as "no frame", and on a faster machine a drawing scene could too. This pass registers a watcher on X_ITE's end-of-frame
field BEFORE the scene is loaded and samples the canvas inside that callback (first 8 frames, then at most one every 150 ms, 20 samples), so it does not wait for
any frame to arrive. It then settles 3.5 s and takes a real screenshot of the canvas box as an independent check of what is on screen.
Usage: python3 render_final3.py data/renders3_x_ite_16.5.0.json   (serve.py running, build/xite from mkxite.py)
Output {key: {nodes, nonblank (best in-callback), shot (screenshot), frames, first, last, series, err, msgs[], unknown, jpg(b64), ms}}"""
import asyncio, base64, glob, io, json, os, re, sys, time
from playwright.async_api import async_playwright
from PIL import Image
EXE=os.environ.get('CHROME')   # unset: Playwright's own Chromium
G=os.environ.get('GPU_PHASE_DIR','/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11')+'/results/x3d'
URL=os.environ.get('RENDER_URL','http://127.0.0.1:8782/render3.html')   # serve.py serves it
OUT=sys.argv[1] if len(sys.argv)>1 else 'renders3.json'
LIMIT=int(os.environ.get('LIMIT','0'))      # smoke test: render only the first N scenes
WORKERS=int(os.environ.get('WORKERS','3'))
SETTLE=int(os.environ.get('SETTLE','3500'))
MAXS=int(os.environ.get('MAXS','20'))        # samples per scene; the extended check on still-animating blank scenes uses SETTLE=12000 MAXS=90
files=sorted(glob.glob(G+'/*/*/*.x3d'))
if os.environ.get('ONLY'): keep_keys=set(json.load(open(os.environ['ONLY']))); files=[f for f in files if '/'.join(f.split('/')[-3:]) in keep_keys]   # ONLY=<json list of keys>
files=files[:LIMIT or None]
NOISE=re.compile(r'font|x_ite\.css|mikktspace|logo\.svg|Content Security|Fetch API|PAGEERR Event|Failed to load resource')


def shot_nonblank(png):
    """Same measure as the page's grab(): background = most common 5-bit colour over every 4th pixel, a pixel differs if |dR|+|dG|+|dB| > 48."""
    raw = Image.open(io.BytesIO(png)).convert('RGB').tobytes(); n = len(raw) // 3
    cnt = {}
    for i in range(0, n, 4):
        k = (raw[3 * i] >> 3) << 10 | (raw[3 * i + 1] >> 3) << 5 | (raw[3 * i + 2] >> 3); cnt[k] = cnt.get(k, 0) + 1
    bg = max(cnt, key=cnt.get); r0, g0, b0 = (bg >> 10 & 31) << 3, (bg >> 5 & 31) << 3, (bg & 31) << 3
    diff = sum(1 for i in range(n) if abs(raw[3 * i] - r0) + abs(raw[3 * i + 1] - g0) + abs(raw[3 * i + 2] - b0) > 48)
    return round(diff / n, 4)


async def worker(b, q, out):
    while True:
        try: f = q.get_nowait()
        except asyncio.QueueEmpty: break
        key = '/'.join(f.split('/')[-3:]); x = open(f, encoding='utf-8', errors='replace').read(); msgs = []; t = time.time()
        pg = await b.new_page(viewport={'width': 400, 'height': 300})
        pg.on('console', lambda m: msgs.append(m.type + ': ' + m.text[:200].replace('\n', ' ')) if m.type in ('error', 'warning') else None)
        r = {}
        try:
            await pg.goto(URL); await pg.wait_for_function('document.querySelector("x3d-canvas").browser!==undefined', timeout=20000)
            await pg.evaluate('initCss()'); msgs.clear()
            r = await asyncio.wait_for(pg.evaluate('([x,s,m])=>measure(x,s,m)', [x, SETTLE, MAXS]), timeout=40)
            if not r.get('err'):
                try: r['shot'] = shot_nonblank(await pg.locator('#box').screenshot())
                except Exception as e: r['shot'] = None; r['shot_err'] = type(e).__name__
        except Exception as e: r = {'err': 'harness: ' + type(e).__name__}
        png = r.pop('png', None)
        if png:
            im = Image.open(io.BytesIO(base64.b64decode(png.split(',')[1]))).convert('RGB').resize((192, 144)); buf = io.BytesIO(); im.save(buf, 'JPEG', quality=72); r['jpg'] = base64.b64encode(buf.getvalue()).decode()
        keep = [m for m in msgs if not NOISE.search(m)]
        r['unknown'] = sum(1 for m in keep if 'Unknown node type' in m)
        r['msgs'] = [m[:170] for m in keep][:4]; r['nmsg'] = len(keep); r['ms'] = int((time.time() - t) * 1000); out[key] = r
        print(len(out), key, r.get('nodes'), 'cb', r.get('nonblank'), 'shot', r.get('shot'), 'frames', r.get('frames'), (r.get('err') or '')[:50], flush=True)
        await pg.close()


async def main():
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--hide-scrollbars'])
        q = asyncio.Queue(); [q.put_nowait(f) for f in files]
        await asyncio.gather(*[worker(b, q, out) for _ in range(WORKERS)]); await b.close()
    json.dump(out, open(OUT, 'w')); print('done', len(out))
asyncio.run(main())
