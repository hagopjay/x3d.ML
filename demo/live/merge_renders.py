"""Merge the render files of the recorded live run (one per render pass; a key in a later file replaces the same key in an earlier one).
Usage: python3 merge_renders.py <out.json> <part1.json> [<part2.json> ...]"""
import json, sys
out, parts = sys.argv[1], sys.argv[2:]
m = {}
for p in parts:
    d = json.load(open(p)); m.update(d); print(p, len(d), "keys")
json.dump(m, open(out, "w"), separators=(",", ":"))
print(out, len(m), "keys")
