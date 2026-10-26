#!/usr/bin/env python3
"""Blender-for-X3D ecosystem watcher. Stdlib only, $0, deterministic.

Probes sources a cloud container can reach without credentials:
  * git ls-remote / shallow commit-only fetches of public GitHub repos
  * PyPI and npm JSON APIs
Compares against state.json, appends changes to LEDGER.md, prints a JSON
digest of what changed (empty "changes" list = nothing new).

Sources that only WebSearch/WebFetch can reach (projects.blender.org,
extensions.blender.org, web3d.org lists, Blender Lab MCP) are checked by the
routine's session itself and logged with `--note`.

Usage:
  python3 watch.py                 # probe, diff, update state + ledger, print digest
  python3 watch.py --dry-run       # probe and diff, write nothing
  python3 watch.py --note "text"   # append a manual/web finding to the ledger
"""
import argparse, datetime as dt, json, os, re, subprocess, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
LEDGER = os.path.join(HERE, "LEDGER.md")

# repo -> what to watch. "tags": newest tags matching regex; "heads": branch names matching regex;
# "log": commit subjects on the default branch matching regex since last run.
GIT = {
    "blender/blender": {"tags": r"^v[45]\.\d+\.\d+$", "heads": r"^blender-v\d+\.\d+-release$",
                        "log": r"(?i)gsplat|gaussian splat|point ?cloud type|\bUSD\b|glTF|\bPLY\b|\bSPZ\b|python ?api|pyapi|"
                               r"extensions?:|asset[- ]librar|geometry nodes: (add|new)|x3d|vrml"},
    "KhronosGroup/glTF-Blender-IO": {"log": r"(?i)splat|gauss|KHR_|point ?cloud|collection export"},
    "ahujasid/blender-mcp": {"log": r".*"},
    "create3000/x_ite": {"log": r"(?i)splat|gauss|physicalmaterial|environment|x3d ?4\.1|build version"},
    "Kiri-Innovation/3dgs-render-blender-addon": {"log": r".*"},
    "FishWoWater/trellis_blender": {"log": r".*"},
    "Tencent-Hunyuan/Hunyuan3D-2": {"log": r"(?i)blender|release|v\d"},
    "coderextreme/X3DJSONLD": {"log": r"(?i)blend|hanim|splat|gauss"},
    "Web3DConsortium/BlenderX3DSupport": {"log": r".*"},
}
PYPI = ["bpy", "x3d", "mcp-for-blender"]
NPM = ["x_ite", "@playcanvas/splat-transform", "@sparkjsdev/spark"]
MAX_LOG = 25


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)


