"""Bake tether-firehose-v3.html: template + replay.json (174 real scenes of the 11 Oct GPU phase) + live.json (the recorded live run of 17 Oct) + X_ITE stylesheet text.
The page loads X_ITE 16.5.0 from its own published files (xite/, see mkxite.py), not from a CDN.
Usage: python3 build_v3.py <replay.json> <live.json> <x_ite.css> <out.html> [--share]
The stylesheet is injected into X_ITE's shadow root at runtime (a page policy can block the stylesheet link X_ITE adds itself).
--share bakes a source-level clean variant for sharing: every model id becomes a size or class label (open-8B/14B/20B for the replay; closed-A..C and open-D, open-E for the live run),
providers become "api", all prices and costs are zeroed, hardware is generic, run ids are opaque, vendor and model names inside scene text are redacted, and the links to the private
v1 and v2 pages are dropped. The share-safe switch in the page then has nothing left to hide; leak_sweep.py must pass on it."""
import json, sys, os, re, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SHARE = "--share" in sys.argv
tpl = open(HERE + "/tether-firehose-v3.template.html", encoding="utf-8").read()
real = open(args[0], encoding="utf-8").read().strip()
live = json.load(open(args[1], encoding="utf-8"))
css = open(args[2], encoding="utf-8").read().replace("url(assets/", "url(xite/assets/")   # the stylesheet is injected into the page, so its relative urls must point at the published xite/ folder
js = lambda s: s.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
for ph in ("/*__REAL__*/[]", "/*__LIVE__*/[]", "/*__LIVEMETA__*/{models:[],validator:\"fork@eb4b4b4\",t_total:0,idle_collapsed_s:0}", '/*__XCSS__*/""'):
    assert tpl.count(ph) == 1, ph
SAFE = [("qwen2.5-coder-14b-awq", "open-14B"), ("qwen2.5-coder-14b", "open-14B"), ("qwen3-8b", "open-8B"), ("gpt-oss-20b", "open-20B"),
        ("gemini-3.8-flash", "closed-A"), ("gemini-3.1-pro-preview", "closed-B"), ("gpt-6.1-sol", "closed-C"), ("z-ai/glm-5.3", "open-D"), ("nvidia/nemotron-3-super-120b-a12b", "open-E")]
VENDOR = re.compile(r"\b(ChatGPT|OpenAI|Anthropic|Claude|Gemini|Gemma|Nemotron|NVIDIA|Zhipu|GLM|GPT)\b", re.I)
redacted = 0
items, meta = live["items"], live["meta"]
if SHARE:
    r_items = json.loads(real)
    for it in r_items:
        it["hw"] = "1x 24 GB GPU, vLLM 0.11"; it["rc"] = 0
        it["rid"] = hashlib.sha256(it["rid"].encode()).hexdigest()[:8]
        n = len(VENDOR.findall(it["b"]))
        if n: redacted += n; it["b"] = VENDOR.sub("model", it["b"])
    real = json.dumps(r_items, separators=(",", ":"), ensure_ascii=False)
    for it in items:
        for a in it["A"]: a["u"] = 0
        for k, b in enumerate(it["B"]):
            n = len(VENDOR.findall(b))
            if n: redacted += n; it["B"][k] = VENDOR.sub("model", b)
    for m in meta["models"]: m["prov"] = "api"
    for a, b in SAFE:
        real = real.replace(a, b); tpl = tpl.replace(a, b)
    live_s = json.dumps(items, separators=(",", ":"), ensure_ascii=False); meta_s = json.dumps(meta, separators=(",", ":"), ensure_ascii=False)
    for a, b in SAFE: live_s = live_s.replace(a, b); meta_s = meta_s.replace(a, b)
    items, meta = json.loads(live_s), json.loads(meta_s)
    for a, b in [('.replace(/(&quot;|")provider\\1:\\1(vertex|openai|nvidia)\\1/g,\'$1provider$1:$1api$1\')', ""),
                 ('.replace(/ChatGPT|OpenAI|Anthropic|Claude|Gemini/gi,"a model")', ""),   # data is already clean; the page need not name what it scrubs
                 ('.replace(/g2-standard-8[^"]*?us-central1/g,"1x 24 GB GPU, vLLM 0.11")', ""),
                 ("in the x3d.ML repo", "in the project repo")]:
        assert tpl.count(a) == 1, a; tpl = tpl.replace(a, b)
    for lab in ("v1 synthetic only", "v2 replay of 174 real runs"):
        link = re.search(r'<a href="https://claude\.ai/artifact/[^"]*"[^>]*>(' + re.escape(lab) + r')</a>', tpl)
        assert link, lab; tpl = tpl.replace(link.group(0), link.group(1))
out = (tpl.replace("/*__REAL__*/[]", js(real))
          .replace("/*__LIVE__*/[]", js(json.dumps(items, separators=(",", ":"), ensure_ascii=False)))
          .replace("/*__LIVEMETA__*/{models:[],validator:\"fork@eb4b4b4\",t_total:0,idle_collapsed_s:0}", js(json.dumps(meta, separators=(",", ":"), ensure_ascii=False)))
          .replace('/*__XCSS__*/""', js(json.dumps(css))))
assert "/*__" not in out
open(args[3], "w", encoding="utf-8").write(out)
print(args[3], len(out) // 1024, "KB;", len(json.loads(real)), "replay scenes,", len(items), "live scenes", f"(share build, {redacted} scene-text redactions)" if SHARE else "")
