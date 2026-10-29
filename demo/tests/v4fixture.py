"""v4fixture.py — shared fixture for the Firehose 4 suites (ARCHITECTURE §6).

    from v4fixture import Fixture
    fx = Fixture(build_dir="demo/build/v4", csp="viewer")       # csp: viewer | eval | noeval | nowasm | noworker
    async with fx.browser() as b:
        pg = await fx.page(b, width=1500, height=1000, claude=None, fx=None, query="")
        await fx.goto(pg)
        fx.ok("name", cond, detail); errs = fx.errors(pg); await fx.wait(pg, "js expr", 20000)
    fx.summary()                                                   # prints SUMMARY, exits 1 on a FAIL (2 on FAIL-SOFT unless JSVAL_OPTIONAL=1)

The fixture serves the built directory itself on a free 127.0.0.1 port with one of demo/serve.py's CSP profiles (same names, same text): viewer = today's rig
policy WITH 'unsafe-eval' and 'wasm-unsafe-eval', worker-src 'self' blob:; eval = alias of viewer; noeval = viewer minus 'unsafe-eval' (Text fonts do not
draw); nowasm = minus 'wasm-unsafe-eval' AND minus 'unsafe-eval' (Chromium lets 'unsafe-eval' alone compile wasm, so a true no-wasm profile has neither; this is the one place the text differs from serve.py); noworker = worker-src 'none'. The real artifact viewer's policy is unknown until the Step 0 probe reports.
Pages open with a dark colour scheme (dark first) so a fresh context never flips the page light. HTTP 4xx/5xx responses are recorded as errors. Chromium runs with the SwiftShader flags; CHROME names the executable
(default: the newest /opt/pw-browsers/chromium*/chrome-linux/chrome); the context locale is en-US (X_ITE throws on an invalid language tag).
`claude` installs a window.claude.use stub before load: {"user": {"isOwner": True}, "files": {}, "sample": "<js function source>", "downloads": None}.
`fx` forces __FX.set(n) after load. `--csp <profile>` on any check script's command line overrides the profile; PAGE overrides the URL (no server started);
KEEP=1 keeps the server up after the run and prints the URL. One headless browser at a time; the fixture closes it.
"""
import asyncio, contextlib, http.server, json, os, re, socket, socketserver, sys, threading, time, glob, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)
REPO = os.path.dirname(DEMO)
NOISE = re.compile(r"font|fonts\.g|stylesheet|mikktspace|Content Security|Fetch API|Failed to load resource|net::ERR|XML Parser|wasm|WebAssembly|fflate|cdnjs|favicon", re.I)
# Profiles are demo/serve.py's, by name and by text. "viewer" is today's rig policy and DOES carry 'unsafe-eval' (X_ITE's woff2 font decoder
# needs it); whether the real artifact viewer grants it is UNKNOWN until the Step 0 probe (SPEC §9) reports — so run the suites under
# noeval too before trusting a feature that needs eval. "eval" is an alias of viewer.
CSP_VIEWER = ("default-src 'none'; script-src 'unsafe-inline' 'self' 'wasm-unsafe-eval' 'unsafe-eval'; style-src 'unsafe-inline' 'self' https://fonts.googleapis.com; "
              "font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:")
CSP = {"viewer": CSP_VIEWER, "eval": CSP_VIEWER,
       "noeval": CSP_VIEWER.replace(" 'unsafe-eval'", ""),
       # nowasm strips BOTH tokens: in Chromium 'unsafe-eval' alone still permits WebAssembly, so serve.py's "viewer minus 'wasm-unsafe-eval'" does not block wasm (reported to ops)
       "nowasm": CSP_VIEWER.replace(" 'wasm-unsafe-eval'", "").replace(" 'unsafe-eval'", ""),
       "noworker": CSP_VIEWER.replace("worker-src 'self' blob:", "worker-src 'none'")}
assert CSP["noeval"] != CSP_VIEWER and CSP["nowasm"] != CSP_VIEWER and CSP["noworker"] != CSP_VIEWER
MIME = {".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm", ".woff2": "font/woff2", ".txt": "text/plain", ".json": "application/json", ".x3d": "application/xml", ".html": "text/html", ".css": "text/css", ".svg": "image/svg+xml"}