def run(cmd, cwd=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def ls_remote(repo, kind, pattern):
    ref = "refs/tags/*" if kind == "tags" else "refs/heads/*"
    p = run(["git", "ls-remote", f"https://github.com/{repo}", ref], timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[:200])
    out = {}
    for line in p.stdout.splitlines():
        sha, name = line.split("\t")
        name = name.split("/", 2)[2]
        if name.endswith("^{}"):
            continue
        if re.search(pattern, name):
            out[name] = sha[:12]
    return out


def recent_log(repo, pattern, since, workdir):
    """Commit-only shallow fetch (no trees, no blobs) of the default branch since `since`."""
    d = os.path.join(workdir, repo.replace("/", "_"))
    p = run(["git", "clone", "-q", "--filter=tree:0", "--no-checkout", "--single-branch",
             f"--shallow-since={since}", f"https://github.com/{repo}", d], timeout=600)
    if p.returncode:
        if "shallow" in p.stderr or "no commits" in p.stderr.lower() or "not our ref" in p.stderr:
            return {"head": None, "matches": []}
        raise RuntimeError(p.stderr.strip()[:200])
    p = run(["git", "log", "--format=%H\t%cI\t%s"], cwd=d)
    lines = [l.split("\t", 2) for l in p.stdout.splitlines() if l.count("\t") >= 2]
    head = lines[0][0][:12] if lines else None
    hits = [{"sha": h[:12], "date": t[:10], "subject": s[:140]} for h, t, s in lines if re.search(pattern, s)]
    return {"head": head, "matches": hits}


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def pypi(name):
    d = fetch_json(f"https://pypi.org/pypi/{name}/json")
    v = d["info"]["version"]
    files = d["releases"].get(v) or [{}]
    return {"version": v, "date": (files[0].get("upload_time") or "")[:10]}


def npm(name):
    d = fetch_json(f"https://registry.npmjs.org/{name.replace('/', '%2F')}")
    v = d["dist-tags"]["latest"]
    return {"version": v, "date": d["time"].get(v, "")[:10]}


def probe(state):
    last = state.get("last_run")
    since = (dt.date.fromisoformat(last[:10]) - dt.timedelta(days=1)).isoformat() if last else \
        (now().date() - dt.timedelta(days=14)).isoformat()
    cur, errors, logs = {}, [], {}
    with tempfile.TemporaryDirectory() as work:
        for repo, spec in GIT.items():
            for kind in ("tags", "heads"):
                if kind in spec:
                    try:
                        cur[f"git:{repo}:{kind}"] = ls_remote(repo, kind, spec[kind])
                    except Exception as e:  # noqa: BLE001 - keep probing other sources
                        errors.append(f"{repo} {kind}: {e}")
            if "log" in spec:
                try:
                    r = recent_log(repo, spec["log"], since, work)
                    cur[f"git:{repo}:head"] = r["head"]
                    logs[repo] = r["matches"]
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{repo} log: {e}")
    for n in PYPI:
        try:
            cur[f"pypi:{n}"] = pypi(n)
        except Exception as e:  # noqa: BLE001
            errors.append(f"pypi {n}: {e}")
    for n in NPM:
        try:
            cur[f"npm:{n}"] = npm(n)
        except Exception as e:  # noqa: BLE001
            errors.append(f"npm {n}: {e}")
    return cur, logs, errors, since


def diff(prev, cur, logs, seen):
    changes = []
    for k, v in cur.items():
        old = prev.get(k)
        if old is None and k not in prev:
            changes.append({"key": k, "kind": "baseline", "new": v})
            continue
        if isinstance(v, dict) and k.endswith((":tags", ":heads")):
            added = sorted(set(v) - set(old or {}))
            if added:
                changes.append({"key": k, "kind": "new-refs", "new": added})
        elif k.endswith(":head"):
            if v and v != old:
                repo = k.split(":")[1]
                fresh = [m for m in logs.get(repo, []) if m["sha"] not in seen]
                changes.append({"key": k, "kind": "new-commits", "old": old, "new": v, "relevant": fresh[:MAX_LOG],
                                "relevant_total": len(fresh)})
        elif v != old:
            changes.append({"key": k, "kind": "version", "old": old, "new": v})
    return changes


def ledger_lines(ts, changes, errors):
    out = [f"\n## {ts.isoformat()}Z  ({len(changes)} change(s))\n"]
    for c in changes:
        k = c["key"]
        if c["kind"] == "baseline":
            val = c["new"]
            if isinstance(val, dict) and "version" in val:
                val = f"{val['version']} ({val['date']})"
            elif isinstance(val, dict):
                val = ", ".join(sorted(val)[-4:]) or "none"
            out.append(f"- baseline `{k}` = {val}")
        elif c["kind"] == "new-refs":
            out.append(f"- **new refs** `{k}`: {', '.join(c['new'])}")
        elif c["kind"] == "version":
            o, n = c["old"] or {}, c["new"]
            out.append(f"- **version** `{k}`: {o.get('version')} -> {n['version']} ({n['date']})")
        else:
            out.append(f"- **commits** `{k}` {c['old']} -> {c['new']}: {c['relevant_total']} relevant")
            for m in c["relevant"][:10]:
                out.append(f"  - {m['date']} `{m['sha'][:9]}` {m['subject']}")
    for e in errors:
        out.append(f"- probe error: {e}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note")
    a = ap.parse_args()
    ts = now()
    if a.note:
        with open(LEDGER, "a") as f:
            f.write(f"\n- {ts.isoformat()}Z note: {a.note}\n")
        print(json.dumps({"noted": a.note}))
        return
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    prev = state.get("values", {})
    seen = set(state.get("seen_commits", []))
    cur, logs, errors, since = probe(state)
    changes = diff(prev, cur, logs, seen)
    digest = {"run": ts.isoformat() + "Z", "since": since, "changes": changes, "errors": errors,
              "first_run": not prev}
    if not a.dry_run:
        for repo, ms in logs.items():
            seen.update(m["sha"] for m in ms)
        merged = dict(prev)
        merged.update({k: v for k, v in cur.items() if v is not None or k not in merged})
        json.dump({"last_run": ts.isoformat(), "values": merged, "seen_commits": sorted(seen)[-5000:]},
                  open(STATE, "w"), indent=1, sort_keys=True)
        if changes or errors:
            if not os.path.exists(LEDGER):
                open(LEDGER, "w").write("# Blender-for-X3D ecosystem ledger\n\nAppend-only. Written by watch.py "
                                        "(deterministic probes) and by the daily routine's web pass (`note:` lines).\n")
            with open(LEDGER, "a") as f:
                f.write("\n".join(ledger_lines(ts, changes, errors)) + "\n")
    json.dump(digest, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
