"""Assemble the X_ITE subset that works as an artifact's own files (recipe verified 16 Oct 2026 in the Shroud thread):
x_ite.min.js, x_ite.css, LICENSE.md (MIT, must travel with copies), assets/components/*.min.js, assets/fonts/**, assets/lib/* minus libktx.wasm, assets/images, hatching, linetype.
Usage: python3 mkxite.py <node_modules/x_ite/dist> <out dir>   (prints the file count and size)"""
import os, shutil, sys
src, out = sys.argv[1:3]
keep = []
for root, _, files in os.walk(src):
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), src).replace(os.sep, "/")
        if rel in ("x_ite.min.js", "x_ite.css", "LICENSE.md") or \
           (rel.startswith("assets/components/") and rel.endswith(".min.js")) or \
           rel.startswith(("assets/fonts/", "assets/images/", "assets/hatching/", "assets/linetype/")) or \
           (rel.startswith("assets/lib/") and not rel.endswith("libktx.wasm")):
            keep.append(rel)
shutil.rmtree(out, ignore_errors=True)
for rel in sorted(keep):
    os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True); shutil.copyfile(os.path.join(src, rel), os.path.join(out, rel))
print(len(keep), "files,", round(sum(os.path.getsize(os.path.join(out, r)) for r in keep) / 1e6, 2), "MB ->", out)
