import sys, re, json
sys.path.insert(0, "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/x3dpkg")
import x3d.x3d as X
R = "/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/blender-io/repo/source/"
files = {k: open(R + v, encoding="utf-8").read() for k, v in {
    "import": "import_x3d.py", "emit40": "emit_x3d40.py", "export33": "export_x3d.py",
    "extract": "extract.py", "parse40": "parse_x3d40.py", "populate": "populate.py", "splat_native": "splat_native.py"}.items()}
names = []
for n in dir(X):
    o = getattr(X, n)
    if isinstance(o, type) and n[0].isupper() and not n.startswith("_") and not n.startswith("X3D") or n in ("X3D",):
        pass
# robust: nodes have NAME() classmethod
for n in dir(X):
    o = getattr(X, n)
    if isinstance(o, type) and hasattr(o, "NAME") and n[0].isupper():
        try:
            nm = o.NAME()
        except Exception:
            continue
        if isinstance(nm, str) and nm == n:
            names.append(n)
names = sorted(set(names))
print(len(names), "node classes in x3d package")
def has(src, n):
    return bool(re.search(r'''["'<]%s["' >/]''' % re.escape(n), src))
rows = {}
for n in names:
    rows[n] = {k: has(v, n) for k, v in files.items()}
json.dump(rows, open("node_coverage.json", "w"), indent=0)
print("import-referenced:", sorted(n for n in names if rows[n]["import"]))
print("emit40-referenced:", sorted(n for n in names if rows[n]["emit40"]))
print("export33-referenced:", sorted(n for n in names if rows[n]["export33"]))
print("parse40-referenced:", sorted(n for n in names if rows[n]["parse40"]))
