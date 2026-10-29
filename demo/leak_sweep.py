"""Leak sweep for a baked Tether Firehose page or a whole v4 build directory.
Usage:  python3 leak_sweep.py <page.html> [--share]                      single file (v3 mode, output unchanged)
        python3 leak_sweep.py [--share] --root <build dir> [extra paths...]   v4 build sweep (SPEC-v4 section 15 scope)
Private build: reports what the source carries (open model names, run cost, hardware string are expected there).
--share: zero tolerance for model/vendor names, run costs, hardware strings, GCP ids, private links, keys, emails, image stamps,
         plus the v4 rules: OS/hardware strings (Apple M*, macOS, darwin, loadavg, arm64, x86_64, /Users/), provider endpoints and
         function ids, more vendor names (minimax, stepfun, moonshot, kimi, deepseek, poolside, z-ai, glm), branch names
         (feat/ fix/ perf/ claude/), people and machines, sample channel ids (chan_...), credit/quota strings, sample capability fields.
--root <dir>: walks every emitted file: the page(s), parts/*.txt and jsval/**/*.txt (gzip+base64 DECODED first; a .txt that does not
         decode is swept as plain text), workers/*.js, jsval/*.js and *.mjs, manifest.json, files.json, data/*.x3d, css/shaders, plus any
         extra files or directories given after the root (e.g. the release copy demo/releases/tether-firehose-v4.html and its .parts/).
         Image files (.webp .png .jpg) and other binaries are byte-swept for stamp markers. xite/ is skipped (third-party renderer,
         served from the v3 artifact's own copy). In files.json the publisher copy rows {"artifact":"https://claude.ai/artifact/..."} are
         allowed (they are an instruction to the publisher, never a published byte) and their count is printed on the file's line.
         One summary line per file (findings listed under it), then RESULT. The new v4 rules also print as notes in private --root mode.
Env LEAK_IDS adds the private project id, run-as name and project number to the GCP check (set it locally, never commit the values).
Exit code 1 when a --share sweep finds anything (or the root is missing / empty). Decoded thumbnails are byte-swept as well."""
import os, re, sys, base64, json, gzip
ARGS = sys.argv[1:]; SHARE = "--share" in ARGS
ROOT = ARGS[ARGS.index("--root") + 1] if "--root" in ARGS and ARGS.index("--root") + 1 < len(ARGS) else None
POS = [a for i, a in enumerate(ARGS) if not a.startswith("--") and not (i > 0 and ARGS[i - 1] == "--root")]
STAMP = rb"(?i)anthropic|claude|c2pa|cabx|jumb|openai|google|gemini"
ALLOW = [r'claude:viewport-fit-sides',                    # artifact page contract meta (not visible)
         r'(?:window|self|globalThis)\.claude\b', r'\bclaude\.use\b', r'"claude" in (?:window|self)', r'\bclaude\.(?:sample|files|user|downloads|assets)\b',   # the artifact runtime API (claude.use), not a vendor mention
         r'https://fonts\.(googleapis|gstatic)\.com',     # the one allowed stylesheet host
         r'cdn\.jsdelivr\.net/npm/x_ite@16\.4\.1',        # pinned renderer (v3)
         r'cdn\.jsdelivr\.net/npm/x_ite@16\.5\.[01]',     # pinned renderer (v4: 16.5.0 runtime, 16.5.1 as data)
         r'libxml2', r'x3d_mcp', r'X_ITE', r'x3d-blender-io', r'Blender']   # SPEC-v4 section 15 allowlist (public tools)
