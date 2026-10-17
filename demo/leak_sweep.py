"""Leak sweep for a baked Tether Firehose page. Usage: python3 leak_sweep.py <page.html> [--share]
Private build: reports what the source carries (open model names, run cost, hardware string are expected there).
--share: zero tolerance for model/vendor names, run costs, hardware strings, GCP ids, private links, keys, emails, image stamps.
Env LEAK_IDS adds the private project id, run-as name and project number to the GCP check (set it locally, never commit the values).
Exit code 1 when a --share sweep finds anything. Decoded thumbnails are byte-swept as well."""
import os, re, sys, base64, json
path = sys.argv[1]; SHARE = "--share" in sys.argv
s = open(path, encoding="utf-8").read()
# thumbnails: byte-sweep the decoded JPEGs, then drop long base64 runs so they cannot cause false word hits
img_hits = 0; n_img = 0
for m in re.finditer(r'"jpg":"([A-Za-z0-9+/=]{100,})"', s):
    n_img += 1; raw = base64.b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4))
    if re.search(rb"(?i)anthropic|claude|c2pa|cabx|jumb|openai|google|gemini", raw): img_hits += 1
t = re.sub(r"[A-Za-z0-9+/=]{120,}", "<b64>", s)
ALLOW = [r'claude:viewport-fit-sides',                    # artifact page contract meta (not visible)
         r'https://fonts\.(googleapis|gstatic)\.com',     # the one allowed stylesheet host
         r'cdn\.jsdelivr\.net/npm/x_ite@16\.4\.1']        # pinned renderer
for a in ALLOW: t = re.sub(a, "<allowed>", t)
CHECKS = [
 ("closed model / vendor names", r"(?i)\banthropic\b|\bclaude\b|\bopus\b|\bsonnet\b|\bhaiku\b|\bfable\b|gemini|openai|chatgpt|\bgpt-?\d|\bkimi\b|nemotron|vertex ai|deepmind|mistral|\bllama\b|\bgoogle\b"),
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
bad = 0
print(f"{path}: {len(s)//1024} KB, {n_img} thumbnails byte-swept")
for name, p in CHECKS:
    if p is None: hits = [f"{img_hits} of {n_img} decoded thumbnails carry a stamp-like marker"] if img_hits else []
    else: hits = [(m.group(0), t[max(0, m.start()-40):m.end()+50].replace("\n", " ")) for m in re.finditer(p, t)]
    # expected, harmless matches
    hits = [h for h in hits if not (isinstance(h, tuple) and (h[0] == "$1" or "$1" in h[1] and "hidden" in h[1]))]
    # the share-safe switch's own regexes name the strings it scrubs; they only matter in the private build
    exp = (not SHARE)
    kinds = {}
    for h in hits: kinds.setdefault(h[0].lower() if isinstance(h, tuple) else h, []).append(h)
    flag = "OK  " if not hits else ("note" if exp else "FAIL")
    print(f"  [{flag}] {name}: {len(hits)}" + ("" if not hits else "  " + "; ".join(f"{k!r} x{len(v)}" for k, v in sorted(kinds.items(), key=lambda x: -len(x[1]))[:6])))
    if hits and SHARE:
        bad += len(hits)
        for k, v in list(kinds.items())[:4]: print("        e.g.", v[0][1] if isinstance(v[0], tuple) else v[0])
print("RESULT:", "clean" if not bad else f"{bad} finding(s)" if SHARE else "private build, notes above are expected there")
sys.exit(1 if bad else 0)
