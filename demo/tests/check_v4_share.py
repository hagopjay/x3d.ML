"""check_v4_share.py: leak gate for the SHARE build of Tether Firehose 4 (SPEC-v4 sections 13 and 15; WORKPLAN "Tests and ops").
Usage:  python3 demo/tests/check_v4_share.py [<share build dir>] [extra files or dirs...]
        default dir: $SHARE_DIR, else demo/build/v4.share, else build/v4.share (relative to the repo root, cwd-independent)
        extras: the release copy, e.g. demo/releases/tether-firehose-v4.html demo/releases/tether-firehose-v4.parts
What it asserts (every emitted file: page, parts/*.txt and jsval/**/*.txt gzip+base64 DECODED, workers, jsval text, manifest.json,
files.json, data/*.x3d, css/shaders, images byte-swept; xite/ skipped as in leak_sweep.py):
  1. `python3 demo/leak_sweep.py --share --root <dir> [extras]` ends with `RESULT: clean` (its output is echoed, indented, so the
     reason for a FAIL is on screen); the exit code must be 0.
  2. Independently of the sweep's rule set, over the same decoded texts:
       no `claude.ai/artifact`   (private artifact links; the publisher copy rows `{"artifact": "https://claude.ai/artifact/..."}`
                                 inside files.json are exempt: they are an instruction to the publisher, never a published byte)
       no `$` followed by a digit (cost strings; the exact JS back-reference `$1` is exempt, as in leak_sweep.py)
       no `chan_`                (sample-capability channel ids, any length)
       no env-block strings      (`"macos"`, `"loadavg_1m"`, `"ncpu"` keys of the physics ledger's step-1 env object; SPEC section 15)
  3. The page exists (`index.html`), is < 16 MB, and carries no `/*__` placeholder left by the build.
Exit codes: 0 all PASS; 1 any FAIL; 2 SKIP (the directory does not exist yet: run `python3 demo/v4/build_v4.py <dir> --share` first).
No browser is used; this is a file-level gate and runs anywhere. A DOM-text sweep of the served page belongs to check_v4.py.
"""
import os, re, sys, gzip, base64, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
SWEEP = os.path.join(REPO, "demo", "leak_sweep.py")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
root = args[0] if args else (os.environ.get("SHARE_DIR") or os.environ.get("V4_BUILD") or next((d for d in [os.path.join(REPO, "demo", "build", "v4.share"), os.path.join(REPO, "build", "v4.share")] if os.path.isdir(d)), os.path.join(REPO, "demo", "build", "v4.share")))
extras = args[1:]
if not os.path.isdir(root):
    print(f"SKIP check_v4_share: no share build at {root} (run: python3 demo/v4/build_v4.py {root} --share)"); sys.exit(2)
res = []
def ok(name, cond, detail=""):
    res.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name + ((" :: " + str(detail)[:300]) if detail != "" else ""), flush=True)

# 1. the sweep itself
cmd = [sys.executable, SWEEP, "--share", "--root", root] + extras
p = subprocess.run(cmd, capture_output=True, text=True)
out = (p.stdout + p.stderr).rstrip("\n")
print("$ " + " ".join(cmd)); print("\n".join("    " + l for l in out.splitlines()[-60:]) if out else "    (no output)")
last = out.splitlines()[-1] if out else ""
ok("leak_sweep --share --root ends with RESULT: clean", last.strip() == "RESULT: clean" and p.returncode == 0, f"exit {p.returncode}; last line: {last!r}")

# 2. independent walk
TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".json", ".jsonl", ".x3d", ".xml", ".xsd", ".css", ".txt", ".frag", ".vert", ".glsl", ".md", ".svg", ".csv", ".map"}
SKIP = {"xite", "__pycache__", "node_modules", ".git"}
def files_of(p):
    if os.path.isfile(p): return [p]
    out = []
    for d, dirs, fs in os.walk(p):
        dirs[:] = sorted(x for x in dirs if x not in SKIP); out += [os.path.join(d, f) for f in sorted(fs)]
    return out
def text_of(path):
    raw = open(path, "rb").read()
    if path.endswith(".txt"):
        body = raw.strip()
        if body and re.fullmatch(rb"[A-Za-z0-9+/=\s]+", body):
            try:
                dec = base64.b64decode(body + b"=" * (-len(body) % 4))
                if dec[:2] == b"\x1f\x8b": return gzip.decompress(dec).decode("utf-8", "replace")
            except Exception: pass
    return raw.decode("utf-8", "replace")
texts = {}
for f in files_of(root) + [x for e in extras for x in files_of(e)]:
    if os.path.splitext(f)[1].lower() in TEXT_EXT: texts[f] = text_of(f)
