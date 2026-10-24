"""Local rig for the demo: one origin with a Content-Security-Policy that mimics the artifact viewer (own files only, no CDN).
Default (v3 behaviour, unchanged): :8782, serves build/ (page test copies from tests/mktest.py, build/xite/ from mkxite.py)
plus /render.html and /render3.html for the render passes.  Run from demo/:  python3 serve.py

v4 flags (all optional):
  --root <dir>      directory to serve (default demo/build; relative paths resolve against the cwd, e.g. --root build/v4)
  --port <n>        default 8782
  --csp <profile>   viewer | eval | noeval | nowasm | noworker   (default viewer; env CSP, when set and --csp is not, overrides it as before)
Profiles (SPEC-v4 section 9 / 13):
  viewer    today's policy: script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' 'unsafe-eval'; worker-src 'self' blob:
            NOTE today's rig policy DOES carry 'unsafe-eval' (X_ITE's woff2 font decoder needs it). Whether the real
            artifact viewer grants 'unsafe-eval' is UNKNOWN until the Step 0 probe (SPEC section 9) reports; this file
            records the rig's assumption, not a measurement. (demo/tests/v4fixture.py names this same policy "eval" and its
            own "viewer" is the no-eval one; `eval` is accepted here as an alias so both vocabularies work.)
  noeval    viewer minus 'unsafe-eval'            (Text fonts do not draw; nothing else on the page may need eval)
  nowasm    viewer minus 'wasm-unsafe-eval'       (libxml2 port cannot instantiate: VAL.mode none/semantic-only)
  noworker  viewer with worker-src 'none'         (page falls back to main-thread slices)
MIME: .txt text/plain (gzip+base64 parts), .js/.mjs text/javascript, .x3d application/xml, .wasm application/wasm,
      .webp image/webp, .woff2 font/woff2, .json application/json, .frag text/plain.
LOG404=1 prints missing files.  Check the policy with:  curl -sI localhost:<port>/ | grep -i content-security-policy"""
import http.server, socketserver, threading, os, sys, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES = {"/render.html": os.path.join(HERE, "render/render.html"), "/render3.html": os.path.join(HERE, "render/render3.html")}
# own files only; the woff2 font decoder in X_ITE needs eval, mikktspace and the libxml2 port need wasm, the hash/val/diff workers need worker-src
CSP = ("default-src 'none'; script-src 'unsafe-inline' 'self' 'wasm-unsafe-eval' 'unsafe-eval'; style-src 'unsafe-inline' 'self' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:")
PROFILES = {
    "viewer":   CSP,
    "eval":     CSP,                                   # alias: demo/tests/v4fixture.py calls the with-'unsafe-eval' policy "eval"
    "noeval":   CSP.replace(" 'unsafe-eval'", ""),
    "nowasm":   CSP.replace(" 'wasm-unsafe-eval'", ""),
    "noworker": CSP.replace("worker-src 'self' blob:", "worker-src 'none'"),
}
assert PROFILES["noeval"] != CSP and PROFILES["nowasm"] != CSP and PROFILES["noworker"] != CSP
MIME = {".txt": "text/plain", ".js": "text/javascript", ".mjs": "text/javascript", ".x3d": "application/xml", ".wasm": "application/wasm",
        ".webp": "image/webp", ".woff2": "font/woff2", ".json": "application/json", ".frag": "text/plain", ".html": "text/html", ".css": "text/css",
        ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".map": "application/json", ".md": "text/plain"}
class Page(http.server.SimpleHTTPRequestHandler):
    root = os.path.join(HERE, "build"); policy = None
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **MIME}
    def __init__(s, *a, **k): super().__init__(*a, directory=s.root, **k)
    def translate_path(s, p): return ROUTES.get(p.split("?")[0]) or super().translate_path(p)
    def end_headers(s): s.send_header("Content-Security-Policy", s.policy if s.policy is not None else os.environ.get("CSP", CSP)); super().end_headers()
    def log_message(s, fmt, *a):
        if os.environ.get("LOG404") and " 404 " in (fmt % a): print("404", s.path, flush=True)
def serve(root=None, port=8782, csp=None, block=True):
    """csp: a profile name, a raw policy string (anything with a ';'), or None (env CSP, else viewer)."""
    Page.root = os.path.abspath(root) if root else os.path.join(HERE, "build")
    Page.policy = PROFILES[csp] if csp in PROFILES else csp
    if not os.path.isdir(Page.root): sys.exit(f"serve.py: root is not a directory: {Page.root}")
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), Page); threading.Thread(target=srv.serve_forever, daemon=True).start()
    label = csp if csp in PROFILES else ("env CSP" if Page.policy is None and os.environ.get("CSP") else ("custom" if csp else "viewer"))
    print(f"up on :{port}  root={Page.root}  csp={label}", flush=True)
    if block: threading.Event().wait()
    return srv
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="directory to serve (default demo/build)")
    ap.add_argument("--port", type=int, default=8782)
    ap.add_argument("--csp", default=None, help="viewer | noeval | nowasm | noworker (default: env CSP if set, else viewer)")
    a = ap.parse_args()
    if a.csp is not None and a.csp not in PROFILES and ";" not in a.csp: ap.error(f"--csp must be one of {', '.join(PROFILES)} (or a raw policy string)")
    serve(a.root, a.port, a.csp)