def chrome_path():
    p = os.environ.get("CHROME")
    if p and os.path.isfile(p): return p
    if p and os.path.isdir(p):
        for c in (os.path.join(p, "chrome-linux", "chrome"), os.path.join(p, "chrome")):
            if os.path.isfile(c): return c
    cands = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")) + sorted(glob.glob("/opt/pw-browsers/chromium/chrome-linux/chrome"))
    return cands[-1] if cands else None

class Fixture:
    def __init__(self, build_dir=None, csp=None, argv=None):
        argv = sys.argv[1:] if argv is None else argv
        build_dir = build_dir or os.environ.get("V4_BUILD") or "demo/build/v4"   # V4_BUILD: a module agent's own build dir
        if "--csp" in argv: csp = argv[argv.index("--csp") + 1]
        self.csp = csp or "viewer"
        assert self.csp in CSP, "csp must be one of " + ", ".join(CSP)
        self.build_dir = build_dir if os.path.isabs(build_dir) else os.path.join(REPO, build_dir)
        self.res = []; self.soft = []; self.server = None; self.port = None; self.url = os.environ.get("PAGE")
        self.shots = os.path.join(HERE, "shots"); os.makedirs(self.shots, exist_ok=True)
    # ---- reporting ----
    def ok(self, name, cond, detail=""):
        self.res.append((name, bool(cond), str(detail)[:300])); print(("PASS " if cond else "FAIL ") + name + ((" :: " + str(detail)[:300]) if detail != "" else ""), flush=True); return bool(cond)
    def fail_soft(self, name, detail=""):
        self.soft.append((name, detail)); print("FAIL-SOFT " + name + " :: " + str(detail)[:300], flush=True)
    def summary(self):
        p = sum(1 for r in self.res if r[1]); f = sum(1 for r in self.res if not r[1])
        print(f"\nSUMMARY {p} pass {f} fail" + (f" {len(self.soft)} soft" if self.soft else ""), flush=True)
        if f: sys.exit(1)
        if self.soft and os.environ.get("JSVAL_OPTIONAL") != "1": sys.exit(2)
    # ---- server ----
    def serve(self, root=None):
        if self.url: return self.url
        root = root or self.build_dir
        assert os.path.isfile(os.path.join(root, "index.html")), f"no index.html under {root} (run python3 demo/v4/build_v4.py demo/build/v4 --files-map)"
        csp = CSP[self.csp]
        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(s, *a, **k): super().__init__(*a, directory=root, **k)
            def translate_path(s, p):
                q = p.split("?")[0]; blobs = os.environ.get("V4_BLOBS")   # artifact asset stand-in: a dir of files named by asset id (see demo/serve.py)
                if blobs and q.startswith("/_blob/"):
                    f = os.path.join(blobs, q[len("/_blob/"):].split("/")[0])
                    if os.path.isfile(f): return f
                return super().translate_path(p)
            def end_headers(s): s.send_header("Content-Security-Policy", csp); s.send_header("Cache-Control", "no-store"); super().end_headers()
            def log_message(s, *a): pass
        H.extensions_map.update(MIME)
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); self.port = srv.server_address[1]; self.server = srv
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.port}/index.html"; return self.url
    def stop(self):
        if self.server and not os.environ.get("KEEP"):
            self.server.shutdown(); self.server.server_close(); self.server = None
        elif self.server: print("KEEP=1: server left up at", self.url)
    # ---- browser ----
    @contextlib.asynccontextmanager
    async def browser(self):
        from playwright.async_api import async_playwright
        exe = chrome_path()
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=exe, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--no-sandbox", "--hide-scrollbars", "--disable-dev-shm-usage"])
            try: yield b
            finally:
                await b.close(); self.stop()
    async def page(self, b, width=1500, height=1000, claude=None, fx=None, query="", csp=None):
        ctx = await b.new_context(viewport={"width": width, "height": height}, locale="en-US", color_scheme="dark")
        pg = await ctx.new_page(); pg._errs = []; pg._fx = fx; pg._query = query
        pg.on("pageerror", lambda e: pg._errs.append("PAGEERR " + str(e)[:300]))
        pg.on("response", lambda r: pg._errs.append(f"HTTP {r.status} {r.url[-120:]}") if r.status >= 400 and "favicon" not in r.url else None)
        pg.on("console", lambda m: pg._errs.append("console.error: " + m.text[:240]) if m.type == "error" and not NOISE.search(m.text) else None)
        if claude is not None: await pg.add_init_script(self.claude_stub(claude))
        return pg
    @staticmethod
    def claude_stub(spec):
        parts = []
        for k, v in spec.items():
            if v is None: parts.append(f"{json.dumps(k)}:null")
            elif k == "user": parts.append(f"{json.dumps(k)}:{{isOwner:async()=>{json.dumps(bool(v.get('isOwner')))},canEdit:async()=>{json.dumps(bool(v.get('canEdit', True)))}}}")
            elif isinstance(v, str): parts.append(f"{json.dumps(k)}:({v})")
            else: parts.append(f"{json.dumps(k)}:{json.dumps(v)}")
        return "window.__claudeStub={" + ",".join(parts) + "};window.__claudeCalls={};window.claude={use:async n=>{window.__claudeCalls[n]=(window.__claudeCalls[n]||0)+1;return (n in window.__claudeStub)?window.__claudeStub[n]:null}};"
    async def goto(self, pg, wait_ms=0):
        url = self.serve() + (pg._query or "")
        await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        if pg._fx is not None: await pg.evaluate(f"__FX.set({int(pg._fx)})")
        if wait_ms: await pg.wait_for_timeout(wait_ms)
        return url
    XITE_WASM = re.compile(r"WebAssembly\.instantiateStreaming|Refused to compile or instantiate WebAssembly|mikktspace")   # X_ITE's optional wasm (tangents) under a no-wasm CSP: excluded by the brief
    XITE_EVAL = re.compile(r"Refused to evaluate a string as JavaScript")   # X_ITE's woff2 font decoder under a no-eval profile (our own probe catches its EvalError): excluded there only
    def errors(self, pg): return [e for e in pg._errs if "Failed to fetch" not in e and not self.XITE_WASM.search(e) and not (self.csp in ("noeval", "nowasm") and self.XITE_EVAL.search(e))]
    async def wait(self, pg, expr, timeout=20000):
        """Poll a JS expression every 250 ms through page.evaluate until truthy (True) or the timeout (False).
        Not page.wait_for_function: its default rAF polling never evaluates the predicate while SwiftShader holds rAF in a shader compile
        (tens of seconds on a loaded box), and its interval polling compiles the predicate in the page, which a no-eval CSP refuses."""
        t0 = time.time(); self._last_wait_err = None
        while True:
            try:
                if await pg.evaluate(f"!!({expr})"): return True
            except Exception as e: self._last_wait_err = str(e)[:200]
            if (time.time() - t0) * 1000 > timeout: return False
            await asyncio.sleep(0.25)
    async def txt(self, pg, sel): return await pg.evaluate("s=>document.querySelector(s)?.innerText||''", sel)
    async def shot(self, pg, name, full=False):
        try: await pg.screenshot(path=os.path.join(self.shots, name), full_page=full)
        except Exception as e: print("screenshot failed", e)
    @staticmethod
    def run(main):
        asyncio.run(main())
    # ---- a corrupted copy of the build for refusal tests ----
    def corrupted_copy(self, part="drift", how="bytes"):
        """how="bytes": one base64 character of parts/<part>.txt changed (gzip decode fails → refused, 'decode failed');
        how="manifest": one hex digit of that part's sha256 in parts/manifest.json AND the inline MANIFEST changed (decode ok → 'hash mismatch')."""
        tmp = tempfile.mkdtemp(prefix="v4corrupt-")
        for f in os.listdir(self.build_dir):
            src = os.path.join(self.build_dir, f); dst = os.path.join(tmp, f)
            if f == "xite": os.symlink(src, dst)
            elif os.path.isdir(src): shutil.copytree(src, dst)
            else: shutil.copyfile(src, dst)
        if how == "bytes":
            p = os.path.join(tmp, "parts", part + ".txt"); s = open(p).read()
            i = s.find("A", 200); s = s[:i] + "B" + s[i + 1:]
            open(p, "w").write(s)
        else:
            man = json.load(open(os.path.join(tmp, "parts", "manifest.json"))); sha = man["parts"][part]["sha256"]
            bad = ("0" if sha[0] != "0" else "1") + sha[1:]
            for p in (os.path.join(tmp, "parts", "manifest.json"), os.path.join(tmp, "index.html")):
                s = open(p, encoding="utf-8").read(); assert sha in s, p; open(p, "w", encoding="utf-8").write(s.replace(sha, bad))
        return tmp
