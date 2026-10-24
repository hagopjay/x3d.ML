"""cycles_manifest.py: the STAGED manifest for the Cycles turntables and stills (SPEC-v4 section 5; WORKPLAN `cycles_turntables` row).
Usage (repo root; the images are model output rendered in the scratchpad, so run with -I):
  python3 -I demo/v4/build/cycles_manifest.py [--turn <ledger.json>] [--stage <ledger.json>] [--out demo/v4/data/staged.json]
                                              [--strip] [--clean-dir <dir>] [--quality 90]
Inputs (both optional, both may be incomplete while a background render appends to them; a missing or half-written ledger is
reported and treated as empty; an entry whose file is not on disk yet is listed as pending):
  --turn   turntable ledger, dict slug -> {webp, bytes, frames, meshes, triangles, scene_lights, bbox_size, render_s, blender, engine,
           res, importer, webp_sha256, kind, k, src_sha256, cat, prompt}   (default scratchpad/turn/out/ledger.json; ../manifest.json
           beside it lists the planned scenes, so the pending ones can be named)
  --stage  stills ledger, dict slug -> {png, objects, meshes, triangles, scene_lights, staged_lights, camera, bbox_size, render_s,
           blender, engine, res, importer, png_sha256, kind, k, src_sha256, ...}; slugs end in _vp (scene Viewpoint) or _staged (auto 3/4)
Output demo/v4/data/staged.json (JSON only; nothing binary is ever written under the repo or /mnt/project-files):
  {"built", "schema", "sources": {turn, stage, pending[]}, "stripped": bool,
   "turntables": {<scene key>: {file, bytes, frames, sha256, blender, engine, importer, res, kind, url: null, render_sha256, src_sha256,
                                meshes, triangles, scene_lights, render_s, cat, sweep_hits, ledger_sha_ok}},
   "stills":     {<scene key>: {"vp": {... same fields + camera, staged_lights}, "staged": {...}}},
   "sweep": {"regex", "files", "hits"}}
  <scene key> is the ledger's `k` verbatim: live keys `<model slug>/<prompt>_a<k>.x3d` (03-data `keyOf`), replay keys
  `<model>/<mode>/<prompt>.x3d`, and the physics ledger path. `url` stays null: the lead uploads the assets (Artifact … asset: true)
  and fills it; `BUILD.has_cycles` must stay false until every turntable has a url.
Byte sweep: (?i)anthropic|claude|c2pa|cabx|jumb|openai|google|gemini over the raw bytes of every listed image (the same markers as
  leak_sweep.py); hits are printed per file and recorded as sweep_hits. Note the file NAMES carry model names (the private build may
  name models); the bytes must not.
--strip: PIL re-encodes every listed image without metadata into --clean-dir (default scratchpad/turn/clean/; any path under
  /mnt/project-files is refused): PNG -> PNG with no text/ICC/EXIF chunks (lossless); animated WebP -> WebP with the frames, their
  durations and the loop count kept and EXIF/XMP/ICC dropped (lossy re-encode at --quality, default 90; method 4). The clean copy is
  re-swept and its chunk list printed; the manifest's file/bytes/sha256 then describe the clean copy and render_sha256 keeps the
  render's own hash. Without --strip the manifest points at the render output.
Prints one table row per image, then the pending list. Exit 1 only when a listed file is unreadable or a clean copy still has hits.
"""
import os, re, sys, json, hashlib, struct, argparse, datetime
SCRATCH = "/tmp/claude-0/-home-user/d1db4f4e-b69c-59c1-8b63-a13c27f16e5d/scratchpad"
HERE = os.path.dirname(os.path.abspath(__file__)); V4 = os.path.dirname(HERE)
STAMP = rb"(?i)anthropic|claude|c2pa|cabx|jumb|openai|google|gemini"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--turn", default=os.path.join(SCRATCH, "turn/out/ledger.json"))
ap.add_argument("--stage", default=os.path.join(SCRATCH, "stage/out/ledger.json"))
ap.add_argument("--out", default=os.path.join(V4, "data", "staged.json"))
ap.add_argument("--strip", action="store_true")
ap.add_argument("--clean-dir", default=os.path.join(SCRATCH, "turn/clean"))
ap.add_argument("--quality", type=int, default=90)
a = ap.parse_args()
if a.strip and os.path.abspath(a.clean_dir).startswith("/mnt/project-files"): sys.exit("refusing to write images under /mnt/project-files")
if not a.out.endswith(".json"): sys.exit("--out must be a .json file")