CHECKS = [
 ("closed model / vendor names", r"(?i)\banthropic\b|\bclaude\b|\bopus\b|\bsonnet\b|\bhaiku\b|\bfable\b|gemini|openai|chatgpt|\bgpt-?\d|\bkimi\b|nemotron|vertex ai|aiplatform|deepmind|mistral|\bllama\b|\bgoogle\b|\bglm\b|z-ai|zhipu|gemma|deepseek"),
 ("open model names", r"(?i)qwen|gpt-oss|alibaba"),
 ("hardware / region strings", r"(?i)g2-standard|NVIDIA|us-central1|us-east1"),
 ("GCP ids and hosts", r"(?i)" + (os.environ["LEAK_IDS"] + "|" if os.environ.get("LEAK_IDS") else "") + r"gserviceaccount|projects/[a-z0-9-]{6,}|\bgs://|\.run\.app|nip\.io|storage\.googleapis"),   # LEAK_IDS='<project id>|<run-as name>|<project number>' (kept out of the repo)
 ("dollar amounts", r"\$\s?[0-9]"),
 ("non-zero run cost in data", r'"rc":(?!0[,}])[0-9.]+'),
 ("private links / people", r"(?i)claude\.ai|/artifact/|hagopjay|x3d\.ML|bigquery|\bpolys\b|\bnick(olas)?\b"),
 ("emails", r"[\w.+-]+@[A-Za-z][\w-]*\.(com|org|net|edu|io)\b"),
 ("keys", r"(?i)AIza[0-9A-Za-z_-]{20,}|\bsk-[A-Za-z0-9]{16,}|bearer\s+[a-z0-9._-]{16,}|BEGIN (RSA |EC )?PRIVATE"),
 ("image stamps in decoded thumbnails", None),
]
# v4 share rules (SPEC-v4 section 15); applied under --share, and shown as notes in private --root mode
V4_CHECKS = [
 ("OS / hardware strings", r"(?i)apple m\d|macos|darwin|loadavg|arm64|x86_64|/Users/"),
 ("provider endpoints / function ids", r"(?i)integrate\.api\.nvidia\.com|Function '[0-9a-f]{8}-"),
 ("more model / vendor names", r"(?i)minimax|stepfun|moonshot|\bkimi\b|deepseek|poolside|z-ai|\bglm\b"),
 ("branch names", r"(?i)\b(feat|fix|perf|claude)/[a-z0-9-]+"),
 ("people / machines", r"(?i)hagsmac|zenodelic|hagopjay"),
 ("sample channel ids", r"chan_[A-Za-z0-9]{10,}"),
 ("credit / quota strings", r"insufficient_quota|credit_balance"),
 ("sample capability fields", r"(?i)modelApplied|modelTierApplied"),
]
B64 = r"[A-Za-z0-9+/=]{100,}"
def b64dec(x): return base64.b64decode(x + "=" * (-len(x) % 4))
def is_image(raw): return raw[:2] == b"\xff\xd8" or raw[:4] == b"\x89PNG" or (raw[:4] == b"RIFF" and raw[8:12] == b"WEBP") or raw[:4] == b"GIF8"
def scan(s, checks, img_mode, extra_allow=()):
    """Sweep one text. img_mode 'page': v3 rule, decoded '"jpg":"<b64>"' thumbnails; 'any': every long base64 run that decodes to an image.
    Returns (n_img, img_hits, rows) with rows = [(name, hits, kinds)]; hits are (match, context) tuples or strings."""
    img_hits = 0; n_img = 0
    if img_mode == "page":
        for m in re.finditer(r'"jpg":"(' + B64 + r')"', s):
            n_img += 1
            if re.search(STAMP, b64dec(m.group(1))): img_hits += 1
    else:
        for m in re.finditer(B64, s):
            try: raw = b64dec(m.group(0))
            except Exception: continue
            if is_image(raw):
                n_img += 1
                if re.search(STAMP, raw): img_hits += 1
    t = re.sub(r"[A-Za-z0-9+/=]{120,}", "<b64>", s)          # drop long base64 runs so they cannot cause false word hits
    for a in list(ALLOW) + list(extra_allow): t = re.sub(a, "<allowed>", t)
    rows = []
    for name, p in checks:
        if p is None: hits = [f"{img_hits} of {n_img} decoded thumbnails carry a stamp-like marker"] if img_hits else []
        else: hits = [(m.group(0), t[max(0, m.start()-40):m.end()+50].replace("\n", " ")) for m in re.finditer(p, t)]
        # expected, harmless matches
        hits = [h for h in hits if not (isinstance(h, tuple) and (h[0] == "$1" or "$1" in h[1] and "hidden" in h[1]))]
        kinds = {}
        for h in hits: kinds.setdefault(h[0].lower() if isinstance(h, tuple) else h, []).append(h)
        rows.append((name, hits, kinds))
    return n_img, img_hits, rows
