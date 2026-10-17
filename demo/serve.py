"""Local rig for the demo: one origin (:8782) with a Content-Security-Policy that mimics the artifact viewer (own files only, no CDN).
Serves build/ (page test copies from tests/mktest.py, and build/xite/ from mkxite.py) plus /render.html and /render3.html for the render passes.
Run from demo/:  python3 serve.py   (CSP env overrides the policy; LOG404=1 prints missing files)."""
import http.server, socketserver, threading, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES = {"/render.html": os.path.join(HERE, "render/render.html"), "/render3.html": os.path.join(HERE, "render/render3.html")}
# own files only; the woff2 font decoder in X_ITE needs eval, mikktspace needs wasm
CSP = ("default-src 'none'; script-src 'unsafe-inline' 'self' 'wasm-unsafe-eval' 'unsafe-eval'; style-src 'unsafe-inline' 'self' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:")
class Page(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=os.path.join(HERE, "build"), **k)
    def translate_path(s, p): return ROUTES.get(p.split("?")[0]) or super().translate_path(p)
    def end_headers(s): s.send_header("Content-Security-Policy", os.environ.get("CSP", CSP)); super().end_headers()
    def log_message(s, fmt, *a):
        if os.environ.get("LOG404") and " 404 " in (fmt % a): print("404", s.path, flush=True)
if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 8782), Page); threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("up on :8782"); threading.Event().wait()