def read_ledger(path):
    """-> (dict, note). A ledger being appended to by a renderer may be absent or half-written: never fail on it."""
    if not os.path.isfile(path): return {}, "missing"
    try:
        d = json.load(open(path, encoding="utf-8"))
        return (d if isinstance(d, dict) else {}), f"{len(d)} entries"
    except Exception as e: return {}, f"unreadable ({type(e).__name__}: incomplete write?)"
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def sweep(path):
    raw = open(path, "rb").read(); hits = {}
    for m in re.finditer(STAMP, raw): hits[m.group(0).lower().decode()] = hits.get(m.group(0).lower().decode(), 0) + 1
    return hits
def chunks(path):
    """chunk / RIFF tag list, for the report: PNG tEXt/iTXt/zTXt/eXIf/iCCP and WebP EXIF/XMP/ICCP are the metadata carriers."""
    raw = open(path, "rb").read(); out = []
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        i = 8
        while i + 8 <= len(raw):
            n, = struct.unpack(">I", raw[i:i+4]); out.append(raw[i+4:i+8].decode("latin1")); i += 12 + n
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        i = 12
        while i + 8 <= len(raw):
            n, = struct.unpack("<I", raw[i+4:i+8]); out.append(raw[i:i+4].decode("latin1").strip()); i += 8 + n + (n & 1)
    counts = {}
    for c in out: counts[c] = counts.get(c, 0) + 1
    return " ".join(f"{c}x{n}" if n > 1 else c for c, n in counts.items())
META_TAGS = {"tEXt", "iTXt", "zTXt", "eXIf", "iCCP", "EXIF", "XMP", "ICCP"}
def strip_image(src, dst, quality):
    from PIL import Image, ImageSequence
    im = Image.open(src)
    if im.format == "PNG":
        im.load(); clean = im.copy(); clean.info = {}
        clean.save(dst, "PNG", icc_profile=None)
    elif im.format == "WEBP":
        frames, durs = [], []
        for fr in ImageSequence.Iterator(im):
            frames.append(fr.convert("RGBA" if "A" in fr.getbands() else "RGB").copy()); durs.append(int(fr.info.get("duration", im.info.get("duration", 100)) or 100))
        kw = dict(quality=quality, method=4, icc_profile=None, exif=b"", xmp="")
        if len(frames) > 1: frames[0].save(dst, "WEBP", save_all=True, append_images=frames[1:], duration=durs, loop=int(im.info.get("loop", 0) or 0), **kw)
        else: frames[0].save(dst, "WEBP", **kw)
    else: raise ValueError(f"unsupported image format {im.format}")
    return getattr(im, "n_frames", 1)

turn, tnote = read_ledger(a.turn); stage, snote = read_ledger(a.stage)
planned = []
pm = os.path.join(os.path.dirname(os.path.dirname(a.turn)), "manifest.json")
if os.path.isfile(pm):
    try: planned = [r.get("slug") for r in json.load(open(pm)) if isinstance(r, dict)]
    except Exception: planned = []