def kinds_str(kinds): return "; ".join(f"{k!r} x{len(v)}" for k, v in sorted(kinds.items(), key=lambda x: -len(x[1]))[:6])
def examples(kinds, indent="        "):
    for k, v in list(kinds.items())[:4]: print(indent + "e.g.", v[0][1] if isinstance(v[0], tuple) else v[0])

if ROOT is None:
    # ---- single-file mode (v3): output format unchanged ----
    path = POS[0]
    s = open(path, encoding="utf-8").read()
    n_img, img_hits, rows = scan(s, CHECKS + (V4_CHECKS if SHARE else []), "page")   # v4 rules apply to --share; private output unchanged
    bad = 0
    print(f"{path}: {len(s)//1024} KB, {n_img} thumbnails byte-swept")
    for name, hits, kinds in rows:
        # the share-safe switch's own regexes name the strings it scrubs; they only matter in the private build
        exp = (not SHARE)
        flag = "OK  " if not hits else ("note" if exp else "FAIL")
        print(f"  [{flag}] {name}: {len(hits)}" + ("" if not hits else "  " + kinds_str(kinds)))
        if hits and SHARE:
            bad += len(hits); examples(kinds)
    print("RESULT:", "clean" if not bad else f"{bad} finding(s)" if SHARE else "private build, notes above are expected there")
    sys.exit(1 if bad else 0)

# ---- --root mode (v4): every emitted file ----
TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".json", ".jsonl", ".x3d", ".xml", ".xsd", ".css", ".txt", ".frag", ".vert", ".glsl", ".md", ".svg", ".csv", ".map", ".py"}
IMG_EXT = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
SKIP_DIRS = {"xite", "__pycache__", "node_modules", ".git"}
def listing(p):
    if os.path.isfile(p): return [p]
    out = []
    for d, dirs, files in os.walk(p):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        out += [os.path.join(d, f) for f in sorted(files)]
    return out
def decode_txt(raw):
    """gzip+base64 one-line part -> (text, 'gz+b64') ; plain base64 -> ('', None) is not attempted; else plain text."""
    body = raw.strip()
    if body and re.fullmatch(rb"[A-Za-z0-9+/=\s]+", body):
        try:
            dec = base64.b64decode(body + b"=" * (-len(body) % 4))
            if dec[:2] == b"\x1f\x8b": return gzip.decompress(dec).decode("utf-8", "replace"), "gz+b64"
        except Exception: pass
    return raw.decode("utf-8", "replace"), None
if not os.path.isdir(ROOT): print(f"RESULT: root is not a directory: {ROOT}"); sys.exit(1)
files = listing(ROOT)
for extra in POS:
    if os.path.exists(extra): files += listing(extra)
    else: print(f"  (extra path missing, skipped: {extra})")
# the page(s) first, then everything else in path order
AR = os.path.abspath(ROOT)
files = sorted(set(files), key=lambda p: (0 if p.endswith(".html") and os.path.dirname(os.path.abspath(p)) == AR else 1, p))
if not files: print(f"RESULT: no files under {ROOT}"); sys.exit(1)
checks = CHECKS + V4_CHECKS
bad = 0; bad_files = 0; n_text = 0; n_bin = 0; n_imgs = 0; kb_text = 0; skipped_xite = os.path.isdir(os.path.join(ROOT, "xite"))
def rel(p):
    ap = os.path.abspath(p); ar = os.path.abspath(ROOT)
    return os.path.relpath(ap, ar) if ap.startswith(ar + os.sep) else p
