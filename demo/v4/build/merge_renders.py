"""Render parts for Tether Firehose 4 (SPEC section 8 step 2; drawn by S8 "first-light raster", S3 twin verdicts, S12 pass pills).
Reads the two offline X_ITE passes over every live attempt (demo/data/renders_live_x_ite_16.5.0.json, renders_live_x_ite_16.5.1.json) and the 16.5.1 pass over the replay
scenes (demo/data/renders3_x_ite_16.5.1.json). Keys are <model slug>/<prompt>_a<k>.x3d for live attempts and <model>/<mode>/<prompt>.x3d for replay scenes (the replay's own
16.5.0 series is already in replay.json). Writes two JSON files that carry NO thumbnail bytes:
  demo/v4/data/renders.series.json  {xite:"16.5.0", live:{key:{series[20], first, last, frames, nonblank}}}    the 16.5.0 watcher trace per live attempt
  demo/v4/data/renders.151.json     {xite:"16.5.1", live:{key:{nb, frames, first, last, err, series, unknown}}, replay:{key:{same}}}   the 16.5.1 pass; replay keys give r.nb151
nb is the page's measure: null if X_ITE threw, else the larger of the in-callback best frame and the 3.5 s screenshot (demo/build_live.py, build_replay.py). err is collapsed to
the page's fixed text, so no page URL or port leaves this script. Usage: python3 demo/v4/build/merge_renders.py"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
D = os.path.join(ROOT, "demo/data")
OUT_S, OUT_1 = os.path.join(ROOT, "demo/v4/data/renders.series.json"), os.path.join(ROOT, "demo/v4/data/renders.151.json")
PARSE_FAIL = "X_ITE could not parse this file"
r150 = json.load(open(D + "/renders_live_x_ite_16.5.0.json")); r151 = json.load(open(D + "/renders_live_x_ite_16.5.1.json")); p151 = json.load(open(D + "/renders3_x_ite_16.5.1.json"))
live = json.load(open(D + "/live.json")); replay = json.load(open(D + "/replay.json"))
slug = lambda m: m.replace("/", "_")
live_keys = [f"{slug(i['m'])}/{i['p']}_a{k}.x3d" for i in live["items"] for k in range(1, len(i["A"]) + 1)]
replay_keys = [i["k"] for i in replay]


def err_of(rd):
    e = rd.get("err")
    return (PARSE_FAIL if "parse X3D" in e else re.sub(r"https?://\S+", "<url>", e)[:120]) if e else None


def nb_of(rd):
    if rd.get("err"): return None
    seen = [v for v in (rd.get("nonblank"), rd.get("shot")) if v is not None]
    return max(seen) if seen else 0


series = {k: {"series": v.get("series"), "first": v.get("first"), "last": v.get("last"), "frames": v.get("frames"), "nonblank": v.get("nonblank")} for k, v in r150.items()}
pass151 = lambda src: {k: {"nb": nb_of(v), "frames": v.get("frames"), "first": v.get("first"), "last": v.get("last"), "err": err_of(v), "series": v.get("series"), "unknown": v.get("unknown", 0)} for k, v in src.items()}
out1 = {"xite": "16.5.1", "live": pass151(r151), "replay": pass151(p151)}
outs = {"xite": "16.5.0", "live": series}

# every attempt on the page and every replay scene has a row in both passes; the two live passes cover the same 383 files
assert set(r150) == set(r151) and all(k in r150 for k in live_keys), (len(r150), len(r151), [k for k in live_keys if k not in r150][:3])
assert all(k in p151 for k in replay_keys) and len(p151) == len(replay_keys), (len(p151), len(replay_keys))
for k in live_keys:        # the 16.5.0 series part must agree with what live.json already shows for the same attempt
    it = next(i for i in live["items"] if k.startswith(slug(i["m"]) + "/" + i["p"] + "_a")); a = it["A"][int(k.rsplit("_a", 1)[1][:-4]) - 1]
    assert a["r"]["frames"] == series[k]["frames"] and a["r"]["last"] == series[k]["last"], k

for path, obj in ((OUT_S, outs), (OUT_1, out1)):
    json.dump(obj, open(path, "w"), separators=(",", ":"))
    s = open(path).read()
    assert not re.search(r"[A-Za-z0-9+/]{200,}", s) and "/9j/" not in s, f"base64 image data in {path}"
    assert ":878" not in s and "http" not in s, f"a page URL leaked into {path}"
cls = lambda rec: "err" if rec["err"] else "draws" if (rec["nb"] or 0) >= 0.005 else "blank"
same_live = sum(1 for k in r150 if cls({"err": r150[k].get("err"), "nb": nb_of(r150[k])}) == cls(out1["live"][k]))
same_rep = sum(1 for i in replay if cls({"err": i["r"]["err"], "nb": i["r"]["nb"]}) == cls(out1["replay"][i["k"]]))     # replay.json already carries the page's nb
print(f"renders.series: {len(series)} live attempts (16.5.0) · renders.151: {len(out1['live'])} live + {len(out1['replay'])} replay (16.5.1); same draw/blank/err class as 16.5.0: live {same_live}/{len(r150)}, replay {same_rep}/{len(replay)}")
print(OUT_S, os.path.getsize(OUT_S), "B;", OUT_1, os.path.getsize(OUT_1), "B")
