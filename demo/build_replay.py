"""Build replay.json for the Tether Firehose v2 page from cached project data (no network, no spend).
Inputs: gcp-showcase/gpu-phase-2026-10-11 (bodies, runs, results, prompts), ../drift/verdicts_by_fork_commit.json (fork 8c0a457, eb4b4b4),
a render file from render/render_final3.py (headless X_ITE 16.5.0, one fresh page per scene, frame watcher registered before load plus a screenshot cross-check).
r.nb is the larger of the in-callback best frame (cb) and the screenshot (shot); r.nf is 1 only when X_ITE finished no frame at all.
Env EXT=<file> adds r.ext (the same measure over a longer window) for the scenes in it.
Optional third argument: the same pass on another X_ITE version (adds r.nb164 / r.err164 for the cross-version line).
Usage: GPU_PHASE_DIR=<dir> python3 build_replay.py data/renders3_x_ite_16.5.0.json data/replay.json [data/renders3_x_ite_16.4.1.json]"""
import json, sys, hashlib, collections, os, re
from lxml import etree
G = os.environ.get("GPU_PHASE_DIR", "/mnt/project-files/gcp-showcase/gpu-phase-2026-10-11")  # cached 11 Oct GPU-phase run: results/, prompts.jsonl
HERE = os.path.dirname(os.path.abspath(__file__))
drift = json.load(open(HERE + "/../drift/verdicts_by_fork_commit.json"))
renders = json.load(open(sys.argv[1]))
renders164 = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
ext = json.load(open(os.environ["EXT"])) if os.environ.get("EXT") else {}   # longer look at scenes still animating when the 3.5 s window ended
prompts = {json.loads(l)["prompt_id"]: json.loads(l) for l in open(G + "/prompts.jsonl")}
PARSE_FAIL = "X_ITE could not parse this file"


def well_formed(text):
    try:
        etree.fromstring(text.encode("utf-8"), etree.XMLParser(resolve_entities=False, no_network=True)); return True
    except etree.XMLSyntaxError:
        return False


items = []
for model in ("qwen3-8b", "qwen2.5-coder-14b-awq", "gpt-oss-20b"):
    runs = {r["run_id"]: r for r in map(json.loads, open(f"{G}/results/{model}-runs.jsonl"))}
    res = collections.defaultdict(list)
    for r in map(json.loads, open(f"{G}/results/{model}-results.jsonl")): res[(r["run_id"], r["prompt_id"])].append(r)
    per_run = collections.Counter(rid for rid, _ in res)
    for (rid, pid), atts in sorted(res.items()):
        run = runs[rid]; mode = "grounded" if run["grounded"] else "oneshot"; key = f"{model}/{mode}/{pid}.x3d"
        path = f"{G}/results/x3d/{key}"
        if not os.path.exists(path): continue
        atts.sort(key=lambda a: a["attempt"]); fin = atts[-1]; body = open(path, encoding="utf-8", errors="replace").read()
        rd = renders.get(key, {}); pr = prompts[pid]
        err = rd.get("err")
        if err and "parse X3D" in err: err = PARSE_FAIL
        cb, shot = rd.get("nonblank"), rd.get("shot"); seen = [v for v in (cb, shot) if v is not None]
        nb = None if err else (max(seen) if seen else 0)
        it = {"k": key, "m": model, "mo": mode, "p": pid, "c": pr["category"], "pt": pr["prompt"], "psha": hashlib.sha256(pr["prompt"].encode()).hexdigest(),
              "at": len(atts), "x": int(fin["xsd_valid"]), "s": int(fin["semantic_valid"]), "cn": int(fin["constraints_ok"]),
              "earlier": [[int(a["xsd_valid"]), int(a["semantic_valid"])] for a in atts[:-1]],
              "ti": sum(a["tokens_in"] for a in atts), "to": sum(a["tokens_out"] for a in atts), "lat": sum(a["latency_ms"] for a in atts),
              "rid": rid[:8], "hw": run["hardware"], "rc": run["cost_usd"], "nrun": per_run[rid],
              "f1": [int(drift["8c0a457"][key]["valid"]), drift["8c0a457"][key]["codes"]],
              "f2": [int(drift["eb4b4b4"][key]["valid"]), drift["eb4b4b4"][key]["codes"]],
              "wf": int(well_formed(body)),
              "r": {"nodes": rd.get("nodes"), "nb": nb, "cb": cb, "shot": shot, "nf": 1 if (not err and not rd.get("frames")) else 0, "err": err,
                    "msgs": [m.split(": ", 1)[-1][:150] for m in rd.get("msgs", [])][:3], "unknown": rd.get("unknown", 0), "nmsg": rd.get("nmsg", 0),
                    "frames": rd.get("frames"), "first": rd.get("first"), "last": rd.get("last"), "series": rd.get("series"), "ms": rd.get("ms"), "jpg": rd.get("jpg") if (nb or 0) >= 0.005 else None},   # a blank frame is not worth a JPEG
              "b": body}
        r4 = renders164.get(key)
        if r4 is not None:
            e4 = r4.get("err"); s4 = [v for v in (r4.get("nonblank"), r4.get("shot")) if v is not None]
            it["r"]["err164"] = int(bool(e4)); it["r"]["nb164"] = None if e4 else (max(s4) if s4 else 0)
        rx = ext.get(key)
        if rx is not None:
            sx = [v for v in (rx.get("nonblank"), rx.get("shot")) if v is not None]; it["r"]["ext"] = max(sx) if sx else 0; it["r"]["extFrames"] = rx.get("frames")
        items.append(it)
