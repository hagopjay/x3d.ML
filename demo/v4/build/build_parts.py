"""Parts and manifest for Tether Firehose 4 (SPEC section 7.4 data loading, 7.5 size budget, section 8 step 5).
Each part is one own file demo/v4/parts/<name>.txt = gzip (level 9, mtime 0) + base64, one line, no trailing newline; the page decodes with DecompressionStream and checks the
sha256 of the decoded bytes against the manifest before it mounts the part. Parts:
  live.core        demo/data/live.json minus every B[] body and every r.jpg (the page re-attaches them from the two parts below)
  live.bodies      [[body per attempt] per chain]: the 358 attempt bodies, aligned with live.core items
  live.jpg         [[jpg or null per attempt] per chain]: the measured 192x144 JPEG frames (null where the attempt drew nothing or did not parse)
  replay           demo/data/replay.json as is (174 scenes of 11 Oct, bodies and 16.5.0 renders inside)
  events           demo/v4/data/events.json (build_events.py)
  renders.series   demo/v4/data/renders.series.json (merge_renders.py)        renders.151   demo/v4/data/renders.151.json
  drift            {by_commit: drift/verdicts_by_fork_commit.json, v8dd0d3e: drift/verdicts-8dd0d3e.json, attribution: drift/drift_attribution.json}
  suite            {result: runs/suite-physics-2026-10-17/result.json, steps: {main, crease, x41}}
  xsd40, xsd41     demo/jsval/data/schemas/x3d-4.0.xsd and x3d-4.1.xsd, raw bytes (for the js-port's XSD pass)
  live2            only with --run2 <live2.json> (the 24 Oct run once build_live.py has written it; not run while that run is still recording): HAS_RUN2 becomes true
demo/v4/parts/manifest.json = {parts:{name:{bytes_raw, bytes_gz, bytes_b64, sha256, rows, source, recorded, validator, xite, file}}, canary:{bodies, flips, set} (from stats.json),
HAS_CYCLES (true once staged.json urls are filled), HAS_RUN2, validator_recorded, port, xite, passes, built}. Every part is decoded back from its file and its sha256 compared before the manifest is written.
Usage: python3 demo/v4/build/build_parts.py [--run2 <live2.json>]"""
import base64, copy, datetime, gzip, hashlib, json, os, sys

def _has_cycles():
    """True once data/staged.json carries an uploaded url for at least one turntable or still (the Cycles assets live in the artifact, never in this repo)."""
    try:
        import json as _j, os as _o
        st = _j.load(open(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))), "data", "staged.json")))
        if any(e.get("url") for e in st.get("turntables", {}).values()): return True
        return any(c.get("url") for e in st.get("stills", {}).values() for c in e.values() if isinstance(c, dict))
    except Exception:
        return False


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
D, V4, P = os.path.join(ROOT, "demo/data"), os.path.join(ROOT, "demo/v4/data"), os.path.join(ROOT, "demo/v4/parts")
RUN2 = sys.argv[sys.argv.index("--run2") + 1] if "--run2" in sys.argv else None
os.makedirs(P, exist_ok=True)
J = lambda p: json.load(open(p, encoding="utf-8"))
enc = lambda obj: json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
R17 = dict(source="RECORDED 17 Oct", recorded="2026-10-17", validator="fork@eb4b4b4", xite="16.5.0")

live = J(D + "/live.json"); core = copy.deepcopy(live)
bodies = [it.pop("B") for it in core["items"]]
jpgs = [[a["r"].pop("jpg", None) for a in it["A"]] for it in core["items"]]
suite_dir = os.path.join(ROOT, "runs/suite-physics-2026-10-17")
steps = {k: J(f"{suite_dir}/x3d_suite_{k}.steps.json") for k in ("main", "crease", "x41")}
drift = {"by_commit": J(ROOT + "/drift/verdicts_by_fork_commit.json"), "v8dd0d3e": J(ROOT + "/drift/verdicts-8dd0d3e.json"), "attribution": J(ROOT + "/drift/drift_attribution.json")}
events = J(V4 + "/events.json"); rs = J(V4 + "/renders.series.json"); r151 = J(V4 + "/renders.151.json"); replay = J(D + "/replay.json"); stats = J(V4 + "/stats.json")

