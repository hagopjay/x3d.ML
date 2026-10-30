#!/usr/bin/env python3
"""build_v4.py — bake Tether Firehose 4 (demo/v4/) into one page plus its own files (SPEC-v4 §12, ARCHITECTURE §1, §7).

Usage: python3 demo/v4/build_v4.py <out_dir> [--share] [--files-map] [--monolith] [--no-xite] [--modules=12-hero,14-morph]

Writes <out_dir>/index.html (template + css/*.css in order + js/*.js in order inside ONE <script>; every placeholder baked exactly once),
<out_dir>/parts/ (the gzip+base64 parts and manifest.json), <out_dir>/data/ (physics-ledger.x3d with the DOCTYPE stripped, rigok.json),
<out_dir>/jsval/ (x3dval.js, worker.js, vendor bundle, data/*.json and the five small XSDs; the two big XSDs are the parts xsd40/xsd41),
<out_dir>/workers/ (hash.worker.js = js/04-prov.js + workers/hash.shim.js; probe.js; probe.json; any other worker a wave-2 module adds),
<out_dir>/manifest.json, <out_dir>/hero.json, and, unless --no-xite, a local copy of demo/build/xite/ for testing (the publish copies xite/ server-side from v3).
--files-map writes <out_dir>/files.json for the Artifact publish: every local file under the out dir mapped to its path plus the 105 xite/* rows as
{"artifact": v3 url, "path": "xite/..."} copies (list from the Step 0 probe, scratchpad/probe_files.json, mirrored at demo/v4/data/xite_files.json).
--monolith inlines the parts into the page (var __PARTS) for file:// debugging. --share applies demo/v4/build/safe_map.py (model ids -> lane labels, providers, hardware, branches, people, vendor words) to every decoded part, data file and the baked page, re-encodes the parts (new sha256 in manifest.json), sets BUILD.share / safe_map_sha / lanes, and runs demo/leak_sweep.py --share on the output: the build exits 4 unless RESULT: clean.
Refuses on: a placeholder count != 1, a leftover /*__, `new Function` / `eval(` outside the two lines tagged /*@env-probe*/, `</script` or `<!--` inside the bundle,
a part whose sha256 differs from the manifest, files.json with != 105 xite rows or >= 511 entries, a page over 16 MB.
"""
import sys, os, re, json, gzip, base64, hashlib, shutil, subprocess, datetime, runpy
HERE = os.path.dirname(os.path.abspath(__file__))            # demo/v4
DEMO = os.path.dirname(HERE)                                  # demo
REPO = os.path.dirname(DEMO)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = {a.split("=",1)[0] for a in sys.argv[1:] if a.startswith("--")}
SHARE = "--share" in flags   # the SHARE build: demo/v4/build/safe_map.py applied to every decoded part, data file and the baked page; parts re-encoded; leak_sweep --share must end clean
sys.path.insert(0, os.path.join(HERE, "build"))
if not args:
    print(__doc__); sys.exit(1)
OUT = os.path.abspath(args[0]); os.makedirs(OUT, exist_ok=True)
V3_ARTIFACT = "https://claude.ai/artifact/S98mPP7PcEtR5kKWgSU2y7"
VERSIONS = [{"v": "v1", "id": "BqBVTHDK32xA32EZQEfvni", "title": "synthetic only"},
            {"v": "v2", "id": "PuMcK4xbf6uPZ7LrtYsUrV", "title": "replay of 174 real runs"},
            {"v": "v3", "id": "S98mPP7PcEtR5kKWgSU2y7", "title": "the recorded live run, 17 Oct"},
            {"v": "v4", "id": None, "this": True, "title": "Tether Firehose 4: the stage, the loop, the record"},
            {"v": "v5", "id": None, "title": "planned: 3D spectacle"}]
js_escape = lambda s: s.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
J = lambda o: js_escape(json.dumps(o, separators=(",", ":"), ensure_ascii=False))
def read(p): return open(p, encoding="utf-8").read()
def sha256(b): return hashlib.sha256(b).hexdigest()