for p in files:
    ext = os.path.splitext(p)[1].lower(); raw = open(p, "rb").read(); label = rel(p); fbad = 0
    if ext in TEXT_EXT:
        s, how = decode_txt(raw) if ext == ".txt" else (raw.decode("utf-8", "replace"), None)
        n_text += 1; kb_text += len(s) // 1024
        extra_allow = []; copy_rows = 0; schema = False
        if "<xs:schema" in s[:200000]:
            # a public W3C/Web3D schema (x3d-4.x.xsd): its annotations and comments are published documentation
            # (author credits, "nVidia Cg", google URLs); element and attribute names and enumeration values stay swept
            schema = True; s = re.sub(r"(?s)<xs:annotation>.*?</xs:annotation>|<!--.*?-->", "", s)
        if "/jsval/vendor/" in p.replace(os.sep, "/") or "\\jsval\\vendor\\" in p:
            # third-party minified library (libxml2-wasm): "$6"-style tokens are code, not cost strings
            checks_here = [c for c in checks if c[0] != "dollar amounts"]
        else: checks_here = checks
        if os.path.basename(p) == "files.json":
            copy_rows = len(re.findall(r'"artifact"\s*:\s*"https://claude\.ai/artifact/[A-Za-z0-9]+"', s))
            extra_allow = [r'"artifact"\s*:\s*"https://claude\.ai/artifact/[A-Za-z0-9]+"']
        n_img, img_hits, rows = scan(s, checks_here, "any", extra_allow); n_imgs += n_img
        found = [(n, h, k) for n, h, k in rows if h]
        head = f"  {label}: {len(s)//1024} KB" + (f" decoded ({how}, {len(raw)//1024} KB published)" if how else "") + (f", {n_img} thumbnails byte-swept" if n_img else "") + (f", {copy_rows} publisher copy rows (artifact url allowed)" if copy_rows else "") + (" (public schema: annotations and comments not swept)" if schema else "")
        if not found: print(head + " -> clean"); continue
        nh = sum(len(h) for _, h, _ in found)
        print(head + (f" -> {nh} finding(s)" if SHARE else f" -> {nh} note(s)"))
        for name, hits, kinds in found:
            print(f"      [{'FAIL' if SHARE else 'note'}] {name}: {len(hits)}  {kinds_str(kinds)}")
            if SHARE: examples(kinds, indent="          ")
        if SHARE: fbad = nh
    else:
        n_bin += 1
        hits = [m.group(0) for m in re.finditer(STAMP, raw)]
        kinds = {}
        for h in hits: kinds.setdefault(h.lower(), []).append(h)
        what = "image" if ext in IMG_EXT or is_image(raw) else "binary"
        head = f"  {label}: {len(raw)//1024} KB {what}, byte-swept"
        if not hits: print(head + " -> clean"); continue
        print(head + (f" -> {len(hits)} finding(s)" if SHARE else f" -> {len(hits)} note(s)"))
        print(f"      [{'FAIL' if SHARE else 'note'}] stamp-like markers in {what} bytes: {len(hits)}  " + "; ".join(f"{k!r} x{len(v)}" for k, v in sorted(kinds.items(), key=lambda x: -len(x[1]))[:6]))
        if SHARE: fbad = len(hits)
    if fbad: bad += fbad; bad_files += 1
print(f"{ROOT}: {len(files)} files swept ({n_text} text, {kb_text} KB after decoding, {n_imgs} embedded thumbnails; {n_bin} binary)" + ("; xite/ skipped (third-party renderer, served from the v3 artifact copy)" if skipped_xite else "") + f"; rules: {len(checks)} {'share' if SHARE else 'private (v4 rules shown as notes)'}")
print("RESULT:", "clean" if not bad else f"{bad} finding(s) in {bad_files} file(s)" if SHARE else "private build, notes above are expected there")
sys.exit(1 if bad else 0)