PARTS = [  # name, raw bytes, rows, provenance
 ("live.core", enc(core), len(core["items"]), {**R17, "source_file": "demo/data/live.json minus B[] and r.jpg"}),
 ("live.bodies", enc(bodies), sum(len(b) for b in bodies), {**R17, "source_file": "demo/data/live.json B[]"}),
 ("live.jpg", enc(jpgs), sum(1 for j in jpgs for x in j if x), {**R17, "source_file": "demo/data/live.json A[].r.jpg"}),
 ("replay", enc(replay), len(replay), dict(source="RECORDED 11 Oct", recorded="2026-10-11", validator="svc@11Oct + fork@8c0a457 + fork@eb4b4b4", xite="16.5.0", source_file="demo/data/replay.json")),
 ("events", enc(events), len(events["failed"]) + len(events["cut"]) + len(events["probes"]), {**R17, "xite": None, "source_file": "demo/v4/data/events.json"}),
 ("renders.series", enc(rs), len(rs["live"]), {**R17, "validator": None, "source_file": "demo/v4/data/renders.series.json"}),
 ("renders.151", enc(r151), len(r151["live"]) + len(r151["replay"]), dict(source="MEASURED 24 Oct", recorded="2026-10-24", validator=None, xite="16.5.1", source_file="demo/v4/data/renders.151.json")),
 ("drift", enc(drift), sum(len(v) for v in drift["by_commit"].values()) + drift["v8dd0d3e"]["n"], dict(source="RECORDED per commit", recorded="2026-10-11..24", validator="fork " + ", ".join(drift["by_commit"]) + ", 8dd0d3e", xite=None, source_file="drift/*.json")),
 ("suite", enc({"result": J(suite_dir + "/result.json"), "steps": steps}), sum(len(v) for v in steps.values()), dict(source="RECORDED 17 Oct (owner's machine)", recorded="2026-10-17", validator="fork@fa0b389 (ledger XSD)", xite=None, source_file="runs/suite-physics-2026-10-17/")),
 ("xsd40", open(ROOT + "/demo/jsval/data/schemas/x3d-4.0.xsd", "rb").read(), None, dict(source="Web3D X3D 4.0 schema", recorded=None, validator=None, xite=None, source_file="demo/jsval/data/schemas/x3d-4.0.xsd")),
 ("xsd41", open(ROOT + "/demo/jsval/data/schemas/x3d-4.1.xsd", "rb").read(), None, dict(source="Web3D X3D 4.1 schema", recorded=None, validator=None, xite=None, source_file="demo/jsval/data/schemas/x3d-4.1.xsd")),
]
if RUN2:   # the 24 Oct run, once build_live.py has written its live2.json (tolerates arm, sample, tft_ms, stream[], autofix rows); never run against a recording directory
    l2 = J(RUN2); m2 = l2["meta"]
    for m in m2.get("models", []): m["arms"] = sorted({r["arm"] for r in m2.get("lane_list", []) if r["m"] == m["id"]} | {it["arm"] for it in l2["items"] if it["m"] == m["id"] and it.get("arm")})
    m2.setdefault("wall_min", 150); m2.setdefault("wall_src", "docs/LIVE-RUN-2-FINDINGS.md: 150 min wall, cap 1 USD unused")   # the run's own facts, not retyped numbers
    PARTS.append(("run24", enc(l2), len(l2["items"]), dict(source="RECORDED 24 Oct", recorded=m2.get("date", "2026-10-24"), validator=m2.get("validator", "fork@8dd0d3e"), xite="16.5.0", source_file=RUN2)))
assert len(bodies) == len(core["items"]) and sum(len(b) for b in bodies) == sum(len(it["A"]) for it in core["items"]) == 358
assert b"/9j/" not in PARTS[0][1] and not any("jpg" in a["r"] for it in core["items"] for a in it["A"]), "a thumbnail stayed in live.core"
assert b'"B":' not in PARTS[0][1], "a body stayed in live.core"

manifest = {}
for name, raw, rows, prov in PARTS:
    gz = gzip.compress(raw, compresslevel=9, mtime=0); b64 = base64.b64encode(gz)
    path = os.path.join(P, name + ".txt"); open(path, "wb").write(b64)
    back = gzip.decompress(base64.b64decode(open(path, "rb").read()))          # round trip from the file on disk
    sha = hashlib.sha256(raw).hexdigest(); assert hashlib.sha256(back).hexdigest() == sha and back == raw, name
    assert len(raw) <= 16_000_000, (name, len(raw))
    manifest[name] = {"bytes_raw": len(raw), "bytes_gz": len(gz), "bytes_b64": os.path.getsize(path), "sha256": sha, "rows": rows, **prov, "file": f"parts/{name}.txt"}
out = {"built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "parts": manifest, "canary": {k: stats["canary"][k] for k in ("bodies", "flips", "set")},
       "HAS_CYCLES": _has_cycles(), "HAS_RUN2": bool(RUN2), "validator_recorded": ["fork@eb4b4b4", "fork@8dd0d3e"], "port": "js-port-of-8dd0d3e", "xite": "16.5.0", "passes": ["16.5.0", "16.5.1"],
       "encoding": "gzip level 9 mtime 0, base64, one line; sha256 is of the decoded bytes"}
json.dump(out, open(P + "/manifest.json", "w"), indent=1)

head = ["part", "source", "raw B", "gz B", "published B", "sha256", "rows"]
rows = [[n, m["source_file"], f"{m['bytes_raw']:,}", f"{m['bytes_gz']:,}", f"{m['bytes_b64']:,}", m["sha256"][:8], m["rows"] if m["rows"] is not None else "-"] for n, m in manifest.items()]
rows.append(["total", f"{len(manifest)} parts", f"{sum(m['bytes_raw'] for m in manifest.values()):,}", f"{sum(m['bytes_gz'] for m in manifest.values()):,}", f"{sum(m['bytes_b64'] for m in manifest.values()):,}", "", ""])
w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
for r in rows: print("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))
print(f"manifest {P}/manifest.json · canary {out['canary']} · HAS_CYCLES {out['HAS_CYCLES']} · HAS_RUN2 {out['HAS_RUN2']} · every part round-trips (sha256 equal)")