# ---------- inputs ----------
tpl = read(os.path.join(HERE, "template.html"))
css_files = sorted(f for f in os.listdir(os.path.join(HERE, "css")) if f.endswith(".css"))
js_files = sorted(f for f in os.listdir(os.path.join(HERE, "js")) if f.endswith(".js"))
# --modules a,b,c (or env V4_MODULES): build the wave-1 core plus only the named modules, so parallel module agents
# never pick up each other's half-written files. A token matches a css/js file when it is a substring of the file name.
WAVE1_CSS = {"00-tokens.css", "10-base.css", "40-panels.css"}
WAVE1_JS = {"00-util.js", "01-loop.js", "02-claims.js", "03-data.js", "04-prov.js", "05-val.js", "06-env.js", "07-tier.js",
            "08-stage.js", "10-curtain-mast.js", "20-sim.js", "46-footer.js", "99-boot.js"}
_mods = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--modules=")), os.environ.get("V4_MODULES"))
if _mods is not None:
    toks = [t for t in _mods.split(",") if t]
    keep = lambda f, core: f in core or any(t in f for t in toks)
    css_files = [f for f in css_files if keep(f, WAVE1_CSS)]
    js_files = [f for f in js_files if keep(f, WAVE1_JS)]
    print(f"modules filter {toks}: css {css_files} js {js_files}")
css = "\n".join(f"/* ===== css/{f} ===== */\n" + read(os.path.join(HERE, "css", f)) for f in css_files)
js = "\n".join(f"/* ===== js/{f} ===== */\n" + read(os.path.join(HERE, "js", f)) for f in js_files)
shaders = {}
if os.path.isdir(os.path.join(HERE, "shaders")):
    for f in sorted(os.listdir(os.path.join(HERE, "shaders"))):
        shaders[f] = read(os.path.join(HERE, "shaders", f))
if shaders:
    js = "var SHADERS=" + J(shaders) + ";\n" + js
stats = json.load(open(os.path.join(HERE, "data", "stats.json")))
hero = json.load(open(os.path.join(HERE, "data", "hero.json")))
manifest = json.load(open(os.path.join(HERE, "parts", "manifest.json")))
prompts = [json.loads(l) for l in open(os.path.join(DEMO, "live", "prompts_live.jsonl"), encoding="utf-8") if l.strip()]
sysmod = runpy.run_path(os.path.join(DEMO, "live", "prompts_sys.py"))
SYS = {k: sysmod[k] for k in ("SYSTEM", "REPAIR", "REPAIR_AUTOFIX") if k in sysmod}
xcss = read(os.path.join(DEMO, "data", "x_ite.css")).replace("url(assets/", "url(xite/assets/")
try:
    LM = json.load(open(os.path.join(DEMO, "data", "live.json")))["meta"]
except Exception:
    LM = stats["meta"]
assert LM["t_total"] == stats["meta"]["t_total"] and [m["id"] for m in LM["models"]] == [m["id"] for m in stats["meta"]["models"]], "live.json meta and stats.json meta disagree"

# ---------- parts: decode, check, copy ----------
parts_out = os.path.join(OUT, "parts"); os.makedirs(parts_out, exist_ok=True)
decoded = {}
for name, p in manifest["parts"].items():
    src = os.path.join(HERE, "parts", name + ".txt")
    b64 = open(src, "rb").read()
    raw = gzip.decompress(base64.b64decode(b64))
    assert sha256(raw) == p["sha256"], f"part {name}: decoded sha256 differs from the manifest"
    assert len(raw) == p["bytes_raw"] and len(b64) == p["bytes_b64"], f"part {name}: sizes differ from the manifest"
    decoded[name] = raw
    if not SHARE: shutil.copyfile(src, os.path.join(parts_out, name + ".txt"))