print(f"turntable ledger {a.turn}: {tnote}" + (f"; {len(planned)} planned in {pm}" if planned else ""))
print(f"stills ledger    {a.stage}: {snote}")
if a.strip: os.makedirs(a.clean_dir, exist_ok=True)
rows = []; failures = 0; pending = []; all_hits = 0; n_files = 0
def entry(kind_label, slug, e, img_key, dirpath):
    global failures, all_hits, n_files
    fn = e.get(img_key); src = os.path.join(dirpath, fn) if fn else None
    if not src or not os.path.isfile(src): pending.append(f"{kind_label} {slug}: file not on disk yet ({fn})"); return None
    try:
        b = os.path.getsize(src); sha = sha256(src); hits = sweep(src)
    except Exception as ex: print(f"  ERROR {src}: {ex}"); failures += 1; return None
    n_files += 1; all_hits += sum(hits.values()); src_chunks = chunks(src)
    ledger_sha = e.get(f"{img_key}_sha256"); rec = {
        "file": os.path.abspath(src), "bytes": b, "frames": e.get("frames", 1), "sha256": sha, "render_sha256": sha, "render_chunks": src_chunks,
        "render_has_metadata": any(c.split("x")[0] in META_TAGS for c in src_chunks.split()),
        "blender": e.get("blender"), "engine": e.get("engine"), "importer": e.get("importer"), "res": e.get("res"), "kind": e.get("kind"),
        "url": None, "src_sha256": e.get("src_sha256"), "meshes": e.get("meshes"), "triangles": e.get("triangles"), "scene_lights": e.get("scene_lights"),
        "render_s": e.get("render_s"), "cat": e.get("cat"), "sweep_hits": sum(hits.values()), "ledger_sha_ok": (ledger_sha == sha) if ledger_sha else None}
    if "camera" in e: rec["camera"] = e["camera"]
    if "staged_lights" in e: rec["staged_lights"] = e["staged_lights"]
    clean_note = ""
    if a.strip:
        dst = os.path.join(a.clean_dir, fn)
        try:
            nfr = strip_image(src, dst, a.quality); cb = os.path.getsize(dst); csha = sha256(dst); chits = sweep(dst); ch = chunks(dst)
            rec.update({"file": os.path.abspath(dst), "bytes": cb, "sha256": csha, "frames": nfr if img_key == "webp" else 1, "sweep_hits": sum(chits.values()), "clean_chunks": ch})
            if chits or any(t in ch.split() or t in [c.split("x")[0] for c in ch.split()] for t in META_TAGS): failures += 1; clean_note = f" CLEAN STILL CARRIES {chits or ch}"
            clean_note = f" -> clean {cb:,} B {csha[:8]} [{ch}]" + clean_note
        except Exception as ex: failures += 1; clean_note = f" STRIP FAILED: {ex}"
    rows.append((kind_label, e.get("k", slug), os.path.basename(src), b, rec["frames"], "x".join(map(str, e.get("res") or [])) or "?", sha[:12], "ok" if rec["ledger_sha_ok"] else ("MISMATCH" if rec["ledger_sha_ok"] is False else "n/a"), ", ".join(f"{k} x{v}" for k, v in hits.items()) or "0", f" [{src_chunks}]" + clean_note))
    return rec
turntables = {}
for slug, e in sorted(turn.items()):
    r = entry("turntable", slug, e, "webp", os.path.dirname(a.turn))
    if r: turntables[e.get("k", slug)] = r
for slug in planned:
    if slug and slug not in turn: pending.append(f"turntable {slug}: not in the ledger yet (render in progress)")
stills = {}
for slug, e in sorted(stage.items()):
    variant = "vp" if slug.endswith("_vp") else ("staged" if slug.endswith("_staged") else "other")
    r = entry("still", slug, e, "png", os.path.dirname(a.stage))
    if r: stills.setdefault(e.get("k", slug), {})[variant] = r
w = [9, 52, 44, 9, 6, 8, 12, 8, 10]
hdr = ["kind", "scene key", "file", "bytes", "frames", "res", "sha256", "ledger", "sweep"]
print("  ".join(h.ljust(n) for h, n in zip(hdr, w)) + "  [render chunks]" + ("  -> clean copy" if a.strip else ""))
for r in rows: print("  ".join(str(v)[:n].ljust(n) if i != 3 else f"{v:,}".rjust(n) for i, (v, n) in enumerate(zip(r[:9], w))) + r[9])
for p in pending: print("  pending:", p)
out = {"built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "schema": "turntables[k] and stills[k][vp|staged]: file, bytes, frames, sha256 (of file), render_sha256, blender, engine, importer, res, kind, url (null until uploaded), src_sha256 (the X3D bytes rendered), sweep_hits; k = ledger scene key",
       "sources": {"turn": a.turn, "turn_note": tnote, "stage": a.stage, "stage_note": snote, "pending": pending},
       "stripped": bool(a.strip), "clean_dir": os.path.abspath(a.clean_dir) if a.strip else None,
       "turntables": turntables, "stills": stills,
       "sweep": {"regex": STAMP.decode(), "files": n_files, "hits": all_hits}}
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
print(f"{a.out}: {len(turntables)} turntables, {sum(len(v) for v in stills.values())} stills over {len(stills)} scenes, {n_files} files byte-swept, {all_hits} marker hits, {len(pending)} pending" + (f"; clean copies in {a.clean_dir}" if a.strip else "") + (f"; {failures} FAILURE(S)" if failures else ""))
sys.exit(1 if failures else 0)