ok("emitted text files found", len(texts) > 0, f"{len(texts)} text files under {root}" + (f" + {len(extras)} extra path(s)" if extras else ""))
def find(pattern, exempt=None):
    hits = []
    for f, s in texts.items():
        t = re.sub(r"[A-Za-z0-9+/=]{120,}", "<b64>", s)
        if exempt: t = exempt(f, t)
        for m in re.finditer(pattern, t): hits.append(f"{os.path.relpath(f, root)}: ...{t[max(0, m.start()-30):m.end()+30].replace(chr(10), ' ')}...")
    return hits
def exempt_files_map(f, t): return re.sub(r'"artifact"\s*:\s*"https://claude\.ai/artifact/[A-Za-z0-9]+"', '"artifact":"<publisher copy>"', t) if os.path.basename(f) == "files.json" else t
h = find(r"claude\.ai/artifact", exempt_files_map); ok("no claude.ai/artifact in any emitted text (files.json publisher rows exempt)", not h, h[:3] or "0")
h = find(r"\$\s?[0-9]", lambda f, t: "" if "/jsval/vendor/" in f.replace(os.sep, "/") else t.replace("$1", "<bref>")); ok("no $ followed by a digit ($1 back-reference exempt; jsval/vendor third-party minified code exempt, as in leak_sweep.py)", not h, h[:3] or "0")
h = find(r"chan_"); ok("no chan_ anywhere", not h, h[:3] or "0")
h = find(r'"(macos|loadavg_1m|ncpu)"\s*:'); ok("no physics-ledger env block keys (macos, loadavg_1m, ncpu)", not h, h[:3] or "0")

# 3. the page
page = os.path.join(root, "index.html")
ok("index.html present", os.path.isfile(page), page)
if os.path.isfile(page):
    sz = os.path.getsize(page); s = texts.get(page) or text_of(page)
    ok("index.html < 16 MB", sz < 16 * 1024 * 1024, f"{sz:,} bytes")
    ok("no /*__ placeholder left in index.html", "/*__" not in s, s.count("/*__"))
# 4. the SAFE map took: BUILD.share, the map's sha, lane labels in place of every model id the private data names (ids read from the data, never typed here)
if os.path.isfile(page):
    s = texts.get(page) or text_of(page)
    ok("BUILD.share true and BUILD.safe_map_sha set", re.search(r'"share":true', s) and re.search(r'"safe_map_sha":"[0-9a-f]{64}"', s), "BUILD block")
    ids = []
    try:
        import json
        live = json.load(open(os.path.join(REPO, "demo", "data", "live.json"))); ids = [m["id"] for m in live["meta"]["models"]]
        if os.path.isfile(os.path.join(REPO, "demo", "data", "live2.json")): ids += [m["id"] for m in json.load(open(os.path.join(REPO, "demo", "data", "live2.json")))["meta"]["models"]]
        if os.path.isfile(os.path.join(REPO, "demo", "data", "replay.json")): ids += sorted({i["m"] for i in json.load(open(os.path.join(REPO, "demo", "data", "replay.json")))})
    except Exception as e: print("note: model ids not read from demo/data:", e)
    leaks = [(os.path.relpath(f, root), i) for f, t in texts.items() for i in ids if i in t or i.replace("/", "_") in t]
    ok(f"no private model id ({len(ids)} read from demo/data) in any emitted text", ids and not leaks, leaks[:4] or f"{len(ids)} ids checked")
    labels = sorted(set(re.findall(r"\blane-[A-Z]\b", s)))
    ok("lane labels stand where the page prints a model (STATS lanes, LM.models, hero keys)", len(labels) >= 5 and re.search(r'"id":"lane-A"', s) and re.search(r'"models":\[\{"id":"lane-A"', s), labels)
    parts_dir = os.path.join(root, "parts")
    pl = [n for n in ("live.core", "replay", "events", "renders.151") if os.path.isfile(os.path.join(parts_dir, n + ".txt")) and "lane-A" not in text_of(os.path.join(parts_dir, n + ".txt")) and "lane-F" not in text_of(os.path.join(parts_dir, n + ".txt"))]
    ok("lane labels inside the re-encoded parts (live.core, replay, events, renders.151)", not pl, pl or "all")
    ok("the id -> label map itself is not published (no lanes object keyed by a private id)", not any(re.search(r'"lanes":\{"[^"]*(?:gemini|qwen|nemotron|gpt-|glm|minimax)', t) for t in texts.values()))
n_fail = sum(1 for _, c in res if not c)
print(f"SUMMARY check_v4_share: {len(res) - n_fail} pass, {n_fail} fail ({root})")
sys.exit(1 if n_fail else 0)