SM = None
if SHARE:
    import safe_map
    ids = [m["id"] for m in json.load(open(os.path.join(DEMO, "data", "live.json")))["meta"]["models"]]
    ids += list(dict.fromkeys(i["m"] for i in json.loads(decoded["replay"])))
    if "run24" in decoded: ids += [m["id"] for m in json.loads(decoded["run24"])["meta"]["models"]]
    SM = safe_map.SafeMap(list(dict.fromkeys(ids)))
    for name in list(manifest["parts"]):
        if name.startswith("xsd"): shutil.copyfile(os.path.join(HERE, "parts", name + ".txt"), os.path.join(parts_out, name + ".txt")); continue
        text = SM.apply(decoded[name].decode("utf-8")); raw = text.encode("utf-8"); decoded[name] = raw
        gz = gzip.compress(raw, 9, mtime=0); b64 = base64.b64encode(gz) + b"\n"
        open(os.path.join(parts_out, name + ".txt"), "wb").write(b64)
        manifest["parts"][name].update({"bytes_raw": len(raw), "bytes_gz": len(gz), "bytes_b64": len(b64), "sha256": sha256(raw), "share": True})
    manifest["share"] = {"safe_map_sha": SM.sha(), "lanes": sorted(SM.lanes.values())}   # the id -> label map itself is never published
    json.dump(manifest, open(os.path.join(parts_out, "manifest.json"), "w"), separators=(",", ":"))
    shutil.copyfile(os.path.join(parts_out, "manifest.json"), os.path.join(OUT, "manifest.json"))
    open(os.path.join(OUT, "hero.json"), "w", encoding="utf-8").write(SM.apply(read(os.path.join(HERE, "data", "hero.json"))))
else:
    shutil.copyfile(os.path.join(HERE, "parts", "manifest.json"), os.path.join(parts_out, "manifest.json"))
    shutil.copyfile(os.path.join(HERE, "parts", "manifest.json"), os.path.join(OUT, "manifest.json"))
    shutil.copyfile(os.path.join(HERE, "data", "hero.json"), os.path.join(OUT, "hero.json"))

# DRIFTSUM: per-commit counts from the drift part (decoded; nothing retyped)
drift = json.loads(decoded["drift"])
commits = []
prev = None
for ref, verd in drift["by_commit"].items():
    n = len(verd); valid = sum(1 for v in verd.values() if v.get("valid"))
    flips = sum(1 for k, v in verd.items() if prev and prev.get(k, {}).get("valid") and not v.get("valid")) if prev else 0
    commits.append({"ref": ref, "n": n, "valid": valid, "flips_from_prev": flips}); prev = verd
DRIFTSUM = {"commits": commits, "v8dd0d3e": {"n": drift["v8dd0d3e"]["n"], "tree": drift["v8dd0d3e"]["tree"],
            "valid": sum(1 for v in drift["v8dd0d3e"]["verdicts"].values() if v.get("valid"))},
            "drifted": len(drift.get("attribution", {}).get("drifted", [])), "rule": "valid = recorded valid flag per commit over the 174 replay bodies; flips_from_prev = valid on the previous commit and invalid on this one"}

# LADDER_ROWS: the cross-dataset strip (SPEC S14), quoted not re-measured; links only on the private build (none known to this build: owner to supply)
LADDER_ROWS = [
    {"id": "firehose-live", "name": "Firehose live 17 Oct", "commits": ["eb4b4b4"], "xite": "16.5.0 / 16.5.1", "headline": "20 → 98 · 57 → 100 · 77 → 100 % valid, three paid lanes; 7 of 178 valid finals blank", "grade": "C", "here": True, "link": None},
    {"id": "replay-11oct", "name": "Replay 11 Oct", "commits": ["svc@11Oct", "8c0a457", "eb4b4b4"], "xite": "16.5.0", "headline": "91 valid on the service, 55 on 8c0a457, 54 on eb4b4b4; 17 of 91 blank", "grade": "C", "here": True, "link": None},
    {"id": "flywheel", "name": "Flywheel", "commits": ["d5598c4", "acdf5c4"], "xite": "16.5.1", "headline": "4 of 16 Geo-wrap", "grade": "S", "here": False, "link": None},
    {"id": "dspy", "name": "DSPy", "commits": ["d5598c4"], "xite": None, "headline": "34.4 → 63.9 %", "grade": "S", "here": False, "link": None},
    {"id": "y8", "name": "Y8", "commits": ["688174f", "74da0ec"], "xite": None, "headline": "64.5 % nothing missing", "grade": "S", "here": False, "link": None},
    {"id": "e2", "name": "E2 mutation recall", "commits": ["688174f"], "xite": None, "headline": "82.3 → 98.3 %", "grade": "S", "here": False, "link": None},
    {"id": "judge", "name": "Judge bench", "commits": ["74da0ec"], "xite": None, "headline": "97 % → 61 %", "grade": "S", "here": False, "link": None},
    {"id": "splat", "name": "Splat Park", "commits": ["688174f", "74da0ec"], "xite": "16.5.1", "headline": "0 / 13 → 11 / 13", "grade": "S", "here": False, "link": None},
    {"id": "playground", "name": "Playground", "commits": ["020221e"], "xite": "16.4.3", "headline": "free workbench and judge arena", "grade": "S", "here": False, "link": None}]

