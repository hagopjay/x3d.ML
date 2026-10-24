"""check_v4_parts.py — every part decodes and matches the manifest (Python side), the page loads them all with hash ok, a corrupted copy is refused and named,
page < 16 MB, each text file < 16 MB, files.json < 511 entries with 105 xite rows (SPEC §13)."""
import os, sys, json, gzip, base64, hashlib, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture
fx = Fixture()
async def main():
    B = fx.build_dir
    man = json.load(open(os.path.join(B, "parts", "manifest.json")))
    n = 0
    for name, p in man["parts"].items():
        raw = gzip.decompress(base64.b64decode(open(os.path.join(B, "parts", name + ".txt"), "rb").read()))
        fx.ok(f"part {name} decodes and sha256 matches ({p['bytes_raw']:,} B)", hashlib.sha256(raw).hexdigest() == p["sha256"] and len(raw) == p["bytes_raw"]); n += 1
    fx.ok("11 parts in the manifest", n == 11, n)
    fx.ok("index.html under 16 MB", os.path.getsize(os.path.join(B, "index.html")) < 16 * 1024 * 1024, os.path.getsize(os.path.join(B, "index.html")))
    big = [(r, f, os.path.getsize(os.path.join(r, f))) for r, d, fs in os.walk(B) for f in fs if os.path.getsize(os.path.join(r, f)) >= 15 * 1024 * 1024]
    fx.ok("every own file under 15 MB", not big, big)
    fm = os.path.join(B, "files.json")
    if os.path.exists(fm):
        f = json.load(open(fm)); x = sum(1 for k in f if k.startswith("xite/"))
        fx.ok("files.json: 105 xite rows, under 511 entries", x == 105 and len(f) < 511, (x, len(f)))
        fx.ok("files.json local rows exist on disk", all(os.path.exists(os.path.join(B, k)) for k, v in f.items() if isinstance(v, str)))
    else:
        fx.ok("files.json present (build with --files-map)", False)
    async with fx.browser() as b:
        pg = await fx.page(b); await fx.goto(pg)
        fx.ok("page loads every data part with hash ok (xsd parts stay idle until VAL asks)", await fx.wait(pg, 'Object.entries(DATA.status).filter(([k])=>!k.startsWith("xsd")).every(([,s])=>s.state==="loaded")', 90000), await pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state])))"))
        sh = await pg.evaluate("Object.entries(DATA.status).filter(([,v])=>v.state==='loaded').map(([k,v])=>v.sha===MANIFEST.parts[k].sha256)")
        fx.ok("in-page sha256 of every decoded part equals the manifest (9 parts)", len(sh) == 9 and all(sh), sh)
        fx.ok("xsd parts are present in the manifest and idle", await pg.evaluate("DATA.status.xsd40.state==='idle'&&DATA.status.xsd41.state==='idle'&&!!MANIFEST.parts.xsd40&&!!MANIFEST.parts.xsd41"))
        fx.ok("no page errors", not fx.errors(pg), fx.errors(pg)[:3])
        await pg.context.close()
        # corrupted copies: (a) manifest sha changed → decode ok, hash mismatch; (b) one base64 byte changed → gzip decode fails. Both refused, both named in #under.
        for how, needle in (("manifest", "hash mismatch"), ("bytes", "decode failed")):
            tmp = fx.corrupted_copy("drift", how)
            fx2 = Fixture(build_dir=tmp, csp=fx.csp); fx2.res = fx.res
            pg2 = await fx2.page(b); await fx2.goto(pg2)
            fx.ok(f"[{how}] corrupted drift part is refused", await fx2.wait(pg2, 'DATA.status.drift.state==="refused"', 60000), await pg2.evaluate("DATA.status.drift"))
            fx.ok(f"[{how}] DATA.messages carries 'part drift refused: {needle}'", await pg2.evaluate("DATA.messages.some(m=>m.includes('part drift refused: ' + %r))" % needle), await pg2.evaluate("DATA.messages.filter(m=>m.includes('drift'))"))
            await pg2.wait_for_timeout(1500)
            under = await fx2.txt(pg2, "#under")
            fx.ok(f"[{how}] #under names the refused part", "part drift refused" in under and needle in under, [l for l in under.split("\n") if "refused" in l][:2])
            fx.ok(f"[{how}] DRIFT stays empty after the refusal", await pg2.evaluate("DRIFT===null||DRIFT===undefined"))
            fx.ok(f"[{how}] the other data parts still load", await fx2.wait(pg2, 'Object.entries(DATA.status).filter(([k])=>k!=="drift"&&!k.startsWith("xsd")).every(([,s])=>s.state==="loaded")', 90000))
            fx.ok(f"[{how}] the #under row for drift is marked refused", await pg2.evaluate("document.querySelector('#under tr[data-part=\"drift\"]')?.dataset.state") == "refused")
            await pg2.context.close(); fx2.stop(); shutil.rmtree(tmp, ignore_errors=True)
    fx.summary()
Fixture.run(main)
