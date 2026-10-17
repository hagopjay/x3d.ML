"""Bake tether-firehose-v2.html: template + replay.json (174 real scenes with chains' source bodies and thumbnails) + X_ITE stylesheet text.
The page loads X_ITE 16.5.0 from its own published files (xite/, see tests/mkxite.py), not from a CDN.
Usage: python3 build_v2.py <replay.json> <x_ite.css> <out.html> [--share]
The stylesheet is injected into X_ITE's shadow root at runtime (a page policy can block the stylesheet link X_ITE adds itself).
--share bakes a source-level clean variant for sharing: model ids become open-8B/open-14B/open-20B everywhere (data and code), run cost
is zeroed, hardware is generic, run ids are opaque, the one scene whose own <meta creator> names a chat product is redacted, and the
link to the private v1 page is dropped. The share-safe switch in the page then has nothing left to hide; leak_sweep.py must pass on it."""
import json, sys, os, re, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SHARE = "--share" in sys.argv
tpl = open(HERE + "/tether-firehose-v2.template.html", encoding="utf-8").read()
real = open(args[0], encoding="utf-8").read().strip()
css = open(args[1], encoding="utf-8").read().replace("url(assets/", "url(xite/assets/")   # the stylesheet is injected into the page, so its relative urls must point at the published xite/ folder
js = lambda s: s.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
assert tpl.count("/*__REAL__*/[]") == 1 and tpl.count('/*__XCSS__*/""') == 1
SAFE = [("qwen2.5-coder-14b-awq", "open-14B"), ("qwen2.5-coder-14b", "open-14B"), ("qwen3-8b", "open-8B"), ("gpt-oss-20b", "open-20B")]
redacted = 0
if SHARE:
    items = json.loads(real)
    for it in items:
        it["hw"] = "1x 24 GB GPU, vLLM 0.11"; it["rc"] = 0
        it["rid"] = hashlib.sha256(it["rid"].encode()).hexdigest()[:8]
        n = len(re.findall(r"ChatGPT|OpenAI|Anthropic|Claude|Gemini", it["b"], re.I))
        if n: redacted += n; it["b"] = re.sub(r"ChatGPT|OpenAI|Anthropic|Claude|Gemini", "model", it["b"], flags=re.I)
    real = json.dumps(items, separators=(",", ":"), ensure_ascii=False)
    for a, b in SAFE: real = real.replace(a, b); tpl = tpl.replace(a, b)
    for a, b in [('.replace(/ChatGPT|OpenAI|Anthropic|Claude|Gemini/gi,"a model")', ""),   # data is already clean; the page need not name what it scrubs
                 ('.replace(/g2-standard-8[^"]*?us-central1/g,"1x 24 GB GPU, vLLM 0.11")', ""),
                 ("in the x3d.ML repo", "in the project repo")]:
        assert tpl.count(a) == 1, a; tpl = tpl.replace(a, b)
    link = re.search(r'<a href="https://claude\.ai/artifact/[^"]*"[^>]*>(v1 synthetic only)</a>', tpl)
    assert link; tpl = tpl.replace(link.group(0), link.group(1))
out = tpl.replace("/*__REAL__*/[]", js(real)).replace('/*__XCSS__*/""', js(json.dumps(css)))
assert "/*__" not in out
open(args[2], "w", encoding="utf-8").write(out)
print(args[2], len(out) // 1024, "KB;", len(json.loads(real)), "replay scenes", f"(share build, {redacted} scene-text redactions)" if SHARE else "")