# BUILD
try:
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", "--short=10", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
except Exception:
    sha = "unknown"
BUILD = {"sha": sha, "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "share": SHARE,
         "safe_map_sha": SM.sha() if SM else None, "lanes": sorted(SM.lanes.values()) if SM else None,
         "validator_recorded": manifest.get("validator_recorded", ["fork@eb4b4b4", "fork@8dd0d3e"]), "port": "js-port-of-8dd0d3e", "xite": "16.5.0", "passes": ["16.5.0", "16.5.1"],
         "HAS_CYCLES": bool(manifest.get("HAS_CYCLES")), "HAS_RUN2": bool(manifest.get("HAS_RUN2")), "has_cycles": bool(manifest.get("HAS_CYCLES")), "has_run24": bool(manifest.get("HAS_RUN2")), "staged": os.path.isfile(os.path.join(HERE, "data", "staged.json")),
         "versions": [dict(v, id=None) for v in VERSIONS] if SHARE else VERSIONS, "title": "Tether Firehose 4", "monolith": "--monolith" in flags, "parts": len(manifest["parts"]), "canary": manifest.get("canary")}

# ---------- bake ----------
PH = {"/*__CSS__*/": css, "/*__JS__*/": js, "/*__STATS__*/null": J(stats), "/*__HERO__*/null": J(hero), "/*__PROMPTS__*/null": J(prompts), "/*__SYS__*/null": J(SYS),
      "/*__XCSS__*/null": J(xcss), "/*__LM__*/null": J(LM), "/*__DRIFTSUM__*/null": J(DRIFTSUM), "/*__LADDER__*/null": J(LADDER_ROWS), "/*__MANIFEST__*/null": J(manifest), "/*__BUILD__*/null": J(BUILD)}
for ph in PH:
    assert tpl.count(ph) == 1, f"placeholder {ph} occurs {tpl.count(ph)} times in template.html (must be exactly once)"
assert "</script" not in js.lower() and "<!--" not in js, "the JS bundle must not contain </script or <!-- (it is inlined in one <script>)"
out = tpl
for ph, val in PH.items():
    out = out.replace(ph, val)
if "--monolith" in flags:
    inline = {n: open(os.path.join(HERE, "parts", n + ".txt"), encoding="ascii").read().strip() for n in manifest["parts"]}
    out = out.replace("<script>\n\"use strict\";", "<script>\n\"use strict\";\nvar __PARTS=" + J(inline) + ";", 1)
assert "/*__" not in out, "a placeholder survived the bake"
if SM: out = SM.apply(out)   # the SHARE map over the whole baked page: data, prose and the bundle's provider compares alike

# ---------- eval / new Function grep (bundle, workers, jsval), comments stripped, env-probe lines allowed ----------
def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", lambda m: "" if "@env-probe" not in m.group(0) else "/*@env-probe*/", s, flags=re.S)
    return re.sub(r"(^|[\s;{}(,=])//[^\n]*", r"\1", s)
EVAL_RE = re.compile(r"new\s+Function\b|(?<![A-Za-z0-9_.$])eval\(")
METHOD_DEF_RE = re.compile(r"^\s*(?:async\s+)?eval\([^()]*\)\s*\{")   # a class method *named* eval (libxml2-wasm's XPath eval), not a call of the global
def grep_eval(label, text):
    hits, allowed = [], 0
    for i, line in enumerate(strip_comments(text).split("\n"), 1):
        if EVAL_RE.search(line) and not METHOD_DEF_RE.match(line):
            if "/*@env-probe*/" in line: allowed += 1
            else: hits.append(f"{label}:{i}: {line.strip()[:120]}")
    return hits, allowed
workers_src = os.path.join(HERE, "workers")
hash_worker = read(os.path.join(HERE, "js", "04-prov.js")) + "\n" + read(os.path.join(workers_src, "hash.shim.js"))
worker_files = {"hash.worker.js": hash_worker, "probe.js": read(os.path.join(workers_src, "probe.js"))}
for f in sorted(os.listdir(workers_src)):
    if f.endswith(".js") and f not in ("hash.shim.js", "probe.js", "hash.worker.js"):
        worker_files[f] = read(os.path.join(workers_src, f))