json.dump(items, open(sys.argv[2], "w"), separators=(",", ":"))
n = len(items); print(n, "items;", os.path.getsize(sys.argv[2]) // 1024, "KB")

draws = lambda i: (not i["r"]["err"]) and (i["r"]["nb"] or 0) >= 0.005
nodraw = lambda i: not draws(i)
DROP = re.compile(r"Unknown node type|Unknown named or imported node|Container field|insufficient component")
dropped = lambda i: i["r"]["unknown"] or any(DROP.search(m) for m in i["r"]["msgs"])
kind = lambda i: "parse-fail" if i["r"]["err"] else "draws" if draws(i) else "nothing-drawable (X_ITE dropped nodes)" if (i["r"]["nf"] or dropped(i)) else "blank-frame"
kinds = collections.Counter(kind(i) for i in items)
print("render outcomes:", dict(kinds), "| thumbnails:", sum(1 for i in items if i["r"]["jpg"]), "| no frame at all:", sum(1 for i in items if i["r"]["nf"]))
print("parse-fail scenes not well-formed XML:", sum(1 for i in items if i["r"]["err"] and not i["wf"]), "of", sum(1 for i in items if i["r"]["err"]),
      "| well-formed overall:", sum(i["wf"] for i in items), "of", n)
both = [i for i in items if not i["r"]["err"] and i["r"].get("cb") is not None and i["r"].get("shot") is not None]
print("in-callback best vs screenshot agree on draw/blank:", sum(1 for i in both if (i["r"]["cb"] < 0.005) == (i["r"]["shot"] < 0.005)), "of", len(both),
      "| disagree:", [i["k"] for i in both if (i["r"]["cb"] < 0.005) != (i["r"]["shot"] < 0.005)])
med = lambda a: sorted(a)[len(a) // 2] if a else None
bl = [i for i in items if not i["r"]["err"] and nodraw(i)]; dr = [i for i in items if draws(i)]
print("blank scenes: median frames", med([i["r"]["frames"] for i in bl]), "last frame ms", med([i["r"]["last"] for i in bl]), "| drawing scenes: median frames", med([i["r"]["frames"] for i in dr]), "last frame ms", med([i["r"]["last"] for i in dr]))
print("drawing scenes where X_ITE printed dropped-node messages:", sum(1 for i in dr if dropped(i)), "of", len(dr))
if renders164:
    cls = lambda r, e: "u" if r.get(e) else ("b" if (r.get("nb164") or 0) < 0.005 else "d")
    c164 = [i for i in items if "nb164" in i["r"]]
    print("X_ITE 16.4.1 same draw/blank/parse answer:", sum(1 for i in c164 if ("u" if i["r"]["err164"] else "b" if (i["r"]["nb164"] or 0) < 0.005 else "d") == ("u" if i["r"]["err"] else "b" if (i["r"]["nb"] or 0) < 0.005 else "d")), "of", len(c164))
V = {"svc (11 Oct service)": lambda i: i["x"] and i["s"], "fork 8c0a457": lambda i: i["f1"][0], "fork eb4b4b4": lambda i: i["f2"][0]}
allDraw = sum(draws(i) for i in items)
print(f"scenes that draw: {allDraw} of {n}")
for tag, f in V.items():
    v = [i for i in items if f(i)]; d = sum(draws(i) for i in v)
    print(f"{tag}: valid {len(v)}, of which draw nothing {len(v) - d} ({100 * (len(v) - d) / max(1, len(v)):.1f}%); recall of drawing scenes {d}/{allDraw}")
flip = [i for i in items if (i["x"] and i["s"]) and not i["f1"][0]]
print("valid on svc but invalid on fork 8c0a457:", len(flip), "| of those draw nothing:", sum(nodraw(i) for i in flip))
print("first-try valid on fork eb4b4b4 (at==1) per model/mode, and final valid:")
for (m, mo), g in sorted(collections.Counter((i["m"], i["mo"]) for i in items).items()):
    sub = [i for i in items if i["m"] == m and i["mo"] == mo]
    print(f"  {m:24s}{mo:9s} n={g:2d} svc-valid {sum(1 for i in sub if i['x'] and i['s']):2d} f2-valid {sum(i['f2'][0] for i in sub):2d} draws {sum(draws(i) for i in sub):2d} mean attempts {sum(i['at'] for i in sub) / len(sub):.2f}")
print("bodies lacking <X3D:", sum(1 for i in items if "<X3D" not in i["b"]), "| with </head>:", sum(1 for i in items if "</head>" in i["b"]),
      "| with </script (must escape):", sum(1 for i in items if "</script" in i["b"].lower()))