jsval_src = os.path.join(DEMO, "jsval")
jsval_files = {"x3dval.js": os.path.join(jsval_src, "x3dval.js"), "worker.js": os.path.join(jsval_src, "worker.js"), "vendor/libxml2-wasm.bundle.mjs": os.path.join(jsval_src, "vendor", "libxml2-wasm.bundle.mjs"),
               "data/uom-4.1.json": os.path.join(jsval_src, "data", "uom-4.1.json"), "data/nodes-4.0.json": os.path.join(jsval_src, "data", "nodes-4.0.json"), "data/nodes-4.1.json": os.path.join(jsval_src, "data", "nodes-4.1.json")}
for f in sorted(os.listdir(os.path.join(jsval_src, "data", "schemas"))):
    p = os.path.join(jsval_src, "data", "schemas", f)
    if f.endswith(".xsd") and os.path.getsize(p) < 32768:      # the five small ones; x3d-4.0.xsd and x3d-4.1.xsd are the parts xsd40 / xsd41
        jsval_files["data/schemas/" + f] = p
if os.path.exists(os.path.join(jsval_src, "VERSION")): jsval_files["VERSION"] = os.path.join(jsval_src, "VERSION")
hits, allowed = grep_eval("bundle", js)
for name, text in worker_files.items():
    h, a = grep_eval("workers/" + name, text); hits += h; allowed += a
for name, path in jsval_files.items():
    if name.endswith((".js", ".mjs")):
        h, a = grep_eval("jsval/" + name, read(path)); hits += h
if hits:
    print("REFUSED: eval / new Function outside the tagged env probes:\n  " + "\n  ".join(hits), file=sys.stderr); sys.exit(3)
assert allowed == 2, f"expected exactly 2 /*@env-probe*/ lines (06-env.js, workers/probe.js), found {allowed}"
n_si = len(re.findall(r"setInterval\(", strip_comments(js)))
assert n_si == 0, f"setInterval( appears {n_si} times in the bundle (rule 8: one rAF loop)"
# share-sweep preview (wave 3 gate, information only here): "$" followed by a digit anywhere in the bundle or a worker fails the share rule;
# wave-2 code must not use $2+ back-references in replacement strings (use a function replacer). Reported, never refused, in wave 1.
dollar_hits = {f: len(re.findall(r"\$[0-9]", read(os.path.join(HERE, "js", f)))) for f in js_files}
dollar_hits = {f: n for f, n in dollar_hits.items() if n}

# ---------- write ----------
index = os.path.join(OUT, "index.html")
open(index, "w", encoding="utf-8").write(out)
os.makedirs(os.path.join(OUT, "workers"), exist_ok=True)
for name, text in worker_files.items():
    open(os.path.join(OUT, "workers", name), "w", encoding="utf-8").write(SM.apply(text) if SM else text)
open(os.path.join(OUT, "workers", "probe.json"), "w").write('{"ok":true,"name":"probe.json"}\n')
for name, path in jsval_files.items():
    dst = os.path.join(OUT, "jsval", name); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(path, dst)
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
ledger = read(os.path.join(REPO, "runs", "suite-physics-2026-10-17", "physics-stress.ledger.x3d"))
ledger = re.sub(r"<!DOCTYPE[^>]*>\s*", "", ledger, count=1)
open(os.path.join(OUT, "data", "physics-ledger.x3d"), "w", encoding="utf-8").write(SM.apply(ledger) if SM else ledger)
STAGED_SRC = os.path.join(HERE, "data", "staged.json"); HAS_STAGED = os.path.isfile(STAGED_SRC)
for src, dst in [(os.path.join(HERE, "data", "rigok.json"), "rigok.json")] + ([(STAGED_SRC, "staged.json")] if HAS_STAGED else []):
    if SM: open(os.path.join(OUT, "data", dst), "w", encoding="utf-8").write(SM.apply(read(src)))
    else: shutil.copyfile(src, os.path.join(OUT, "data", dst))   # 40-sheet fetches data/staged.json when BUILD.staged (urls null until the assets are uploaded)
if "--no-xite" not in flags:
    xsrc = os.path.join(DEMO, "build", "xite")
    if os.path.isdir(xsrc):
        if os.path.isdir(os.path.join(OUT, "xite")): shutil.rmtree(os.path.join(OUT, "xite"))
        shutil.copytree(xsrc, os.path.join(OUT, "xite"))
    else:
        print("note: demo/build/xite missing (run demo/mkxite.py); the local page will have no X_ITE", file=sys.stderr)

# ---------- files map ----------
if "--files-map" in flags:
    xf = None
    for cand in (os.path.join(HERE, "data", "xite_files.json"), "/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad/probe_files.json"):
        if os.path.exists(cand):
            xf = json.load(open(cand)); break
    assert xf, "no xite file list (demo/v4/data/xite_files.json)"
    xrows = {k: v for k, v in xf.items() if k.startswith("xite/") and isinstance(v, dict) and v.get("artifact")}
    assert len(xrows) == 105, f"expected 105 xite rows, found {len(xrows)}"
    if not os.path.exists(os.path.join(HERE, "data", "xite_files.json")):
        json.dump(xrows, open(os.path.join(HERE, "data", "xite_files.json"), "w"), indent=0)
    fmap = {}
    for root, dirs, files in os.walk(OUT):
        dirs[:] = [d for d in dirs if d != "xite"]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), OUT).replace(os.sep, "/")
            if rel in ("index.html", "files.json"): continue
            fmap[rel] = rel
    fmap.update(xrows)
    assert len(fmap) < 511, f"{len(fmap)} files: over the 511 cap"
    json.dump(fmap, open(os.path.join(OUT, "files.json"), "w"), indent=0)

# ---------- report ----------
size = os.path.getsize(index)
assert size <= 16 * 1024 * 1024, "index.html over the 16 MB cap"
local = [(os.path.relpath(os.path.join(r, f), OUT), os.path.getsize(os.path.join(r, f))) for r, d, fs in os.walk(OUT) for f in fs]
own = [(p, s) for p, s in local if not p.startswith("xite" + os.sep) and p != "files.json"]
xite = [(p, s) for p, s in local if p.startswith("xite" + os.sep)]
big = max(own, key=lambda x: x[1])
print(f"{index}: {size:,} B ({size/1048576:.2f} MB of the 16 MB cap)")
print(f"own files: {len(own)} ({sum(s for _, s in own):,} B); largest {big[0]} {big[1]:,} B; parts {len(manifest['parts'])} ({sum(p['bytes_b64'] for p in manifest['parts'].values()):,} B published)")
print(f"xite: {len(xite)} local files ({sum(s for _, s in xite):,} B){' (copied locally for tests; published as server-side copies from v3)' if xite else ''}")
if "--files-map" in flags:
    print(f"files.json: {len(fmap)} entries ({len(xrows)} xite copies + {len(fmap)-len(xrows)} local) of 511; version bytes ≈ {(size + sum(s for _, s in own) + 8482051)/1048576:.1f} MB of 256")
print(f"css {len(css_files)} files {len(css):,} B · js {len(js_files)} files {len(js):,} B · BUILD.sha {sha} · env-probe lines {allowed} · setInterval 0 · $digit in js {dollar_hits or 0} (share sweep, wave 3)")

# ---------- SHARE gate: the sweep runs on the output; anything left fails the build ----------
if SM:
    p = subprocess.run([sys.executable, os.path.join(DEMO, "leak_sweep.py"), "--share", "--root", OUT], capture_output=True, text=True)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    print("share: SAFE map " + SM.sha()[:12] + " · " + str(len(SM.lanes)) + " lanes (the id map stays local: " + os.path.join(OUT + ".safe_map.json") + ") · replacements " + json.dumps(SM.counts))
    json.dump({"safe_map_sha": SM.sha(), "lanes": SM.lanes, "providers": SM.providers, "counts": SM.counts}, open(OUT + ".safe_map.json", "w"), indent=1)   # beside the build dir, never inside it
    print("share sweep: " + last)
    if p.returncode != 0 or last != "RESULT: clean":
        print(p.stdout[-6000:], file=sys.stderr); print("REFUSED: the share sweep is not clean", file=sys.stderr); sys.exit(4)
